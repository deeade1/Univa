"""
Batch dispatch optimizer.

`AIDispatchOptimizer` produces 1:1 request → provider assignments across
a batch. It reuses `AIService` for per-request provider scoring, then
greedily pairs the highest-scoring combinations without reusing a
provider.
"""

import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class DispatchAssignment:
    request_id: int
    provider_id: int
    match_score: float
    estimated_eta: float  # minutes


class AIDispatchOptimizer:
    """Greedy batch matcher with AI scoring."""

    def __init__(self):
        self.initialization_successful = False
        self._ai_service = None
        try:
            from .ai_service import AIService
            self._ai_service = AIService()
            self._ai_service.initialize()
            self.initialization_successful = True
        except Exception as exc:
            logger.warning("AIDispatchOptimizer init failed: %s", exc)
            self.initialization_successful = False

    async def optimize_dispatch_batch(
        self,
        requests: List,
        providers: List,
        context: Optional[Dict[str, Any]] = None,
    ) -> List[DispatchAssignment]:
        """Return a list of assignments for the batch."""
        if not requests or not providers:
            return []

        # Compute score matrix
        triples = []  # (score, request_idx, provider_idx)
        for r_idx, request in enumerate(requests):
            for p_idx, provider in enumerate(providers):
                score = self._score(request, provider, context)
                triples.append((score, r_idx, p_idx))

        # Greedy highest-score assignment, no provider reuse.
        triples.sort(key=lambda t: t[0], reverse=True)
        used_requests = set()
        used_providers = set()
        assignments: List[DispatchAssignment] = []

        for score, r_idx, p_idx in triples:
            if r_idx in used_requests or p_idx in used_providers:
                continue
            used_requests.add(r_idx)
            used_providers.add(p_idx)
            assignments.append(
                DispatchAssignment(
                    request_id=getattr(requests[r_idx], "id", r_idx),
                    provider_id=getattr(providers[p_idx], "id", p_idx),
                    match_score=float(score),
                    estimated_eta=self._estimate_eta(
                        providers[p_idx], requests[r_idx]
                    ),
                )
            )

        return assignments

    # ------------------------------------------------------------------

    def _score(self, request, provider, context) -> float:
        if self._ai_service is None:
            return self._fallback_score(request, provider)
        try:
            return self._ai_service._score_provider(provider, request)
        except Exception:
            return self._fallback_score(request, provider)

    @staticmethod
    def _fallback_score(request, provider) -> float:
        """Rating × proximity heuristic when ML is unavailable."""
        rating = float(getattr(provider, "rating", 0) or 0)
        try:
            distance = provider.distance_to(request.pickup_location)
        except Exception:
            distance = None
        proximity = max(0.0, 5 - (distance / 10)) if distance is not None else 0.0
        return rating + proximity

    @staticmethod
    def _estimate_eta(provider, request) -> float:
        try:
            distance = provider.distance_to(request.pickup_location)
        except Exception:
            distance = None
        if distance is None:
            return 15.0
        # Assume 30 km/h average
        return max(1.0, (distance / 30) * 60)