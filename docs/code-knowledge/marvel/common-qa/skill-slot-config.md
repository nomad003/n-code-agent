---
type: Common QA
title: SkillSlot 配置
description: 面向策划和程序的 SkillSlot 技能槽位配置说明，覆盖 SkillSlot.txt 字段、索引展开、RoleSkill 初始化和 XEcs 触发链路。
repo: marvel
module: common-qa/skill-slot-config
resource: docs/code-knowledge/marvel/common-qa/skill-slot-config.md
tags: qa, common, skill, slot, SkillSlot, role, config, 配置
questions: SkillSlot配置, SkillSlot怎么配置, SkillSlot如何配置, SkillSlotTable怎么配置, 技能槽位怎么配置, 技能槽怎么配置, 角色技能槽位怎么配置
aliases: skill slot config, skill slot table, 角色技能槽配置, 按键技能槽配置
question_types: config_impl, feature_impl, outage_log, general
depends_on: skill-config.md, ../unit/skill-mgr.md, ../gameserver/combat-core-overview.md
updated_at: 2026-06-22
---

# SkillSlot 配置

`SkillSlot.txt` 控制角色 / 伙伴在不同状态下，每个输入槽位对应哪个技能。
它不是怪物技能表；主要服务于 Role 的按键槽位、战斗 / 非战斗槽位、移动状态、爆发状态和变身状态切换。

## 配置明细

| 配置面 | 字段 | 用途 | 注意点 |
| --- | --- | --- | --- |
| 角色技能模板 | SkillPartnerId | 指向角色技能模板 ID。运行时用 `PartnerConfig::GetSkillPartnerId(partner_id)` 取得。 | 必须能和该角色的 `SkillListForRole` / `SkillListForPartner` 对上。 |
| 移动状态 | State | 可用竖线分隔多个状态，运行时通过 `CGsDir::StateAbility` 转成 move。 | 每个 State 会展开成一组 `(move, burst, transform)` 索引。 |
| 战斗状态 | BattleState | 区分战斗 / 非战斗槽位。 | 当前代码 `BattleState == 0` 写入 battle 槽位；非 0 写入 non-battle 槽位。 |
| 爆发状态 | BuffType1 | 可用竖线分隔多个 burst 值。 | 空值会按 `0` 处理。运行时来自 `XBuffChangeSlot` 的 `SkillChangeBusrt`。 |
| 变身状态 | BuffType2 | 可用竖线分隔多个 transform 值。 | 空值会按 `0` 处理。运行时来自 `XBuffChangeSlot` 的 `SkillChangeTrans`。 |
| 槽位技能 | Slot1 ~ Slot10 | 每列填技能脚本名，运行时 `xecs::hash(skill)` 后绑定到对应槽位。 | `Slot1` 对内部 slot `0`，`Slot10` 对内部 slot `9`。空字段会尝试回退到 run / 非 burst / 非 transform 的同槽位技能。 |

## 槽位编号

| 内部 slot | 配置字段 | 含义 |
| --- | --- | --- |
| 0 | Slot1 | Normal |
| 1 | Slot2 | Dash |
| 2 | Slot3 | Ultimate |
| 3 | Slot4 | Skill 1 |
| 4 | Slot5 | Skill 2 |
| 5 | Slot6 | Skill 3 |
| 6 | Slot7 | Burst |
| 7 | Slot8 | Jump / Fly |
| 8 | Slot9 | Virtual Dash |
| 9 | Slot10 | Virtual Normal |

## 加载与索引展开

```mermaid
flowchart TD
    A["table/SkillSlot.txt"] --> B["SkillConfig::CheckLoad"]
    B --> C["m_oSkillSlotTable.CopyFrom"]
    C --> D["SkillConfig::InitSkillRole"]
    D --> E["遍历 SkillSlotTable.Table"]
    E --> F["Split(State, '|')"]
    E --> G["Split(BuffType1, '|')，空值补 0"]
    E --> H["Split(BuffType2, '|')，空值补 0"]
    F --> I["组合 move / burst / transform"]
    G --> I
    H --> I
    I --> J{"BattleState == 0 ?"}
    J -->|是| K["m_partner_slot_skills"]
    J -->|否| L["m_partner_slot_skills_nobattle"]
    K --> M["InitSlotSkill Slot1 ~ Slot10"]
    L --> M
    M --> N["slot -> skill hash"]
```

## 运行时链路

```mermaid
sequenceDiagram
    participant Config as SkillConfig
    participant Role as RoleSkill
    participant Buff as XBuffContainer
    participant Ecs as XEcs
    participant Client as 客户端输入

    Config->>Role: GetRoleSlotSkills(skillPartnerId, battle)
    Role->>Role: InitRole 写 Origin_Slots / Origin_Slots_Battle
    Role->>Role: ResetSlot 选择当前战斗状态槽位
    Role->>Ecs: bind_onslotskill(base slots)
    Buff->>Role: TransformSkill(move / burst / transform)
    Role->>Config: GetRoleSlotSkills(skillPartnerId, battle, move, burst, transform)
    Role->>Ecs: bind_onslotskill(updated slots)
    Client->>Ecs: slot2skill(slot, ButtonDown / ButtonUp / ButtonPress)
    Ecs->>Ecs: QTE 槽位优先，否则 base slot
    Ecs->>Ecs: skillType 匹配后 RequireSkill
```

## QTE 与临时槽位

| 来源 | 机制 |
| --- | --- |
| `SkillListForRole.QTE` | 通过 `qte -> slot -> skill` 建索引。QTE 里配置的 slot 是 1-based，代码会减 `SkillSlot_Offset`。 |
| `RoleSkill::QTEChangeSlotSkill` | QTE add 时写入 `m_SlotsQTE[slot]`，QTE del 时恢复基础槽位。 |
| `RoleSkill::GetSlotSkill` | 优先返回 QTE 槽位技能；没有 QTE 时返回基础槽位技能。 |
| `XSkillSlotType` | 输入事件分 `ButtonDown`、`ButtonUp`、`ButtonPress`，XEcs 会检查技能 JSON 的 `skillType` 是否匹配。 |

## 常见排查

| 现象 | 优先检查 |
| --- | --- |
| 技能槽为空 / 按键没技能 | `SkillPartnerId` 是否正确；`BattleState` 是否写到当前战斗状态；`State` 是否匹配当前 move。 |
| 配了技能但释放不了 | `SlotN` 填的是技能脚本名；该技能是否存在于当前角色的技能集合；`RoleSkill::InitRole` 是否通过 `IsValidSkill`。 |
| 爆发 / 变身后槽位没切换 | `BuffType1` / `BuffType2` 是否和 `XBuffChangeSlot` 产出的 burst / transform 值一致。 |
| 技能按下无反应 | 客户端上报的 slot 是否 0-based；`XSkillSlotType` 是否和技能 JSON 的 `skillType` 一致。 |
| QTE 技能没覆盖槽位 | `SkillListForRole.QTE` 的 slot 是否按 1-based 配；QTE flag 为 2 时还会检查技能条件和 CD。 |
| 日志 slot out of range | slot 必须在 0 ~ 9；配置侧 `Slot1` 对内部 0，不要混用。 |

## 继续追问方向

- 问“某个角色技能槽不对”，应给出 `partner_id` / `SkillPartnerId`、当前战斗状态、move、burst、transform 和具体 slot。
- 问“按键技能放不出来”，应继续查 `XActionReceiver::OnSlotSync`、`XEcs slot2skill`、技能 JSON `skillType`。
- 问“变身后技能没换”，应继续查 `XBuffChangeSlot` 和 `RoleSkill::TransformSkill`。
