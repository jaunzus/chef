# 大厨 Chef

> 日常饮食管理 SKILL — 菜品推荐、菜单规划、菜谱生成、食材库存、饮食记录、营养分析

## 功能

| 功能 | 说明 |
|------|------|
| 🍳 菜品推荐 | 多源搜索（下厨房/豆果/小红书）+ 8步SOP智能推荐 |
| 📅 菜单规划 | 一日三餐自动规划，含搭配审查和流水线优化 |
| 📦 食材库存 | 购买/消耗/预警，追踪保质期 |
| 🛒 购物清单 | 菜单驱动生成，一键结算转入库存 |
| 📝 饮食记录 | 每餐记录，热量估算，口味追踪 |
| 📊 营养分析 | 多维度分析 + Excel周报（含图表） |
| 👅 习惯学习 | 自动记住你的口味偏好和食材习惯做法 |

## 安装

```bash
# 下载到 TRAE SOLO 的 skills 目录
cd .trae/skills/
git clone https://github.com/你的用户名/chef.git chef
```

## 使用

在 TRAE SOLO 中说：

> "帮我推荐几个菜"
> "规划今天的晚餐"
> "把冰箱里的XX加到库存"

Skill 会自动触发。

## 架构

```
SKILL.md           # 技能定义（SOP + 规则）
api.py             # API 兼容层（CLI + Python import）
pipeline.py        # 搜索管道（缓存 + 多渠道合并）
report_generator.py # Excel 周报生成器
data/              # 用户数据（不上传 GitHub，首次使用自动创建）
```

## 外部集成

```bash
python api.py list-inventory 蔬菜
python api.py meal-stats 2026-05-01 2026-05-31
```

```python
from api import inventory_list, meal_stats
```

---

MIT License
