def reciprocal_rank_fusion(
    rankings: list[list[dict]], limit: int, k: int = 60
) -> list[dict]:
    """Merge several ranked hit lists (each hit has a unique ``chunk_id``).

    Score = sum over lists of 1 / (k + rank). Hits that appear in several lists
    (e.g. both vector and keyword search) float to the top.
    """
    scores: dict[int, float] = {}
    items: dict[int, dict] = {}
    for ranking in rankings:
        for rank, hit in enumerate(ranking):
            cid = hit["chunk_id"]
            scores[cid] = scores.get(cid, 0.0) + 1.0 / (k + rank + 1)
            items.setdefault(cid, hit)
    ordered = sorted(items, key=lambda cid: scores[cid], reverse=True)
    return [{**items[cid], "rrf": scores[cid]} for cid in ordered[:limit]]
