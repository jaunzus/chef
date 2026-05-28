"""
大厨技能 - 菜谱数据管道
管理网络菜谱搜索 → 本地缓存 → 菜谱库 的完整数据流。

管道架构:
  WebSearch (下厨房/豆果/小红书)
       ↓
  data/recipe_cache.json  (搜索结果缓存，TTL=7天)
       ↓
  推荐引擎 (SOP Step 1-6)
       ↓
  data/recipes.json  (用户确认保存的菜谱库)
"""

import json
import os
import tempfile
import uuid
from datetime import datetime, timedelta

DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
CACHE_FILE = os.path.join(DATA_DIR, "recipe_cache.json")


def _load_json(path: str) -> dict:
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def _save_json(path: str, data: dict) -> None:
    """Atomic write — 先写临时文件再 os.replace"""
    os.makedirs(os.path.dirname(path), exist_ok=True)
    fd, tmp_path = tempfile.mkstemp(suffix=".tmp", dir=DATA_DIR)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        os.replace(tmp_path, path)
    except Exception:
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)
        raise


def get_cache() -> dict:
    """获取搜索缓存"""
    return _load_json(CACHE_FILE).get("entries", {})


def cache_get(query: str) -> dict | None:
    """查询缓存，过期(>7天)的自动失效"""
    cache = _load_json(CACHE_FILE)
    entries = cache.get("entries", {})
    if query in entries:
        entry = entries[query]
        cached_at = datetime.fromisoformat(entry["cached_at"])
        if datetime.now() - cached_at < timedelta(days=7):
            return entry["results"]
    return None


def cache_put(query: str, results: list, source_channels: list) -> None:
    """缓存搜索结果，标注来源渠道"""
    cache = _load_json(CACHE_FILE)
    if "entries" not in cache:
        cache["entries"] = {}
    cache["entries"][query] = {
        "cached_at": datetime.now().isoformat(),
        "source_channels": source_channels,
        "results": results
    }
    _save_json(CACHE_FILE, cache)


def cache_clear_expired() -> int:
    """清理过期缓存，返回清理条数"""
    cache = _load_json(CACHE_FILE)
    entries = cache.get("entries", {})
    expired = []
    for q, entry in entries.items():
        cached_at = datetime.fromisoformat(entry["cached_at"])
        if datetime.now() - cached_at >= timedelta(days=7):
            expired.append(q)
    for q in expired:
        del entries[q]
    cache["entries"] = entries
    _save_json(CACHE_FILE, cache)
    return len(expired)


def merge_results(channel_results: dict) -> list:
    """
    合并多渠道搜索结果，去重并按共识度排序。
    channel_results: {"下厨房": [result1, ...], "豆果": [...], "小红书": [...]}
    返回: 合并排序后的结果列表，每个结果带 consensus_score
    """
    # 按菜品名聚合
    dish_map = {}  # name -> {channels: set, details: ...}
    for channel, results in channel_results.items():
        for r in results:
            name = r.get("name", r.get("title", ""))
            if not name:
                continue
            if name not in dish_map:
                dish_map[name] = {"channels": set(), "details": []}
            dish_map[name]["channels"].add(channel)
            dish_map[name]["details"].append(r)

    merged = []
    for name, info in dish_map.items():
        merged.append({
            "name": name,
            "consensus_score": len(info["channels"]),  # 出现在几个渠道
            "channels": list(info["channels"]),
            "details": info["details"]
        })

    # 按共识度排序：三个渠道都有的排最前
    merged.sort(key=lambda x: -x["consensus_score"])
    return merged


# ── 菜谱搜索搜索模板 ──

SEARCH_TEMPLATES = {
    "下厨房": "site:xiachufang.com {ingredient} {style} 做法",
    "豆果": "site:douguo.com {ingredient} {style} 怎么做好吃",
    "小红书": "site:xiaohongshu.com {ingredient} {style} 食谱",
}

SPECIAL_SCENARIOS = {
    "一人食": "site:xiaohongshu.com 一人食 {ingredient} 简单 食谱",
    "减脂": "site:xiaohongshu.com 减脂餐 {ingredient} 低卡 食谱",
    "一锅出": "site:xiaohongshu.com 一锅出 {ingredient} 食谱",
}


def build_search_queries(ingredient: str, style: str = "",
                         scenario: str = "") -> dict:
    """
    根据食材和场景生成多渠道搜索词。
    返回 {"下厨房": "query_string", "豆果": "...", "小红书": "..."}
    """
    queries = {}
    for channel, template in SEARCH_TEMPLATES.items():
        q = template.format(ingredient=ingredient, style=style)
        queries[channel] = q

    # 特殊场景追加小红书专属搜索词
    if scenario in SPECIAL_SCENARIOS:
        queries[f"小红书_{scenario}"] = SPECIAL_SCENARIOS[scenario].format(
            ingredient=ingredient)

    return queries


def search_pipeline(ingredient: str, style: str = "",
                    scenario: str = "") -> dict:
    """
    完整搜索管道：
    1. 先查缓存
    2. 缓存未命中则生成搜索词
    3. 返回需要执行搜索的 query 列表

    返回: {"cached": [...], "need_search": {"channel": "query", ...}}
    """
    # 拼缓存 key
    cache_key = f"{ingredient}|{style}|{scenario}"
    cached = cache_get(cache_key)

    if cached:
        return {"cached": cached, "need_search": {}}

    queries = build_search_queries(ingredient, style, scenario)
    return {"cached": [], "need_search": queries}
