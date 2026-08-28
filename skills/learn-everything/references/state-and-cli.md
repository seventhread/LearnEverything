# 本地状态与 CLI 契约

只在初始化、持久化、恢复或数据控制时读本文件。CLI 只负责校验、并发保护和原子保存；问题与讲解由 Skill 生成。

## 通用调用

从本 Skill 目录解析 `scripts/learn-everything` 的绝对路径，不依赖 cwd。结构化输入只接受标准输入：必须写 `--input -`；`init`、`session get` 不读输入，`data inspect` 可不带输入。

每次调用只在 stdout 输出一个 JSON envelope：

```json
{"ok":true,"data":{}}
```

```json
{"ok":false,"error":{"code":"INVALID_INPUT","message":"...","details":{"field":"input.goal"}}}
```

成功退出码 0，失败退出码 2。`details` 可能省略；只根据 `ok`、`error.code` 和结构化 details 判断，不解析 message。未知字段、错误类型、空必填字符串、无效枚举、重复局部 ID 和悬空引用均为 `INVALID_INPUT`。

CLI 通过用户级配置定位首次授权的数据根，因而可跨项目调用。`LEARN_EVERYTHING_CONFIG` 只供隔离测试，正常教学不要设置，也不要在当前项目复制规范状态。

## 命令

### `init`

```text
learn-everything init --data-root <path>
```

先取得用户对该目录的一次性明确授权。成功 `data` 精确为：

```json
{
  "initialized": true,
  "reused": false,
  "data_root": "/absolute/root",
  "database_path": "/absolute/root/learn-everything.sqlite3"
}
```

同一规范化目录重复调用仍成功，只有 `reused` 变为 `true`。配置已指向别处则报 `ALREADY_INITIALIZED`，不静默换根。

### `context get`

```text
learn-everything context get --input -
```

输入 object 的三个字段均可省略：

```json
{
  "topic_terms": ["attention", "注意力机制"],
  "concept_keys": ["linear-algebra.dot-product"],
  "scopes": ["machine-learning.attention"]
}
```

- `topic_terms` 匹配主题 ID、标题、别名，也可匹配概念别名；
- `concept_keys` 必须是 canonical key，匹配概念 key/别名及主题；
- `scopes` 匹配作用域；匹配采用不区分大小写的双向子串；
- 全局（`global`/`*`）显式偏好始终返回；适配信号只返回匹配的 `candidate`/`active`；
- `{}` 只返回全局偏好，不倾倒历史。

成功 `data` 精确为：

```json
{
  "explicit_preferences": [],
  "concept_notes": [],
  "adaptation_signals": [],
  "topic_memories": []
}
```

### `session get`

```text
learn-everything session get
```

成功 `data` 为 `{"open_session":null}` 或 `{"open_session":<完整会话>}`。没有开放会话不是错误。

### `session start`

```text
learn-everything session start --input -
```

等待诊断时输入：

```json
{
  "session_id": "ses-optional",
  "topic_id": "ml.attention",
  "topic_title": "Attention 机制",
  "status": "active",
  "goal": {"purpose": "看懂 Q/K/V 公式", "target_depth": "explain"},
  "diagnosis": {
    "phase": "awaiting_answers",
    "questions": [
      {
        "question_id": "dq-01",
        "prompt": "两个向量方向越接近时，点积通常怎样变化？",
        "options": [
          {"option_id": "a", "label": "通常变大", "kind": "answer"},
          {"option_id": "u", "label": "在看到选项前不知道，或主要靠猜", "kind": "unknown_or_guessing"}
        ]
      }
    ]
  }
}
```

- 必填：`topic_id`、`topic_title`、`goal`、`diagnosis`；`session_id` 可省略让 CLI 生成，`status` 可省略且默认 `active`。
- `topic_id` 是主题记忆的 upsert 主键：明确命中既有主题时复用；否则使用可移植的 ASCII canonical slug。通常省略 `session_id`，避免手工碰撞。
- awaiting 时 goal 可缺 `purpose`/`target_depth`，但不得含 `completion_items`；questions 为 1–5 题。产品默认恰好三道知识诊断；若目标深度未明确，同组另存一道 `question_id:"goal-depth"` 的选择，通常共四题。该选择不计入知识诊断。
- complete 时 goal 必须完整，并提供 `teaching_state`；若准备立即交付第一单元，也可提供 `unconfirmed_unit`。
- CLI 添加 revision 1、`created_at`、`updated_at`。成功 `data` 精确为 `{"session":<完整会话>}`。
- 已有会话报 `OPEN_SESSION_EXISTS`，不覆盖。

### `session checkpoint`

```text
learn-everything session checkpoint --expected-revision <n> --input -
```

输入是可变快照，不含 topic、revision 或时间戳：

```json
{
  "session_id": "ses-123",
  "status": "active",
  "goal": {
    "purpose": "看懂 Q/K/V 公式",
    "target_depth": "explain",
    "completion_items": [
      {"item_id": "dw-01", "description": "解释 Q、K、V 的来源和作用", "status": "pending"}
    ]
  },
  "diagnosis": {
    "phase": "complete",
    "basis": "questions",
    "starting_point": "从点积相似度接到加权汇总",
    "summary": [
      {"concept_key": "linear-algebra.dot-product", "starting_state": "known"}
    ]
  },
  "teaching_state": {
    "confirmed_summary": null,
    "unresolved_confusions": [],
    "local_teaching_notes": [],
    "current_focus": "Q/K/V 的角色",
    "next_move": "用数值例连接分数、权重和 V"
  },
  "unconfirmed_unit": {
    "summary": "用检索类比解释 Q、K、V 的角色",
    "may_cover": ["dw-01"]
  }
}
```

- `session_id`、`status`、`goal`、`diagnosis` 始终必填；ID 必须对应当前会话。
- awaiting 快照不得含 completion items、teaching state 或 unconfirmed unit。
- 首次转 complete 时必须给完整 goal 和 teaching state；complete 后省略 `teaching_state` 表示保留。
- 省略 `unconfirmed_unit` 表示保留，传 `null` 删除，传 object 替换；`may_cover` 只能引用当前 completion item。
- complete 不能退回 awaiting。成功 `data` 为 `{"session":<revision 加 1 的完整会话>}`。
- revision 或 session ID 不符报 `REVISION_CONFLICT` 且不写；无会话报 `NO_OPEN_SESSION`。

### `session close`

```text
learn-everything session close --expected-revision <n> --input -
```

必须先获得用户明确的关闭或切换决定。

仍在 awaiting 时只接受：

```json
{"session_id":"ses-123"}
```

成功清空槽位但不写长期记忆，`data` 精确为：

```json
{
  "closed_session_id": "ses-123",
  "topic_memory": null,
  "concept_notes_upserted": 0,
  "adaptation_observations_applied": 0
}
```

诊断 complete 时输入：

```json
{
  "session_id": "ses-123",
  "topic_memory": {
    "aliases": ["attention"],
    "summary": "Q 和 K 产生匹配权重，权重用于汇总 V。",
    "unresolved_questions": [],
    "source_links": [],
    "close_reason": "scope_delivered"
  },
  "concept_notes": [],
  "adaptation_observations": []
}
```

- `topic_memory` 必须含 summary、unresolved questions、close reason；title/goal 可省略并由 CLI 从会话复制，若提供必须完全一致。
- CLI 添加 topic ID 与 `closed_at`。`scope_delivered` 要求所有完成项 covered；`user_stopped` 要求至少一项 pending 及非空 `suggested_next_step`。
- concept notes 可省略；adaptation observations 可省略且最多三条，两者都要用下文完整规范对象（含时间戳）。
- 成功 `data` 为 `{closed_session_id,topic_memory,concept_notes_upserted,adaptation_observations_applied}`；topic memory 是完整已保存记录，后两项为整数。
- 关闭、长期 upsert、适配合并和清空槽位在同一事务。revision/session 冲突不写；无会话报 `NO_OPEN_SESSION`。
- 复用 topic ID 时，CLI 会替换该主题记录；Skill 应先把仍有效的既有摘要合入新摘要，当前纠正优先。

### `data inspect`

```text
learn-everything data inspect
learn-everything data inspect --input -
```

无输入或 `{}` 时成功 `data` 为 `{"state":<完整 canonical state>}`。窄查输入：

```json
{"record_type":"concept_note","record_id":"linear-algebra.dot-product"}
```

`record_type` 可为 `explicit_preference`、`concept_note`、`adaptation_signal`、`topic_memory`。`record_id` 可省略；成功 `data` 精确为 `{record_type,record_id,matches}`，省略 ID 时返回 null，未命中时返回空数组。

### `data correct` 与 `data forget`

```text
learn-everything data correct --input -
learn-everything data forget --input -
```

correct 输入 `{"record_type":"concept_note","record":<该类完整规范记录>}`。它按该类主 ID upsert/替换，不接受 JSON Patch；成功 `data` 精确为 `{record_type,record,replaced}`，`replaced` 是 boolean。

forget 输入 `{"record_type":"concept_note","record_id":"linear-algebra.dot-product"}`。成功 `data` 精确为 `{record_type,record_id,removed}`；目标不存在也是成功，`removed:false`。

两者都不能修改 open session。纠正或遗忘后，下一教学单元前重新 `context get`，不继续使用旧上下文。

## 规范对象

所有必填字符串非空。普通 ID 最长 200 字符且匹配 `^[A-Za-z0-9][A-Za-z0-9._:-]*$`；canonical key 最长 200 字符且匹配 `^[a-z0-9]+(?:[._-][a-z0-9]+)*$`。时间是带时区 RFC 3339。未知字段无效，同一数组内 ID 唯一。

### Goal 与 diagnosis

完整 goal：

```json
{
  "purpose": "本次为何学习",
  "target_depth": "explain",
  "completion_items": [
    {"item_id": "dw-01", "description": "承诺讲清的边界", "status": "pending"}
  ]
}
```

target depth 是 `orientation|explain|apply|independent`；completion items 为 1–5 项，status 是 `pending|covered`。

awaiting diagnosis 形状见 start；questions 为 1–5，每题 options 为 2–8，并必须含 `kind:"unknown_or_guessing"`。option kind 是 `answer|unknown_or_guessing|cannot_parse_options`。回答前可省略 `selected_option_id`，提供时只能引用本题 option。

目标深度未明确时使用同一 questions 数组保存第四道选择，以便中断后原样恢复：`question_id` 固定为 `goal-depth`，四个结果选项的 `option_id` 分别为 `orientation|explain|apply|independent`，另加 `option_id:"unsure"`、`kind:"unknown_or_guessing"` 的“不确定，请根据我的学习目的推荐”。它没有正确答案，不进入 diagnosis summary；结算后只写入 `goal.target_depth`。用户明确给出等价结果时不生成该题。选择 unsure 或明确拒答才允许采用最低足够深度；漏答或中断时继续保持 awaiting。

complete diagnosis：

```json
{
  "phase": "complete",
  "basis": "questions",
  "starting_point": "选定起点",
  "summary": [{"concept_key":"canonical.key","starting_state":"partial"}]
}
```

basis 是 `questions|prior_context|user_statement|refusal_as_unknown|conservative_fallback|mixed`；summary 最多五项；starting state 是 `known|partial|unknown|possible_misconception|cannot_parse_question`。最后一项表示题目或选项所依赖的术语/概念尚不可理解，不是能力标签。

### Teaching state

```json
{
  "confirmed_summary": null,
  "unresolved_confusions": [{"description":"仍未解决的问题","kind":"too_abstract"}],
  "local_teaching_notes": [
    {
      "scope": "canonical.scope",
      "condition": "canonical.condition",
      "strategy": "canonical.strategy",
      "outcome": "helped",
      "summary": "直接反馈的压缩依据",
      "observed_at": "2026-08-27T00:00:00Z"
    }
  ],
  "current_focus": "当前焦点",
  "next_move": "可直接执行的下一步"
}
```

confirmed summary 首次可为 null；local notes 最多三条。confusion kind 是 `missing_prerequisite|unfamiliar_term|skipped_step|unsuitable_example|too_abstract|too_detailed|other|unknown`。outcome 是 `helped|hindered`。

unconfirmed unit 只含：

```json
{"summary":"即将发送单元的短摘要","may_cover":["dw-01"]}
```

### 长期记录

- **显式偏好**：`{preference_id,scope,instruction,updated_at}`；主 ID 是 `preference_id`。
- **概念笔记**：`{concept_key,aliases?,summary,state,basis,last_observed_at}`；主 ID 是 `concept_key`；state 为 `known|partial|needs_revisit`，basis 为 `user_declared|diagnostic_observation|closed_topic`。
- **适配信号**：`{signal_id,scope,condition,strategy,status,last_evidence_session_id,basis_summary,last_observed_at}`；主 ID 是 `signal_id`，status 为 `candidate|active|inactive`。阶段本身表达一条支持、两条跨会话支持或已被负反馈停用，不另存重复计数。
- **适配观察**：使用 local teaching note 的完整形状；close 依据 session ID 合并生命周期，不要自行计算长期 signal。
- **主题记忆**：`{topic_id,title,aliases?,goal,summary,unresolved_questions,suggested_next_step?,source_links?,close_reason,closed_at}`；主 ID 是 `topic_id`。source links 必须是绝对 URI。

canonical state 精确包含 `{schema_version:"0.2.0",learner:{explicit_preferences,concept_notes,adaptation_signals},topic_memories,open_session,updated_at}`。

## 错误与恢复

| code | details | 动作 |
| --- | --- | --- |
| `NOT_INITIALIZED` | `{config_path}` | 首次需保存时请用户授权目录后 init；聚焦问题无需初始化 |
| `ALREADY_INITIALIZED` | `{configured_data_root,requested_data_root}` | 不换根；说明已配置位置 |
| `OPEN_SESSION_EXISTS` | `{session_id,topic_id,topic_title}` | get 后让用户明确恢复、保留或关闭，绝不覆盖 |
| `NO_OPEN_SESSION` | 无 | 重读状态，不声称已保存/关闭 |
| `INVALID_INPUT` | `{field}` | 修正 payload，不丢字段绕过校验 |
| `REVISION_CONFLICT` | 同 session：`{session_id,expected_revision,actual_revision}`；错 session：`{expected_session_id,actual_session_id,actual_revision}` | 立即 get；不自动合并或覆盖，让用户决定真实边界 |
| `STORAGE_UNAVAILABLE` | 按位置含 `config_path`、`data_root`、`database_path`、`reason` 的适用子集 | 继续讲解，明确本轮未可靠保存；恢复后先 get，不回填临时进度 |

任何失败都不代表写入成功；只有 `ok:true` 才能告诉用户已保存。
