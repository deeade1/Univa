# apps/backend/biometrics/processing/face.py

"""
Canonical face-processing implementation.

This module is the only place in the biometrics domain that owns
InsightFace / ArcFace model initialization and face detection.

Architecture:

    GraphQL / Service
          |
          v
    ArcFaceModel
          |
          v
    InsightFace
          |
          v
    embedding + detection metadata
"""

from __future__ import annotations

import os
from threading import Lock

import cv2
from django.conf import settings
from graphql import GraphQLError
from insightface.app import FaceAnalysis


MODEL_NAME = "buffalo_l"

MODEL_DIR = os.path.join(
    settings.BASE_DIR,
    "assets",
    "insightface",
    MODEL_NAME,
)


class ArcFaceModel:
    """
    Singleton-style InsightFace processor.

    The model is initialized lazily rather than at module import time.

    This is important because importing the biometrics application should
    not immediately initialize a large ML model.
    """

    _app = None
    _lock = Lock()

    @classmethod
    def get_app(cls, use_gpu: bool = False):
        """
        Return the initialized InsightFace application.

        The model is initialized once per Django process.
        """

        if cls._app is not None:
            return cls._app

        with cls._lock:
            if cls._app is not None:
                return cls._app

            providers = ["CPUExecutionProvider"]

            # GPU support can be enabled later without changing callers.
            if use_gpu:
                providers = [
                    "CUDAExecutionProvider",
                    "CPUExecutionProvider",
                ]

            cls._app = FaceAnalysis(
                name=MODEL_NAME,
                root=MODEL_DIR,
                providers=providers,
            )

            cls._app.prepare(
                ctx_id=0 if use_gpu else -1,
                det_size=(640, 640),
            )

        return cls._app

    @classmethod
    def detect_faces(
        cls,
        image_path: str,
        *,
        use_gpu: bool = False,
    ):
        """
        Detect faces in an image.

        Returns the complete InsightFace face list.

        Authentication/enrollment services decide whether one or multiple
        faces are acceptable.
        """

        app = cls.get_app(use_gpu=use_gpu)

        image = cv2.imread(image_path)

        if image is None:
            raise GraphQLError(
                "Invalid or unreadable image file."
            )

        faces = app.get(image)

        return faces

    @classmethod
    def get_embedding_and_detection(
        cls,
        image_path: str,
        *,
        use_gpu: bool = False,
    ):
        """
        Extract exactly one face embedding.

        Authentication and enrollment require exactly one detectable face.

        Returns:

            (
                embedding,
                detection_metadata,
            )
        """

        faces = cls.detect_faces(
            image_path,
            use_gpu=use_gpu,
        )

        if not faces:
            raise GraphQLError(
                "No face detected."
            )

        if len(faces) > 1:
            raise GraphQLError(
                "Image must contain exactly one face."
            )

        face = faces[0]

        if face.embedding is None:
            raise GraphQLError(
                "Unable to generate face embedding."
            )

        embedding = (
            face.embedding
            .astype("float32")
            .tolist()
        )

        if len(embedding) != 512:
            raise GraphQLError(
                "Invalid face embedding dimensions."
            )

        bbox = getattr(
            face,
            "bbox",
            None,
        )

        detection = {
            "bbox": (
                [int(value) for value in bbox.tolist()]
                if bbox is not None
                else None
            ),
            "confidence": float(
                getattr(
                    face,
                    "det_score",
                    0.0,
                )
            ),
        }

        return embedding, detection