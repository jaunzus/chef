"""
大厨技能 - API 兼容层
提供统一的 JSON 读写接口，任何外部系统（Shell 脚本/定时任务/其他 Skill）
都可以通过读写 data/ 目录下的 JSON 文件与大厨互通数据。

设计原则：
- 所有接口都是纯函数，无状态，只操作文件
- 输出格式稳定，字段名和结构不变
- 支持 CLI 模式和 Python import 模式双调用
"""

import json
import os
import sys
import uuid
import tempfile
from datetime import datetime
from typing import Any, Optional

DATA_DIR = os.path.join(os.path.dirname(__file__), "data")


def _gen_id(prefix: str = "") -> str:
    """生成唯一 ID（uuid hex 前8位 + 可选前缀）"""
    return f"{prefix}{uuid.uuid4().hex[:8]}"


def _load(filename: str) -> dict:
    path = os.path.join(DATA_DIR, filename)
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def _save(filename: str, data: dict) -> None:
    """
    Atomic write: 先写临时文件，成功后再 os.replace 到正式文件。
    防止写一半 crash 导致原数据损坏。
    """
    data["last_updated"] = datetime.now().strftime("%Y-%m-%d %H:%M")
    path = os.path.join(DATA_DIR, filename)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    # 写临时文件
    fd, tmp_path = tempfile.mkstemp(suffix=".tmp", dir=DATA_DIR)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        # 原子替换
        os.replace(tmp_path, path)
    except Exception:
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)
        raise


# ── 食材库存接口 ──

def inventory_list(category: str = None) -> list:
    """列出食材。可选按分类过滤"""
    data = _load("inventory.json")
    items = data.get("items", [])
    if category:
        items = [i for i in items if i.get("category") == category]
    return items


def inventory_add(name: str, category: str, quantity: float = 1,
                  unit: str = "份", notes: str = "", expiry_date: str = "") -> str:
    """添加食材到库存，返回新增食材 ID"""
    data = _load("inventory.json")
    items = data.get("items", [])
    new_id = _gen_id("inv_")
    items.append({
        "id": new_id, "name": name, "category": category,
        "quantity": quantity, "unit": unit,
        "purchase_date": datetime.now().strftime("%Y-%m-%d"),
        "expiry_date": expiry_date, "notes": notes
    })
    data["items"] = items
    _save("inventory.json", data)
    return new_id


def inventory_remove(name: str) -> bool:
    """从库存删除食材（用户明确说用完才调用）"""
    data = _load("inventory.json")
    items = data.get("items", [])
    before = len(items)
    data["items"] = [i for i in items if i["name"] != name]
    if len(data["items"]) < before:
        _save("inventory.json", data)
        return True
    return False


def inventory_update_note(name: str, note: str) -> bool:
    """更新食材备注（如：已用一部分）"""
    data = _load("inventory.json")
    for item in data.get("items", []):
        if item["name"] == name:
            item["notes"] = note
            _save("inventory.json", data)
            return True
    return False


# ── 菜谱库接口 ──

def recipe_list(category: str = None, cuisine: str = None) -> list:
    """列出菜谱，可选按分类/菜系过滤"""
    data = _load("recipes.json")
    recipes = data.get("recipes", [])
    if category:
        recipes = [r for r in recipes if r.get("category") == category]
    if cuisine:
        recipes = [r for r in recipes if r.get("cuisine") == cuisine]
    return recipes


def recipe_add(name: str, ingredients: list, seasonings: list,
               steps: list, **kwargs) -> str:
    """添加菜谱到菜谱库"""
    data = _load("recipes.json")
    recipes = data.get("recipes", [])
    rid = _gen_id("rec_")
    recipe = {
        "id": rid, "name": name,
        "category": kwargs.get("category", "家常菜"),
        "cuisine": kwargs.get("cuisine", "中式家常"),
        "cooking_time": kwargs.get("cooking_time", 20),
        "difficulty": kwargs.get("difficulty", "简单"),
        "servings": kwargs.get("servings", 2),
        "scene": kwargs.get("scene", ["家庭日常"]),
        "ingredients": ingredients,
        "seasonings": seasonings,
        "steps": steps,
        "nutrition": kwargs.get("nutrition", {}),
        "tags": kwargs.get("tags", []),
        "notes": kwargs.get("notes", ""),
        "source": kwargs.get("source", "API导入"),
        "rating": kwargs.get("rating", 0),
        "cook_count": 0,
        "created_date": datetime.now().strftime("%Y-%m-%d"),
        "last_cooked": None
    }
    recipes.append(recipe)
    data["recipes"] = recipes
    _save("recipes.json", data)
    return rid


# ── 饮食记录接口 ──

def meal_log(date: str, meal_type: str, dishes: list,
             notes: str = "") -> str:
    """记录一餐"""
    data = _load("meal_log.json")
    records = data.get("records", [])
    mid = _gen_id("meal_")
    record = {
        "id": mid, "date": date, "meal_type": meal_type,
        "dishes": dishes,
        "total_calories": sum(d.get("calories", 0) for d in dishes),
        "notes": notes
    }
    records.append(record)
    data["records"] = records
    _save("meal_log.json", data)
    return mid


def meal_query(start_date: str = None, end_date: str = None) -> list:
    """查询饮食记录，可选日期范围"""
    data = _load("meal_log.json")
    records = data.get("records", [])
    if not start_date and not end_date:
        return records
    return [r for r in records
            if (not start_date or r["date"] >= start_date)
            and (not end_date or r["date"] <= end_date)]


def meal_stats(start_date: str, end_date: str) -> dict:
    """统计一段时间内的饮食数据"""
    records = meal_query(start_date, end_date)
    dates = sorted(set(r["date"] for r in records))
    daily_cal = {}
    dish_freq = {}
    for r in records:
        daily_cal[r["date"]] = daily_cal.get(r["date"], 0) + r.get("total_calories", 0)
        for d in r.get("dishes", []):
            name = d["name"]
            dish_freq[name] = dish_freq.get(name, 0) + d.get("portions", 1)

    return {
        "start_date": start_date,
        "end_date": end_date,
        "total_days": len(dates),
        "daily_calories": daily_cal,
        "avg_calories": sum(daily_cal.values()) / len(daily_cal) if daily_cal else 0,
        "dish_frequency": dish_freq,
        "total_records": len(records)
    }


# ── 购物清单接口 ──

def shopping_add(name: str, category: str, quantity: float = 1,
                 unit: str = "份", priority: str = "必须",
                 source: str = "手动添加") -> str:
    """添加购物项"""
    data = _load("shopping_list.json")
    items = data.get("items", [])
    sid = _gen_id("shop_")
    items.append({
        "id": sid, "name": name, "category": category,
        "quantity": quantity, "unit": unit,
        "priority": priority, "source": source, "purchased": False
    })
    data["items"] = items
    _save("shopping_list.json", data)
    return sid


def shopping_checkout() -> list:
    """一键结算：已购项转入库存，返回转入的食材列表"""
    data = _load("shopping_list.json")
    purchased = [i for i in data.get("items", []) if i.get("purchased")]
    data["items"] = [i for i in data.get("items", []) if not i.get("purchased")]
    _save("shopping_list.json", data)

    transferred = []
    for item in purchased:
        inv_id = inventory_add(item["name"], item["category"],
                               item["quantity"], item["unit"],
                               f"购物清单转入: {item.get('source', '')}")
        transferred.append({"name": item["name"], "inv_id": inv_id})
    return transferred


# ── 数据导出接口 ──

def export_meal_csv(start_date: str, end_date: str, output_path: str) -> str:
    """导出饮食记录为 CSV"""
    records = meal_query(start_date, end_date)
    csv_lines = ["日期,餐次,菜品,份数,热量(kcal),备注"]
    for r in records:
        dishes_str = "; ".join(f"{d['name']}x{d.get('portions', 1)}" for d in r.get("dishes", []))
        csv_lines.append(
            f"{r['date']},{r['meal_type']},{dishes_str},"
            f"{sum(d.get('portions', 1) for d in r.get('dishes', []))},"
            f"{r.get('total_calories', 0)},{r.get('notes', '')}"
        )
    content = "\n".join(csv_lines)
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(content)
    return output_path


def export_data_snapshot(output_path: str) -> str:
    """导出全量数据快照（JSON），供外部系统分析"""
    snapshot = {
        "exported_at": datetime.now().isoformat(),
        "inventory": _load("inventory.json"),
        "recipes": _load("recipes.json"),
        "meal_log": _load("meal_log.json"),
        "shopping_list": _load("shopping_list.json"),
        "taste_prefs": _load("taste_prefs.json"),
        "restrictions": _load("restrictions.json"),
    }
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(snapshot, f, ensure_ascii=False, indent=2)
    return output_path


# ── CLI 入口 ──

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("用法: python api.py <command> [args...]")
        print("命令: list-inventory | add-inventory | remove-inventory")
        print("      list-recipes | meal-stats | export-csv | export-snapshot")
        print("      shopping-checkout")
        sys.exit(1)

    cmd = sys.argv[1]

    if cmd == "list-inventory":
        cat = sys.argv[2] if len(sys.argv) > 2 else None
        for item in inventory_list(cat):
            print(f"[{item['category']}] {item['name']} x{item['quantity']}{item['unit']} | {item.get('notes', '')}")

    elif cmd == "add-inventory" and len(sys.argv) >= 5:
        inv_id = inventory_add(sys.argv[2], sys.argv[3], float(sys.argv[4]), sys.argv[5] if len(sys.argv) > 5 else "份")
        print(f"已添加: {inv_id}")

    elif cmd == "remove-inventory" and len(sys.argv) >= 3:
        ok = inventory_remove(sys.argv[2])
        print("已删除" if ok else "未找到")

    elif cmd == "list-recipes":
        for r in recipe_list():
            print(f"[{r['category']}] {r['name']} | {r['difficulty']} | ⏱{r['cooking_time']}min")

    elif cmd == "meal-stats" and len(sys.argv) >= 4:
        stats = meal_stats(sys.argv[2], sys.argv[3])
        print(json.dumps(stats, ensure_ascii=False, indent=2))

    elif cmd == "export-csv" and len(sys.argv) >= 5:
        path = export_meal_csv(sys.argv[2], sys.argv[3], sys.argv[4])
        print(f"已导出: {path}")

    elif cmd == "export-snapshot" and len(sys.argv) >= 3:
        path = export_data_snapshot(sys.argv[2])
        print(f"已导出: {path}")

    elif cmd == "shopping-checkout":
        items = shopping_checkout()
        for item in items:
            print(f"已转入库存: {item['name']}")
        print(f"共转入 {len(items)} 项")

    else:
        print(f"未知命令: {cmd}")
