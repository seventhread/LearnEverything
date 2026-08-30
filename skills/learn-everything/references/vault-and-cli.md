# Markdown Vault 与 CLI

需要定位、初始化、检索、保存或检查 Vault 时读取本文件。脚本路径从本 Skill 目录解析为
`scripts/learn-everything` 的绝对路径，不依赖 cwd。

## CLI

```text
learn-everything vault init --root <absolute-path> [--existing]
                            [--git managed|external|off]
                            [--auto-commit on|off]
                            [--ignored-path <vault-relative-dir> ...]
                            [--clear-ignored-paths]
                            (--dry-run | --expect-plan <sha256>) --format text|json
learn-everything vault root --format text|json
learn-everything vault lint [--root <absolute-path>] [--base <git-rev>]
                            --format text|json
```

所有命令无交互。`init` 写入前必须先 dry-run；没有 plan hash、hash 过期或参数组合非法时失败。
CLI 只处理 Vault 的初始化、定位和结构检查；偏好与知识内容由模型维护。

退出码：

- `0`：无结构 error，允许 warning 或 Git 降级；
- `1`：结构 lint error；
- `2`：参数、配置、plan mismatch、locator、I/O 或工具失败。

JSON error 形状：

```json
{
  "schema_version": 1,
  "ok": false,
  "error": {"code": "...", "message": "...", "details": {}}
}
```

不要解析自然语言 message；根据退出码、`error.code`、diagnostics 和结构化状态行动。只有成功
结果才能被描述为已初始化或 lint 通过。

`vault root` 精确读取用户 locator。`NOT_INITIALIZED`、`VAULT_UNAVAILABLE`、`VAULT_INVALID`
在普通学习开始时都降级为空上下文；最终保存时则必须报告并进入显式 init 必要子集。

`vault lint` 默认使用 active Vault；只读，不联网，不调用 LLM，不修改文件。error 阻断保存，
warning 不阻断。

## Vault 结构

```text
<vault>/
├── Home.md
├── knowledge/              # concept / map
├── learning/YYYY/          # 只保存完成记录
├── profile/                # 可选 Learning Guidance.md
├── sources/                # 可选来源笔记
└── .learn-everything/
    ├── vault.json
    └── cache/              # 可删除，首版可不存在
```

`.obsidian/` 由 Obsidian 自己管理，不属于 LearnEverything 事实。

marker：

```json
{
  "schema_version": 1,
  "ignored_paths": [],
  "git": {"mode": "managed", "auto_commit": true}
}
```

Git mode：

- `managed`：由新建 init 创建，可重试 baseline；
- `external`：使用用户已有的 Vault 根仓库，init 不创建或修复 Git；
- `off`：LearnEverything 不使用 Git，且 `auto_commit` 必须为 false。

## 通用 frontmatter

| kind | 位置 | 必填字段 |
| --- | --- | --- |
| `index` | `Home.md` | `id`、`kind`、`updated` |
| `concept` / `map` | `knowledge/` | `id`、`kind`、`created`、`updated`；aliases 可选 |
| `learning-record` | `learning/YYYY/` | `id`、`kind`、`completed_at` |
| `profile` | `profile/` | `id`、`kind`、`created`、`updated` |
| `source` | `sources/` | `id`、`kind`、`url`、`accessed_at`、`created`、`updated` |

固定 ID：

```text
index.home
knowledge.<ascii-slug>
learning.<YYYY-MM-DD>.<ascii-slug>.<sequence>
profile.learning-guidance
source.<ascii-slug>
```

learning 序号是全 Vault 当日递增值：1–9 写 `01`–`09`，10 起不带前导零；文件名固定为
`YYYY-MM-DD <sequence> <安全主题标题>.md`，放入对应年份目录。路径或标题改变不改变 ID。

每个受管 Markdown 恰好一个 H1。knowledge 的 `{file stem, H1, aliases}` 联合身份不能与另一
knowledge 页冲突；任一受管 stem 也不能与可见 Markdown stem 冲突。落盘 wikilink 写实际唯一
stem 或 Vault-relative path，显示名使用 `[[实际文件|显示名]]`。

## 页面形状

learning record：

```markdown
---
id: learning.2026-08-29.attention-mechanism.01
kind: learning-record
completed_at: 2026-08-29T21:00:00+08:00
---

# Attention 机制学习

## 本次目标
...

## 已完成内容
...

## 本次沉淀
- 新建 [[Attention 机制]]。

## 后续方向
...

## 网络来源
...
```

`本次沉淀` 至少链接一个实际存在的受管 concept/map。record 表示内容已交付并确认结束，不表示
掌握；正常学习只新增，用户显式纠正或遗忘时才能改删。

knowledge concept/map：

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
...

## 核心解释
...

## 关系
- 前置：[[向量点积]]
- 属于：[[Transformer]]

## 来源
...
```

`concept` 解释可独立复用的知识点；`map` 组织大主题、子概念和推荐路径。不要把普通名词或一句
细节拆成空洞页面。关系优先用 `属于 / 包含 / 前置 / 组成 / 相关 / 对比` 写在正文。

Learning Guidance 只有一个固定 ID，正文恰好包含：

```markdown
## 明确偏好

## 教学反馈
```

明确偏好来自用户的长期要求；教学反馈必须有条件、结果和适用范围。两者不能重复；没有内容时
不创建空页。删除最后内容前扫描 backlinks，并同步维护 Home。

普通外部来源只在 learning/knowledge 的来源段保存标题、URL 和访问日期；只有反复复用或需要
独立摘要时才创建 source 页面，不保存网页全文。

## 检索

1. 运行 lint，排除 error 文件正文但保留路径/stem；
2. 读取 Home、knowledge frontmatter 和 Learning Guidance；
3. 精确解析 ID、路径、标题、alias；
4. 用 `rg` 或等价全文扫描标题、正文和 learning records；
5. 沿 wikilink/backlink 扩展一跳；
6. 只展开真正会改变本轮讲法的少量页面。

优先级：当前陈述 > 明确偏好 > 条件匹配的直接教学反馈 > knowledge > 一跳关系 > 最近相关的
1–2 条 learning records。模糊或全文命中只表示相关，不能自动覆盖、复用或合并页面身份。
