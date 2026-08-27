# Research notes: explanation-first tutoring

- Status: non-normative research background
- Canonical design: [`SKILL-DESIGN.zh-CN.md`](SKILL-DESIGN.zh-CN.md)
- Date checked: 2026-08-21
- Purpose: validate the MVP's teaching center and identify implementation patterns worth borrowing
- Scope: primary learning-science sources and a few directly relevant open-source agent tutors; this is not a market ranking

These notes record supporting evidence and implementation references. They do not define product behavior, state semantics, or acceptance requirements; if they differ from the canonical design, the canonical design governs.

## What the evidence changes

### Start novices with an explained example, not unsupported discovery

Worked-example research consistently supports giving novices a visible solution path before demanding unsupported problem solving. An adaptive study also found benefits from varying worked, faded, and independent tasks according to the help the learner needed. This supports a first explanation built around a causal model plus a concrete walkthrough, with independence faded in only when useful.

Sources: [Najar, Mitrovic, and McLaren, adaptive support vs. alternating worked examples](http://www.cs.cmu.edu/%7Ebmclaren/pubs/NajarMitrovicMcLaren-AdaptiveSupportVsAlternatingWETutors-UMAP2014.pdf); [van Gog, Kester, and Paas, examples and problem ordering](https://www.sciencedirect.com/science/article/abs/pii/S0361476X1000055X).

### Explanation quality is not explanation quantity

Research on instructional explanations reports an assistance dilemma: explanations should connect principles to concrete steps and adapt to prior knowledge, but fully spelling out every inference can suppress constructive processing. Self-explanation or analogy can improve transfer, while learners who cannot generate a useful explanation still benefit from instructional scaffolding.

Product implication: explain first, then optionally invite one prediction, comparison, or self-explanation. If the learner struggles, supply a changed explanation rather than withholding help or starting a test chain.

Sources: [Nokes-Malach et al., principles, examples, analogy, and self-explanation](https://www.lrdc.pitt.edu/nokes/documents/nokes-malach_et_al.,_2013.pdf); [How much is too much?](https://www.sciencedirect.com/science/article/abs/pii/S0959475212001016); [Worked-out examples: instructional explanations support learning by self-explanations](https://www.sciencedirect.com/science/article/abs/pii/S0959475201000305).

### A diagram needs an explanatory job

Visuals are most defensible when they externalize a relationship, process, hierarchy, or invisible mechanism and guide attention to the relevant part. A meta-analysis found that visual cueing can reduce cognitive load and improve retention and transfer. This argues for small, labeled diagrams with deliberate highlighting, not a compulsory image in every lesson.

Source: [Xie et al., cueing and multimedia learning meta-analysis](https://journals.plos.org/plosone/article?id=10.1371%2Fjournal.pone.0183884).

## Open-source implementations: borrow selectively

### `manuelschurr/tutor`

The project keeps personalized courses in a user-level local directory, lazily expands future chapters, and resumes from persisted state. Those are useful implementation patterns. Its 30–80-node concept graph, fixed chapter rhythm, mandatory coverage check, and end-of-chapter quiz are too curriculum- and assessment-heavy for this MVP.

Borrow: user-local data, lazy planning, resumable state, explicit approval for large route changes.

Do not borrow for v1: mandatory course creation, comprehensive concept graph, fixed quiz boundary, or “must-cover” completion as the session's center.

Source: [`manuelschurr/tutor`](https://github.com/manuelschurr/tutor).

### `PranitMohnot/repo-learner-suite`

This project demonstrates a user-level skill suite that can route across Codex and other agents, preserve generated learning artifacts, and separate tutoring from quiz/exercise generation. It is specifically for learning codebases and front-loads a full curriculum/exercise pipeline, so it is an architectural reference rather than a universal teaching template.

Borrow: thin routing skill, platform-aware installation, separation of teaching from optional exercises.

Do not borrow for v1: mandatory analysis pipeline, large artifact tree, quiz bank, or 4–5-question onboarding for every request.

Source: [`PranitMohnot/repo-learner-suite`](https://github.com/PranitMohnot/repo-learner-suite).

### `ktaletsk/learn-codebase`

This project has a persistent learning journal, explicit pause/resume behavior, compact diagrams, and good examples of reconnecting a session to its open question. Its declared defaults—always ask before telling, always predict before revealing, frequent mastery updates, and scheduled review—conflict with LearnEverything's explanation-first center.

Borrow: resume-oriented journal fields, open questions, learner-controlled pause, codebase-specific anchors.

Do not borrow for v1: forced Socratic interaction, universal prediction-before-explanation, traffic-light mastery labels, or review schedules.

Source: [`ktaletsk/learn-codebase`](https://github.com/ktaletsk/learn-codebase).

## Resulting design stance

LearnEverything should not choose between “the agent lectures” and “the agent only asks questions.” It should:

1. identify the smallest useful starting point;
2. provide a coherent model and worked example;
3. leave one meaningful inference for the learner only when that helps;
4. repair confusion with a different representation;
5. store only what changes a future explanation or resume.

The open-source projects confirm that user-level invocation and local recovery are practical. They also show the main failure mode to avoid: allowing curriculum graphs, quizzes, or progress bookkeeping to become more concrete—and therefore more dominant—than the explanation itself.
