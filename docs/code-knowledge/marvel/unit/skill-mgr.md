---
type: Code Module
title: SkillMgr 技能管理
description: SkillMgr 负责技能类型判断、SkillCore 创建、AI 技能注册、条件技能和 ECS 绑定。
repo: marvel
module: gameserver/unit/SkillMgr
resource: gameserver/unit/skill/skillmgr.h
tags: unit, skill, skillmgr, skillcore, ecs, ai
symbols: SkillMgr, SkillCore, SkillMgr::Init, SkillMgr::CreateSkill, SkillMgr::RegisterAIMgr, SkillMgr::BindEcs
logs: skill not find in conf
asserts: CHECK_COND_WITH_LOG_RETURN
question_types: crash_stack, outage_log, feature_impl, config_impl
part_of: unit/index.md
depends_on: combatunit.md
updated_at: 2026-06-20
---

# SkillMgr 技能管理

## 卡片说明

| 项 | 内容 |
| --- | --- |
| 模块 | `SkillMgr` / `SkillCore`。 |
| 职责 | 创建技能对象，注册 AI 技能分类，绑定 ECS 技能系统。 |
| 配置 | Role、Enemy、Spawn 分别走不同技能表。 |

## 字段

| 字段 | 用途 |
| --- | --- |
| `m_type` | `SKILL_ROLE` / `SKILL_ENEMY` / `SKILL_SPAWN`。 |
| `m_AllSkills` | 所有技能对象。 |
| `m_SkillMap` | skill hash 到 `SkillCore`。 |
| `m_ai_mgr` | AI 技能分类。 |
| `m_HpMaxSkills` / `m_StageSkills` | 条件技能索引。 |

## 初始化时序

```mermaid
sequenceDiagram
    participant Unit as CombatUnit
    participant SkillMgr as SkillMgr
    participant Config as SkillConfig
    participant AI as AI 配置
    participant XEcs as XEcs

    Unit->>SkillMgr: Init(scene, unit)
    SkillMgr->>SkillMgr: 判断技能类型
    SkillMgr->>AI: 读取 AI 技能名
    SkillMgr->>Config: 查 SkillList
    Config-->>SkillMgr: 技能行或失败
    SkillMgr->>SkillMgr: RegisterAIMgr
    SkillMgr->>SkillMgr: InitConditionSkills
    Unit->>SkillMgr: PostInit BindEcs
    SkillMgr->>XEcs: 绑定技能系统
```

## 排查入口

| 现象 | 检查点 |
| --- | --- |
| 技能对象不存在 | `m_SkillMap`、`CreateSkill`、技能类型。 |
| AI 不用技能 | `RegisterAIMgr` 和 `AISkillType`。 |
| HP 阈值技能不触发 | `m_HpMaxSkills`、`HpMaxLimit`。 |

