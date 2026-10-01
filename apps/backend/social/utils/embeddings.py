# utils/embeddings.py
from typing import List

import numpy as np


def embed_texts(texts: List[str]) -> List[List[float]]:
    """
    Replace this with real embedding calls.
    Must return list of lists (floats) of length dim.
    """
    # Placeholder: raise if not configured so you don't accidentally use randoms.
    raise NotImplementedError("Hook up embed_texts to your embedding provider (OpenAI / HF / ST).")

def normalize(vec):
    arr = np.array(vec, dtype=float)
    norm = np.linalg.norm(arr) or 1.0
    return (arr / norm).tolist()


def embed_video(video: 'VideoContent') -> List[float]:
    # Compose meaningful text: title + description + hashtags + maybe audio tags
    text = " ".join(filter(None, [
        video.title or "",
        video.description or "",
        " ".join(video.hashtags or []),
    ]))
    return embed_texts([text])[0]
