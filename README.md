# LearnEverything

LearnEverything is an explanation-first learning mode for Codex. It helps a learner understand a new topic from an appropriate starting point, adapts the explanation when they get stuck, and preserves enough local state to pause and resume.

It is not a quiz-first tutor, a mastery-scoring system, or a pre-generated curriculum.

## Canonical v1 design

[docs/SKILL-DESIGN.zh-CN.md](docs/SKILL-DESIGN.zh-CN.md) is the single normative source for v1 product intent and the Skill/CLI boundary. The schema and acceptance scenarios are executable derived contracts; they must remain consistent with the design, and the design governs until any conflict is deliberately reconciled. Research notes are non-normative background.

## v1 decisions

- A user-level Codex Skill owns diagnosis, explanations, examples, visuals, repair, and closure.
- A small local CLI owns validation, atomic persistence, and one user-approved data root that works from any project directory.
- v1 supports one resumable learning session at a time. Focused questions are answered directly without creating a session.
- A broad learning session always resolves a starting point. Without sufficient direct evidence it normally uses three brief multiple-choice questions.
- Explanation is the primary activity; checks and practice are optional aids for choosing the next explanation.
- Progress means the agreed explanation boundary was covered, not that the learner was scored or certified as having mastered it.
- Stored context is compact, scoped, inspectable, correctable, and forgettable. Raw conversations and learner-type labels are not stored.
- Teaching adaptations use a minimal candidate → active → inactive lifecycle based only on clear, scoped feedback.

## Design artifacts

- [docs/SKILL-DESIGN.zh-CN.md](docs/SKILL-DESIGN.zh-CN.md) — canonical Chinese v1 design.
- [schemas/learning-state.schema.json](schemas/learning-state.schema.json) — machine-readable v1 state contract.
- [evals/fixtures/paused-session.example.json](evals/fixtures/paused-session.example.json) — interrupted-session example conforming to the schema.
- [evals/acceptance-scenarios.md](evals/acceptance-scenarios.md) — observable v1 behavioral requirements.
- [evals/explanation-quality-rubric.md](evals/explanation-quality-rubric.md) — explanation and repair quality gate.
- [docs/research-notes.md](docs/research-notes.md) — non-normative research background.

## Current phase

The v1 design artifacts are synchronized as the implementation baseline; no Skill or CLI has been created yet. The next vertical slice is the smallest local CLI and user-level Skill that can diagnose one broad topic, begin a useful explanation, save one open session, and resume it from another Codex task or working directory.

Multi-window coordination, cross-device sync, mastery models, quiz banks, and plugin distribution are outside v1.
