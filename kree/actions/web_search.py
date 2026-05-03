# actions/web_search.py
# MARK XXV — Web Search
# Primary: Gemini google_search
# Fallback: DuckDuckGo (ddgs)

from __future__ import annotations

import json
import os
import sys
import time
import warnings
from pathlib import Path
from typing import Any

from core import vault


from kree._paths import PROJECT_ROOT
BASE_DIR = PROJECT_ROOT
API_CONFIG_PATH = BASE_DIR / "config" / "api_keys.json"
_CACHE_TTL_SEC = 180.0
_SEARCH_CACHE: dict[tuple[str, str], tuple[float, str]] = {}


def _get_api_key() -> str:
    env_key = os.environ.get("GEMINI_API_KEY", "").strip()
    if env_key:
        return env_key

    api_key = vault.load_api_key(API_CONFIG_PATH).strip()
    if api_key:
        return api_key

    try:
        with open(API_CONFIG_PATH, "r", encoding="utf-8") as file_handle:
            data = json.load(file_handle)
    except (FileNotFoundError, json.JSONDecodeError) as exc:
        raise RuntimeError(f"Gemini API key not available: {exc}") from exc

    api_key = str(data.get("gemini_api_key", "") or data.get("google_api_key", "")).strip()
    if not api_key:
        raise RuntimeError("Gemini API key missing from config/api_keys.json and GEMINI_API_KEY is not set.")
    return api_key


def _is_current_events_query(query: str) -> bool:
    lowered = query.lower()
    markers = (
        "news",
        "latest",
        "current",
        "today",
        "now",
        "world",
        "breaking",
        "headline",
        "headlines",
        "happening",
        "update",
        "updates",
    )
    return any(marker in lowered for marker in markers)


def _expanded_queries(query: str) -> list[str]:
    cleaned = query.strip()
    if not cleaned:
        return []

    queries = [cleaned]
    if _is_current_events_query(cleaned):
        expanded = f"{cleaned} latest news today current events"
        if expanded not in queries:
            queries.insert(0, expanded)
    return queries


def _extract_response_text(response: Any) -> str:
    text = getattr(response, "text", "")
    if isinstance(text, str) and text.strip():
        return text.strip()

    candidates = getattr(response, "candidates", None) or []
    parts: list[str] = []
    for candidate in candidates:
        content = getattr(candidate, "content", None)
        candidate_parts = getattr(content, "parts", None) or []
        for part in candidate_parts:
            part_text = getattr(part, "text", "")
            if part_text:
                parts.append(part_text)

    text = "".join(parts).strip()
    if not text:
        raise ValueError("Empty Gemini response")
    return text


def _gemini_search(query: str) -> str:
    from google import genai

    client = genai.Client(api_key=_get_api_key())
    response = client.models.generate_content(
        model="gemini-2.5-flash-lite",
        contents=query,
        config={"tools": [{"google_search": {}}]},
    )
    return _extract_response_text(response)


def _ddg_search(query: str, max_results: int = 6, prefer_news: bool = False) -> list[dict[str, str]]:
    warnings.filterwarnings(
        "ignore",
        message="This package (`duckduckgo_search`) has been renamed to `ddgs`! Use `pip install ddgs` instead.",
    )
    try:
        from ddgs import DDGS
    except ImportError:
        from duckduckgo_search import DDGS

    results: list[dict[str, str]] = []
    with DDGS() as ddgs:
        search_iter = None
        if prefer_news and hasattr(ddgs, "news"):
            try:
                search_iter = ddgs.news(query, max_results=max_results)
            except Exception:
                search_iter = None

        if search_iter is None:
            search_iter = ddgs.text(query, max_results=max_results)

        for item in search_iter:
            results.append(
                {
                    "title": str(item.get("title", "")),
                    "snippet": str(item.get("body", item.get("snippet", ""))),
                    "url": str(item.get("href", item.get("url", ""))),
                }
            )

    return results


def _format_ddg(query: str, results: list[dict[str, str]], headline: str | None = None) -> str:
    if not results:
        return f"No results found for: {query}"

    lines = [headline or f"Search results for: {query}", ""]
    for index, result in enumerate(results, 1):
        title = result.get("title", "").strip()
        snippet = result.get("snippet", "").strip()
        url = result.get("url", "").strip()
        if title:
            lines.append(f"{index}. {title}")
        if snippet:
            lines.append(f"   {snippet}")
        if url:
            lines.append(f"   {url}")
        lines.append("")
    return "\n".join(lines).strip()


def _compare(items: list, aspect: str) -> str:
    query = f"Compare {', '.join(items)} in terms of {aspect}. Give specific facts and data."
    try:
        return _gemini_search(query)
    except Exception as exc:
        print(f"[WebSearch] ⚠️ Gemini compare failed: {exc}")
        all_results = {}
        for item in items:
            try:
                all_results[item] = _ddg_search(f"{item} {aspect}", max_results=3)
            except Exception:
                all_results[item] = []

        lines = [f"Comparison - {aspect.upper()}\n{'-' * 40}"]
        for item in items:
            lines.append(f"\n- {item}")
            for result in all_results.get(item, [])[:2]:
                snippet = result.get("snippet", "").strip()
                if snippet:
                    lines.append(f"  * {snippet}")
        return "\n".join(lines)


def _cache_lookup(cache_key: tuple[str, str]) -> str | None:
    cached = _SEARCH_CACHE.get(cache_key)
    if not cached:
        return None
    timestamp, text = cached
    if (time.time() - timestamp) > _CACHE_TTL_SEC:
        _SEARCH_CACHE.pop(cache_key, None)
        return None
    return text


def _cache_store(cache_key: tuple[str, str], text: str) -> None:
    _SEARCH_CACHE[cache_key] = (time.time(), text)


def web_search(
    parameters: dict,
    response=None,
    player=None,
    session_memory=None,
) -> str:
    params = parameters or {}
    query = str(params.get("query", "")).strip()
    mode = str(params.get("mode", "search")).lower()
    items = params.get("items", []) or []
    aspect = str(params.get("aspect", "general"))

    if not query and not items:
        return "Please provide a search query, sir."

    if items and mode != "compare":
        mode = "compare"

    cache_key = (mode, query or "|".join(map(str, items)) + f"::{aspect}")
    cached = _cache_lookup(cache_key)
    if cached:
        print(f"[WebSearch] Cache hit for {cache_key[1]!r}")
        return cached

    if player:
        player.write_log(f"[Search] {query or ', '.join(map(str, items))}")

    print(f"[WebSearch] Query: {query!r} Mode: {mode}")

    try:
        if mode == "compare" and items:
            print(f"[WebSearch] Comparing: {items}")
            result = _compare(list(items), aspect)
            print("[WebSearch] Compare done.")
            _cache_store(cache_key, result)
            return result

        search_queries = _expanded_queries(query)
        prefer_news = _is_current_events_query(query)

        last_error: Exception | None = None
        for search_query in search_queries:
            print(f"[WebSearch] Gemini search: {search_query!r}")
            try:
                result = _gemini_search(search_query)
                print("[WebSearch] Gemini OK.")
                _cache_store(cache_key, result)
                return result
            except Exception as exc:
                last_error = exc
                print(f"[WebSearch] Gemini failed ({exc}), trying DDG...")

        for search_query in search_queries:
            try:
                results = _ddg_search(search_query, prefer_news=prefer_news)
                if results:
                    headline = f"Latest results for: {query}" if prefer_news else f"Search results for: {query}"
                    result = _format_ddg(query, results, headline=headline)
                    print(f"[WebSearch] DDG: {len(results)} results.")
                    _cache_store(cache_key, result)
                    return result
            except Exception as exc:
                last_error = exc
                print(f"[WebSearch] DDG failed for {search_query!r}: {exc}")

        if last_error is not None:
            return f"Search failed, sir: {last_error}"
        return f"No results found for: {query}"

    except Exception as exc:
        print(f"[WebSearch] Failed: {exc}")
        return f"Search failed, sir: {exc}"