# 大厨参考数据

> ⚠️ 此文件为 SKILL.md 的补充参考。核心规则在 SKILL.md，这里放详细 schema 和操作说明。

---

## 数据结构全集

### inventory.json — 食材库存

```json
{
  "items": [{
    "id": "uuid",
    "name": "食材名称",
    "category": "蔬菜|肉类|海鲜|豆制品|调料|主食|水果|乳制品|蛋类|其他",
    "quantity": 1.0,
    "unit": "斤|个|盒|袋|瓶|克|ml|份",
    "purchase_date": "YYYY-MM-DD",
    "expiry_date": "",
    "notes": ""
  }],
  "last_updated": "ISO datetime"
}
```

操作：添加/消耗（notes 追加，不删除除非用户明确说用完）/查看按分类/过期预警。

**消耗规则**：用户说"做了XX"但没说用完 → 只追加 notes"X日用掉部分"。明确说"用完了"才删除。**不准替用户判断用完。**

### recipes.json — 菜谱库

```json
{
  "recipes": [{
    "id": "uuid",
    "name": "菜名",
    "category": "家常菜|汤羹|凉菜|主食|烘焙|快手菜|减脂餐|其他",
    "cuisine": "川菜|粤菜|鲁菜|苏菜|湘菜|东北菜|西餐|日料|韩餐|其他",
    "cooking_time": 20,
    "difficulty": "简单|中等|困难",
    "servings": 2,
    "scene": ["家庭日常", "健身减脂", "快手便当", "宴客"],
    "ingredients": [{"name": "食材名", "amount": 200, "unit": "g"}],
    "seasonings": [{"name": "调料名", "amount": 1, "unit": "汤匙"}],
    "steps": ["步骤1", "步骤2"],
    "nutrition": {"calories": 0, "protein": 0, "fat": 0, "carbs": 0, "fiber": 0},
    "tags": [],
    "notes": "",
    "source": "大厨推荐|用户自创|外部收录",
    "rating": 0,
    "cook_count": 0,
    "created_date": "YYYY-MM-DD",
    "last_cooked": null
  }],
  "last_updated": "ISO datetime"
}
```

### meal_log.json — 饮食记录

```json
{
  "records": [{
    "id": "uuid",
    "date": "YYYY-MM-DD",
    "meal_type": "早餐|午餐|晚餐|加餐",
    "dishes": [{"recipe_id": null, "name": "菜品", "portions": 1, "calories": 0}],
    "total_calories": 0,
    "notes": ""
  }],
  "last_updated": "ISO datetime"
}
```

### taste_prefs.json — 口味偏好

```json
{
  "favorite_flavors": ["麻辣", "清淡", "酸甜", "鲜香", "酱香", "蒜香"],
  "favorite_ingredients": [],
  "favorite_cuisines": [],
  "cooking_style": "",
  "serving_size": "一人食",
  "ingredient_methods": {"糯冬瓜": "红烧"},
  "meal_pattern": {"breakfast": "", "lunch": "", "dinner": ""},
  "taste_notes": [{"date": "YYYY-MM-DD", "note": ""}],
  "last_updated": "ISO datetime"
}
```

⚠️ `taste_notes` 表短期心情（今天想吃辣）；`favorite_*` 表长期偏好。冲突时**短期覆盖长期**。详见 SKILL.md 偏好优先级。

### restrictions.json — 忌口

```json
{
  "allergies": [],
  "dislikes": [],
  "dietary_restrictions": [],
  "health_goals": {
    "target_calories": 2000,
    "target_protein": 60,
    "target_fat": 55,
    "target_carbs": 300,
    "goal": "健康饮食"
  },
  "last_updated": "ISO datetime"
}
```

### shopping_list.json — 购物清单

```json
{
  "items": [{
    "id": "uuid",
    "name": "",
    "category": "",
    "quantity": 1.0,
    "unit": "份",
    "estimated_price": 0,
    "priority": "必须|可选",
    "source": "菜单规划|库存补充|手动添加",
    "purchased": false
  }],
  "last_updated": "ISO datetime"
}
```

### meal_plans.json — 菜单计划

```json
{
  "plans": [{
    "week_start": "YYYY-MM-DD",
    "days": [{
      "date": "YYYY-MM-DD",
      "day_of_week": "周一",
      "meals": {
        "breakfast": {"recipe_id": null, "name": "", "notes": ""},
        "lunch": {"recipe_id": null, "name": "", "notes": ""},
        "dinner": {"recipe_id": null, "name": "", "notes": ""}
      }
    }],
    "shopping_needed": [],
    "scene": "家庭日常"
  }],
  "last_updated": "ISO datetime"
}
```

### recipe_cache.json — 搜索缓存

```json
{
  "entries": {
    "query_key": {
      "cached_at": "ISO datetime",
      "source_channels": ["下厨房", "豆果", "小红书"],
      "results": []
    }
  }
}
```

---

## 搜索渠道规则

| 优先级 | 渠道 | 搜索方式 | 场景 |
|:--:|------|------|------|
| 🥇 | 下厨房 | `site:xiachufang.com {食材} {做法}` | 首选，步骤详细 |
| 🥈 | 豆果美食 | `site:douguo.com {食材} {做法}` | 补充验证 |
| 🥉 | 小红书 | `site:xiaohongshu.com {食材} {做法} 食谱` | 创新/一人食/减脂 |

策略：并行三搜 → 交叉验证 → 有分歧以下厨房为准 → 三渠道无果用训练数据兜底。

---

## 流水线审查规则表

| 前一道菜 | 残留物 | 下一道菜 | 判定 |
|---------|--------|------|:--:|
| 煎蛋/炒蛋 | 蛋渣+油 | 煎肉片/炒蔬菜 | ✅ |
| 番茄炒蛋 | 蛋渣+番茄汁+糖 | 红烧冬瓜 | ❌ 糊锅 |
| 煎肉类 | 油+焦香肉汁 | 炒蔬菜 | ✅ |
| 红烧/焖炖 | 酱油汁+油脂 | 任何菜 | ❌ 串味 |
| 炒青菜 | 清水+油 | 蔬菜 | ✅ |
| 煎鱼/虾 | 油+腥 | 蔬菜 | ❌ 串味 |

---

## 搭配审查五维度

| 维度 | 红线 | 修正 |
|------|------|------|
| 🍳 烹饪方式 | 同方式 >2道 | 炒+蒸+煮混搭 |
| 👅 口味 | 同口味 >2道 | 至少一浓一淡 |
| 🌿 口感 | 全脆/全软 | 脆配软、干配汤 |
| 🥘 荤素 | 全荤或全素 | ≥1硬荤+1半荤+1纯素 |
| 🥣 汤 | 全干炒 | 至少1汤/凉菜 |

---

## 人数→菜品数映射

- **1人**: 1-2道（一人食简化：蒸煮炖优先，一锅出）
- **2人**: 2-3道（触发搭配审查）
- **3人+**: 3-4道（至少1汤1荤1素）

---

## 营养分析 & Excel 报告

营养维度：单餐/每日/周趋势/食材多样性。输出简短总结 + 改善建议。

报告（Excel，5个 Sheet）：饮食概览(每日三餐+热量) / 营养分析(三大营养素趋势图) / 菜品排行(频率+评分) / 食材消耗 / 改善建议。

---

## API 兼容层

`api.py` 提供 CLI + Python import 双模式。核心接口：`inventory_list/add/remove` / `recipe_list/add` / `meal_log/query/stats` / `shopping_add/checkout` / `export_csv/snapshot`。

外部接入：直接读写 `data/*.json` 或 `import api`。

`pipeline.py`：搜索缓存(TTL 7天) + 多渠道合并(按共识度排序) + 场景模板。
