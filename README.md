# LearnEverything

LearnEverything is an explanation-first learning mode for Codex. Its primary output is a useful explanation adapted to the learner's purpose and prior knowledge—not a score, mastery percentage, quiz history, or pre-generated curriculum.

## MVP decision

- A user-level Codex Skill owns teaching behavior, examples, diagrams, and interaction.
- A narrow local CLI owns a single user-selected data root and atomic session persistence.
- One learning session may be open at a time; it can be interrupted and resumed.
- Every explicit broad learning session resolves a starting point. Without reliable prior evidence it uses three brief diagnostic questions; a focused question is answered directly.
- Checks and practice are optional tools for choosing the next explanation, never gates before help.
- Teaching adaptations are scoped, correctable signals: useful session hypotheses may mature from candidate to active across distinct sessions, while silence, one correct answer, or cross-domain analogy never promote them.
- The canonical state is structured local data; a Markdown profile, if provided, is only a rebuildable inspection view.

## Design artifacts

- [`docs/SKILL-DESIGN.zh-CN.md`](docs/SKILL-DESIGN.zh-CN.md) — 中文 Skill 设计评审稿：激活边界、三题诊断、解释协议、目标收束、恢复语义、可纠正适配生命周期与 Skill/CLI 分工
- [`docs/RFC-0001-explanation-first-mvp.md`](docs/RFC-0001-explanation-first-mvp.md) — product center, teaching flow, architecture boundary, and MVP exclusions
- [`docs/research-notes.md`](docs/research-notes.md) — learning-science grounding and selective comparison of open-source tutors
- [`schemas/learning-state.schema.json`](schemas/learning-state.schema.json) — compact interchange schema for learner context, topic memory, one open session, and adaptation signals
- [`evals/fixtures/paused-session.example.json`](evals/fixtures/paused-session.example.json) — realistic interrupted-session example
- [`evals/explanation-quality-rubric.md`](evals/explanation-quality-rubric.md) — the primary release rubric for generated explanations and repair turns
- [`evals/acceptance-scenarios.md`](evals/acceptance-scenarios.md) — behavioral scenarios for diagnosis, teaching, recovery, memory correction, and project-independent invocation

## Current phase

This repository is intentionally still in design review. No Skill or CLI has been created yet. After the Chinese Skill design is approved, the next vertical slice should implement the smallest user-level Skill and CLI path that can start one topic, produce an explanation, atomically save an open-session snapshot, and resume it. Quiz banks, event sourcing, mastery models, multi-session concurrency, cross-device sync, and a full plugin package are outside that slice.
