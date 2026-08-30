# LearnEverything

LearnEverything 是一个 explanation-first（讲解优先）的 Codex Skill：它从合适起点帮助用户
系统学懂一个主题，并在目标真实完成、用户明确确认后，把结果沉淀到用户拥有的 Obsidian
Markdown Vault。

学习中的诊断、完成项、困惑和教学调整只存在于当前对话。尚未覆盖确认边界时的中断、沉默、
换 task 或停止均不保存，也不承诺跨对话恢复。聚焦问题仍然直接回答，不会被强制变成课程。

## 当前规范

[docs/SKILL-DESIGN-v2.zh-CN.md](docs/SKILL-DESIGN-v2.zh-CN.md) 是当前产品、Skill 和 Vault
边界的规范来源。[evals/acceptance-scenarios.md](evals/acceptance-scenarios.md) 与测试是由它派生的
可验证契约；发生冲突时先修正规范或实现，不让两者长期分叉。

v2 的核心决定：

- 学习过程零持久化，只有“已完成 + 用户随后确认保存”才写长期结果；
- 广泛学习默认保留 v1 的前置诊断；到达约定边界时主动收束，不无限推荐“下一段”；
- Markdown Vault 是唯一业务事实源，不再使用 SQLite；
- `learning/` 记录每次完成历史，正常学习流程只追加；
- `knowledge/` 是概念与 map 组成的当前知识 Wiki，通过 wikilink 表达关系；
- `profile/Learning Guidance.md` 用两个分区区分明确偏好与有直接反馈依据的教学方式；
- 模型负责检索、语义判断和 Markdown patch；确定性工具只负责 Vault 初始化、定位和结构 lint；
- Obsidian 提供阅读、搜索、backlinks、Properties 和 Graph View，不另建网站或 API；
- Git 提供版本历史和撤销，但不会收进无关的用户改动。

## 仓库结构

- [skills/learn-everything](skills/learn-everything) — Skill、按需参考和 Vault 工具；
- [docs/SKILL-DESIGN-v2.zh-CN.md](docs/SKILL-DESIGN-v2.zh-CN.md) — 当前 v2 设计规范；
- [evals/acceptance-scenarios.md](evals/acceptance-scenarios.md) — v2 可观察验收场景；
- [evals/explanation-quality-rubric.md](evals/explanation-quality-rubric.md) — 讲解与修复质量门槛；
- [tests/test_cli.py](tests/test_cli.py) — `vault init/root/lint` 黑盒测试。

## Vault 工具

工具使用 Python 标准库，无学习运行态，也不读写知识内容：

```bash
skills/learn-everything/scripts/learn-everything vault init \
  --root /absolute/path/to/vault --dry-run --format json

skills/learn-everything/scripts/learn-everything vault init \
  --root /absolute/path/to/vault --expect-plan <plan_hash> --format json

skills/learn-everything/scripts/learn-everything vault root --format json
skills/learn-everything/scripts/learn-everything vault lint --format json
```

`vault init` 必须先 dry-run，再携带完全相同计划的 `plan_hash` 执行。新建独立 Vault 默认建立
managed Git baseline；注册已有 Vault 默认不操作 Git。完整参数和失败语义见
[vault-and-cli.md](skills/learn-everything/references/vault-and-cli.md)。

运行验证：

```bash
python3 -m unittest discover -s tests -v
python3 -m py_compile skills/learn-everything/scripts/learn_everything_vault.py
```

本地开发时，可把 `~/.codex/skills/learn-everything` 链接到仓库中的
`skills/learn-everything`，让本仓库保持唯一可编辑来源。

## v1 数据

v2 不兼容也不自动迁移 v1 SQLite 数据。仓库的忽略规则继续保护可能存在的本地旧数据；只有
用户明确选择备份、归档或删除时才处理它们。
