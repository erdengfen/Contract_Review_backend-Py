"""
检索结果融合模块。
"""
from __future__ import annotations

from typing import Iterable

from app.rag.schemas import RetrievalHit


def reciprocal_rank_fusion(
    ranked_lists: list[list[RetrievalHit]],
    *,
    weights: list[float] | None = None,
    rrf_k: int = 60,
) -> list[RetrievalHit]:
    """
    对多路排序结果执行加权 RRF 融合。
    """
    if not ranked_lists:
        return []

    scores: dict[tuple[str, str], float] = {}
    hit_map: dict[tuple[str, str], RetrievalHit] = {}
    resolved_weights = weights or [1.0] * len(ranked_lists)

    for route_idx, hits in enumerate(ranked_lists):
        weight = resolved_weights[route_idx] if route_idx < len(resolved_weights) else 1.0
        for rank, hit in enumerate(hits, start=1):
            key = (hit.source_collection, hit.record_id)
            scores[key] = scores.get(key, 0.0) + weight / (rrf_k + rank)
            hit_map[key] = hit

    fused: list[RetrievalHit] = []
    for key, score in sorted(scores.items(), key=lambda item: item[1], reverse=True):
        base_hit = hit_map[key]
        fused.append(base_hit.model_copy(update={"score": score}))
    return fused


def take_top_k(hits: Iterable[RetrievalHit], top_k: int) -> list[RetrievalHit]:
    return list(hits)[:top_k]


def _main_test_hybrid_fusion():
    hit_a_dense = RetrievalHit(
        source_collection="external_legal_kb",
        record_id="law-1",
        title="民法典",
        content="当事人应全面履行义务。",
        score=0.9,
    )
    hit_b_dense = RetrievalHit(
        source_collection="external_legal_kb",
        record_id="law-2",
        title="招标投标法",
        content="投标活动应公平公正。",
        score=0.8,
    )
    hit_a_sparse = RetrievalHit(
        source_collection="external_legal_kb",
        record_id="law-1",
        title="民法典",
        content="当事人应全面履行义务。",
        score=0.7,
    )
    fused = reciprocal_rank_fusion(
        [[hit_a_dense, hit_b_dense], [hit_a_sparse]],
        weights=[1.0, 1.0],
    )
    assert fused[0].record_id == "law-1"
    assert len(fused) == 2
    print("hybrid_fusion self test passed")


if __name__ == "__main__":
    _main_test_hybrid_fusion()
