# LearnEverything v2 设计提案

- 状态：提案，等待评审；尚未替代当前 v1 规范
- 日期：2026-08-29
- 最近更新：2026-08-30
- 范围：Skill 行为、Markdown Vault、知识组织、检索、lint、Git 与 Obsidian 使用约定

## 1. 设计结论

LearnEverything v2 把一次学习视为当前对话内的临时活动。诊断、目标、完成边界、困惑、
教学调整和检索到的临时上下文只存在于对话中，不写入项目自己的长期存储。

只有同时满足以下条件，才产生长期结果：

1. 本次约定的完成项都已经通过先前的 assistant 消息真实交付；
2. 没有仍会阻碍本次目标的范围内困惑；
3. Skill 已明确告诉用户本次目标已覆盖；
4. 用户随后明确选择“结束并保存”。

中断、沉默、换 task、切换主题、诊断未完成或用户提前结束都不保存。v2 不承诺跨对话
恢复，也不把未完成学习伪装成“学过”。

长期数据不再保存到 SQLite，而是保存到一个用户拥有的 Obsidian Markdown Vault。Vault 中
只有三类核心内容：

1. `learning/`：每次完成学习的历史记录，正常学习流程只追加；
2. `knowledge/`：由模型与用户共同维护的当前知识 Wiki；
3. `profile/`：在一个学习指导页中分别保存明确偏好和有直接反馈依据的教学方式信息。

大主题、小概念和跨主题知识点不再使用三套数据模型。它们都是 `knowledge/` 中的页面，
通过 wikilink 形成关系；主要用于组织其他页面时标记为 `map`，主要解释一个边界清楚的知识
点时标记为 `concept`。

Obsidian 就是首版界面。v2 不建设独立 Learning Atlas、网页前端、本地 HTTP API 或网页
服务。Obsidian 提供阅读、搜索、Properties、backlinks 和 Graph View；Git 提供 diff、历史
和撤销。

模型直接维护 Markdown。命令行工具不再是业务数据访问层，只保留 Vault 初始化、路径定位
和确定性 lint；它没有学习运行态或业务状态，也不保存 session、事务 receipt、投影或检索
索引。

```text
当前对话（临时，零写入）
  -> 用户确认结束并保存
  -> 模型直接更新 knowledge / learning / profile
  -> 只读结构 lint
  -> 检查限定文件 diff
  -> Git commit（版本快照）
  -> 下次从 Markdown 与链接图检索上下文
```

初始化是与学习并列的显式数据控制流程，不是学习状态：

```text
用户显式 init
  -> 选择或确认 Vault
  -> 可选设置 Learning Guidance
  -> 查看 dry-run 与精确写入预览
  -> 用户确认
  -> 初始化/注册 Vault，必要时再写入已确认的学习指导
```

普通学习不会因为 Vault 缺失而自动进入初始化问卷；读取失败时仍使用空上下文继续教学。

## 2. 产品中心与非目标

### 2.1 产品中心

产品的中心仍然是把新内容讲明白：

- 从合适起点开始；
- 解释概念之间的关键关系；
- 用适合该知识结构的例子或表示落地；
- 用户困惑时立即换一种方式修复；
- 在约定边界真实覆盖后收束；
- 只保存完成后的学习记录、当前知识和有直接依据的偏好信息。

Markdown Wiki 服务于未来讲解，不应反过来让学习过程变成知识库录入工作。

### 2.2 v2 非目标

- 不保存原始对话、逐轮事件、诊断答案或中间 checkpoint；
- 不支持暂停、恢复、开放会话、多窗口协调或抢占；
- 不保存未完成学习或“以后从这里继续”的恢复点；
- 不生成掌握率、能力等级、学习者类型或人格标签；
- 不保存 init 问卷进度、原始答案、`onboarding_completed` 状态或学习风格测评结果；
- 不把讲过某概念、一次答对或没有反对当成长期掌握证据；
- 不使用 SQLite 保存业务数据或首版检索索引；
- 不建设独立网站、HTTP API、React 前端或后台服务；
- 不把 Obsidian 自身的缓存、索引或插件数据当作 LearnEverything 事实；
- 不在首版引入 embedding、向量数据库或云端知识库；
- 不在首版处理多用户协作、后台同步或多个自动写者；
- 不保存网页全文、完整来源快照或重型 claim/provenance ledger；
- 不兼容 v1 的 `open_session` 和 SQLite 数据结构。

## 3. 请求路由与对话内生命周期

### 3.1 显式初始化

用户明确说“初始化 LearnEverything”“初始化/设置学习库”、`$learn-everything init`，或要求把
某个目录注册/切换为 LearnEverything Vault 时，进入用户面对的 `init` 流程。仅仅出现“初始化”
一词，或用户要从零学习某个主题，不触发此路由。

`init` 是可重跑的独立数据控制操作，不开始学习、不做起点诊断，也不创建 knowledge、source
或 learning record。它可以设置 active Vault、创建最小 scaffold、配置静态 Git/ignore 行为，
并按用户选择创建或更新 Learning Guidance。收集路径和偏好时不写入；只有展示完整计划并得到
确认后才执行。

用户面对的是 Skill 的对话式初始化，底层 `vault init` 仍是无 LLM、无交互的机械工具。Skill
负责理解自然语言、提供少量可跳过选项、整理拟保存偏好和取得授权；CLI 只负责路径、冲突、
scaffold、marker、locator 与 Git 等确定性操作。

初始化首先只读当前 locator，然后区分：

1. 保持并验证当前 Vault；
2. 新建独立 Vault，作为推荐默认；
3. 注册已有文件夹或 Obsidian Vault；
4. 切换到另一个已初始化 Vault。

相对路径和 `~` 必须先规范化为绝对路径再展示给用户。已有 active Vault 时必须同时显示旧、
新路径。切换不复制、迁移、合并或删除旧 Vault；通常只替换 locator。若目标 Vault 的静态配置
因目录移动等原因已经不安全，例如 `git.mode` 不是 `off` 但实际位于父仓库中，Skill 只能把
关闭该配置作为同一预览中的显式目标变更，或拒绝切换，不能静默修改。目标位于另一个 Vault
内部、包含另一个 LearnEverything Vault、marker 不兼容或保留路径冲突时，普通 init 拒绝继续，
不提供 `force` 覆盖。

若用户只想修改或清除学习偏好，可以直接走普通数据控制，不必重跑完整 init。重复执行相同
初始化，且期望机械状态已经满足、Learning Guidance diff 也为空时返回成功 no-op，不重复
Home 链接、profile 条目或 Git commit。

用户在一次尚未完成的学习中显式要求 init 时，Skill 先说明“当前学习仍未保存”。用户可以
推迟 init，或把独立的 init 数据控制操作执行完再继续；后者可以保存 Vault 配置和已确认偏好，
但不能保存当前学习。若 active Vault 因此改变，Skill 丢弃此前从旧 Vault 装配的临时检索上下文，
从新 Vault 重新检索；本次学习以后若真实完成并再次确认，保存到新 active Vault。该影响必须
进入切换预览，不创建任何学习恢复状态。

### 3.2 聚焦问题

可独立回答的问题直接回答：

- 可以使用当前对话上下文；
- 不创建学习记录；
- 不要求目标深度或诊断；
- 不触发任何 Vault 写入。

### 3.3 广泛学习目标

广泛学习使用四个仅存在于当前对话中的逻辑阶段：

```text
确定目标与起点 -> 教学与修复 -> 等待结束决定 -> 已保存
```

这些阶段不是 CLI 状态，不分配 session ID，也不创建任何 Vault 文件。

开始学习时：

1. 定位 Vault；不存在、未配置或暂时不可读时返回空上下文，不能阻塞教学；
2. 做轻量结构预检；有 error 的文件不参与正文上下文装配，诊断可以报告但不能阻塞使用其他
   合法文件或开始教学；其现有路径和文件 stem 仍被保留，不能因为文件无效而新建同名页面；
   同时在开场明确提示“这些 error 不影响本次讲解，但结束保存前必须先单独修复”，不能等到
   用户学完才首次说明；
3. 按标题、alias、全文和 wikilink 检索当前主题、关键前置和相关偏好；
4. 确定学习目的、目标深度和起点；
5. 形成 1–5 个当前对话内稳定的完成项；
6. 立即开始第一段实质讲解。

教学过程中可以改变顺序、例子、表示、前置桥梁和当前焦点。用户明确扩展目标时可以在
当前对话中追加完成项；目标根本改变时，旧目标不保存，直接开始新的对话内目标。

Vault 读取失败只能导致本轮不使用旧上下文，不能触发重新初始化、静默切换数据根或阻塞
讲解。

### 3.4 完成与保存门槛

“讲解已交付”与“长期结果已保存”严格分开。

当所有完成项都已由上一条或更早的 assistant 消息覆盖时，Skill 给出紧凑合成，并让用户
选择结束并保存、继续巩固或明确扩展。只有用户在看到已交付内容后明确选择结束并保存，
下一轮才能修改 Vault。

这里的紧凑合成只能重述已经交付的关系。如果它首次补出了某个完成项所需的实质解释，
则完成实际发生在这条消息中，必须再等待下一条用户消息确认结束，不能立即保存。

若用户在完成门槛前说“结束”“换话题”或离开，Skill 简短说明本次没有保存学习结果，
不创建 learning record，不修改知识页或学习指导文件，也不创建 Git commit。

## 4. Markdown Vault 模型

### 4.1 唯一事实源与派生视图

Vault 中受管的 Markdown 文件是 LearnEverything 的唯一长期事实源。

| 内容 | 回答的问题 | 定位 |
| --- | --- | --- |
| `learning/` | 这一次完成了什么学习 | 完成历史；正常流程只追加 |
| `knowledge/` | 目前怎样解释和连接这些知识 | 活的、可持续更新的当前 Wiki |
| `profile/` | 以后怎样讲更合适 | 当前偏好和有直接反馈依据的教学信息 |
| `sources/` | 哪些外部资料值得反复引用 | 可选来源笔记，不默认保存网页全文 |
| Git history | 哪些文件曾怎样变化 | 安全与撤销机制，不是另一套业务模型 |

同一份内容在不同层的权威范围不同：

- learning record 是“本次交付过什么”的历史事实；
- knowledge page 是“当前应怎样理解”的正式综合内容；
- knowledge page 的存在不证明用户已经掌握；
- profile 只能表达明确偏好或有直接反馈的教学方式，不能扩写成人格画像；
- Obsidian 图谱、搜索结果、统计、未来 BM25/embedding 索引都是可重建视图。

模型生成知识页不可避免地是有损综合，因此不能用它替代完成学习历史。反过来，learning
record 也不需要复制知识页全文，只记录本次目标、完成内容、沉淀去向和必要来源。

### 4.2 Vault 目录

建议使用一个独立、用户选择的目录作为 Obsidian Vault：

```text
<vault>/
├── Home.md
├── knowledge/
│   ├── Attention 机制.md
│   ├── Transformer.md
│   └── 向量点积.md
├── learning/
│   └── 2026/
│       └── 2026-08-29 01 Attention 机制.md
├── profile/
│   └── Learning Guidance.md          # 首次有长期内容时创建，可重命名
├── sources/                         # 可选，按需创建
├── .obsidian/                       # Obsidian 自己管理
└── .learn-everything/
    ├── vault.json                   # schema/version、忽略路径、Git 静态配置
    └── cache/                       # 可删除、Git 忽略、首版可不存在
```

概念层级由链接表达，不靠深层目录表达。`knowledge/` 初期保持扁平；只有页面数量产生真实
的浏览组织需求后才引入领域子目录。受管 Markdown 的文件 stem 必须相对所有可见 Markdown
保持唯一；不同领域的同名概念使用带限定语的标题，不能依赖目录消除 Obsidian 链接歧义。

Vault 路径可以记录在用户级配置中，但该配置只用于定位目录，不保存学习状态。模型不得
从当前工作目录猜测另一个数据根。

首版只配置一个 active Vault。用户级 locator 使用系统标准配置目录：macOS 为
`~/Library/Application Support/LearnEverything/config.json`，Linux 为
`${XDG_CONFIG_HOME:-~/.config}/learn-everything/config.json`，Windows 为
`%APPDATA%\LearnEverything\config.json`。schema 固定为：

```json
{
  "schema_version": 1,
  "vault_root": "/absolute/path/to/vault"
}
```

Vault 内的 `.learn-everything/vault.json` 是目录标记和静态 lint 配置：

```json
{
  "schema_version": 1,
  "ignored_paths": [],
  "git": {
    "mode": "managed",
    "auto_commit": true
  }
}
```

`ignored_paths` 只能包含使用 `/` 分隔的严格 POSIX Vault-relative 目录。解析前拒绝空值、`.`、
`./`、绝对路径、`..`、glob、首尾 `/`、重复分隔符或空路径分量；解析 symlink 后也不能越出
Vault。规范化后的第一个路径分量不能是 `.learn-everything`、`knowledge`、`learning`、`profile`
或 `sources` 这些受管根，不能用 `knowledge/subdir` 绕过保护。每一项排除该目录整棵子树。
排除规则先于受管路径分类、链接扫描和检索生效。`init` 在所有机械 scaffold、lint 和可选
Git baseline 均完成或被准确降级后，才原子更新用户 locator。
`git.mode` 与“以后是否自动提交”分开：`managed` 表示这是由新建 init 创建并可在后续重试
baseline 的独立仓库；`external` 表示只使用用户已经建立的仓库，init 永不创建或修复其 Git；
`off` 表示 LearnEverything 不使用 Git。新独立 Vault 默认 `managed/true`；显式关闭后为
`off/false`；只关闭 auto-commit 时仍以 `managed/false` 建立一次 baseline。已有 Vault 首次
注册默认 `off/false`，用户手工提交 scaffold 后可重跑选择 `external`。`external` 只有在实际
Git top-level 等于 Vault root、存在有效 HEAD，且 HEAD 已经跟踪 marker 与必要 scaffold 时才
允许；`auto_commit: true` 要求 mode 不是 off。必要 scaffold 固定指 marker、`Home.md` 和初始化
创建且明确受管的 `.gitignore`（仅 `managed` 必需）；空目录不属于 Git baseline。init、lint
与 commit gate 共用同一谓词。index 或 working tree 是否干净不是静态启用资格，而是每次
自动 commit 的操作 gate。Vault 位于另一个项目仓库内部时必须使用 `off`。可选初始 Learning
Guidance 是 locator 激活后的独立数据控制子结果，失败时不撤销已经有效的 Vault。重跑 init
保留现有两个值，除非预览中包含用户明确要求的修改；若静态
安全前提已经失效则不得继续沿用，必须预览改成 `off/false` 或拒绝操作。

普通流程拒绝创建嵌套 LearnEverything Vault；若候选目录位于已有 LearnEverything marker
之下，或自身包含另一个 marker，要求用户选择正确的根。发现父目录是普通 Obsidian Vault 时
也应提示 Obsidian 不推荐嵌套 Vault，并要求改选父 Vault 或独立目录，而不是静默继续。
新建路径若已经位于父 Git 仓库中，默认也不创建嵌套仓库；用户必须改选独立路径，或在预览中
明确选择 `--git off`，让 LearnEverything 不操作父仓库的 Git。

existing 路径先解析 symlink 和文件系统实际大小写；新路径先规范化已存在父目录，再拼接候选
basename。locator 比较、Vault 嵌套检测和 Git top-level 判断都使用该 canonical path，但预览
同时显示用户输入值。文件系统根、Windows 盘符根和用户 home 不能作为 existing Vault root；
这不妨碍在 home 下选择一个专用子目录。

定位优先级只有“当前命令显式 `--root` > 用户 locator”；没有 cwd 猜测、用于指定 Vault 的
环境变量覆盖或隐式搜索父目录。除 `vault init` 的明确新建模式外，root 不存在、不是目录、
缺少有效 Vault marker 或 schema 版本不支持时，工具以配置错误失败；读取学习上下文时 Skill
把它降级为空上下文，保存时则明确报告并要求用户处理。

### 4.3 通用身份与 frontmatter

所有受管 Markdown 文件必须：

- 使用 UTF-8；
- 以可解析的 YAML frontmatter 开头；
- 有全 Vault 唯一、创建后稳定的 `id`；
- 有与目录职责匹配的 `kind`；
- 正文恰好有一个 H1；
- 日期序列化为 ISO 格式，时间使用带时区的 ISO 格式；YAML 解析器可以将日期返回为字符串
  或 date/datetime 标量，lint 按序列化值校验；
- 若使用受管 wikilink，则必须遵守本节的链接解析规则。

各类文件的最小字段为：

| `kind` | 位置 | 必填 frontmatter |
| --- | --- | --- |
| `index` | `Home.md` | `id`、`kind`、`updated` |
| `concept` / `map` | `knowledge/` | `id`、`kind`、`created`、`updated`；`aliases` 可选 |
| `learning-record` | `learning/YYYY/` | `id`、`kind`、`completed_at` |
| `profile` | `profile/` | `id`、`kind`、`created`、`updated` |
| `source` | `sources/` | `id`、`kind`、`url`、`accessed_at`、`created`、`updated` |

字段类型固定如下：

- `id`、`kind` 和 `url` 是非空字符串；`kind` 只能取上表列出的值，`url` 只能是绝对
  `http`/`https` URL；
- `aliases` 若存在，必须是由非空字符串组成的 YAML sequence，规范化后不能重复，不能用
  单个逗号分隔字符串代替；
- `created`、`updated` 和 `accessed_at` 是实际存在的 `YYYY-MM-DD` 公历日期；
- `completed_at` 是带显式 `Z` 或 `±HH:MM` 时区的 RFC 3339 datetime。

先从 Vault 文件集合中排除 `.obsidian/**`、`.learn-everything/**`、`.trash/**`、
`templates/**`、任何路径分量以 `.` 开头的目录，以及 `vault.json` 明确列出的子树。剩余
可见文件中，受管文件精确定义为 `Home.md`、`knowledge/**/*.md`、`learning/**/*.md`、
`profile/*.md` 和 `sources/**/*.md`；只有它们接受 frontmatter schema 和出链检查。链接
解析器、file stem 索引和 backlink 图扫描所有可见 `.md`，包括已有 Vault 的非受管笔记。
受管页可以链接非受管笔记，但非受管页
不具有 LearnEverything 的 `kind` 或稳定身份，也不能满足 learning record 的 `本次沉淀`
要求。backlink 图也解析所有可见 Markdown，确保删除前能发现非受管笔记的入链；但非受管
笔记自身的断链、frontmatter 和格式问题不产生 lint 诊断。附件只参与链接存在性检查。

`id` 使用小写 ASCII，并带命名空间：

```text
index.home
knowledge.attention-mechanism
learning.2026-08-29.attention-mechanism.01
profile.learning-guidance
source.attention-is-all-you-need
```

首版 ID 语法完全固定。`slug` 为 `[a-z0-9]+(?:-[a-z0-9]+)*`；各类型分别为：

```text
index.home
knowledge.<slug>
learning.<YYYY-MM-DD>.<slug>.<sequence>
profile.learning-guidance
source.<slug>
```

其中日期必须有效；`sequence` 是该日期下所有 learning record 共用的递增序号，新建时取
当前 Vault 该日最大现存序号加一，不回填删除产生的中间空洞；在 1–9 时写成 `01`–`09`，从
`10` 起使用无前导零的十进制正整数。新建 knowledge/source 时，候选完整 ID 已存在就给
slug 依次追加 `-2`、`-3`；路径或标题改变不产生新 ID。

路径、文件名和标题可以改变，`id` 不随之改变。每个 knowledge 页的检索身份 token 集合为
`{file stem, H1, aliases}`；不同 knowledge ID 的任意两个 token 规范化后相同都是 error，
包括某页 alias/H1 与另一页 file stem 冲突。learning record 等其他类型可以有相同 H1，但
不能有相同 stem 或 ID。任何受管 file stem 与另一个可见 Markdown 的 stem 冲突也属于
error；两个非受管笔记之间的冲突只在受管链接因此无法唯一解析时成为 error。身份规范化
统一使用 Unicode NFKC、首尾空白删除、连续空白折叠和 Unicode casefold。模糊或语义相似
只能表示相关，不能自动合并页面。

新建文件时采用可读标题，但不等于原样复制标题。生成 stem 时先做 Unicode NFKC，把 C0 控制
字符以及 `\\ / : * ? \" < > | # ^ [ ]` 的连续片段替换为 `-`，折叠连续空白和连字符，并
移除首尾空白、点和连字符；结果为空时使用 ID 的 slug。knowledge/source 的 stem 冲突时
追加 `(<id 的最后一段>)`。learning 文件固定为
`YYYY-MM-DD <sequence> <安全主题标题>.md`，日期和序号与 ID 一致，因此同日重复学习同一
主题也不会碰撞。H1 保留真实人类标题，不受文件名字符替换影响。人工安全重命名是 canonical，
lint 不要求 stem 永远等于 H1 的机械变换，只要求 stem 非空、不含上述禁用字符、身份无歧义；
learning 文件还必须保留精确日期和序号前缀。

Obsidian 落盘链接的目标与检索身份不同：wikilink 必须写实际且唯一的文件 stem，或写
Vault-relative path；显示名使用 `[[实际文件|显示名]]`。lint 不得因为 H1 或 alias 命中就把
Obsidian 实际无法解析的 `[[target]]` 判为有效。

首版 frontmatter 保持窄小，不把正文关系复制成复杂 YAML 图：

```yaml
---
id: knowledge.attention-mechanism
kind: concept
aliases: [注意力机制, Attention]
created: 2026-08-29
updated: 2026-08-29
---
```

### 4.4 `learning/`：完成学习记录

一次用户确认保存的学习对应一个 Markdown 文件：

```markdown
---
id: learning.2026-08-29.attention-mechanism.01
kind: learning-record
completed_at: 2026-08-29T21:00:00+08:00
---

# Attention 机制学习

## 本次目标

看懂 Q、K、V 如何形成注意力结果。

## 已完成内容

- 解释 Q、K、V 的角色及关系；
- 沿一个数值例走通权重计算和加权汇总。

## 本次沉淀

- 新建 [[Attention 机制]]；
- 更新 [[向量点积]]；
- 关联 [[Transformer]]。

## 后续方向

- 多头注意力怎样拆分表示空间。

## 网络来源

- [Attention Is All You Need](https://arxiv.org/abs/1706.03762)，访问于 2026-08-29。
```

规则：

- learning record 不保存原始对话、逐题答案、诊断过程、未解决范围或逐轮教学状态；
- 它表达“本次内容已经交付并由用户确认结束”，不表达用户已经掌握；
- `本次沉淀` 至少链接一个实际存在且受管的 concept/map 页面；
- 重复学习同一主题产生新的 record，同时更新相关知识页；
- 正常学习只新增 record；用户明确纠正或从当前记忆中移除时可以修改或删除，Git 默认仍保留
  变化历史；
- `learning/` 中不出现 `draft`、`paused`、`open` 等状态，文件存在就表示一次完成学习。

### 4.5 `knowledge/`：统一知识 Wiki

`knowledge/` 取代原设计中的 `topics`、`topic aggregate`、`concept_notes` 和
`learner_concepts`。大、小知识都使用同一种页面身份：

- `kind: concept`：解释一个边界清楚、未来可独立复用的知识点；
- `kind: map`：组织一个大主题、子概念和推荐阅读路径。

“原子”不等于一个名词一页或一句话一页。只有当一个知识点值得未来独立检索、能形成
自足解释、并可能被多个学习主题复用时，才创建独立页面。只在当前页面中有意义的细节
留在正文，避免把 Vault 切成大量空洞碎片。

建议页面形状：

```markdown
---
id: knowledge.attention-mechanism
kind: concept
aliases: [注意力机制, Attention]
created: 2026-08-29
updated: 2026-08-29
---

# Attention 机制

## 一句话

根据查询与候选项的匹配程度，对候选信息做加权汇总。

## 核心解释

...

## 关系

- 属于：[[Transformer]]
- 前置：[[向量点积]]
- 组成：[[Query Key Value]]
- 相关：[[Softmax]]

## 来源

- [Attention Is All You Need](https://arxiv.org/abs/1706.03762)，访问于 2026-08-29。
```

关系首先写在正文中，让人和 Obsidian 都能直接理解。首版推荐使用少量稳定关系词：

```text
属于 / 包含 / 前置 / 组成 / 相关 / 对比
```

learning record 指向本次沉淀的 knowledge 页，这是学习历史关系的唯一存储方向；knowledge
页不再手写反向的“学习记录”列表，Obsidian backlinks 负责展示。其他概念关系也不强制
手写反向边。语义相似度只能建议关系，不能自动落成 wikilink。模型更新旧页面时必须先读
完整当前文件，进行局部合并，并保留不在本次范围内的人工内容。

### 4.6 `profile/`：学习指导

首版只管理一个可选 profile 页面，默认新建路径为：

```text
profile/Learning Guidance.md  id: profile.learning-guidance
```

页面身份由固定 ID 而不是文件名决定；用户可在 Obsidian 中安全重命名，Skill 同步更新链接。
无长期偏好或教学反馈时不创建空页面，Home 也不创建指向它的链接。

旧设计中的 `Preferences` 和 `Teaching Patterns` 都回答“以后怎样讲更合适”。在个人规模下
拆成两个文件会导致同一信息重复、优先级不清和检索时同时召回，因此合并成一页
`Learning Guidance`；但两类信息的证据强度不同，仍保留为两个正文分区：

- `明确偏好`：用户明确表达具有长期或默认效力的要求，例如“以后先给具体例子，再抽象总结”；
- `教学反馈`：用户对某种讲法在具体情境中的直接正面或负面反馈，例如“公式过于抽象时，
  逐步数值例有帮助”或“已经理解直觉后，继续类比反而干扰”。

正文至少包含以下结构（frontmatter 仍按 4.3 节）：

```markdown
# Learning Guidance

## 明确偏好

- 先给具体例子，再抽象总结。

## 教学反馈

### 逐步数值例

- 条件：公式表达过于抽象时
- 结果：有帮助
- 适用范围：数学和机器学习公式
- 来源：[[2026-08-29 01 Attention 机制]]
```

`结果` 至少能表达“有帮助”和“无帮助（应避免）”；它描述的是某种讲法在给定情境中的用户反馈，
不是对教学法普遍有效性的证明。

同一信息不能在两个分区重复保存。用户后来明确确认某个教学反馈为长期偏好时，把它移动并
去重到 `明确偏好`，至少保留仍适用的条件、范围和必要来源说明，而不是在两个分区各复制一份；
当前用户陈述始终高于旧的局部反馈。不得把一次反馈扩展成“用户是视觉型学习者”之类人格标签。

“这次讲快一点”“这里先不要公式”等一次性指令只影响当前对话；只有用户表达“以后”“通常”
“默认”或其他明确持续意图时，才写入 `明确偏好`。模型不能仅凭重复行为推断长期偏好。

若偏好或方式反馈来自一次已保存学习，使用 wikilink 指向对应 learning record。用户在独立
数据控制请求中明确设置、纠正或撤销偏好或教学反馈时，可以直接修改该页，不需要伪造
learning record。

学习过程中表达的长期偏好或教学反馈，只有在本次完成并确认保存后才随结果写入；用户明确
要求“现在就永久记录/撤销这项偏好或教学反馈”时，才作为独立数据控制立即修改 profile。

撤销后若两个分区都为空且页面没有其他人工内容，默认删除该可选页面并在同一变更中移除 Home
入口；删除前仍须按第 9 节扫描全部 backlinks，并在同一预览中处理。存在其他人工内容或无法
安全更新 backlink 时保留页面，不为追求空模板而覆盖、删除或制造断链。

#### 初始化时的偏好入口

显式 init 只采集跨主题仍可能有用的默认行为。进入任何菜单或自由讲述前都先提醒：Learning
Guidance 是本地明文 Markdown；新 Vault 默认启用 Git 时会留下历史 commit，配置同步还可能
复制到其他设备。清空当前页面只会停止后续使用，不等于从 Git、同步端或备份中彻底擦除。

用户随后选择“暂不设置/修改（推荐）”“快捷选择”“自由讲述”或“快捷选择后补充”。首次
初始化时暂不设置不会创建规则或空 profile；重跑时暂不修改表示保留已有设置。四组中的
“按主题决定”则表示在用户确认 diff 后删除该维度的全局默认，选择具体行为会新增或替换同一
维度。“清空明确偏好”“清空教学反馈”或“清空两个受管分区”始终是另行显式确认的数据控制
操作；连同用途明确的人工内容删除整页属于范围更强的另一项操作，必须单独预览和授权。

快捷选择最多展示以下四组。每组默认单选，也可以不答：

| 维度 | 可选行为 |
| --- | --- |
| 默认怎样开始 | 快速确认已知再定起点；先具体例子和直觉；先整体框架和定义；按主题决定 |
| 默认怎样互动 | 讲解为主、关键节点检查；多用问题引导；先尝试、卡住后逐级提示；尽量连续讲；按主题决定 |
| 默认详细程度 | 先给简洁全貌再深入；逐步详细展开；可以直接进入较深细节；按主题决定 |
| 默认怎样巩固 | 关键节点给短练习；更频繁检查；只在用户要求时测验；按主题决定 |

Skill 可以临时把选项显示为 `1B 2A 3C` 之类分组编号，用户也可直接说人话或只回答关心的项；
编号只服务当前对话，不写入 Vault，也不要求特定聊天 UI 支持表单或多选组件。用户在同一组
选择多个相反行为时，只有明确补充各自适用条件才能并存，否则 Skill 至多追问一个会真实改变
保存结果的问题；追问后仍无法消解时，首次 init 不保存该维度，重跑则保留原条目，并在最终
预览标成“未更改/未保存”，不能由模型代选。

用户也可以完全不用菜单，直接描述通常有帮助、应该避免，或需要照顾的语言与术语、公式推导、
代码、图表、反例、互动、外部资料和来源的呈现方式，以及可访问性要求。问卷不要求姓名、
年龄、职业、兴趣大全，也不询问全局“初级/中级/高级”、当前主题、截止时间或本轮时间预算；
这些要么与教学行为无关，要么应在每次学习开始时按主题确定。“优先一手来源”“展示关键链接”
等呈现偏好可以保存；允许或禁止联网属于权限，不写入 Learning Guidance，由当前明确指令、
宿主设置、运行环境和 6.3 节的准确性边界决定，不能让旧 profile 静默授权或禁止联网。用户在
init 中表达长期禁止联网时，Skill 明确说明本项不会保存，并指出应通过当前指令或宿主设置控制。

选项只是帮助表达的 UI 脚手架，不是持久 schema：

- Vault 只保存用户确认过的自然语言规则，不保存 `pace=B`、问卷答案或选项目录版本；
- 菜单规则和自由讲述中面向未来的长期要求进入 `明确偏好`；带条件、结果和适用范围的既往体验
  才可进入 `教学反馈`，来源写成“初始化时用户明确陈述（日期）”，不伪造 learning record；
- 仅针对当前主题或本轮的要求不保存；身份、诊断和解释原因默认也不保存，只提取可执行行为。
  教学反馈缺少条件、结果或范围时不能静默补齐，模型先展示候选整理，必要时只追问一个问题；
  追问后仍不完整时，首次 init 不保存该项，重跑保留原条目，并在预览中说明；
- 自由文字只在同一行为维度且适用范围重叠时高于菜单；更具体的条件规则可以与一般默认并存。
  发现真实冲突时只追问会改变行为的部分，再展示最终 Markdown diff；
- 不提供 VARK、视觉型/听觉型、MBTI、注意力类型、智力或能力标签。用户主动使用这类标签时，
  模型把它转换成可执行问题，例如“关系复杂时是否优先用图示”，得到确认后只保存具体行为；
- 真实可访问性需求不能被当成伪学习风格忽略。默认只保存“为图示提供文字替代”“不要只用颜色
  区分”等适配行为，不保存疾病或诊断名称；用户明确要求保留必要上下文时除外；
- 初始化选项不会写成“已验证有效”的普遍教学法；之后的真实反馈仍按本节规则更新。

最终预览再次显示将落盘的自然语言条目和 Git 行为。模型优先保存可执行要求，不保存无必要的
诊断、身份信息或解释原因；用户仍可明确要求保留其认为必要的上下文。

页面中允许使用简单表格或列表，不引入 evidence 表、置信度分数、candidate/active/inactive
状态机或 reducer。只有页面真实增长到影响阅读或检索时才重新拆分，不预建两个近似模型。

### 4.7 `sources/`：轻量外部来源

首版不复制网页全文，也不要求传统 LLM Wiki 的 immutable raw 层。

- 一般网页只在 learning record 和相关 knowledge 页的来源段保存 URL、标题和访问日期；
- 同一来源会被多个页面反复引用、需要独立摘要或包含重要限定时，才创建 `kind: source` 页面；
- source 页面是对来源的可读笔记，不宣称是网页的完整、不可变镜像；
- lint 只检查 `http`/`https` 语法和必要字段，不联网探活或判断可信度；
- 模型没有实际访问过来源时，不得生成看似可追溯的 URL、引文或访问日期。

未来若对可追溯性、时效性或引用审计有真实需求，再增加来源快照和 claim ledger；不在首版
预建。

## 5. 初始化与完成后的直接写入

### 5.1 为什么让模型直接写 Markdown

v2 只有一个用户、一个前台写者，且学习中零写入。继续保留 JSON commit payload、数据库
transaction、receipt、projection rebuild 和恢复 journal，会重新引入已经决定删除的复杂度。

因此模型直接使用文件工具维护 Markdown。CLI 不生成内容、不决定概念边界，也不代理每次
写入。

### 5.2 显式初始化流程

Skill 收到 3.1 节的显式 init 后执行：

1. 只读检查当前 locator、active Vault、候选路径、marker、写权限、`.obsidian/`、保留路径、
   实际 Git top-level、baseline 和已有受管文件；规范化路径并记录将受影响文件、locator 和 Git
   前提的 hash/status，不扫描 home 猜测其他 Vault；
2. 让用户选择新建独立 Vault、注册已有 Vault、保持并验证当前 Vault 或切换到已初始化 Vault，
   并展示规范化后的绝对路径；
3. 新建模式要求目标不存在或为空；existing 模式先说明未忽略的 Markdown 都会参与 stem、链接
   和 backlink 解析，然后只补缺失 scaffold，任何同名或 schema 冲突都在写前阻断；非受管笔记
   保持原样；
4. 对大型已有 Vault，可以根据只读扫描建议 `ignored_paths`，但必须列出将排除的子树并由用户
   确认；不能为让 lint 通过而自动隐藏问题；
5. 可选执行 4.6 节的偏好快捷选择和自由讲述，由模型整理成精确的 Learning Guidance diff；
6. 新独立 Vault 明确区分三种 Git 结果：启用 Git 且以后自动提交（默认）、建立初始 baseline
   但以后不自动提交、完全不让 LearnEverything 操作 Git。首次 existing 注册和 external mode
   不执行 `git init`、stage 或 commit，也不能在尚无 baseline 时选择 `external`；由新建 init
   记录为 managed 的 Vault 可以在重跑时修复 baseline。已受管 Vault 可在 4.2 节的静态条件
   满足时显式修改未来行为。可选 profile 子结果的 Git 动作单独预览；初始化后是否打开
   Obsidian 只是一项当次 UI 选择，不写进配置；
7. 调用确定性 CLI 的 `--dry-run --format json`，再向用户展示一个合并预览：模式、绝对路径、
   locator 旧值与新值、将创建或修改的文件、ignored paths、Learning Guidance diff、Git 动作
   和警告；同时用一句话说明长期数据契约：只保存完成且确认的学习、明确偏好和直接反馈，
   中断学习不保存。CLI 返回覆盖机械参数和 precondition 的 `plan_hash`；Skill 另记录机械 init
   完成后 profile 与 Home 应有的 preimage/hash；若预览会删除 profile，还记录全 Vault backlink
   集合及相关文件 hash。新 Vault 的预期 scaffold 内容也参与计算；
8. 只有用户确认这份预览后才执行；实际 CLI 调用携带 `--expect-plan <plan_hash>`，任一机械
   前提变化就以零写入失败并重新预览，不能静默执行新计划。中途沉默、取消、换任务或修改
   尚未确认的答案均为零写入；
9. 新 Vault 尽量在同一父目录的临时候选中构造机械 scaffold，lint 通过后再放到目标路径；已有
   Vault 记录 scaffold 目标的 preimage/hash 后批量 patch，失败时恢复本批次修改；
10. CLI 完成 scaffold/marker 和首次结构 lint；新 Vault 的 `git.mode: managed` 时，先尝试建立
    只包含机械初始化内容的 baseline，再运行最终 lint。Git 不可用或 baseline 失败且 Git/index
    已安全恢复时只产生 warning；无法恢复则在 locator 前停止。之后只有 canonical target 改变、
    locator 缺失或无效时，才通过临时文件加 atomic replace 激活。已经正确指向当前 Vault 时
    返回 `unchanged_active`，不重写 locator。首次 existing 注册和 external mode 的机械 init
    不创建 commit；
11. 若预览含 Learning Guidance，模型在已经有效的 Vault 上重新读取 profile/Home 和预览涉及的
    backlinks，并核对预期 preimage/hash；任一不匹配都不写 profile，而是重新生成 diff 并再次
    确认。首次创建 profile 时与 Home 同批更新；准备删除空 profile 时先扫描全 Vault backlinks，
    把所有需要更新的受管和非受管链接纳入同一预览。不能安全处理全部 backlink 时保留带空
    受管分区的页面，不制造断链。实际 patch 保留不相关人工内容，然后运行全库结构 lint 和
    限定 diff；失败时
    精确恢复全部受影响文件的 preimage，无法安全恢复则报告路径和“不完整 profile”。新 Vault
    可再创建 `vault: configure learning guidance` commit，但只在 `git.auto_commit: true` 且有效
    baseline 已存在时执行；existing Vault 也只有相同条件满足时才按普通数据控制规则提交，
    否则保留未提交 diff 并说明；
12. 两个子结果都完成或已准确失败后，才按用户选择打开 Obsidian。完成摘要分别报告 Vault、
    Learning Guidance、locator、lint、Git 和 Obsidian 的真实结果。

这里不宣称 Vault、用户配置、profile、Git 和 GUI 存在跨文件系统事务。locator 更新失败时，
根据操作后 locator 的实际解析结果报告；只有目标确实有效但未激活时才使用“目标目录已经是
有效 Vault，但尚未设为 active”，并保留旧 locator。重跑 init 可以安全完成。
已有 Vault 无法安全回滚时，报告“不完整初始化”和具体路径，不能伪装成成功。临时目录和
preimage 在本次操作结束后删除，不形成可恢复的 init session。进程崩溃可能留下未激活的临时
候选目录；重跑只能依据 locator 和有效 marker 重新判断，不能把候选目录当成 init session 恢复。
可选 Learning Guidance 写入失败时保留已经有效且 active 的 Vault，明确报告“Vault 已初始化，
学习指导尚未保存”，用户可直接重试偏好数据控制；不为可选 profile 失败回滚机械初始化。

若用户没有预先 init，却在完成学习后第一次确认保存，Skill 只进入上述流程的必要子集：选择
Vault 模式和路径、dry-run、确认并初始化，不临时插入整套偏好问卷；本次学习中已经明确且满足
保存条件的长期偏好仍可随学习结果正常写入。预览必须说明初始化成功后当前已完成学习将保存到
该 Vault。用户拒绝初始化时报告“学习已完成，但没有保存”；若 Vault 已成功激活，但后续学习
写入失败或对话中断，则保留机械初始化并准确报告“Vault 已初始化；本次学习仍未保存”。

### 5.3 保存流程

用户明确确认结束并保存后，Skill 执行：

1. 精确定位 Vault；若尚未配置，或 locator 指向已删除目录、缺失 marker、schema 不支持等无效
   目标，先报告旧配置错误，再按 5.2 节的必要子集完成路径、dry-run 和初始化确认；用户不授权
   或初始化失败时报告“学习已完成，但没有保存”，不得猜目录或静默创建别的 Vault；
2. 运行一次全库结构 lint；若已有 error，则不做任何学习结果写入，报告“学习已完成但未保存”
   和诊断路径，等待用户单独授权修复；warning 不阻断；
3. 读取 Home、相关 knowledge 页、可能受影响的 profile 和现有 aliases；
4. 在当前上下文中决定创建、更新和链接哪些页面，形成完整变更集，但不把计划持久化；
5. 对拟变更页、相关 learning record、同名/alias/全文重复候选和一跳链接/反链页自动执行
   增量语义审阅；先由模型结合本地证据消解问题，事实正确性、来源冲突或时效性仍不明确时，
   按 6.3 节执行必要或选择性联网核查；
6. 按审阅结果分流：没有实质问题，或只需修正措辞、链接、来源元数据等不改变已交付语义的
   内容时继续；若核查改变了本次已经讲过的核心 claim、完成项或适用边界，停止本轮保存，先
   向用户交付纠正后的讲解，重新回到 3.4 节的完成门槛并等待新的“结束并保存”确认；若仍涉及
   页面边界、合并/删除、人工观点如何保留，或证据不足时如何降级表达等重要取舍，则先给出
   证据、模型推荐及备选项，等待用户决定；对话在任一等待点中断都不写学习结果；
7. 根据审阅结论冻结完整变更集，并记录目标文件的精确写入前内容、hash、Git dirty 和 staged
   状态；这些 preimage 只存在于
   当前进程或 Vault 外临时空间，操作结束即删除；
8. 写前再次读取并核对所有目标；发现 hash、mtime 或 patch 上下文变化时重新合并，并相应
   更新完整变更集和 preimage；
9. 尽量通过一次多文件 patch 更新相关 knowledge、必要的 profile，并新增 learning record；
   首次创建、重命名或删除 Learning Guidance 页面时，同批更新 Home 入口；
10. 再次运行全库结构 lint；
11. lint 失败时先修复本次变更；无法修复时恢复本批次写入前的精确内容并删除本批次新文件，
   不得声称保存成功；若外部修改导致无法安全恢复，明确报告“不完整 Vault”和受影响路径；
12. 检查限定文件的 Git diff，确认没有原始聊天、临时文件或无关改动；
13. 只有所有目标文件在操作前都干净、且操作前 Git index 没有任何 staged 变化时，才 stage
    本次全部路径并创建一个 Git commit；任一条件不满足时整个批次默认不自动提交。始终禁止
    `git add .`。

保存结果中用一行非持久状态说明增量语义审阅实际覆盖了多少拟变更页和邻接页。若新增 record
使总数首次到达新的 10 的倍数，或审阅发现与本次变更无直接关系的系统性风险，先完成当前
保存，再建议是否进行全库深度审阅；这种维护建议不能把已经满足条件的当前保存变成额外 gate。

写入顺序应避免“只有 learning record 落盘、知识页却没更新”的假完成。文件工具支持单次
多文件 patch 时必须使用；不支持时优先写 knowledge/profile，最后创建 learning record。

上述回滚只处理进程仍在运行时发现的普通 lint 失败。首版不承诺进程在多文件写入中途崩溃
后的自动恢复；Git working tree 和下一次全库 lint 可以暴露半写入，但不能把它恢复成学习
会话。只有真实出现多个自动写者、后台同步、并发编辑或频繁半写入事故时，才升级为带
expected hash 的 write-gate。

首版不支持用户在最终保存的几秒内同时修改相同文件。写前复核和 patch context 只能尽力
发现冲突，不构成原子并发保证。

### 5.4 Git 语义

Markdown 文件是事实，Git 是安全网：

- 对全新独立目录执行 `vault init` 时，`git.mode: managed` 默认执行 `git init`；机械 scaffold
  和静态配置通过 lint 后创建一次 `vault: initialize` 初始 commit。可选初始 Learning Guidance
  只有在 `git.auto_commit: true` 且 baseline 成功时才再创建
  `vault: configure learning guidance`；Git 不可用不阻塞 Markdown Vault，只给 warning；
- 新建目标已经位于父 Git 仓库中时，不创建嵌套仓库；用户改选独立路径，或显式 `--git off`
  后让 LearnEverything 完全不操作父仓库；
- 首次 `--existing` 注册及 external mode 的机械 init 不执行 `git init`、stage 或初始 commit，
  沿用其现有 Git 状态；managed mode 的重跑可以修复缺失 baseline。之后的可选 profile patch
  是单列预览的数据控制子结果，才可能按既有安全 auto-commit 配置提交；
- 后续只有 `git.mode` 不是 off、存在 4.2 节定义的有效 baseline、`git.auto_commit: true`、lint
  通过且全部目标操作前干净时，才创建一次只包含本次路径的 commit；
- commit message 使用 `learn: <主题> (<日期>)` 或 `vault: <操作>`；
- 不提交 `.obsidian/` 运行态、`.learn-everything/cache/` 或无关用户修改；
- Vault 中其他路径已有未提交改动时，只 stage 本次明确路径；
- 任一目标文件在写入前已经有未提交人工修改时，模型仍以当前文件为 canonical 进行合并，
  但整个保存批次默认跳过自动 commit 并说明原因；只有用户同意把这些文件当前全部变化一起
  纳入时才提交；
- 操作开始前 index 中已有任意 staged 变化时，整个批次跳过自动 commit，不得把既有暂存内容
  混入，也不使用临时 index 制造难以理解的提交；
- 写入工具报告 context 冲突，或写前复核发现目标变化时，停止覆盖并重新读取；
- 每次 stage 前记录 index preimage；Git commit 失败时恢复原 index，只保留已经成功写入的
  Markdown，并报告“内容已保存，版本快照未创建”。新 Vault 的 baseline 失败且 `.git` 完全由
  本轮创建、尚无 HEAD 时，还原 index 后移除这个空的工具创建仓库，保留 `managed` 配置以便
  下次 init 重试；无法安全恢复 index/Git 状态时报告残留 staged 路径和 degraded 结果，机械
  init 不继续激活一个尚未 active 的目标；
- existing Vault 的实际 Git top-level 不等于 Vault root 时，init 必须预览改成 `off/false` 或
  拒绝操作，并给出父仓库路径；不得仅因目录位于某个仓库内就向该仓库自动提交；
- 没有 Git 时 Vault 仍可使用；只有配置的 mode 不是 off 时 lint 才给出缺少版本保护的 warning，
  用户明确设为 off 后不重复提醒。

Obsidian 中的人工编辑也是 canonical。模型不能假设“生成区域”天然高于人工内容，也不能用
整页重生成静默抹掉用户修改。

## 6. 最小 Vault 工具与 lint

### 6.1 CLI 边界

v2 不保留原意义上的产品 CLI，只保留一个没有学习运行态或业务状态的 Vault 工具：

- 不能只依赖模型自检：跨文件 ID、stem、alias、断链和人工编辑后的完整性都适合由确定性
  程序全库复核，并需要稳定退出码和 golden tests；
- 也不应让工具代理内容写入：概念是否拆分、旧知识如何合并和人工段落如何保留仍是语义判断，
  把它们塞进命令 payload 只会重建一层业务状态和协议。

因此边界是“模型负责语义与 patch，工具负责机械约束”，而不是“模型随意写”或“CLI 掌管
所有数据”。

```text
learn-everything vault init --root <absolute-path> [--existing]
                            [--git managed|external|off]
                            [--auto-commit on|off]
                            [--ignored-path <vault-relative-dir> ...]
                            [--clear-ignored-paths]
                            (--dry-run | --expect-plan <sha256>) --format text|json
learn-everything vault root --format json
learn-everything vault lint [--root <path>] [--base <git-rev>] --format text|json
```

所有 CLI 命令都无交互；缺少必要参数直接失败。用户问答只存在于 Skill 层，因此不提供
`--yes`/`--no-input`，也不提供会覆盖人工文件的 `--force`。

职责：

- `init`：一次性创建、注册或重配置目录和最小模板，不创建学习数据。目标有有效 marker 时始终
  进入 initialized/reconfigure 模式，可安全重跑，是否带 `--existing` 不改变已有身份；无 marker
  且为空或不存在时只允许新建模式；无 marker 且非空时只有 `--existing` 才允许注册；
  `--existing` 指向不存在或空目录、损坏或过新 marker 都失败；
- 新建模式创建受管 `.gitignore`，并按 5.4 节建立初始 Git baseline。existing 注册只在完整
  冲突检查后补缺失 scaffold，绝不覆盖人工文件，也不更改已有 `.gitignore`、Git config、index
  或历史；缺少推荐 ignore 项只给 warning；
- `--git` 和 `--auto-commit` 都是目标静态配置。新建默认 `managed/true`，不接受 `external`；
  `--git off` 在省略 `--auto-commit` 时同时设为 false，与显式 `--auto-commit on` 组合则以退出码
  `2` 拒绝；仅给 `--auto-commit off` 时 Git 仍为 managed，并建立一次 baseline。existing 首次
  注册固定为 `off/false`，显式要求 external 或 auto-commit on 都退出 `2`；已受管 Vault 省略
  参数时保留现值，显式 `external` 必须满足 4.2 节的完整 baseline 条件，`managed` 只能沿用
  由新建 init 已经记录的 managed mode，不能把 existing 仓库改由工具接管；`off` 不删除现有
  `.git`，只停止 LearnEverything 使用它；
- `--dry-run` 返回同一套预检、精确动作、precondition 和 `plan_hash`，但零写入。真正写入必须
  去掉 `--dry-run` 并携带 `--expect-plan <sha256>`；二者互斥。任何 precondition 变化导致退出
  `2` 和零写入，由 Skill 重新展示预览；两者都没有或同时出现也退出 `2`。plan digest 覆盖本次
  完整预检和最终 lint 所读取的状态，至少包括 canonical 可见路径清单及相关内容 hash、marker/
  config、ignored paths、locator、Git top-level/HEAD/index 和所有拟写文件 preimage，不能只 hash
  命令参数或目标文件。plan hash 只做本轮乐观并发校验，不持久化为 receipt；
- `--ignored-path` 可重复，提供时表示完整目标集合；省略时保留已有值或在新 Vault 使用空集合。
  与它互斥的 `--clear-ignored-paths` 显式把现有集合改为空；
- `root`：让 Skill 在任意工作目录精确定位 Vault，禁止猜路径；
- `lint`：全量扫描受管 Markdown，检查文件结构、身份和链接，返回稳定诊断与退出码；可选
  Git base 只用于报告历史变化，不用于缩小全 Vault 身份索引。

退出码固定为：`0` 表示无 error（允许 warning），包括 Git 不可用或 baseline/commit 失败、
Git/index 已安全恢复且 Vault 仍有效的降级结果；`1` 表示发现 lint error，写入型 init 必须先
尝试回滚；`2` 表示参数、配置、plan mismatch、locator、I/O 或工具自身失败。locator 写入失败
返回 `2`，同时准确报告
“Vault 有效但未激活”；回滚本身失败也返回 `2` 并列出受影响路径。JSON 输出至少包含
`schema_version`、汇总计数，以及按稳定 code、severity、Vault-relative path、可选行号和
message 排列的 diagnostics；text 与 JSON 必须来自同一诊断集合。

`init --format json` 还要返回规范化 root、模式、当前/候选 locator、将创建或修改的路径、
Git 动作、冲突列表、`plan_hash`，以及 `vault_valid`、`changed`、`no_op`、`degraded`、
`locator.before/after/status`、各文件与 Git action 的 planned/status、`rollback.status` 与受影响
路径、`git.index_restored`、最终 lint 汇总。相同有效 Vault 且全部期望机械状态已经满足时，
重跑退出 `0` 并报告 no-op；上次 baseline 或 locator 未完成等降级状态不能伪装成 no-op，而应在
新计划中列出可重试动作。非空未标记目录未显式给出 `--existing`、marker 损坏/版本过新、
嵌套 Vault 或任何保留路径冲突都在写入前失败。用户面对的整体 init 只有在机械计划 no-op 且
Learning Guidance diff 也为空时，才能报告 no-op。

明确删除：

```text
session get/start/checkpoint/close
context get
result commit
data inspect/correct/forget
dashboard serve
```

工具不得承担：

- LLM 调用、内容生成或知识合并；
- topic/concept 聚合或用户画像推导；
- session、checkpoint、幂等 receipt 或操作日志；
- SQLite、FTS、embedding、文件 watcher 或 daemon；
- Git 历史的业务抽象；结构、身份和链接始终全量扫描，Git base 只用于比较历史状态并报告
  ID 或 learning record 的修改、移动或消失，不判断用户授权、不提交文件，也不维护 receipt；
- Obsidian 图谱、插件或网页服务。

v2 启用前至少同时交付 init、root 和 lint；可以先共享内部脚本实现，但不能让显式 init 依赖
模型自行猜目录或手写 marker。

### 6.2 结构 lint

lint 默认不联网、不调用 LLM、不修改文件，也不提供首版 `--fix`。

阻断保存的 error：

- `.learn-everything/vault.json` 缺失、无法解析、schema 版本不支持，`ignored_paths` 违反 4.2 节
  约束，`git.mode` 不是 `managed`/`external`/`off`，`git.auto_commit` 不是 boolean，或 mode 为
  off 时 auto-commit 仍为 true；
- `git.mode: external` 但实际 Git top-level、HEAD 或已跟踪必要 scaffold 不满足 4.2 节的静态
  条件；
- frontmatter 无法解析、重复 key、必要字段缺失，或字段类型/固定约束错误（包括重复 alias）；
- `kind` 与目录不匹配；
- `kind: profile` 页面超过一个，ID 不是固定的 `profile.learning-guidance`，或页面存在时没有
  恰好一个 `## 明确偏好` 和一个 `## 教学反馈` 分区；两个分区可以为空，条目内容仍由语义
  审阅判断；
- 受管 file stem 为空或含 4.3 节禁用字符，或 learning 文件的年份、日期、序号与路径、ID、
  `completed_at` 不一致；
- `id` 不符合对应 kind 的固定语法或全 Vault 不唯一；提供 Git base 时，同一路径的既有受管
  文件把 ID 改成另一个 ID；同一 ID 移到新路径视为正常重命名；
- 受管 file stem 与另一个可见 Markdown 的 stem 冲突，或不同 knowledge ID 的
  `{file stem, H1, aliases}` 联合身份 token 产生歧义；
- learning record 缺少 `本次目标`、`已完成内容` 或 `本次沉淀`；
- `本次沉淀` 没有链接任何实际存在且受管的 concept/map；
- 任一受管 note wikilink 不存在或解析到多个页面；未来概念先写普通文本或 TODO，实际建页后
  再改成 wikilink；
- learning record 的 frontmatter 出现固定 legacy 字段集合中的任一项：`status`、
  `session_id`、`checkpoint`、`revision`、`unconfirmed_unit`、`open_session`；文件存在和
  `completed_at` 已足够表达完成；
- source note 的 URL 协议非法或必要字段缺失；
- 受管路径越出 Vault，或存在大小写碰撞。

不阻断保存的 warning：

- knowledge 页既无入链也无出链，且未被 Home 引用；
- 相对所选 Git base，改标题后没有把旧标题保留为 alias；
- 自链接或指向不存在 heading/block 的链接；
- `## 来源` 或 `## 网络来源` 下的某一列表项包含普通 `http`/`https` 链接，但同一列表项
  没有有效 `YYYY-MM-DD` 访问日期；正文其他 URL 不检查此项；
- 相对所选 Git base，既有 learning record 被修改或删除；该诊断只客观提示历史变化，不判断
  是否获得用户授权；
- 相对所选 Git base，一个旧路径和旧 ID 同时消失、另一个新路径和新 ID 同时出现；lint 只
  报告“旧身份消失、新身份出现”，不依赖 Git rename 猜测二者是同一页面；
- `git.mode: managed` 但 Vault 没有 4.2 节定义的可用 Git baseline，无法提供预期版本保护或
  检查历史 record 和 ID 消失；自动 commit 必须跳过，重跑 init 可以重试。mode 为 off 时不为
  同一选择反复告警。

未知 frontmatter properties 默认允许、原样保留且不告警；linter 不做“疑似拼错”启发式
判断。`## 关系` 的关系词和方向属于语义审阅，结构 lint 只检查其中的实际链接。

wikilink 解析忽略代码块、行内代码和 HTML 注释，并在去掉 alias、heading 和 block suffix
后解析目标。目标最终解析到 `.md` 时，无论写成 `[[...]]` 还是 `![[...]]` 都是 note link，
参与断链、backlink 和关系图检查；目标解析到非 Markdown 文件时只检查附件存在，不进入
note 身份或关系图；目标不存在或解析不唯一时是 error。

首版 resolver 用 golden cases 固定以下语义：note 可以写唯一 stem 或 Vault-relative path，
`.md` 扩展名可省略；路径不能是绝对路径或包含 `..`。stem 和 path 都按 NFKC/casefold 匹配，
因此仅大小写不同的候选会触发前述碰撞 error，而不是依赖当前文件系统碰巧选中一个。
`[[note#heading]]` 和 `[[note^block]]` 先解析 note，再检查规范化后的 heading/block；缺失目标
按 warning 报告。非 Markdown 附件必须显式写扩展名，重名时必须写 Vault-relative path；
`![[name]]` 只按 note 解析，不猜测无扩展名附件。note 与附件同名时由实际扩展名确定类型，
不能由前缀 `!` 决定。

### 6.3 知识库语义审阅

结构 lint 不能判断知识质量。语义审阅由模型执行，不属于 `vault lint` 命令，并分为“保存前
增量审阅”和“显式全库审阅”。共同检查：

- 可能重复、同义或边界重叠的概念页；
- 同一概念中互相矛盾、被新证据推翻或可能已经过时的解释；
- 过度宽泛、过度碎片化或只有标题的页面；
- 缺失的关键链接、错误的关系类型或孤立 map；
- profile 中被错误长期化的一次性指令、跨分区重复、缺少条件/结果/范围的教学反馈、存在对应
  learning record 却缺少来源链接的反馈、同一情境下相反的反馈、新偏好与旧条目之间未处理的
  冲突，以及未经明确反馈支持的人格化推断；
- 来源与正文之间不一致，或证据不足以支撑的表述。

#### 保存前增量审阅：自动

用户确认结束并保存后、任何 Vault 写入前，Skill 自动审阅本次拟创建或修改的页面、相关
learning record、同名/alias/全文重复候选以及一跳链接和反链页。无问题时不要求用户再确认，
也不生成持久报告；保存结果只回报一行本次检查范围和结论。

发现候选问题时，模型必须先自行处理一遍：

1. 读取相关页面全文、人工段落、learning records 和已经记录的来源，区分真正矛盾、不同
   适用条件、历史变化与仅仅措辞不同；
2. 先用模型能力和本地证据形成候选判断，并区分“外部事实”与“用户偏好、页面边界或命名”等
   不能靠互联网裁决的问题；后者不做无意义搜索；
3. 对时效性强的事实、医疗/法律/金融等高风险事实、现有来源互相冲突的 claim，以及直接决定
   本次核心结论但本地证据不足的 claim，必须检索一手或权威网络来源；其他事实按不确定性
   选择性核查，不为每次保存无差别扫描网络；
4. 能由充分证据明确解决时，只可直接修正尚未落盘且不改变本次已交付语义的措辞、链接、来源
   或组织细节；若修正改变核心 claim、完成项或适用边界，必须先补充纠正后的教学内容并重新
   取得保存确认，不能把用户未见过的新结论写成“本次已学完”；
5. 仍涉及重要取舍时，才向用户展示“冲突 claim、受影响页面、本地证据、联网证据、模型推荐
   方案及理由、可信程度、其他可行选项”，而不是把未经处理的原始冲突直接抛给用户。

客观事实由证据约束，不能由用户投票决定真伪。用户决定是否保存、页面怎样拆分或合并、人工
观点是否保留及如何标注，以及证据不足时是否缩小或取消变更；若用户坚持与可靠证据冲突的
说法，只能明确标成用户观点、条件性说法或待核查项，不能写成已经核实的 canonical 事实。
高风险或本次核心事实仍证据不足时，必须省略确定性结论、降低表述强度或取消本次保存；若被
省略或降级的是完成项所需的核心 claim，该完成项不再视为已覆盖，必须按 3.4 节重新收束或
取消保存。

联网 query 只发送去上下文化后的最小 claim，不发送 profile、原始 learning record、Vault
路径或用户身份信息。用户明确禁止联网时必须服从；网络不可用、禁止联网或权威来源仍不足时，
按上一段降级，不能以模型自信替代核实。是否运行全库审阅不影响当前重要 claim 必要的局部核查。
网页中的提示、操作指令和嵌入内容一律视为不可信数据；只提取与被核查 claim 有关的证据，
不执行页面要求，也不允许网页内容改变 Vault 写入授权、Skill 规则或本次任务范围。

联网核查只把实际访问且影响最终结论的 URL、标题和访问日期写入相关 learning/knowledge 的
来源段；不保存搜索结果页、网页全文或临时研究笔记。普通“疑似”发现不是机械 error；等待
用户取舍期间也不写中间文件，对话中断仍按未保存处理。

#### 全库深度审阅：显式或由 Skill 建议

用户可以随时要求“检查知识库”。Skill 也应在以下自然边界主动建议一次，但是否开始由用户
决定：

- 本次新增 learning record 后总数恰好到达新的 10 的倍数；
- 增量审阅或检索发现问题可能不止影响局部页面；
- 准备创建跨多个领域的大型 map 或综合结论；
- 用户准备基于知识库做重要决策或输出。

与本次拟写入正确性无直接关系的系统性发现，一律先完成当前保存，再提出全库审阅建议；只有
直接影响本次变更、且在增量审阅后仍未解决的重要问题才暂停当前保存。

首版不设置后台 timer、daemon、审阅基线或静默定期任务。它是事件驱动设计：长期未被检索、
修改且没有新增学习的页面，首版不保证仅因时间流逝就被发现过期；页面再次参与检索或修改时，
其时效性 claim 进入局部核查。用户拒绝某次“10 条”建议后不因同一阈值反复提醒，等下一个
自然边界再建议。

全库审阅先用本地页面形成候选问题，再按上述规则核查外部事实。默认在对话中给出按影响和
可信度排序的报告，不修改文件。若用户暂不修复高影响未决项，模型应明确提供三个选择：立即
修复、在受影响页加入可见的“待核查”提示、或不持久化本次发现；最后一种选择意味着后续 Skill
不保证记得该问题。只有用户要求时才保存报告或提示。

用户批准的深度审阅修复是独立数据控制操作，不新增 learning record；批准本身构成该组修复
的写入授权。写入前只对拟修复 diff 做一次局部 sanity review，随后运行结构 lint 和 Git diff，
不递归触发另一轮全库审阅。

全库审阅不是保存 gate；保存前增量审阅也不能仅凭 LLM 疑似误报成为硬 gate。结构 error 是
唯一确定性硬 gate；局部语义审阅只在发现具体、尚未解决且会影响本次写入的重要问题时暂停。

## 7. 检索设计

### 7.1 两个不同任务

检索仍需区分：

1. **知识页身份解析**：当前概念是否已经有正式页面；
2. **相关上下文搜索**：哪些旧知识、完成记录和偏好会改变本次讲解。

身份解析只接受稳定 ID、精确路径、规范化完整标题或已存 alias。全文或语义相似命中只能
表示相关，不能自动覆盖、合并或复用另一个页面的身份。

### 7.2 首版检索管线

```text
定位 Vault
  -> 结构预检；排除有 error 的正文但保留其路径/stem 占位
  -> 读取 Home、knowledge frontmatter 和 profile
  -> ID / 路径 / 标题 / alias 精确解析
  -> rg 或等价全文扫描受管页面的标题、正文和 learning records
  -> 沿显式 wikilink / backlink 扩展一跳
  -> 模型选择少量真正影响本轮讲解的页面
```

默认装配优先级：

```text
当前用户陈述
  > Learning Guidance 中的明确偏好
  > 与当前情境匹配、且有直接反馈依据的教学方式
  > 精确或高相关 knowledge 页面
  > 这些页面的一跳前置/组成/相关关系
  > 必要时最近 1–2 条相关 learning records
```

检索必须控制上下文：先读 frontmatter、H1、关系和摘要，再按需展开正文；不能把整个 Vault
塞入提示词。learning records 主要用于确认历史目标、近期衔接和知识页变更背景，不应与
knowledge 页全文重复召回。

正面和负面教学反馈具有相同证据权重，都只在其记录的条件与范围内适用。同一情境存在相反
反馈时不得静默选一条；模型先结合最近的明确陈述、上下文差异和来源形成推荐，仍无法消解时
再询问用户，并在用户确认后合并、收窄或撤销旧条目。

若检索结果包含互相冲突的旧知识，模型不得静默挑选一条继续讲解。应先读取相关上下文和来源，
按 6.3 节的条件完成必要联网核查，再给出暂定判断；只有仍涉及用户特定取舍或可靠证据不足时
才询问用户，并顺带建议是否进行一次全库深度审阅。

### 7.3 索引升级边界

首版不上 FTS 服务或 embeddings。文件扫描、`rg`、精确 alias 和一跳链接在个人规模下先行。

只有真实检索评测持续出现下列问题，才增加本地可重建索引：

- 中文改写或跨语言表达持续漏召回；
- 页面数增长后文件扫描延迟不可接受；
- 前置关系未显式链接且全文搜索持续找不到；
- 真实查询集证明语义候选能稳定提高召回。

未来索引无论采用 BM25、向量或混合搜索，都必须：

- 由 Markdown 全量重建；
- 放在 `.learn-everything/cache/` 或 Vault 外；
- 不决定页面身份，不自动生成关系；
- 删除后不丢失任何学习或 profile 信息；
- 明确模型、分词器和索引版本；
- 即使实现内部使用 SQLite，也只能是可删除缓存，不成为 LearnEverything 业务存储。

v2 core 自身不创建或依赖 SQLite。

## 8. Obsidian 作为界面

### 8.1 不再建设 Learning Atlas

Obsidian 已经提供首版需要的主要阅读能力：

| 用户需求 | Obsidian 表达 |
| --- | --- |
| 当前学习偏好、有效或应避免的讲法 | `profile.learning-guidance` 页的两个分区 |
| 学过的东西 | `learning/` 文件夹和 knowledge 页中的学习记录反链 |
| 当前知识 | `knowledge/` 页面 |
| 大小概念关系 | wikilink、backlinks、Graph View |
| 查找内容 | Search、Quick Switcher、Properties 和 aliases |
| 变化与撤销 | Git diff/history；可配合任意 Git UI |

因此删除以下产品范围：

- `dashboard serve`；
- `/api/v1/*` 只读接口；
- 独立前端工程、路由、图谱组件和 API DTO；
- loopback server、端口、浏览器安全头和静态资源缓存；
- “网页只读、未来再编辑”的双界面演进路线。

Obsidian 本身可以编辑。人工修改立即成为 canonical，模型下次必须基于当前文件继续维护。

### 8.2 首页和视图

`Home.md` 是轻量入口，不复制完整数据库式统计。建议包含：

- Learning Guidance 页面入口（仅在页面存在时加入；首次产生 profile 内容时同批更新 Home）；
- 主要 map 页面；
- 一段说明，提示在 Obsidian File Explorer 中按年份浏览 `learning/`；目录本身不伪装成
  wikilink；未来只有确有浏览需求时才增加年度 index note；
- 如何使用搜索、backlinks 和 Graph View 的简短说明。

首版不让模型维护“最近 N 条”或计数等易漂移列表；学习记录按文件名和目录日期排序即可。

动态表格可以以后使用 Obsidian Bases、Dataview 或其他插件，但它们都是可选显示层，不得让
Vault 的可读性和检索依赖某个插件。首版不维护自定义主题、CSS 或 Canvas 作为产品必需项。

init 不创建或修改 `.obsidian/`，也不安装主题、插件或 CSS。初始化成功后只需告诉用户在
Obsidian 中选择“Open folder as vault”；只有用户在预览中明确选择且本机能力可用时，才在
locator commit point 之后代为打开，不把“是否打开”保存成配置。

## 9. 数据控制与人工编辑

用户可以：

- 直接在 Obsidian 中修改 Markdown；
- 在对话中要求模型纠正知识、设置或撤销偏好或教学反馈；
- 重跑 init 以验证当前配置、更新学习指导或切换 active Vault；
- 要求重命名、拆分、合并或删除知识页；
- 要求纠正或遗忘一条完成学习记录。

规则：

- 修改前先读取目标页、backlinks 和可能冲突的 aliases；
- 重命名保留稳定 ID，并在同一变更中更新 wikilinks；
- 拆分或合并页面要明确旧页面去向和所有受影响链接；
- 删除前列出 backlinks；用户明确授权后删除并清理悬空链接；若某 learning record 的
  `本次沉淀` 因此不再有任何有效 concept/map，则必须先得到用户对“改指向另一个语义准确的
  现存页面”或“同时纠正/删除该 record”的明确选择，否则拒绝硬删除 knowledge 页；
- learning record 的修改或删除必须来自明确数据控制请求，不能由普通学习保存顺便完成；
- init 中写入偏好属于独立数据控制，不创建 learning record；重跑时默认局部合并，冲突条目
  按“保留、新增、替换、删除”展示精确 diff，不能简单追加或重置整页；语义等价时保留原文，
  不为润色制造无意义 diff 或 commit；
- 用户可以分别“清空明确偏好”“清空教学反馈”或“重置两个受管分区”，每种范围都需要显式
  授权；始终保留用途不能确认的人工内容。两个受管分区清空且没有其他人工内容时，按 4.6 节
  删除可选页面和 Home 入口；这不会自动擦除 Git、同步端或备份中的历史；
- 切换 active Vault 不搬运旧 Vault 的 profile、知识或历史；如需复制或合并，必须作为另一项
  明确数据操作单独预览；
- 模型不得覆盖不理解的人工段落，应保留或向用户说明冲突；
- 由 Skill 代办的数据控制修改完成后运行 lint，并按目标文件的 dirty-state 规则创建 Git
  commit；用户直接在 Obsidian 中编辑时不要求后台 watcher，下一次使用 Skill 或主动运行
  lint 时再检查。

不存在 `data correct`、`data forget` 或数据库级 cascade。文件修改本身就是数据控制，Git
提供检查和撤销。

默认“移除/遗忘一条学习记录”只从当前 Vault 和后续检索中删除该历史文件，不自动删除已经
沉淀进 knowledge 页的当前知识。若用户还要求删除相应知识，必须先列出受影响页面再处理。
若 profile 中的教学反馈以该 record 为来源，删除前必须列出依赖条目，并让用户选择同时删除
该反馈，或在当前明确重申后将它改写为长期偏好；不能只删来源链接却继续把它描述成有直接
反馈依据的结论。其他 managed backlinks 也必须改为普通历史文字、重定向或删除，不能留下
断链。
普通 Git commit 仍可能保留被删除内容的历史；从 Git 历史和备份中安全擦除属于另一项高风险
数据操作，首版不实现，也不能把普通文件删除描述成彻底擦除。

## 10. v1 数据与切换

v2 不导入 v1 的暂停会话、checkpoint、topic memory、concept note 或 SQLite 投影。未完成
会话直接视为未保存，不进入 Vault、profile 或检索。

正式切换前的部署步骤应：

1. 显示旧数据库和旧数据根的绝对路径；
2. 按用户选择创建备份或归档；
3. 初始化新的独立 Vault；
4. 验证 init 的 atomic locator 已把新 Vault 设为 active；
5. 用 Obsidian 打开并运行全库 lint；
6. 只有用户明确授权后才删除旧数据。

用户目前允许破坏性重构意味着代码和 schema 无需兼容，不意味着实施时可以静默删除个人
数据。当前设计阶段不删除或迁移任何数据。

## 11. 验收标准

### 11.1 显式初始化

- 只有明确的 LearnEverything/Vault 初始化或重配置意图进入 init；普通“从零学习”不会误触发；
- 路径、问卷答案和自由讲述在最终预览确认前均为零写入；
- CLI dry-run 与实际执行使用同一预检和计划模型，并通过 plan hash 绑定用户批准的 precondition；
  计划变化时零写入并重新预览；
- 非法参数组合、filesystem/home 根、损坏 marker、未授权的非空目录和嵌套 Vault 都在写前以
  配置错误失败；existing ignored paths 可以显式清空而不是靠省略参数猜测；
- 新 Vault 加跳过偏好时不创建 `Learning Guidance.md`、knowledge/source/learning 内容页或
  `.obsidian/`；允许创建最小空目录 scaffold；
- 快捷选择与自由讲述只写用户确认过的自然语言规则，不写枚举、原始问卷或人格/能力标签；
- existing 模式不覆盖人工文件；首次注册和 external mode 的机械 init 不初始化、stage 或提交
  Git，可选 profile 子结果只在既有安全 auto-commit 已启用且预览明确列出时提交；managed mode
  重跑只可修复其自身 baseline；保留路径冲突时 locator 保持不变；
- 位于父 Git 仓库中的 Vault 必须把 Git mode 设为 off，并显示实际 Git top-level；
- 机械状态和 profile diff 都为空时整体重跑才返回 no-op，不重复页面、链接、条目或 commit；
- 切换 active Vault 时先验证新根，以原子 locator 更新作为机械激活点，不移动、复制或删除旧
  Vault；目标已经 active 时 locator 保持 `unchanged_active`，不为重跑制造写入；
- 初始化中断或 lint 失败不会激活半成品；无法安全回滚时准确报告目标路径和不完整状态；
- 重配当前 active Vault 失败时恢复精确原内容；无法恢复则明确报告“active Vault 不完整”，
  不能只因为 locator 没变就声称安全；
- 可选 Learning Guidance 失败时保留并准确报告已经有效的 Vault，不声称偏好已保存；
- Git 或 Obsidian 不可用不会被误报成 Vault 无效，相关子结果分别报告；JSON 能区分有效性、
  locator、Git、rollback、final lint、no-op 和 degraded 状态。

### 11.2 零中间持久化

- 学习工作流自身在广泛学习开始、诊断、教学、修复、巩固和等待结束决定时不写 Vault；用户
  同时进行的 Obsidian 人工编辑和明确独立的数据控制请求不在此限制内；
- 中断、沉默、换 task、诊断未完成或用户提前结束时没有新 learning record；
- 学习中检索网络不会在项目中创建 source、缓存或临时笔记；
- 当前对话之外没有 open/paused session 状态。

### 11.3 完成保存

- 只有目标已覆盖且用户随后明确确认保存时才修改 Vault；
- 保存前临时 init 即使成功，也不等于当前学习已经保存；确认前中断，或进程仍在且成功回滚的
  普通写入失败，不得留下这次学习的部分结果。进程崩溃、外部并发或回滚失败仍按 5.3 节准确
  报告“不完整 Vault”，不承诺跨进程自动恢复；
- 每次保存新增一个结构完整的 learning record；
- 本次值得长期复用的知识被创建或合并进 knowledge 页；
- 只有明确偏好或直接教学反馈才修改 profile；
- 写入前自动完成局部增量语义审阅；模型先结合本地证据和必要的联网核查处理问题，只有仍有
  重要取舍时才请求用户决定；
- 核查若改变本次已交付的核心结论或完成边界，会先补充教学并重新等待保存确认，不把未交付的
  新结论记为“已学完”；
- 保存回执显示本次增量语义审阅的页面范围，但不创建审阅报告或中间状态；
- 保存结果不包含 raw chat、诊断答案或逐轮事件；
- 结构 lint 无 error；
- Git mode 不是 off、baseline 有效、auto-commit 开启且全部目标操作前干净时，commit 只包含
  本次明确路径，不收进无关用户修改；
- Git 失败与 Markdown 保存失败分别、真实地报告。

### 11.4 知识质量

- 大小主题使用同一 knowledge 身份模型，没有重复 `topics`/`learner_concepts`；
- 一个普通名词不会因为被提到就自动获得页面；
- 标题和 alias 不能导致身份歧义；
- knowledge 页面不声称用户已掌握；
- profile 不生成能力等级、人格标签或无直接反馈的学习者类型；
- 一次性教学指令不进入长期 profile；同一信息不跨两个分区重复；
- 教学反馈能表达有帮助和无帮助，包含条件、结果和适用范围，并在存在相应 learning record 时
  链接来源；相反反馈不会被静默覆盖；
- 模型更新页面时保留与本次无关的人工内容。

### 11.5 检索

- 精确 ID、路径、标题和 alias 能稳定找到同一页面；
- 模糊全文命中不能自动合并或覆盖知识身份；
- 检索会沿显式链接扩展相关前置，而不是只返回字符串最相似页面；
- 当前用户陈述优先于旧 profile；
- 检索到互相冲突的旧知识时不静默选边，先结合来源和必要的联网核查形成暂定判断；
- 首版没有向量索引时仍能通过真实中文查询 golden cases；
- 不可用或空 Vault 不阻塞教学。

### 11.6 lint 与数据控制

- lint 能检测无效 frontmatter、重复 ID、歧义 alias、关键断链、错误 learning record，以及
  profile 页面数量、固定 ID 和两个必要分区；
- warning 不阻断保存，error 阻断“保存成功”的声明和 Git commit；
- lint 不联网、不改内容、不判断事实正确性或掌握程度；
- 保存前增量语义审阅自动运行且无问题时无需再次确认；保存回执仍显示已执行，候选问题本身
  不构成结构 error；
- 全库深度审阅由用户显式启动或由 Skill 在自然边界建议，首版没有后台 daemon；
- 语义审阅先由模型结合本地证据和必要的权威网络来源形成推荐；外部事实由证据约束，用户决定
  是否写入、页面建模、人工观点如何保留以及证据不足时如何降级；
- 必须联网的 claim、网络失败降级和最小化查询隐私边界符合 6.3 节；
- lint 客观报告历史 record 的修改或删除；是否符合用户意图由当前请求和 Git diff 审阅决定。

### 11.7 Obsidian

- Vault 可以直接作为 Obsidian Vault 打开；
- knowledge、learning 和 profile 都能以普通 Markdown 阅读；
- aliases、wikilinks、backlinks 和 Graph View 正常工作；
- 不启动网站、API server 或后台数据库；
- 禁用所有可选插件后，核心内容仍然完整可读。

## 12. 实施顺序

1. 冻结本文中的 Vault 目录、frontmatter、ID、文件名和页面类型；关系词只作为语义约定；
2. 实现无交互 `vault init/root/lint`、用户级 locator、dry-run/plan hash JSON 和冲突 golden cases；
3. 实现新建、existing、切换、参数互斥、canonical path、嵌套拒绝、父 Git 仓库、locator 最后
   激活、部分成功结果和完整机械状态 no-op 测试；
4. 在 Skill 中加入显式 init 路由；`SKILL.md` 只保留路由和核心边界，详细向导、快捷选项与失败
   语义放入按需加载的 `references/init.md`；
5. 重写学习流程，删除 session/checkpoint，并实现完成后增量语义审阅与直接 Markdown patch；
6. 实现基于标题、alias、`rg` 和 wikilink/backlink 的上下文检索；
7. 加入限定路径 Git commit 和人工编辑保护测试；
8. 用真实 Obsidian Vault 做链接、改名、Graph View 和手工编辑 smoke test；
9. 增加 init 中断零写入、跳过偏好、菜单加自由描述、冲突合并、重跑和切换测试；
10. 增加保存前增量审阅、检索时冲突防护和显式全库深度审阅用例；
11. 增加 profile 固定 ID/分区、一次性指令、正负反馈和删除来源 record 的用例；
12. 经过端到端验收后，才执行显式的 v1 数据备份与切换。

首版没有前端、API、SQLite schema、数据库迁移、FTS 或 embedding 实施工作。

## 13. 已确认决策

- 学习中零写入，未完成或中断时不保存；
- 不提供暂停和跨对话恢复；
- 提供显式、可重跑的对话式 init；普通学习不会因 Vault 缺失自动进入完整初始化问卷；
- Skill 负责 init 交互与偏好语义，CLI 只做无交互机械预检和 scaffold；
- 完成后仍需用户明确确认，下一轮才保存；
- Markdown Vault 是 LearnEverything 唯一业务事实源；
- Git 提供版本历史和撤销；
- Obsidian 是首版唯一的人类浏览/编辑界面，不建设 Learning Atlas；
- `learning/` 保存完成历史，`knowledge/` 保存当前 Wiki，`profile/` 保存明确偏好与教学反馈；
- profile 首版只用一个 `Learning Guidance` 页面，以正文分区保留“明确偏好”和“教学反馈”
  的证据差异；
- init 偏好可跳过、可用行为选项或自由讲述；只存确认后的自然语言，不存问卷枚举或学习风格
  标签；
- 大、小概念统一为 knowledge 页面，以 `concept`/`map` 区分主要职责；
- 不默认保存 raw chat 或网页全文；
- 模型直接修改 Markdown；
- 保留没有学习运行态或业务状态的结构 lint，不保留业务 CLI 或 write-gate；
- 首版使用精确身份、全文搜索和显式链接，不使用 embeddings；
- 保存前自动做局部语义审阅；模型先用本地证据和必要联网核查形成建议，事实由证据约束，用户
  决定写入和知识组织；全库深度审阅显式执行或由 Skill 主动建议；
- Obsidian 人工编辑也是 canonical，模型必须保留人工内容。

## 14. 实施前默认项

以下按推荐默认值进入实现；若评审时反对再调整：

1. **Vault 位置**：使用独立目录，再由 Obsidian 打开；不默认混入已有大型 Vault。
2. **Git commit**：新独立 Vault 默认初始化 Git，并先为机械 scaffold 提交 baseline；可选初始
   profile 成功后单独提交。首次 existing 注册和 external mode 的机械 init 不操作 Git，首次
   注册的 auto-commit 固定关闭且 mode 为 off；用户手工提交 scaffold 后，只有 Git top-level、
   HEAD 和已跟踪 scaffold 满足 4.2 节条件时才能启用 external mode。clean index 是每次 commit
   gate，不是静态启用资格。
   可选 profile 子结果再按既有 auto-commit 配置决定是否提交。学习保存只 stage 本次明确路径；
   任一目标文件预先 dirty 或 index 预先存在 staged 变化时整个批次默认跳过。
3. **文件命名**：按 4.3 节从可读标题生成安全 stem，learning 文件包含日期和序号；稳定
   ASCII `id` 负责机器身份。
4. **来源策略**：普通网络资料只存链接和访问日期；反复复用时才创建 source note。
5. **CLI 形态**：保留无交互的 `init/root/lint`；init 支持 dry-run + plan hash、text/json、
   existing、ignored paths 和 `git.mode`，不支持 force，也不接收偏好枚举或自然语言内容。
6. **语义审阅**：每次保存前自动审阅拟变更页及一跳关联；当新增记录使总数到达 10 的倍数、
   发现系统性风险或进行大型综合前，由 Skill 在不阻塞无关当前保存的时点询问用户是否运行
   全库审阅；不创建后台定时任务或审阅状态机。
7. **init 偏好**：默认允许全部跳过；快捷选项只覆盖开始方式、互动、详细程度和巩固等可执行
   行为，自由讲述可以补充语言、公式、代码、图示、反例和可访问性要求。

## 附录 A：初始化设计调研依据

本节只记录影响设计取舍的外部实践，不作为运行时依赖：

- [shadcn CLI](https://ui.shadcn.com/docs/cli) 和
  [Astro 安装向导](https://docs.astro.build/en/install-and-setup/) 都把交互式问答放在人类入口，
  同时保留参数化命令、默认值和明确覆盖行为；本设计因此把对话式 Skill 与确定性 CLI 分层；
- [npm init](https://docs.npmjs.com/cli/v11/commands/npm-init/) 与
  [Cookiecutter](https://cookiecutter.readthedocs.io/en/stable/advanced/suppressing_prompts.html)
  提供可跳过问答、使用默认值和重放配置的路径；本设计采用可跳过、可重跑、语义等价 no-op，
  但不持久化问卷 replay 或 onboarding 状态；
- [Obsidian Vault 管理说明](https://obsidian.md/help/Files%2Band%2Bfolders/Manage%2Bvaults)把 Vault
  定义为本地目录，并提醒避免嵌套 Vault；本设计优先独立目录，对 existing 和嵌套场景先预检；
- [OpenAI Custom Instructions](https://help.openai.com/en/articles/8096356-chat-preferences-for-chatgpt)
  和 [GitHub Copilot 自定义指令](https://docs.github.com/en/copilot/concepts/prompting/response-customization)
  都以可编辑自由文本表达长期指导；本设计因此把菜单当成输入辅助，最终只保存自然语言规则；
- Pashler 等人的[学习风格证据综述](https://doi.org/10.1111/j.1539-6053.2009.01038.x)没有为按
  固定“视觉型/听觉型”等类型匹配教学提供充分证据；本设计只询问可执行行为和真实反馈，不保存
  学习者类型标签，同时把可访问性适配与此类标签明确区分。
