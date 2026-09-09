"""Degrade-tolerant parallel search engine.

Queries every configured source concurrently with a hard wall-clock budget
per source, applies a per-source circuit breaker (one failing source never
sinks the batch), then merges, scores and orders the results.

Design rules enforced here:
- every source gets at most ``SOURCE_TIMEOUT_SECONDS`` total;
- ``SourceError`` (and any unexpected crash) marks the source as failed and
  the engine keeps going — no retries beyond what adapters do internally;
- results are scored via ``Hit.compute_score`` and sorted by score, with a
  stable tie-break on registry order.
"""
from __future__ import annotations

import concurrent.futures
import logging
from typing import Sequence

from .model import Hit, Source, SourceError

__all__ = ["SOURCE_TIMEOUT_SECONDS", "search_all"]

LOGGER = logging.getLogger("bookscout.fallback")

#: Hard cap on total wall-clock time per source (seconds).
SOURCE_TIMEOUT_SECONDS = 30.0


def search_all(
    title: str,
    author: str = "",
    language: str = "auto",
    sources: Sequence[Source] = (),
) -> tuple[list[Hit], list[str]]:
    """Search all sources in parallel.

    Args:
        title: Query title (required, non-blank).
        author: Optional author hint, forwarded to sources.
        language: ``"zh"``, ``"en"`` or ``"auto"``; forwarded as-is.
        sources: Source instances to query (e.g. registry + custom sources).

    Returns:
        Tuple ``(hits, failed_sources)`` where ``hits`` is the merged,
        scored, ordered result list and ``failed_sources`` is a list of
        *display labels* of sources that failed or timed out (used to tell
        the user "some sources are temporarily unavailable").
    """
    if not title or not title.strip():
        return [], []

    active = list(sources)
    if not active:
        return [], []

    hits: list[Hit] = []
    failed: list[str] = []

    pool = concurrent.futures.ThreadPoolExecutor(
        max_workers=max(1, len(active)), thread_name_prefix="bookscout"
    )
    try:
        future_map = {
            pool.submit(src.search, title, author, language): src for src in active
        }
        done, pending = concurrent.futures.wait(
            set(future_map), timeout=SOURCE_TIMEOUT_SECONDS
        )
        # Sources that did not answer within the budget: mark as failed
        # and drop their futures without waiting for their threads.
        for fut in pending:
            src = future_map[fut]
            LOGGER.warning("source %s timed out after %.0fs", src.id, SOURCE_TIMEOUT_SECONDS)
            failed.append(src.label)
            fut.cancel()
        for fut in done:
            src = future_map[fut]
            try:
                result = fut.result()
            except SourceError as exc:
                LOGGER.warning("source %s failed: %s", src.id, exc)
                failed.append(src.label)
                continue
            except Exception as exc:  # noqa: BLE001 — source-level circuit breaker
                LOGGER.warning("source %s crashed unexpectedly: %r", src.id, exc)
                failed.append(src.label)
                continue
            for hit in result or []:
                hit.score = hit.compute_score(title, author)
            hits.extend(result or [])
    finally:
        # Do not block on stragglers; their results are simply discarded.
        pool.shutdown(wait=False, cancel_futures=True)

    hits.sort(key=lambda h: _sort_key(h, active))
    return hits, failed


def _sort_key(hit: Hit, active: Sequence[Source]) -> tuple[float, int, str]:
    """Score descending; ties broken by registry order, then source id."""
    order = {src.id: i for i, src in enumerate(active)}
    return (-hit.score, order.get(hit.source, len(order)), hit.source)
