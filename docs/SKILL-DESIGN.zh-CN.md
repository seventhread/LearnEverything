# LearnEverything 用户级 Codex Skill 设计（评审稿）

- 状态：待用户评审，不代表已经实现
- 日期：2026-08-21
- 目标版本：v1，单用户、本地状态、同一时间一个可恢复学习会话
- 设计中心：解释与帮助理解是主产品；诊断、检查和记录只为解释与恢复服务

快速评审可先看第 0、5、6、8、9、18 节；实现边界集中在第 11–14 节。

## 0. 一页结论

LearnEverything 是一个安装在用户级目录的 Codex Skill。用户可以在任意项目文件夹中显式调用 `$learn-everything`，也可以通过明确的学习意图（例如“我想系统学 Attention”）触发它。普通的一次性具体问题仍然直接回答，不自动变成一门课。

v1 采用三层结构：

```text
用户级 Skill
  负责：判断入口、诊断起点、设计并交付讲解、修复困惑、判断本次范围何时讲完
                         │
                         │ 结构化 JSON 命令
                         ▼
随 Skill 安装的本地 CLI
  负责：初始化、检索、SQLite 事务、checkpoint、恢复、关闭、查看/纠正/删除数据
                         │
                         ▼
用户选定并完成初始化授权的固定数据目录
  负责：保存规范状态；当前项目目录不保存学习资料
```

核心行为契约如下：

1. 明确开启一个新学习主题时，必须先完成“起点诊断”；若没有可靠先验，常规就是三道低摩擦选择题。
2. 每题必须提供“看选项前不知道，或主要靠猜”；含专业术语、符号或复杂描述时，还必须单独提供“我看不懂这些选项在说什么”。诊断不输出分数、等级或掌握率。
3. 起点决策完成后（常规是三题，确有矛盾时可能是第 4/5 题），下一条回复只能用一句话说明讲解起点，然后在同一条回复中立即开始第一段实质讲解。
4. 讲解是主体：Skill 根据知识结构选择机制图、执行追踪、代码例子、公式、情景表或其他适合的表示；公式只是一个分支，小题只辅助选择下一种讲法。
5. 先形成目标和暂定范围，诊断后再定稿 `done_when`，即“本次承诺讲清哪些内容”。实际讲解计划可随对话微调，但不得静默偏离目标；达到边界后主动收束。
6. v1 同一时间只保留一个可恢复学习会话；可以中断并在以后恢复，但不支持多个主题同时暂停等待恢复。
7. 不保存原始对话、完整答题史、人格标签或掌握概率；只保存会影响下一次解释或恢复位置的压缩状态。适配记忆必须形成“读取、使用、观察、更新、再使用”的闭环，而不是只写不读的档案。

## 1. 目标与非目标

### 1.1 产品目标

Skill 的首要任务是：

> 尽快给当前用户一段与其目标和前置知识匹配的有效解释，并保存足够少但足够准确的上下文，使中断后不用从头开始。

v1 应做到：

- 从任意项目文件夹启动同一个用户级 Skill；
- 对新学习主题做三题为常规预算的起点诊断；
- 以解释、例子和必要的图示帮助用户理解；
- 根据“太难、太抽象、太快、想看例子”等反馈立刻换一种讲法；
- 根据用户的具体目标主动判断何时收束；
- 将一个学习会话暂停、恢复和关闭；
- 用少量历史信息辅助未来前置知识判断；
- 让会话中的有效教学假设在受限作用域内逐步成为可纠正的长期适配信号；
- 允许用户查看、纠正、导出和删除本地记忆。

### 1.2 v1 非目标

- 跨设备同步；
- 多个开放或暂停会话并发管理；
- 准确估计掌握概率；
- 以测验、题库、复习日历或课程图谱为中心；
- 保存逐条事件流或完整聊天记录；
- 自动生成一个覆盖任意主题的完整课程；
- 认证、考试、评分或高风险能力判断；
- 云服务、多用户账户或协作教学；
- 固定“视觉型/听觉型”等学习风格标签。
- 概率化偏好模型、自动跨领域泛化或大规模记忆聚类。

## 2. 入口与激活边界

### 2.1 四种入口

| 用户输入 | Skill 行为 | 是否创建/修改学习会话 |
| --- | --- | --- |
| `$learn-everything Attention` | 保证启动新主题学习流程 | 是 |
| “我想系统学习 Attention” | 可由 Skill 自动匹配，进入新主题流程 | 是 |
| “为什么 Attention 要除以 \(\sqrt{d_k}\)？” | 直接解释具体问题，不做入学流程 | 否 |
| “继续上次的学习” | 读取唯一开放会话并恢复 | 读取已有会话 |

`SKILL.md` 的描述必须足够窄：只有明确的持续学习、恢复或学习数据管理意图才进入本 Skill。普通聊天里偶然出现“学习”一词，或一个可以直接回答的知识问题，不应创建持久会话。

### 2.2 活跃学习中的旁支问题

当一个学习会话正在进行时：

- 与当前目标直接相关的问题，纳入当前解释；
- 临时的无关具体问题，直接回答，但不创建第二个会话，也不污染当前 topic memory；
- 明确要求“开始学习另一个主题”时，必须说明 v1 只有一个可恢复槽位，并让用户先关闭旧会话。旧会话关闭后仍保留压缩 topic memory，但不再保证按原 checkpoint 精确恢复。

任何情况下都不能静默覆盖现有开放会话。

## 3. 总体交互状态机

```text
                         ┌─ 具体问题 ─→ DIRECT_ANSWER ─→ 结束
用户请求 ─→ 入口判断 ────┤
                         ├─ 恢复请求 ─→ RESUME ───────────┐
                         │                               │
                         └─ 新学习 ─→ ORIENT ─→ DIAGNOSE │
                                                        ▼
                                                   EXPLAIN
                                                    │  ▲
                          困惑 ─→ REPAIR ───────────┘  │
                                                    │  │ 明确扩展目标
                                                    ▼  │
                                      DELIVERED_AWAITING_DECISION
                                                    │
                                    总结 + 明确结束判断
                              ┌─────────────────────┼───────────────────┐
                         用户结束              用户要继续深入     用户明确暂停
                              │                     │                   │
                            CLOSE       更新 done_when → EXPLAIN      PAUSED

任一持久学习状态 ── 用户明确暂停 ─→ PAUSED ── 恢复并 claim ─→ 原概念边界
异常中断 ─→ 保持原状态并留下 pending_delivery ─→ 下次 claim 后保守重放
```

这里的 `DELIVERED_AWAITING_DECISION` 只表示约定的解释范围已经覆盖、正在等待用户结束或扩展，不表示用户“掌握”。

## 4. 开始阶段：目标、范围与起点

### 4.1 目标获取

用户已经说清目标时，不重复询问。例如“我的目标是看懂 Q/K/V 公式”已经足够。

目标不清楚且不同目标会显著改变讲解时，才用一次低摩擦选择让用户确定希望达到的结果。内部可映射为：

- `orientation`：能认出概念，并与相邻概念区分；
- `explain`：能看懂并复述核心机制；
- `apply`：能在典型情境中使用；
- `independent`：能处理新情境、比较方案或排查失败。

目标深度是讲解范围输入，不是诊断题，也不产生用户等级。

### 4.2 目标、暂定范围、`done_when` 与讲解计划

这四层不能混成一份固定 step 列表：

| 层次 | 回答的问题 | 变化规则 |
| --- | --- | --- |
| `goal` | 用户最终为什么学、想达到什么结果？ | 最稳定；只有用户改变目标时才改变 |
| `provisional_scope` | 为了设计诊断，初步认为可能要覆盖什么？ | 诊断前形成，只是工作假设 |
| `done_when` | 诊断后，本次至少应交付哪些解释才不算漏项？ | 半稳定；可以在原目标内拆分、合并或重写 |
| `teaching_plan` | 下一段先讲什么、用什么表示、是否补前置？ | 高度动态，随用户反馈持续变化 |

Skill 先根据目标和相关历史形成 `provisional_scope`，用它识别会改变讲解的前置知识并设计诊断；起点决策完成后，才将范围定稿成 2–5 条 `done_when`。诊断显示用户已经熟悉的基础不必机械重讲，暴露出的必要桥梁则进入讲解计划；它们只有在本身属于目标交付范围时才成为新的 `done_when` 项。

```yaml
goal:
  purpose: 看懂大模型 Attention 中的 Q/K/V 公式
  target_depth: explain
  provisional_scope:
    - Q/K/V 角色
    - 相似度到权重
    - 权重到输出
  done_when:
    - id: dw-01
      delivered_when: 已解释 Q、K、V 由输入经过不同投影得到，并逐一说明角色
    - id: dw-02
      delivered_when: 已沿着 QK^T → 缩放 → softmax → 加权 V 拆解公式
    - id: dw-03
      delivered_when: 已给出一个最小数值例子并解释基本矩阵形状
  out_of_scope_by_default:
    - causal mask 的工程细节
    - multi-head attention
```

`done_when.id` 只是当前会话中的稳定引用，例如 `dw-01`；它不是预先存在的课程 ID，也不承担跨主题检索。跨主题知识使用另行命名的 `concept_key`。`done_when` 本身无强制顺序，Skill 不必在开头展示完整列表；目标很宽、边界有歧义或代价较大时，才用一句话确认范围。`provisional_scope` 在诊断后只作为形成起点的出处保留，不能参与完成判断。

在对话中，Skill 可以自行：

- 调整讲解顺序、例子、表示和单元大小；
- 将一个 `done_when` 拆开、合并或改写得更准确；
- 添加只为打通主线所需的最小前置桥梁；
- 删除用户明确表示不需要、且不会破坏原目标的范围项。

每次调整必须满足至少一个条件：直接服务原目标，或解决阻塞原目标的必要前置。若既不满足，也不是用户明确提出的新方向，就只能作为可选旁支。扩展到相邻高级主题必须得到用户明确方向，不能以“优化计划”为名静默扩课。

持久状态用 `scope_revision` 标记当前 `done_when` 版本；拆分产生新会话内 ID。范围变化前必须先清除已有 `pending_delivery`：有送达证据则结算；没有证据则丢弃 intended updates，或先重放并让用户确认。随后才能通过 revision 保护写入新范围，避免待交付单元引用过期范围。

范围修订必须同时写 `coverage_migration`，不能因为换了 ID 而丢失或凭空继承进度：

- 语义等价的改写保留原 ID 和已确认 coverage；
- 拆分时新项带 `supersedes: [旧 ID]`，只把已有交付证据明确覆盖的子部分迁入，其余新项保持未交付；
- 合并时新项带全部 `supersedes`，只有所有组成项都已交付，或现有交付证据明确覆盖合并后的完整条件，才可继承 delivered；
- 新增项默认未交付；删除项不把 coverage 转给无关项；
- 迁移记录必须列出 old/new ID、继承结果与依据，便于恢复和检查；它只能依据已经提交的 coverage，不能使用被丢弃 pending 中的 intended updates。

诊断不得删除用户目标中的核心交付结果，只能调整粒度、讲解起点和必要桥梁；用户明确改变目标或深度时，才按新目标修订核心范围。

### 4.3 新学习会话的启动顺序

`session get` 是对唯一开放槽位的后台只读检查，不是读取学习历史，也不是给用户增加一步操作；历史前置和适配记忆由 `context get` 检索。它用于防止新主题覆盖尚可恢复的旧会话。若用户只问一个临时具体问题，仍可直接回答，不需要关闭旧会话。

1. 用 `session get` 检查是否已有开放槽位；有则先处理恢复或关闭，不能覆盖；
2. 解析用户已给出的目标，只补问真正缺失且会改变讲解的目标信息；
3. 生成少量领域命名的前置概念键，并用 `context get` 取相关投影；
4. 形成 `provisional_scope`、可能前置和初步起点假设；
5. 用 `session start` 原子创建会话并取得第一个 claim；诊断 phase 初始为 `preparing`；
6. 若需要用户回答，设计三题或必要的窄验证并通过 diagnostic `pending_delivery` 交付；若可靠历史或明确拒答已经足够决定保守起点，则直接把诊断结算为 `complete`；
7. 起点决策完成后定稿 `done_when`、初始化 `scope_revision` 与动态 `teaching_plan`；
8. 用一句话说明讲解起点，并在同一回复中立即开始第一段实质讲解。

如果初始化、诊断结算、诊断后首个 complete checkpoint 或第一段 teaching pending 的任一写入失败，转入第 9.5 节的临时教学。若 session 已经创建，保留最后一次成功提交的旧 snapshot，不伪造 `done_when`、交付进度或持久会话更新；临时讲解以后也不得静默并回该 snapshot。

## 5. 诊断协议

### 5.1 “诊断不能跳过”的精确定义

每个明确的新学习会话都必须经过起点判断，但不等于每次都机械重复三道题：

- 没有可靠且相关的历史证据：一次展示三道诊断题；
- 有足够具体、作用域匹配且较新的证据：可用历史证据完成大部分判断，仅在关键前置过期或矛盾时追加最多一道窄验证题；
- 用户已经明确说“完全不会”：三题仍可出现，但允许三题全部直接选择安全选项并立即开始，不劝用户猜；
- 用户明确拒绝答题：不纠缠，把关键前置记为未知并从保守起点开始。诊断决策仍然完成，只是证据为“未知”；
- 恢复旧会话：不重新做三题诊断。

因此，系统不会提供一个把起点判断完全删除的默认“跳过诊断”流程，也不会因为用户拒答而拒绝解释。

“足够可靠的历史证据”至少要求领域命名空间匹配、来源可辨、没有更新的用户纠正，并且时间与当前目标仍相关。用户近期明确声明可以是强依据；旧的 `user_reports_clear`、刚教后的选择题答对或模型生成摘要只能是弱提示，不能单独取消关键前置的窄验证。

### 5.2 常规三题的设计

三题尽量一次展示，分别检验：

1. 会改变讲解起点的关键前置知识；
2. 新主题最核心的关系或直觉；
3. 一个最小应用、结构判断或常见误区。

每题必须满足：

- 不同答案确实会导致不同的讲解起点或表示方式；
- 选项简短，避免要求长文本；
- 始终提供“看选项前不知道，或主要靠猜”，表示语言能理解但知识未知；
- 只要选项含专业术语、符号或非日常描述，就必须另提供“我看不懂这些选项在说什么”，表示题目语言或前置本身过难；只有措辞完全直白的简单题可以省略；
- 选择题的正确答案不能直接写入长期“已知”证据，因为选项本身可能提示答案。

这两个兜底选项不能合并，因为路由不同：选择“不知道/猜测”时从该概念的基础解释开始；选择“看不懂描述”时先降低术语和表示复杂度，必要时退回一个更早前置。后续诊断不得继续用同一套用户已经表示看不懂的词汇。

有交互选择控件时使用控件；没有时允许用户只回复类似 `1A 2C 3D` 的短格式。

### 5.3 追加问题与上限

- 常规为三题；
- 只有答案互相矛盾、或两种讲解起点仍无法区分时才追加；
- 每次只追加一题，并说明这题要区分什么；
- 总数最多五题；到五题仍不清楚，就采用较保守起点开始讲，不继续盘问；
- 用户明确要求更细的能力诊断不属于默认学习流程，可另行约定。

### 5.4 诊断运行状态与强制输出形态

诊断至少区分：

- `preparing`：会话已创建，诊断题尚未确认进入对话上下文；
- `awaiting_answers`：三题或必要追加题已经展示，仍在等待回答；
- `complete`：已完成起点决策，无论依据来自回答、历史、拒答还是保守兜底。

`inconclusive` 是完成后的 `outcome.resolution`，不是一个仍在运行的 phase：到达五题上限仍不明晰时，phase 仍写 `complete`，起点采用保守解释。另存 `basis`（历史证据、用户声明、选择题、拒答视为未知或上限兜底）与压缩 `outcome`。

诊断题本身也通过 `pending_delivery` 交付：输出前保持 `preparing`，把 `awaiting_answers` 放入 intended updates；用户回答自然证明题目已进入上下文，再原子结算。`pending_delivery.kind: diagnostic` 发生在 `done_when/scope_revision` 定稿之前，因此不得要求或携带 `scope_revision`。有足够可靠历史，或用户预先明确拒答时，可以不展示问题，直接从 `preparing` 结算为 `complete`，不创建一个空的 diagnostic pending。用户只声明“完全不会”但没有拒答时，仍按第 5.1 节给三题并允许全部选安全项。这样既保留起点判断，也能在真正等待答案时恢复同一组题。

起点决策完成后，下一条回复必须是：

```text
一句话说明选定的讲解起点。

立即开始第一段实质讲解。
```

不得展示分数、正确率、掌握率、“初级/中级”等标签，不得再给一轮计划、问卷或铺垫。

## 6. 讲解协议：主产品行为

### 6.1 每个讲解单元的内部假设

在输出前，Skill 应形成一个很小的讲解假设：

- 当前要解决的一个关系是什么；
- 可以承接的已知概念是什么；
- 最简洁的中心模型是什么；
- 当前知识属于哪种结构，哪种表示最能让核心关系可见；
- 与当前主题相关的显式偏好、active 适配信号和待验证 candidate 是什么；
- 最可能卡住的边界在哪里；
- 这个单元结束后，离当前 `scope_revision` 的 `done_when` 还差什么。

这只是内部规划，不应先输出一大段“学习路线”。

### 6.2 一个有效讲解单元

根据主题选择下列材料，而不是机械凑齐模板：

- 连接一个可靠的已有知识；
- 给出“它是什么、为什么需要、各部分如何相互作用”的中心模型；
- 将抽象关系映射到一个完整工作示例；
- 用最适合当前关系的执行追踪、代码、公式、情景表、图或反例使其可见；
- 在确有必要时给一个对比、反例或类比边界；
- 用一小段合成把例子重新连回中心模型。

简单概念可以很短；复杂概念应分成连贯层次，但不能把一句完整解释切成连续盘问。

### 6.3 按知识结构选择讲解策略

先识别当前知识中最重要的关系，再选择能使该关系可见的表示。下表是路由提示，不是学科白名单，也不是每次必须完整套用的模板；一个主题可以组合多种结构。

| 知识结构 | 优先考虑的讲解表示 |
| --- | --- |
| 概念或机制 | 要解决的问题、组成部分、因果关系、边界和反例 |
| 算法与数据结构 | 核心不变量、样例执行追踪、复杂度和取舍 |
| 系统、并发与网络 | 组件、状态变化、数据/控制流、时序和故障路径 |
| 代码与 API | 最小可运行例子、输入输出、逐步执行、常见错误和变体 |
| 数学与公式 | 对象与符号角色、运算含义、数值例子、条件或形状，必要时推导 |
| 金融与经济 | 前提假设、现金流或因果渠道、情景计算、风险和适用边界 |
| 操作流程 | 目标、示范、关键步骤、失败恢复和逐步减少帮助 |

例如 Event Loop 应优先外显调用栈、队列和时序；Dijkstra 应围绕不变量与逐步追踪；API 学习应给最小可运行代码与失败案例；债券价格应连接现金流、贴现假设、利率情景和风险，而不是把现实不确定性包装成公式确定性。

### 6.4 数学与公式分支

当公式确实承载当前目标的核心关系时，优先采用以下顺序：

1. 每个符号代表的对象和角色；
2. 每一步运算在概念上完成什么；
3. 一个最小数值例子；
4. 形状检查，用于解释为什么运算可行；
5. 只有与当前目标相关时才进入推导、边界或工程变体。

不得把“把公式念一遍”当作解释，也不得先堆完整推导再补直觉。

### 6.5 图与其他表示

只有在图能外显以下关系时使用：数据流、矩阵对应、层级、时序、空间关系或不可见机制。图必须小、标注清楚，并在正文中解释图的阅读顺序。

优先使用能完成任务的最轻表示：短表格、文本流程图、公式对齐或代码内联图。只有交互变化会显著帮助理解时才使用可视化工具。不得为了“看起来像教学”而生成装饰图。

### 6.6 小检查的地位

小检查只在它会改变下一步讲法，或用户选择了 `apply/independent` 目标时使用：

- 一个连贯概念讲完后最多一道；
- 只检查刚讲过的核心关系，不偷偷引入新知识；
- 用户用自然语言给出等价答案时按语义判断，不要求固定措辞；
- 答对后用一句因果解释确认，不据此宣布掌握；
- 答错、猜测或不知道时，下一条回复先补充或更换解释，再决定是否需要新检查；
- 不产生两轮连续的“只有问题”；
- 用户不想做检查时继续解释，不施加失败暗示。

### 6.7 信息准确性

对可能变化、冷门、存在争议或高风险的知识，Skill 应先查权威来源再教，并保存继续学习真正需要的来源链接。稳定的基础概念无需为了形式强制联网。来源用于保证解释可靠，不应用来堆砌引文。

## 7. 困惑修复与长期适配

### 7.1 同一回复内完成修复

当用户说“太难、没懂、太抽象、太快、太啰嗦”时，下一条回复必须立即包含一种改变后的实质解释。询问或选择可以帮助对准卡点，但不能成为获得帮助的前置门槛。

按以下顺序决定是否询问：

1. 用户已经指出卡点，例如“术语看不懂”或“第二步跳太快”：直接针对它换讲法，不再问同义问题；
2. 上下文能较可靠判断：用一句可纠正的假设说明判断，然后立即修复；末尾可以附一个窄选择让用户纠正；
3. 用户只说模糊的“没懂”：先给一个安全的简化版本，再附 2–3 个低摩擦选项，例如“术语或符号 / 中间跳步 / 例子和概念连不上”；
4. 多个可能卡点会导向差异很大的修复：先交付它们共同需要的最小桥梁，再给选择，不得只问“你哪里不懂？”。

显式困难通常只改变 `teaching_plan`，不自动缩小用户目标或删除 `done_when`。确认缺少必要前置时，加入最小 bridge，讲完立即接回原主线；如果要降低目标深度，必须让用户明确决定。

| 可能的失败点 | 首选修复动作 |
| --- | --- |
| 缺少前置概念 | 只补当前关系所需的最小前置，然后接回原目标 |
| 术语陌生 | 换成普通语言，再把普通语言映射回正式术语 |
| 推理跳步 | 把缺失的一步显式补出，保持原例子连续 |
| 例子不合适 | 换成更小、与用户目的更近的例子 |
| 过于抽象 | 减少符号，换成具体场景、执行追踪、数据流或数值例子，再回到当前目标的正式表示 |
| 细节过多 | 保留中心关系，暂时移除非目标边界 |

仅替换同义词、把原文缩短一点、先表扬用户或只给选择不解释，都不算修复。连续两次仍不清楚时，退回一个具体前置概念；不得给用户贴“基础差”的标签。用户即使不回答附带选择，也必须已经从这一回复得到完整可用的帮助。

### 7.2 可纠正的适配记忆

长期适配记录必须区分：

- 显式偏好：用户自己说“公式先讲直觉”“回答简洁些”；
- 背景声明：用户自己说“我会矩阵乘法”；
- 局部观察：某次矩阵形状图对 Attention 有帮助；
- 模型生成的讲解摘要：记录讲过什么，但不能反向证明用户已经知道。

每条可检索证据应带领域作用域、来源类型、时间和置信度。`user_reports_clear` 只能作为未来起点的弱提示；旧记录、一次答对或模型自己的总结都不能单独证明长期前置知识。用户最新的明确纠正优先于旧推断。

概念键应使用领域命名空间，例如 `llm.attention.qkv`，避免与认知科学中的 attention 混淆。

显式偏好也必须支持作用域：语言、总体篇幅等可保留全局快捷字段；“在公式主题里先讲直觉”应保存为带 `preference_id/scope/instruction/updated_at` 的可纠正记录，不能因为一次局部反馈自动变成全局规则。

### 7.3 适配记忆必须形成使用闭环

```text
新会话开始或恢复
  → context get 返回相关显式偏好、active 信号和少量 candidate
  → 写入当前 session 的 adaptation_context
  → 每个有意义的讲解单元先按内容选表示，再用适配上下文调整候选顺序
  → 观察用户的实质反馈，更新 session hypotheses；直接冲突另写 session overrides
  → checkpoint 保存当前假设；close 时提交 0–3 条 adaptation observations
  → CLI 确定性合并，下一次相关讲解重新读取
```

不需要每条回复前重新读取 SQLite；但每个讲解单元都必须咨询已加载的 `adaptation_context`。该对象可同时含相关显式偏好、有效 active 和少量 candidate，不代表其中每项都已 active。投影还要保存其中最早的 `review_after`；即使 `store_revision` 没变，只要当前时间已经越过它，也必须在下一个讲解单元前重新 `context get` 或用同一确定性规则重算有效状态。

用户在本轮明确纠正偏好时，当前 session 立即刷新。任何已投影策略收到直接 `hindered` 后，还要在 checkpoint 写一个窄作用域 `session_adaptation_overrides`，至少含 scope/condition/strategy、`action: do_not_prioritize`、basis 与 observed_at，不保存原话；它使该策略在本会话余下时间不再被优先采用。用户随后给出更新且无歧义的直接反馈时，可以替换或清除该 override。任何后续 context 刷新都先取最新 store 投影，再叠加这些本会话直接反馈，不能让尚未 close 的旧 active 或 candidate 重新覆盖用户刚说的话。resume、claim、store revision 冲突或适配复核时间到期后，都按这个顺序刷新。

只有满足以下条件的会话假设才值得进入跨会话聚合：Skill 确实采用或切换了一种教学策略，并且出现了会改变后续讲法的可观察结果。每个会话提交 0–3 条，没有实质证据时就是 0 条；同一策略在同一会话反复出现只算一次，pause/resume 仍属于同一 session。原始对话和逐轮事件不进入长期记忆。

### 7.4 最小适配生命周期

显式长期偏好直接写入显式偏好记录并立即生效；推断型信号使用下面的生命周期：

| 状态 | 含义 | 下次相关讲解如何使用 |
| --- | --- | --- |
| `session_hypothesis` | 当前会话中的临时、可替换假设 | 仅影响当前会话并随 checkpoint 恢复 |
| `candidate` | 已有一次值得保留的支持，或旧 active 正因新反证接受复核 | 只作为轻量尝试方向，不作为固定默认；受挑战时不优先采用原策略 |
| `active` | 在独立会话中重复获得支持 | 仅在 scope 和 condition 匹配、且内容本身适合时作为策略排序参考 |
| `inactive` | 已冲突、过期或被用户否定 | 默认不检索；inspect 仍可见，除非用户要求物理删除 |

v1 的推断信号只表达一个方向：**在某个 scope/condition 下，优先尝试某个 strategy**。信号身份就是 `(scope, condition, strategy)`，不另存含糊的 `effect`。`hindered` observation 只反驳并降级这个“优先尝试”信号，不自动推导出“永远避免该策略”；用户明确说“以后不要这样讲”时，写成带作用域的显式偏好并立即生效。

跨会话信号最少包含：

```yaml
signal_id: signal-cs-runtime-sequence
generation: 1
is_current: true
scope: cs.runtime
condition: temporal_order
strategy: numbered_sequence_diagram
status: candidate
support_sessions: 1
direct_support_sessions: 1
conflict_sessions: 0
basis_summary: 用户曾明确把理解改善归因于编号时序图
last_observed_at: 2026-08-21T10:00:00Z
review_after: 2027-02-21T10:00:00Z
```

逻辑身份仍是 tuple，物理存储按 `(signal_id, generation)` 保留压缩后的生命周期行，并对每个 tuple 强制至多一个 `is_current: true`。开启新 generation 时，在同一事务中把旧行标为非 current/archived，再插入计数清零的新 candidate；常规 context 只读取 current 行，`data inspect` 可以展示旧 generation 的聚合摘要。旧行不是逐轮 event log，不含原话或每次互动。

抽象必须保持“最窄但可复用”：记录“在 CS 时序关系中，编号时序图可能有帮助”，而不是“用户是视觉型学习者”。v1 不把子作用域自动提升到父领域，也不跨领域泛化；同一策略在不同 condition 下分别聚合，不能互相借计数。

关闭时提交的 observation 采用绝对结果，而不是“相对某个 effect 的方向”：

```yaml
session_id: session-2026-08-21-event-loop
scope: cs.runtime
condition: temporal_order
strategy: numbered_sequence_diagram
outcome: helped               # helped | hindered
basis: direct_strategy_attribution
summary: 用户明确说明编号时序图帮助看清先后关系
observed_at: 2026-08-21T10:00:00Z
```

支持证据的 `basis` 只有 `direct_strategy_attribution` 和 `weak_user_report`：前者是用户明确把帮助归因于该策略；后者如“这样就懂了”，但未明确归因。`hindered` 只接受直接归因或明确要求切换该策略，不根据答错、停顿或模型猜测生成弱负证据。显式偏好和明确长期纠正走独立数据控制路径，不伪装成 observation。

确定性提升和降级规则如下：

- 第一次合格的 `helped`：创建 `candidate`；
- candidate 在第二个独立 session 再获 `helped`，且累计至少一次直接归因：提升为 `active`；如果全部只是弱用户报告，需要三个独立 session；
- 普通 candidate 遇到一次直接 `hindered`：先写本会话 override，长期聚合时转为 `inactive`，因为原本就没有足够证据成为默认；
- active 遇到一次直接 `hindered`：先写本会话 override，使当前及恢复后的讲解立即换策略；长期聚合时降回受挑战的 candidate，支持计数清零、`conflict_sessions=1`；另一独立 session 再次直接 `hindered` 才 inactive；
- 受挑战的 candidate 后续若获得 `helped`，冲突计数清零并从该 session 的一次支持重新积累，不能借用旧 active 的支持数；
- active 获得新的合格 `helped` 只刷新依据摘要、`last_observed_at` 和 `review_after`，不产生更高等级；
- 用户明确纠正或要求遗忘：立即覆盖、inactive 或物理删除，不等待计数；
- 到达 `review_after` 时，candidate 的有效状态视为 inactive，active 的有效状态视为 candidate；只读投影只计算，不改库。下一次相关写事务必须先实体化该有效状态并重置阶段计数，再合并当前 observation；
- 过期 active 实体化为 candidate 后，当前 `helped` 只算新阶段第一次支持；过期 candidate 先实体化为 inactive，若同一事务有新的 `helped`，则开启新 generation 的 candidate；
- inactive 以后出现新的合格 `helped` 时开启新 generation，旧计数只供 inspect 解释；
- `review_after` 只由被接受的新证据刷新；检索、采用策略、用户沉默或没有投诉都不能续期。具体复核期限是实现时可调参数，不展示为用户分数。

计数按不同 session 去重，只服务当前生命周期阶段；generation 或阶段变化后，旧计数不参与未来提升。这样既能积累，也不会让早期证据永久压住新反馈。

以下均不构成正向支持证据：用户沉默、继续对话、答对一道刚讲过的题、模型自己认为解释不错，以及“系统因为 active 而采用某策略后用户没有投诉”。“懂了”但没有把效果归因于表示方式，只能算弱用户报告；“这个编号时序图让我看清先后关系”才是直接支持。

Skill 负责从对话中提出窄作用域的 observation；CLI 只按 `(scope, condition, strategy)` 去重、保证每 session 最多计一次、应用确定性升降级和时效规则。CLI 不判断教学效果、不创造 scope/condition，也不推断学习风格。

同一 session 对同一 tuple 最终只能提交一条合并 observation：显式纠正先走数据控制路径并覆盖推断；最新且无歧义的直接归因覆盖更早的弱报告；只有一致的弱报告时合并为一次 `helped`；如果直接反馈彼此矛盾且无法由更新的明确纠正消解，则提交 0 条。`session_adaptation_overrides` 在 close 成功合并或显式纠正事务完成后才随 session 一起清除。Skill 应先在当前回复中按最新反馈修复讲法，不能为了凑长期数据追问用户。

一个完整例子是：会话 A 中用户明确说“编号时序图让我看清先后关系”，创建 `cs.runtime + temporal_order + numbered_sequence_diagram` candidate；会话 B 在相同作用域再次得到支持，提升为 active；会话 C 只是继续学习而没有评价该表示，不发生变化；会话 D 明确说编号图反而干扰理解，当前回复立即换讲法并降回 candidate；会话 E 又在匹配作用域出现相同冲突，才转为 inactive。整个过程记录的是可纠正的“何时优先尝试某种策略”，不是“用户属于视觉型学习者”。

## 8. 达到目标后的主动收束

### 8.1 完成依据

每个讲解单元后，Skill 检查：

- 当前 `scope_revision` 的 `done_when` 中，承诺解释的内容是否已经覆盖；
- 用户是否还有一个与承诺范围直接相关、尚未处理的明确困惑；
- 是否需要按用户选择的 `apply/independent` 目标完成必要的应用环节。

这里检查的是诊断后定稿、并可能在原目标内修订过的当前版本。换例子、补跳步、调整顺序或尝试另一种表示只改变 `teaching_plan`，不会自动移动完成边界；只有第 4.2 节允许的范围修订才会生成新的 `scope_revision`。因此，局部困难不会让课程无限扩张，一次小检查答对也不会让尚未交付的解释提前消失。

范围状态只有两个业务值：

- `in_progress`：约定解释仍有未交付项；
- `delivered_awaiting_decision`：约定解释已经交付，正在等待用户关闭或明确扩展。

如果即将输出的单元会覆盖最后一项，不能在输出前直接把状态改成 `delivered_awaiting_decision`；应把该变化放进 `pending_delivery.intended_updates`。只有下一条用户消息证明上一轮已经进入交互上下文时，才原子结算。它仍然不是 `mastered`，也不依赖“连续答对几题”。

### 8.2 收束回复

达到边界后，Skill 必须在同一回复中：

1. 明确判断：“到这里，本次约定的目标已经讲完，可以结束”；
2. 用 3–5 行合成核心关系；
3. 列出仍未解决的显式疑问（若没有则不制造）；
4. 把相邻高级内容作为可选下一目标，而不是默认继续。

例如，目标是“看懂 Q/K/V 公式”时，Q/K/V 的来源与角色、\(QK^T\)、缩放和 softmax、加权 \(V\)、最小数值例子与基本形状覆盖后就应收束。causal mask 和 multi-head attention 默认属于下一层。

如果用户问“那到这里是结束还是继续？”，系统必须给出上述明确判断，不能只把决定推回用户。

### 8.3 关闭时机

收束输出前先保存带有“拟转为 `delivered_awaiting_decision`”的 `pending_delivery`，等待用户的明确方向：

- 用户在包含该收束回复的后续对话轮次中说“结束、先这样、学完了”：在一个事务中结算 pending delivery、关闭会话，并提交压缩 topic memory；
- 跨任务恢复时没有送达证据，而用户只要求结束：丢弃 pending 的 intended updates，按最后已提交快照以 `user_stopped` 关闭；只有用户明确确认看过该单元，才结算后按范围已交付关闭；
- 用户明确要深入某个相邻主题：确认新的目标边界，按送达证据结算或丢弃/重放已有 pending 后，递增 `scope_revision`、更新 `done_when`，把范围状态恢复为 `in_progress` 后继续；
- 用户没有再回复：保持原状态与 pending delivery；下次恢复时保守重述收束内容，再让用户结束或选择下一目标，不重新诊断。

用户也可以在范围未讲完时主动结束。此时以 `close_reason: user_stopped` 关闭，topic memory 必须保留未交付的 `done_when` 项和建议恢复点，不能写成“目标已完成”。用户只说“开始另一个主题”而没有明确放弃旧会话时，先要求确认关闭；若用户已经明确说“关闭当前并学习 X”，无需重复确认。

v1 不在总结发出后静默关闭，以免把用户仍想追问的会话误判为结束。

## 9. Checkpoint、暂停与恢复

### 9.1 保存内容

checkpoint 是当前 phase 的完整原子快照，而不是要求诊断前后使用同一组必填字段。所有 phase 都包含学习主题、目的、目标深度、`provisional_scope`、`diagnosis.phase`、本会话 `adaptation_context` 及其 `store_revision`，其余按条件校验：

- `preparing`：允许尚无题目、诊断 outcome、`done_when`、`scope_revision` 和 `teaching_plan`；若历史或拒答足以决定起点，可从这里直接进入 complete；
- `awaiting_answers`：必须保存结构化题目、已回答/未回答项、交付证据与已取得的 basis；只有尚待送达证明的新题或追问才带 diagnostic `pending_delivery`。此阶段仍不得用暂定范围判断完成；
- `complete`：必须保存诊断 outcome、选定起点、当前 `done_when/scope_revision`、`scope_state`、动态 `teaching_plan` 与必要 bridge；并按进度保存已确认进入交互上下文的中心模型/例子/代码/公式/图、已知困惑、失败讲法、上一个单元的交付证据、`session_hypotheses`、`session_adaptation_overrides`、独立 pending（若有）、精确到下一个概念动作的 next teaching move，以及 2–4 行恢复提示。

schema 应用按 `diagnosis.phase` 区分的 `oneOf` 或等价条件约束，避免实现用空字符串伪造尚未产生的状态。

结构化题目、选项和逐项回答只是开放 session 在 `preparing/awaiting_answers` 时的恢复例外。转入 `complete` 的同一事务必须清除 diagnostic pending 与逐题内容，只留下压缩的 basis、outcome 和讲解起点；close 与 topic memory 不再复制题目或答案。

不保存完整原始对话，也不记录每个寒暄或每次点击事件。

### 9.2 保存时机

在以下边界保存：

- 新学习会话开始；
- 一个有意义的讲解单元输出前，保存 pending delivery；
- 收到下一条用户消息时，结算上一单元并保存会改变下一步的反馈；
- 准备交付范围收束时；
- 用户明确暂停；
- 会话关闭。

checkpoint 只保存恢复与后续决策需要的适配摘要，不保存逐轮 observation event。关闭时，Skill 从整段会话的 `session_hypotheses` 中压缩出 0–3 条 observation，与 topic memory 一起提交；没有合格证据时不提交。未达到第 7.3 节证据条件的适配假设默认在 close 时丢弃，不为了“积累数据”强行长期化；只有“某个讲法已明确失败”且对该主题以后解释仍有用时，才可作为 topic-local 困惑摘要保存，但不能参与 adaptation 计数或跨主题检索。

### 9.3 输出与保存之间的现实边界

Codex 无法可靠获得“回复已经在界面成功展示”之后再执行一次保存的回调。因此 v1 不承诺恢复到最后一个字，而使用独立的两阶段 `pending_delivery`：

```yaml
pending_delivery:
  unit_id: attention-weighted-v-003
  kind: synthesis
  base_session_revision: 7
  scope_revision: 1
  replay_summary: 已用三组 V 解释注意力输出是按 softmax 权重做加权和
  intended_updates:
    delivered_unit: QK^T、softmax 与加权 V 的最小数值例子
    done_when_items_covered: [dw-02, dw-03]
    intended_scope_state: delivered_awaiting_decision
    next_teaching_move: await_scope_decision
  prepared_at: 2026-08-21T10:00:00Z
```

1. 输出前只保存 `pending_delivery`；不得提前推进 `last_delivered_unit`、已交付的 `done_when` 或正式范围状态；
2. 只有后续模型轮次的可见对话上下文确实包含上一条回复，或用户明确回应了该单元时，Skill 才使用 session revision 和 claim token 原子结算为 `delivered_unconfirmed`、`user_reports_clear` 或 `needs_revisit`；同一轮中提前到达的用户消息不能作为送达证据；
3. 如果用户在包含上一条回复的后续对话轮次中直接说“结束”，close 事务可以同时结算 pending delivery；跨任务且没有送达证据时必须丢弃 intended updates，按最后已提交状态关闭；
4. 如果在两者之间异常中断，session 仍保持原来的 `active/paused` 值和 pending delivery；恢复时简短重述该单元的关键点，再继续；
5. 最坏情况是重复一个讲解单元，而不是把用户可能没看到的内容记成已经交付。

`intended_updates` 是待验证提案，不是盲目提交的补丁：如果用户对最后一单元明确表示仍然困惑，结算交付证据后仍保持 `scope_state: in_progress`，进入修复流程，而不是转为等待关闭。

`pending_delivery.kind` 至少区分 `diagnostic/teaching/synthesis`；它只保存必要的可重放内容或摘要与预期的结构化状态变化，不保存完整教学回复文本。诊断选择题仅在开放 session 尚待回答时是恢复所需的结构化例外，可以完整保存；诊断完成就按第 9.1 节删除。`diagnostic` pending 出现在范围定稿前，不带 `scope_revision`；`teaching/synthesis` pending 必须带当前 `scope_revision`，结算时也必须匹配。现有 schema 需要增加这个带条件约束的独立对象，而不仅是给 evidence enum 增加一个值。

### 9.4 暂停与恢复行为

用户说“先到这里、暂停、下次继续”时，不再追加问题：先结算上一单元可观察到的交付状态，再写入 `paused` checkpoint，然后简短确认。只有显式暂停会把 session 状态改成 `paused`；窗口崩溃或无后续消息不会触发一个不存在的“中断后回调”，session 保持原状态。

恢复时用不超过四行说明：

- 上次目标；
- 已覆盖到哪里；
- 未解决困惑；
- 现在要做的下一步。

恢复前先读取 session，再通过带 `expected_session_revision` 的 `session claim` 原子取得写权；若另一个未过期 claim 存在则返回 `SESSION_BUSY`，不得两个窗口同时继续输出。随后从保存的概念边界继续。存在 `pending_delivery` 时先用其 replay summary 重述；已经明确 `user_reports_clear` 的内容不整段重讲；恢复不重新运行默认三题诊断。

claim 后还要比较 checkpoint 中的适配投影与当前 `store_revision` 及最早 `review_after`。revision 变化或时间已到期时，先用 `context get` 刷新基础 `adaptation_context`，再叠加 `session_adaptation_overrides` 后恢复讲解；主题进度仍以 session snapshot 为准，较新的 learner context 只纠正未来讲法，不能反向伪造已交付内容。若新旧投影冲突，保留本会话的事实进度，丢弃已经失效的教学假设，但保留用户在本 session 的直接纠正。

claim 使用短租约并由 checkpoint 刷新；异常退出后租约可过期。接管一个尚未过期的 claim 必须由用户明确确认，不能自动抢占。

### 9.5 存储故障降级

数据目录不可用、权限被撤销或保存失败时，Skill 仍然继续讲解，但进入明确的临时模式：

- 说明“本次进度目前没有可靠保存”；
- 不创建、不覆盖也不合并任何持久 session 或 topic memory；
- 无法读取开放槽位时，不声称单会话约束已被检查；
- 存储恢复后先重新读取并 claim 现有会话，不能把临时讲解静默合并进去；
- 启动中途已经创建 session、但 complete checkpoint 或首个 teaching pending 失败时，保留最后已提交的 preparing/awaiting snapshot；恢复后按该边界重做或由用户决定丢弃，不把临时输出记成已交付；
- v1 只允许用户显式决定丢弃临时内容，或手动提供一段摘要重新开始。

恢复能力是支持项，不是获得解释的门票。

## 10. 本地记忆与检索模型

### 10.1 不采用单一巨型 Profile，也不采用散乱笔记

SQLite 是唯一规范状态：

- 一个很小的 learner context 保存带作用域的显式偏好与少量背景声明；
- 单独的 adaptation signal 保存第 7.4 节的窄作用域聚合结果，而不是人格或学习风格档案；
- 每个主题保存压缩 topic memory；
- 领域命名的 concept key、别名和简单全文检索连接可复用的前置知识；
- 开放会话快照是恢复的唯一事实来源；topic memory 不能覆盖更新的 session snapshot；
- 可选 Markdown Profile 只是可重建的查看视图，不是事实来源。

开始新主题时，Skill 先生成少量“哪些前置会改变讲解”的概念键和当前教学关系的 scope/condition，再让 CLI 只返回匹配投影：相关背景声明、显式偏好、有效 `active` 和少量仍有正向支持的 `candidate`。因直接冲突被降级且 `conflict_sessions > 0` 的受挑战 candidate 不作为教学提示返回，`inactive` 也默认不返回；v1 不加载全部历史，不需要 embeddings 或知识图谱。

### 10.2 默认不保存

- 原始聊天全文；
- 完整题目与答案历史；
- 每次互动的分数；
- 掌握概率；
- 人格或固定学习风格；
- 与学习无关的个人信息；
- 模型可从来源重新构造、且与用户无关的长篇内容。

### 10.3 保留、纠正和删除

v1 的 topic memory、显式声明和显式偏好默认保留到用户主动纠正或删除。推断型 adaptation signal 另有 `review_after`：到期时按第 7.4 节计算较低的 `effective_status`，不再按旧强度检索。只读 `context get` 不偷偷改库；下一次相关写事务先将逻辑降级实体化并重置阶段计数，再处理新证据。`data inspect` 必须同时显示存储状态、当前有效状态、作用域、依据摘要与复核时间，避免一条旧推断看起来永久有效。

逻辑 inactive 仍可用于解释“系统为何不再采用某个推断”，但不进入常规教学投影。只有用户明确遗忘、纠正要求删除，或未来明示的清理策略才物理删除；新证据不得悄悄复活旧计数。

`context get` 只读取每个 tuple 的 current generation；`data inspect` 可查看旧 generation 的压缩依据和状态。纠正或遗忘若以整个 tuple 为目标，默认作用于全部 generation，避免删除当前行后旧行意外变回 current。

SQLite 可明文存储，但只位于用户批准的数据目录，并依赖本机文件权限；v1 不承诺数据库级加密，因此不得存密码、令牌或其他秘密。

纠正必须覆盖后续检索使用的规范记录；删除必须同时删除派生索引和可重建视图。迁移备份只能位于同一批准目录，并应有清晰保留策略。导出只在用户明确要求时生成。

## 11. Skill、CLI 与数据目录的职责边界

### 11.1 Skill 负责

- 判断新学习、恢复、具体问题、旁支问题或数据管理请求；
- 形成目标、`provisional_scope`、诊断问题，并在诊断后定稿和受限修订 `done_when`；
- 选择讲解起点、术语密度、中心模型、例子和图；
- 根据知识结构选择讲解表示，并在每个有意义的单元前咨询当前 `adaptation_context`；
- 解释、处理用户反馈、设计可选小检查；
- 判断范围是否已经覆盖；
- 将会话压缩成结构化 checkpoint 和 topic memory；
- 维护当前 `session_hypotheses`，关闭时只提交 0–3 条窄作用域 observation；
- 决定需要检索的少量主题、前置概念键和适配 scope/condition。

### 11.2 CLI 负责

- 初始化并定位用户批准的数据目录；
- 校验 Skill 传入的结构化数据；
- 精确键、别名、简单全文检索与作用域匹配投影；
- SQLite 事务、schema 迁移、revision 比对与单会话约束；
- 原子 start、get/claim、checkpoint 和 close；
- 按 `(scope, condition, strategy)` 和不同 session 确定性合并 adaptation observation，执行第 7.4 节的升降级与有效期规则；
- 维护 `(signal_id, generation)` 行及“每 tuple 至多一个 current”的唯一约束；
- 检查、纠正、导出和删除数据；
- 返回稳定 JSON 与稳定错误码。

CLI 不生成诊断题、不讲课、不判断某个策略是否教学有效、不创造 scope/condition、不跨领域推广、不推断学习风格、不计算掌握率、不自行联网，也不自行总结对话。它只验证并合并 Skill 已提交的结构化 observation；语义判断仍由 Skill 承担，确定性状态保护由 CLI 承担。

### 11.3 数据目录与 locator

用户第一次初始化时选择一个绝对路径。产品目标是让这次授权可被后续项目目录复用：

```text
<approved-data-root>/
├── learn-everything.sqlite3
├── backups/      # 仅迁移前的可恢复备份，可选
└── exports/      # 仅显式导出时生成
```

另需一个很小的用户级 locator 配置，只保存该绝对路径，不保存学习内容。它放在操作系统的标准用户配置目录，而不是可被 Skill 升级替换的安装目录；CLI 初始化时必须报告解析后的具体位置。第一次初始化可以在同一次明确授权流程中创建 locator 与数据根。

后续从任何项目目录调用时先读 locator，再访问固定数据目录。当前项目目录永远不写规范学习状态；只有用户明确指定项目内某个路径作为导出目标时，才可以在那里生成一次性导出文件。

“一次授权后跨项目复用”是必须做真实端到端验证的目标，不是仅凭目录设计就能保证的事实。如果 Codex 权限在新任务中不能复用，Skill 应请求最小范围的重新授权；拒绝后进入第 9.5 节的临时教学模式。

## 12. CLI 最小命令契约（拟定）

CLI 随 Skill 一起安装，避免另行配置 PATH。所有写命令通过 stdin 接收 JSON，stdout 只输出 JSON，减少 shell 转义问题。

下列命令中的 `learn-everything` 是文档简写。实际 `SKILL.md` 必须相对自身位置解析 `scripts/learn-everything` 的绝对路径，不能依赖当前项目目录或用户 PATH。

```text
learn-everything init --data-dir <absolute-path>
learn-everything context get --input -
learn-everything session start --input -
learn-everything session get
learn-everything session claim --expected-session-revision <n> --client-token <token>
learn-everything session checkpoint --expected-session-revision <n> --claim-token <token> --input -
learn-everything session close --expected-session-revision <n> --expected-store-revision <n> --claim-token <token> --input -
learn-everything data inspect [--topic <key>]
learn-everything data correct --expected-store-revision <n> [--expected-session-revision <n> --claim-token <token>] --input -
learn-everything data forget --expected-store-revision <n> [--expected-session-revision <n> --claim-token <token>] --input -
learn-everything data export --output <path>
```

统一响应信封示例：

```json
{
  "ok": true,
  "schema_version": "0.2.0",
  "data": {},
  "store_revision": 12,
  "session_revision": 3
}
```

`session_revision` 只保护开放会话快照；`store_revision` 保护 learner/topic/adaptation 数据的聚合、纠正与删除。只读响应按需返回其中之一。`init` 由文件锁保证幂等；两个并发 `session start` 依靠事务和 open-session 唯一约束，只能一个成功。

v1 不需要为适配生命周期增加一组独立命令；它进入现有契约：

- `context get` 的请求携带少量 concept key、scope 与 condition，响应返回匹配的显式偏好、背景声明、有效 `active`、少量有正向支持且未受挑战的 `candidate`、投影中最早 `review_after` 及 `store_revision`；
- `session start` 创建 preparing shape：保存 goal、`provisional_scope`、`diagnosis.phase`、`adaptation_context` 及来源 store revision，但不要求 `done_when/scope_revision/teaching_plan`；诊断完成后的首个 checkpoint 才必须带后三者；
- `session checkpoint` 按 `diagnosis.phase` 的条件 schema 校验并原子保存；它保存 `adaptation_context`、其来源 revision、最早 `review_after`、`session_hypotheses` 和 `session_adaptation_overrides`，但不写长期信号；
- `session close` payload 最多携带 3 条结构化 `adaptation_observations`，允许为 0；它们与最终 topic memory 在双 revision 事务中合并；
- `data correct` 允许在用户明确表达时 upsert、覆盖或停用带作用域的显式偏好；若开放会话正在使用相关投影，必须在同一双 revision 事务中刷新 session snapshot；
- `data inspect/correct/forget` 覆盖显式偏好和 adaptation signal，并向用户显示存储状态与 `effective_status`。

失败响应至少区分：

- `NOT_INITIALIZED`；
- `INVALID_INPUT`；
- `OPEN_SESSION_EXISTS`；
- `NO_OPEN_SESSION`；
- `REVISION_CONFLICT`；
- `SESSION_BUSY`；
- `CLAIM_EXPIRED`；
- `OPEN_SESSION_DEPENDENCY`；
- `STORAGE_UNAVAILABLE`；
- `PERMISSION_REQUIRED`；
- `LOCATOR_UNAVAILABLE`；
- `SCHEMA_INCOMPATIBLE`。

关键事务约束：

- `session start` 遇到开放会话必须失败并返回其摘要，不覆盖；
- `session start` 成功时同时建立第一个短租约，并返回 session revision 与 claim token；
- `session get` 只读；继续或恢复前必须 `session claim`，claim 通过短租约与 client token 防止两个窗口同时教学；
- `checkpoint` 原子替换完整会话快照；范围发生变化时必须先清除 pending——有送达证据则结算，否则丢弃 intended updates 或重放确认——再递增 `scope_revision`；diagnostic pending 不带范围版本，teaching/synthesis pending 必须只引用当前范围版本；
- 每个 session mutation 携带 `expected_session_revision` 和有效 claim token；纠正/删除携带 `expected_store_revision`；
- `session close` 同时校验 session revision 与 store revision，并在一个事务内合并最终 topic memory、有效 adaptation observations、递增 store revision、清除 open session；合并每条 observation 前先计算并实体化到期后的有效状态，再按新阶段计数；开启 generation 时原子归档旧 current 行并插入新 current 行；每个 `(session_id, scope, condition, strategy)` 最多计一次，store 冲突时先重读最新纠正，不能用旧会话摘要或旧信号覆盖；
- 纠正若命中开放会话正在引用的背景或 topic 投影，必须同时携带两种 revision 和 claim token，由 Skill 提供同步后的 session snapshot，在一个事务中更新；
- 删除若命中开放会话依赖，默认返回 `OPEN_SESSION_DEPENDENCY`；只有用户明确要求连当前会话一起遗忘时，才用两种 revision 在一个事务中关闭/删除 session 及关联数据；
- 即使产品不支持并发，两个意外打开的 Codex 窗口也不能损坏状态；
- `session get` 的 open session 是恢复的唯一事实来源。
- `context get` 只返回请求主题、少量前置概念和匹配适配信号的投影，不返回完整历史；只读时计算 `effective_status`，不得把“被检索”本身写成支持证据；
- CLI 拒绝同一 session 的重复 observation、超过三条的 close payload、缺少 scope/condition/strategy/outcome/basis 的 observation 或非法状态跳转；`hindered` 必须使用直接策略归因，沉默、答题正确等语义由 Skill 在提交前按第 7.4 节过滤，CLI 不自行补证据；
- `data export` 默认写批准数据根的 `exports/`，只有用户明确给出其他绝对路径时才写到外部目标。

## 13. 未来 Skill 包结构

开发仓库与最终安装包分开：

```text
LearnEverything/
├── docs/
├── evals/
├── schemas/
├── tests/                         # 实现后添加
└── skill/
    └── learn-everything/
        ├── SKILL.md
        ├── agents/
        │   └── openai.yaml
        ├── scripts/
        │   ├── learn-everything   # 稳定入口
        │   └── le_cli/            # SQLite、校验、迁移实现
        └── references/
            ├── start-and-diagnose.md
            ├── repair-and-adapt.md
            ├── state-and-cli.md
            └── learner-data-control.md
```

不预建空 `assets/`、Skill 内 README 或占位 reference。

### 13.1 `SKILL.md` 必须直接包含

- 精确触发边界和四种入口路由；
- 解释优先的核心教学循环；
- `goal / provisional_scope / done_when / teaching_plan` 的边界，以及诊断后才定稿 `done_when`；
- 新主题起点诊断、三题常规预算、“不知道/猜测”和复杂题“看不懂描述”两个安全选项；
- 不输出学习分数或掌握率；
- “诊断后一句路由 + 立即讲解”；
- 按知识结构选择使核心关系可见的表示，不把公式当成通用模板；
- “太难”后同一回复换表示并继续解释，以及第 7.1 节的最小修复决策阶梯；
- 每个有意义的讲解单元咨询已加载适配上下文；推断只在窄作用域内作为可纠正的策略排序依据；
- `done_when` 和达到范围后的主动收束；
- 单开放会话、不得覆盖、当前项目不得写学习资料；
- CLI 是唯一状态写入者；
- `pending_delivery` 两阶段交付、claim 与存储故障降级；
- 各 reference 的明确读取条件。

这些是每次启用都必须生效的约束，不能只藏在 reference 中。

### 13.2 References 的渐进加载

| Reference | 何时完整读取 | 内容 |
| --- | --- | --- |
| `start-and-diagnose.md` | 开启新的宽主题时 | 暂定范围、三题设计、历史证据、追加条件、诊断后定稿 `done_when` |
| `repair-and-adapt.md` | 用户表示困难、明确纠正偏好，或关闭前有实质适配观察时 | 困惑分类、表示切换、会话假设、窄作用域生命周期与证据过滤 |
| `state-and-cli.md` | 初始化、持久化、恢复或关闭前 | 命令 payload、完整快照、revision、确定性适配合并、错误处理 |
| `learner-data-control.md` | 查看、纠正、导出或删除数据时 | 可见性、纠正、删除和导出语义 |

核心教学循环、两种诊断兜底、表示路由、适配使用边界与修复底线留在 `SKILL.md`；详细题目设计、生命周期字段和 CLI payload 再按需渐进加载，避免每轮都读取一个大型通用教学 reference。

### 13.3 激活策略

保留默认隐式发现能力，用 Skill 描述限制误触发；`$learn-everything` 提供跨项目的确定性显式入口。当前没有理由设置 `allow_implicit_invocation: false`。UI 名称与描述应强调“可中断恢复的个性化讲解”，而不是测验或掌握率。

## 14. 对现有状态模型的拟议修订

本设计获批后，再修改现有 RFC、schema 与验收用例；本轮不直接改实现契约。

| 现有设计 | 拟议变化 | 原因 |
| --- | --- | --- |
| `goal` 只有 purpose/target depth | 增加诊断前 `provisional_scope`；诊断后才写 2–5 条带会话内 `dw-*` ID 的 `done_when`、`scope_revision`、默认范围外内容，以及 `in_progress/delivered_awaiting_decision` 两态 `scope_state` | 不要求一开始知道全局 step ID，防止完成后无限延伸，又不伪装成能力判断 |
| 固定路线容易混同目标与执行顺序 | 增加可持续变化的 `teaching_plan`，将表示、顺序、例子和必要 bridge 与半稳定 `done_when` 分离 | 允许根据对话微调，而不静默偏离主线 |
| 范围项改 ID 后没有进度迁移语义 | 每次修订增加 `coverage_migration` 与 `supersedes`；等价改写保留 ID，拆分/合并只继承交付证据明确覆盖的部分 | 防止修订范围时丢失进度或凭空完成新内容 |
| diagnosis 有 `skipped/not_needed` | 增加 `phase: preparing/awaiting_answers/complete`、`basis` 与 `outcome.resolution`（可为 `inconclusive`）；题目表示同时支持 `unknown_or_guessing` 和复杂题 `cannot_parse_options`；具体问题不创建 session | 区分运行阶段、证据来源、知识未知与题目语言过难，并支持诊断中恢复 |
| session snapshot 各阶段共用一组模糊字段 | 按 diagnosis phase 使用 `oneOf` 或等价条件 schema；只有 complete 强制 `done_when/scope_revision/teaching_plan` | 避免诊断前用空值伪造尚未产生的范围和起点 |
| 诊断题保存边界不明确 | 完整题目、选项和逐项回答只存在于开放 session 的 preparing/awaiting；complete 时清除并只留压缩 outcome | 支持诊断中恢复，同时不形成长期答题史 |
| 诊断最多 6 题 | 默认 3，总上限 5 | 控制诊断疲劳 |
| recovery evidence 只有三类 | 增加独立 `pending_delivery` 对象；diagnostic pending 不带范围版本，teaching/synthesis pending 必须匹配当前 `scope_revision`；结算前不推进已交付内容与范围状态 | 承认输出与保存无法原子完成，同时允许诊断发生在范围定稿前 |
| concept note 缺少来源与时间 | 增加 basis、observed_at、领域命名 key | 防止旧证据和模型摘要被误当长期已知 |
| learner profile/教学偏好较含糊 | 显式偏好改为可纠正的带作用域记录；增加 `session_hypotheses` 与独立 adaptation signal：`generation/is_current/scope/condition/strategy/status/support_sessions/direct_support_sessions/conflict_sessions/basis_summary/last_observed_at/review_after`；observation 另带绝对 `outcome: helped/hindered` 与证据 basis | 让讲法真正随使用演化，又避免一次反馈变成固定人格标签或含糊的正反 effect |
| adaptation 旧证据与新阶段可能混在一行 | 逻辑 tuple 下按 `(signal_id, generation)` 保存聚合行，并强制至多一个 current；旧 generation 只供 inspect | 既能重置计数，也不会丢失“为何曾经采用/停用”的可纠正依据 |
| 推断型适配没有成熟与衰减边界 | 增加 `candidate/active/inactive`、不同 session 去重、直接与弱证据阈值、冲突降级及到期 `effective_status`；不保存逐轮事件 | 提供最小可验证闭环，允许旧推断被降低、停用或删除 |
| 开放 session 没有适配投影快照 | checkpoint 增加 `adaptation_context`、来源 store revision、最早复核时间、当前 `session_hypotheses` 与 `session_adaptation_overrides` | 恢复后继续采用已选讲法，并能响应期间发生的纠正或无 revision 变化的自然过期 |
| close 只保存主题摘要 | 增加 `delivered_awaiting_decision`，并给 close 增加 `scope_delivered/user_stopped/switched_topic` 原因与未交付项 | 避免静默关闭、默认继续或把提前退出记成完成 |
| next teaching move 无范围确认 | 增加 `await_scope_decision` 或等价动作 | 正确恢复“目标已讲完但尚未决定”的会话 |
| `active/paused` 没有写权语义 | 增加短租约 claim；异常中断不伪造 paused | 防止两个窗口同时恢复，也承认没有中断后回调 |
| 只有一个含糊 revision | 拆分 session revision 与 store revision | 分别保护会话快照和用户数据纠正/删除 |

需同步删除或修改现有 RFC 中“用户可默认跳过诊断”的表述，以及 acceptance A1/A2/A7 中与本稿冲突的断言。否则 Skill 指令与测试会出现两套规则。

## 15. 故障与反例处理

| 场景 | 必须行为 |
| --- | --- |
| 用户说“我完全不会，别考我” | 可把三题都记为 unknown 或接受拒答，从零立即讲；不劝猜、不拒绝教学 |
| 用户能读懂题目但不知道答案 | 选择“看选项前不知道，或主要靠猜”，从该知识的基础解释开始 |
| 用户连复杂诊断选项都看不懂 | 选择“我看不懂这些选项在说什么”，降低术语和表示复杂度；后续题不重复同一套难词 |
| 三题答案互相矛盾 | 最多逐题追加到总数 5；仍不清楚则保守开讲 |
| 诊断题 pending 尚未定稿范围 | diagnostic pending 不带 `scope_revision`；只有后续 teaching/synthesis pending 才必须匹配范围版本 |
| 诊断完成 | 在同一事务清除题目、选项、逐项答案和 diagnostic pending，只留压缩起点依据；topic memory 不复制题目 |
| 旧记录说会，但用户说忘了 | 最新用户声明优先；重新采用保守起点 |
| 旧记录很久或作用域不匹配 | 只作假设，必要时用一道窄题复核 |
| 用户答对刚讲过的题 | 只记录本会话信号，不升级为长期掌握 |
| 用户只说“没懂”，可能卡点不止一个 | 先给共同需要的简化解释，再附 2–3 个窄选择；不能只回问“哪里不懂” |
| 换例子、补一步或插入必要前置 | 更新 `teaching_plan`；除非目标交付定义确实改变，否则不动 `done_when` |
| 已部分交付后拆分或合并 `done_when` | 按送达证据结算或丢弃/重放 pending 后写 `coverage_migration`；只迁移明确等价或有已提交交付证据覆盖的部分，其余保持未交付 |
| 跨任务看不到 pending 单元却要求改范围 | 丢弃 intended updates，或先重放确认；只用已提交 coverage 做 migration，不能假设已送达 |
| Skill 想顺便讲相邻高级主题 | 作为可选下一目标；没有用户明确方向不得通过计划微调静默扩课 |
| 模型曾讲错并留下摘要 | 摘要不是用户知识证据；纠正规范记录和派生索引 |
| CS 主题中编号时序图曾有效，随后开始金融主题 | 作用域不匹配，不自动套用；先按金融关系选择现金流/情景等表示 |
| active 信号遇到清晰相反反馈 | 当前回复立即换讲法并降回 candidate；不等会话结束才生效 |
| 尚未 active 的 candidate 首次遇到直接 `hindered` | 立即 inactive；若未来重新获得帮助证据，从新 generation 开始 |
| 同一会话多次出现相同正向反馈 | 对该 `(scope, condition, strategy)` 最多计一次，pause/resume 不另算新 session |
| 同一会话先说有帮助、后说有干扰 | 最新无歧义的直接归因覆盖弱报告；直接反馈仍无法消解时提交 0 条，不把矛盾拆成两个 session 证据 |
| 系统采用 active 策略后用户没有投诉 | 不算新的支持证据，防止系统用自己的选择强化自己 |
| candidate/active 已过 `review_after` | context 投影按较低 `effective_status` 使用；inspect 仍可说明原存储状态与依据 |
| `store_revision` 未变但 session 中最早 `review_after` 已到 | 在下一讲解单元或恢复前重新计算投影，不能继续使用缓存的旧 active |
| 当前 session 已直接否定一个 active，随后 context 刷新 | 先取 store 投影，再叠加 `session_adaptation_overrides`；旧 active 不得重新生效 |
| 用户纠正或要求忘记适配推断 | 立即刷新开放会话使用的投影，并降级、停用或物理删除；不得等累计阈值 |
| Attention 会话中问 Git 具体问题 | 直接回答旁支，不新建会话、不污染 Attention 状态 |
| 用户要正式开始 Git 学习 | 明示单槽限制；若未明确放弃 Attention，先确认关闭，不能覆盖 |
| 用户未达目标就说结束 | 以 `user_stopped` 关闭，保存未交付项与建议恢复点，不声称完成 |
| 两个窗口同时恢复/写 | claim 或 revision 冲突，拒绝后写，不静默覆盖 |
| 回复与 checkpoint 之间中断 | 不提交 intended updates；恢复时最多保守重述一个 pending 单元 |
| 数据目录不可用 | 进入不可恢复的临时教学，不创建/合并状态；恢复后先重读开放槽位 |
| session start 成功，但诊断后 complete checkpoint 或首个 teaching pending 失败 | 保留最后成功的 preparing/awaiting snapshot，进入临时教学；恢复后重做，不回填临时交付 |
| 已达到目标 | 主动总结；mask/multi-head 等只作为可选扩展 |

## 16. 验收方案

### 16.1 Attention 纵向样例

将本次真实对话固化为首个端到端样例：

1. 用户：“重新开始 Attention 学习。目标：看懂 Q/K/V 公式。”
2. Skill 先形成只用于出题的 `provisional_scope`，不假装预先存在固定课程 ID；无可靠先验时一次给三题，每题有“不知道/猜测”，含公式或术语的题另有“看不懂这些选项”。
3. 用户回答：点积关系正确、softmax 关系正确、第三题选“看选项前不知道或主要靠猜”。
4. Skill 完成起点判断后定稿三条会话内 `done_when`，只用一句话说明从“有基础数学直觉、缺 Q/K/V 角色连接”开始，然后同一回复立即实质讲解；不向用户展示课程管理细节。
5. 用最小数值例子解释权重为 `[0, 1, 0]` 时输出为何是 `V₂`；接受“就是 v2 的值”这种自然回答。
6. 解释 `n=4` 时 `QK^T` 为 `4×4`，但不据此显示掌握率。
7. 覆盖 `done_when` 后主动说本次目标可以结束并合成公式；不默认进入 multi-head attention。
8. 若收束输出后尚无下一条用户消息就中断，正式范围状态仍未提交；恢复时先重述收束，再等待结束或选择下一层，不重新诊断。

### 16.2 必须通过的其他行为样例

- 新手说“别考我”时仍迅速开始解释；
- 一道含陌生符号的诊断题选择“我看不懂这些选项”后，下一步先降低题目语言和前置表示，而不是把它当成普通答错；
- 具体问题直接回答，不进入开课流程；
- 有旧前置证据但已经过期；
- 可靠历史足以决定起点、或用户在出题前明确拒答时，从 preparing 直接 complete，不创建空题或空 diagnostic pending；
- 诊断答案冲突并触发第 4/5 题；
- 诊断等待回答时中断并恢复；
- `preparing/awaiting_answers/complete` 三种 session shape 分别通过条件 schema；前两者不得被迫填充假的 `done_when`；
- diagnostic pending 无 `scope_revision` 仍可恢复；teaching/synthesis pending 缺失或错配当前范围版本必须拒绝；
- 诊断 complete 的事务清除结构化题目、选项和逐项答案；close/topic memory 只有压缩 outcome，不能重建完整答题史；
- 用户说“太抽象了”后的同一回复改变表示；
- 用户只说“没懂”时，回复先提供安全的简化解释，再给窄选择，而不是只追问卡点；
- 同一目标下两个不同诊断结果使用不同桥梁、顺序和表示，但核心完成边界仍对应用户目标；
- 用户要求换例子或补跳步时只调整 `teaching_plan`；要求加入 multi-head 等相邻目标时才明确修订 `done_when/scope_revision`；
- 一个已部分交付的 `done_when` 被拆分、两个项被合并或一项被删除时，coverage 只按显式 migration 继承；新增和未覆盖部分不能凭空变 delivered；
- 跨任务无送达证据且用户直接改范围时，pending intended coverage 被丢弃或先重放确认，migration 只读取已提交 coverage；
- 小检查答错后先修复解释；
- Event Loop 样例使用队列与时序，Dijkstra 使用不变量与执行追踪，API 使用最小代码和失败案例，债券价格使用现金流与利率情景；不得把四者都硬套成公式讲解；
- 讲解中暂停并从概念边界恢复；
- 活跃主题中的无关旁支问题；
- 未达到目标时主动结束，正确保存未交付项；
- `pending_delivery` 写入后、回复输出前崩溃；
- 最后一个单元输出后没有下一条消息，不能提前提交 `delivered_awaiting_decision`；
- 跨任务看不到 pending 单元却要求结束时，丢弃 intended updates 后关闭；
- 已交付范围在恢复后选择扩展或关闭；
- 保存失败进入临时教学，存储恢复后不静默合并；
- session 已 start、但 complete checkpoint 或首个 teaching pending 写失败时，旧 preparing/awaiting snapshot 保持不变，临时讲解不能在恢复时伪装成已交付；
- 两窗口同时 start、claim、checkpoint 或 close 的冲突；
- close 与并发 data correction 的双 revision 冲突，不能覆盖用户纠正；
- 纠正或删除开放会话正在引用的数据；
- 从带空格的安装路径、无用户 PATH 的项目目录调用 CLI；
- 查看、纠正、删除一条错误记忆后不再被检索；
- 第一个独立会话的直接策略反馈只创建 candidate，第二个匹配会话再次支持且满足直接证据条件才 active；同一会话重复反馈只计一次；
- 全部为弱用户报告时，两个会话仍不得 active，第三个独立会话支持后才允许提升；
- 普通 candidate 在下一独立会话收到直接 `hindered` 后 inactive；由 active 降下来的受挑战 candidate 则要第二个独立直接冲突才 inactive；
- 系统采用 active 策略后用户沉默、继续或答对一道题，不能为该信号增加支持计数；
- 同一 session 先有弱正向、后有直接负向时只提交后者；相互矛盾的直接反馈无法消解时提交 0 条；
- active 遇到一次明确冲突立即降为 candidate，另一个独立会话再冲突后 inactive；用户显式纠正或遗忘则立即生效；
- active 被本 session 直接否定后暂停；即使恢复时 store revision 已变化，刷新后的 store 投影也必须再叠加 session override，不能恢复旧策略优先级；
- 同一表示在 CS 时序主题有效，不得自动推广到金融或其他不匹配 scope/condition；
- 过 `review_after` 的存储状态在只读投影中按较低 `effective_status` 使用，且 inspect 能说明二者差别；
- 过期后的首个写事务先实体化降级并重置阶段计数，再合并新证据；仅检索或没有投诉不得刷新 `review_after`；
- store revision 未变但时间越过缓存投影的最早 `review_after` 时，下一讲解单元仍会刷新有效状态；新 generation 原子归档旧 current，且 inspect 可见旧聚合摘要但 context 只返回 current；
- 达到目标后不自动扩展课程。

### 16.3 发布门槛

- 解释质量仍以 [`evals/explanation-quality-rubric.md`](../evals/explanation-quality-rubric.md) 为主；
- 行为以更新后的 [`evals/acceptance-scenarios.md`](../evals/acceptance-scenarios.md) 为准；
- Skill 创建后先运行结构校验，再用独立的新 Codex 任务做前向测试，不能只检查文件存在；
- 单槽切题/不覆盖、显式与异常中断、范围交付/关闭、pending delivery、意外并发、适配信号升降级/纠正/过期都必须是发布阻断用例；现有 A11、A13 及其新版故障变体必须纳入 release gate；
- 至少用机制、算法、代码、公式和金融情景中的四类主题评估讲解表示路由，避免 Attention 样例把通用 Skill 验收带偏；
- “一次授权跨不同 cwd 和全新 Codex 任务复用”必须真实验证；若平台做不到，降级行为也必须通过验收；
- 诊断题数量、答对率、学习时长都不是发布成功指标；
- 任何将产品变成“先测后教、连续做题、完成后无限延伸”的行为都视为阻断问题。

## 17. 获批后的实现顺序

本设计通过评审后，按以下顺序实现：

1. 同步更新 RFC、状态 schema、fixture 与 acceptance scenarios；
2. 使用 Skill 创建流程生成最小用户级 `learn-everything` 包；
3. 实现 CLI 的 init、context、start、get/claim、checkpoint、close 纵向切片，包含双 revision 与最小 adaptation signal 合并；
4. 实现暂定范围、三题诊断、诊断后 `done_when`、领域中立的表示路由、第一段讲解、修复阶梯、暂停/恢复和目标收束；
5. 补 adaptation 生命周期及 learner data 的 inspect/correct/forget/export；
6. 运行结构校验、CLI 测试、生命周期状态转换测试与独立端到端教学评测；
7. 安装到用户级 skills，并验证从不同项目目录调用同一数据根。

## 18. 本稿采用的默认决定（请重点评审）

若无异议，后续实现按以下默认决定执行：

1. Skill 名称与显式调用名为 `learn-everything` / `$learn-everything`；
2. 保留明确学习意图的隐式触发，具体问题不自动开学习会话；
3. CLI 随 Skill 一起安装，而不是要求用户独立配置 PATH；
4. 无可靠先验时三题为常规诊断，冲突时总上限五题；始终有“不知道/猜测”，复杂题另有“看不懂描述”，拒答按 unknown 继续；
5. `done_when` 在诊断后从 `provisional_scope` 定稿，使用会话内 ID；它主要内部使用，不在开头强制展示完整课程计划；
6. `teaching_plan` 可以随反馈改变顺序、表示、例子和必要 bridge，但不得静默扩展原目标；
7. 讲解先按知识结构选表示，公式只是数学主题的一条分支；用户表示困难时，同一回复先交付改变后的解释，再用可选窄问题校准；
8. v1 现在就实现最小适配闭环：显式偏好立即生效；推断信号只表示“在窄作用域优先尝试某策略”，采用 `candidate/active/inactive`、不同 session 阈值、直接负反馈降级与到期有效状态；自动推断“永远避免”、概率模型、跨领域泛化和大规模抽象留到以后；
9. 达到目标后主动总结，但等用户明确结束后才 close；
10. v1 只保留一个开放/暂停会话，换正式主题前必须关闭旧会话；
11. 回复输出前只写 `pending_delivery`，下一条用户消息再结算；异常中断不伪造 `paused`；
12. session 使用短租约 claim 和 session revision 防止意外双窗口写入；
13. 存储故障时只做不可恢复的临时教学，不静默合并；
14. v1 SQLite 明文存于用户批准目录，不保存秘密，不做跨设备同步；
15. 一次授权跨项目复用是必须实测的产品目标；平台若不能复用，则请求最小重新授权并提供临时教学降级。

## 19. 依据

- OpenAI 官方将 Skills 定义为可复用指令，并允许随包提供 references 与 scripts；用户级 Skill 可跨仓库使用。参见 [OpenAI Docs: Build skills](https://learn.chatgpt.com/docs/build-skills)。
- 解释优先、工作示例、图示职责与开源 tutor 对比见 [`docs/research-notes.md`](research-notes.md)。
- 本文是在 [`docs/RFC-0001-explanation-first-mvp.md`](RFC-0001-explanation-first-mvp.md) 基础上的下一版设计；第 14 节列出了待同步冲突。
