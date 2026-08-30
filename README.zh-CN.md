# LearnEverything

[English](README.md) | 简体中文

LearnEverything 是一个面向 Codex 的系统学习 Skill。告诉它你想学懂什么，它会先判断目标和
起点，再用合适的例子、表示和节奏逐段讲清楚，到达约定范围后主动收束。

学习过程留在当前对话中。只有内容已经讲完，并且你明确选择保存后，LearnEverything 才会把
学习记录和知识整理到你自己的 Obsidian Markdown Vault。

## 安装

需要本机已有 Node.js 和 npm。安装到 Codex 的用户级 skills：

```bash
npx skills add seventhread/LearnEverything --skill learn-everything --agent codex --global --yes
```

也可以交互式选择安装位置或其他兼容的 agent：

```bash
npx skills add seventhread/LearnEverything
```

安装不会创建或修改学习数据。安装后可以直接开始学习；需要保存知识时，说“初始化
LearnEverything”或使用 `$learn-everything init`，再按提示选择 Vault。

## 使用

系统学习一个主题：

```text
请带我系统学懂 Transformer。我会写 Python，但没有学过深度学习。
```

限定学习深度：

```text
我想理解 Git 的内部模型，目标是能独立排查常见的分支和 rebase 问题。
```

只问一个具体问题：

```text
为什么 softmax 要减去最大值？
```

具体问题会直接回答，不会被强制扩成课程。系统学习则会根据你的目标和已有知识选择起点，
并明确告诉你这次会讲到哪里。

## 它如何工作

1. **确定目标**：区分系统学习和聚焦问题，确认你想达到的结果。
2. **选择起点**：利用当前对话、已有知识或简短诊断，避免从太浅或太深的地方开始。
3. **逐段讲解**：围绕核心关系解释“是什么、为什么、各部分怎样关联”，再用例子落地。
4. **即时调整**：遇到卡点时补前置、换表示、换例子或填上推理跳步。
5. **主动收束**：约定内容讲完后给出总结，由你选择保存、巩固或扩展范围。

LearnEverything 不显示掌握率、学习者等级或题目得分，也不会因为一次答对就断言你已经掌握。
如果学习尚未完成就停止，不会留下半成品记录。

## 保存到 Obsidian

初始化后，Vault 使用普通 Markdown 文件组织：

```text
Vault/
├── Home.md
├── knowledge/   # 当前知识 Wiki：概念、关系和主题地图
├── learning/    # 每次已完成学习的记录
├── profile/     # 你明确表达或直接反馈过的教学偏好
└── sources/     # 学习中实际使用的来源
```

知识页通过 Obsidian wikilink 连接，可直接使用搜索、backlinks、Properties 和 Graph View。
Markdown 是长期内容的事实来源，没有隐藏数据库。随 Skill 提供的确定性工具只负责 Vault
初始化、定位和结构检查，不负责替模型生成知识内容。

## 设计原则

- **讲解优先**：诊断和练习只用于改善下一段解释，不取代解释本身。
- **边界明确**：开始时约定范围，完成后主动结束，不把相邻内容无限追加成必修课。
- **确认后保存**：只有已经交付的内容才能进入记录，并且必须由用户明确确认。
- **本地、开放格式**：长期内容保存在用户选择的 Markdown Vault 中，容易阅读、迁移和版本化。
- **聚焦问题保持轻量**：一个具体问题就是一个具体回答，不强制开启学习流程。

## 开发

- [Skill 源码](skills/learn-everything)
- [设计说明](docs)
- [验收场景](evals/acceptance-scenarios.md)
- [讲解质量标准](evals/explanation-quality-rubric.md)
- [Vault CLI 参考](skills/learn-everything/references/vault-and-cli.md)

运行测试：

```bash
python3 -m unittest discover -s tests -v
python3 -m py_compile skills/learn-everything/scripts/learn_everything_vault.py
```

Vault 工具只使用 Python 标准库。本地开发时，可以把
`~/.codex/skills/learn-everything` 链接到仓库中的 `skills/learn-everything`，让仓库保持唯一可编辑
来源。
