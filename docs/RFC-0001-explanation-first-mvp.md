# RFC-0001: Explanation-first LearnEverything MVP

- Status: Draft
- Date: 2026-08-21
- Scope: single local learner, one open learning session, Codex-first

## Summary

LearnEverything should help a user understand a new topic quickly through an explanation adapted to their existing knowledge. Diagnosis, checks, review, and long-term records exist only to improve that explanation or make it resumable. They are not the product center.

The MVP will use a user-level Codex Skill for teaching behavior and a small local CLI for atomic persistence in a user-chosen data directory. It will support one open learning session, interruption, and later resumption. It will not attempt accurate mastery measurement, concurrent sessions, cross-device synchronization, or a comprehensive review system.

## Problem

General-purpose assistants can explain almost anything, but each conversation usually starts with weak knowledge of:

- what the learner already understands;
- why the learner wants the topic;
- which explanation has already failed;
- where an interrupted lesson should resume;
- which examples, diagrams, or level of detail have helped this learner in similar contexts.

The product opportunity is continuity of explanation, not a larger quiz engine.

## Product center

The primary job is:

> Produce the most useful explanation for this learner now, then preserve enough context to continue without starting over.

The following ordering is deliberate:

1. understand the learner's purpose and likely starting point;
2. construct and deliver an appropriate explanation;
3. notice confusion and change the explanation;
4. optionally check whether the explanation was sufficient;
5. preserve a compact session snapshot for continuation.

Diagnosis and exercises must never become a toll the user pays before receiving help.

Every proposed prompt, state field, and feature must pass one of two tests:

- Will it materially change the next explanation?
- Will it materially improve interruption recovery?

If neither answer is yes, it does not belong in the MVP.

## Product principles

### 1. Explanation first

After the minimum useful orientation, begin teaching. Do not turn every topic into a course, curriculum, or assessment plan before explaining it.

A useful explanation normally contains some of the following, selected rather than mechanically required:

- where the idea fits and why it matters;
- a plain-language causal or structural mental model;
- an explicit connection to something the learner already knows;
- a worked example integrated into the explanation;
- a diagram when relationships, sequence, hierarchy, or spatial structure benefit from one;
- a contrast, counterexample, or common misconception;
- a concise synthesis of the central idea.

Examples and diagrams are teaching material, not rewards after a lecture and not evidence of mastery by themselves.

For a novice, prefer an explained worked example before unsupported problem solving. Do not overcorrect into a complete lecture that fills every inference: after a sufficient model and example, one optional prediction, comparison, or self-explanation can help the learner construct the missing relationship. When that attempt fails, restore instructional support immediately.

### 2. Minimal diagnosis for routing

Diagnosis is for a broad learning request whose starting point is unclear. If the learner asks a concrete question, answer that question directly and adapt from the ensuing conversation; do not make the learner pass through placement first.

For a broad topic, use stored learner context when it is relevant and recent enough. If the starting level remains unclear, ask three low-friction questions by default. Prefer presenting the three together to reduce turn-taking overhead.

- Stop after three when they are sufficient to choose an explanation level.
- Ask more only when the result is genuinely inconclusive or the learner requests a more careful diagnosis.
- Record the reason when more than three questions are used.
- Let the learner skip diagnosis and start from a simple explanation.
- Use choices wherever practical; do not require substantial free-form input merely to begin learning.
- Give every knowledge question a safe metacognitive option such as “I did not know before seeing these choices / I am mainly guessing from them.” Add “I do not understand these descriptions” when that distinction would change the starting point.
- Ask only questions whose plausible answers lead to different explanation choices. Do not ask merely to increase confidence in a score.

Purpose, intended use, target depth, and optional time budget are routing inputs, not diagnostic questions. Diagnosis estimates a starting point; it does not certify knowledge or produce a mastery percentage. After it, state the chosen starting point in at most a short sentence and begin teaching.

### 3. Progressive explanation is itself adaptive

Do not treat personalization as a one-time placement decision. Deliver explanations in coherent chunks and use the learner's reactions to decide what comes next.

Useful control choices include:

- continue;
- explain this another way;
- give another example;
- show the missing prerequisite;
- go deeper;
- let me try it.

When the learner says something is too hard or unclear, first locate the failure mode: missing prerequisite, unfamiliar term, skipped reasoning step, unsuitable example, excessive abstraction, or excessive detail. Then change the explanation rather than merely shortening or repeating it.

### 4. Checks support teaching

Checks are optional routing tools. Use them when they answer a real teaching question, such as whether to continue, revisit a prerequisite, or change examples.

- Do not force an exercise after every explanation chunk.
- Prefer one small prediction, distinction, or application over a long quiz.
- Offer deeper practice when the learner wants confidence or the target goal requires application.
- Treat a correct answer immediately after teaching as session evidence only, not long-term mastery.
- Never block an explanation because the learner declines a check.
- Do not produce two consecutive question-only teaching turns. When an answer reveals a gap, the next move must contain a useful explanation, not merely another test.

### 5. Adaptation remains corrigible

Store explicit preferences separately from inferred teaching hypotheses.

Good inferred note:

> On software architecture topics, a component-flow diagram helped twice; confidence medium; re-evaluate later.

Bad inferred note:

> This user is a visual learner.

Preferences and hypotheses must be inspectable, correctable, scoped to a context, and allowed to expire. Matching a fixed “learning style” is not an MVP goal.

### 6. Snapshot at teaching boundaries

Atomically persist the complete open-session snapshot after a meaningful teaching unit, a material learner feedback signal, or an explicit pause. Do not persist every conversational micro-event.

The snapshot must answer:

- What is the learner trying to understand and why?
- What has been explained so far?
- Which mental model, example, or diagram was used?
- What remains confusing?
- What should happen next?
- What short message will reorient the learner on resume?

The snapshot should be sufficient for continuation without replaying the raw conversation. It contains the goal, diagnostic summary, live explanation state, and a small nested `resume_cursor`. The cursor is not a second state store; it only identifies the last delivered unit, coarse recovery signals, unresolved confusion, and next teaching move.

It must distinguish only the coarse recovery signals that are easy to conflate:

- `delivered_unconfirmed`: the system explained it, but the learner gave no clear signal before interruption;
- `user_reports_clear`: the learner said it was clear;
- `needs_revisit`: a known confusion remains.

These are descriptions of observed interaction, not a progression or mastery model. Exercise performance can appear in an optional note when it changes the next explanation, but it does not create more state levels. In particular, “delivered” must never become “learned” during resume.

## Target-depth contract

The learner may choose an observable target rather than a vague “beginner/expert” label:

- `orientation`: recognize the idea and distinguish it from nearby ideas;
- `explain`: explain the central mechanism in their own terms;
- `apply`: use it in a typical situation with limited help;
- `independent`: handle a new situation, compare options, or debug a failure.

The target affects explanation depth and optional practice. It does not require the system to display a mastery score.

## MVP user flow

### Start

1. The learner invokes the user-level Skill with a topic.
2. If the request is already a concrete question, the Skill answers it directly.
3. Otherwise, the Skill asks for purpose and desired depth only when they are not already clear.
4. The CLI retrieves relevant learner context and any topic memory.
5. If the starting level is clear, skip diagnosis. Otherwise ask three brief diagnostic questions.

### Explain

1. Form an explanation hypothesis: useful prior anchor, core mental model, likely confusing boundary, and suitable example or visual.
2. Deliver a coherent first layer soon after orientation.
3. Give the learner low-friction control over pace and direction.
4. When confusion appears, identify its type and switch strategy.
5. Use a small check only when it helps choose the next explanation step or when the learner requests practice.

### Pause and resume

1. Save the open-session snapshot after a meaningful unit or explicit pause.
2. The MVP permits one open learning session. It must be resumed or explicitly closed before another is started; a new topic must never silently overwrite a resumable snapshot.
3. On resume, show a short reorientation and continue at the exact next step.

An active session may temporarily have no resume cursor before the first meaningful unit. Pausing always creates one, even if teaching has not begun; in that case it truthfully records that nothing has been delivered and saves the next teaching move.

### Close

1. Store a compact topic memory: central model covered, useful explanation approaches, unresolved questions, and suggested next step.
2. Offer optional practice or later review; do not make either mandatory.

## Architecture boundary

```text
User-level Codex Skill
  owns: teaching decisions, explanation, examples, visuals, interaction
                 |
                 | small structured commands
                 v
Local CLI
  owns: initialization, context lookup, atomic session snapshots, resume, close
                 |
                 v
User-selected local data directory
  canonical SQLite state + optional generated Markdown views
```

Official OpenAI documentation describes skills as reusable instructions with optional resources and scripts, and user-scoped skills as applicable across repositories. The CLI remains deliberately narrow: it stores state but does not decide how to teach. See [OpenAI Docs: Build skills](https://learn.chatgpt.com/docs/build-skills).

### Provisional CLI responsibilities

The exact command syntax is deferred, but the required operations are:

- initialize and remember the approved data directory;
- retrieve relevant learner and topic context;
- start the single open session;
- atomically replace a versioned open-session snapshot;
- retrieve that snapshot for resume;
- close the session and update compact topic memory;
- inspect, correct, export, or delete stored learner data.

The MVP does not require an event-sourcing interface.

Initialization is project-independent: the CLI is the only component that reads or writes the selected data root, and it stores the chosen path in user-level configuration. Subsequent Skill invocations from other project folders reuse that path and never write learner state into the current repository. The vertical slice must verify that the Codex permission remains reusable in practice rather than merely assuming it.

If persistence is temporarily unavailable, the Skill should still explain the topic and clearly warn that recovery is not being saved. Storage supports the teaching experience; a storage fault must not turn into a refusal to teach.

## State model

The canonical state contains only information that improves future explanations or enables recovery:

1. **Learner context** — explicit preferences and sparse background claims.
2. **Topic memory** — central ideas covered, useful anchors, helpful or unhelpful approaches, and unresolved questions.
3. **Open session** — purpose, target depth, minimal diagnostic summary, current explanation state, and a nullable resume cursor while active.
4. **Adaptation signals** — contextual, corrigible observations about explanation effectiveness.

The formal interchange shape is defined in [`schemas/learning-state.schema.json`](../schemas/learning-state.schema.json), with a realistic paused-session fixture in [`evals/fixtures/paused-session.example.json`](../evals/fixtures/paused-session.example.json). SQLite table design is deferred until the vertical implementation slice.

### Retrieval strategy: neither one giant Profile nor loose notes

SQLite is the canonical source of truth. The model is hybrid:

- a very small learner-level record contains only explicit cross-topic preferences and sparse background claims;
- each topic has a compact memory containing the explanatory model, concept evidence, useful approaches, and unresolved questions;
- concept keys and aliases make prerequisite evidence retrievable across topics;
- an optional Markdown profile is a human-readable, rebuildable view, never the canonical store.

When a new topic starts, the Skill first identifies the few prerequisites that could change its explanation, then the CLI retrieves only matching topic/concept records by exact key, alias, or simple full-text search. The MVP does not load the learner's entire history and does not require embeddings or a knowledge graph.

### Data not stored by default

- raw conversation transcripts;
- exhaustive question and answer histories;
- a score for every interaction;
- inferred personality or fixed learning-style labels;
- unsupported mastery probabilities;
- unrelated personal information;
- content that can be reconstructed from a cited source rather than remembered about the learner.

## Invariants

- Explanation is available even when diagnosis or practice is declined.
- Default diagnostic budget is three questions.
- More than three diagnostic questions requires an explicit reason.
- A concrete question receives a direct explanation rather than mandatory diagnosis.
- A session contains no numerical mastery claim.
- Only one session may be open in the MVP.
- The open session always references an existing topic. `active` session and `started` topic statuses move together; `paused` session and topic statuses move together; closing atomically marks the topic closed and clears the open session.
- No other topic may remain `started` or `paused` while an open session exists.
- The open-session snapshot is the sole source for resume. Topic memory is a compact prerequisite-retrieval projection; when an open session exists, it must never override the snapshot. Closing derives and commits the final topic memory in the same transaction that clears the open session.
- Resume does not require the raw prior conversation.
- No record means unknown, not “the learner does not know.”
- Explicit preferences and inferred adaptation signals remain distinguishable.
- The learner can inspect, correct, export, and delete persisted information.

## Success criteria

The MVP succeeds when:

- a new learner reaches a useful first explanation with little startup friction;
- the explanation visibly changes when relevant prior knowledge or confusion is discovered;
- examples and visuals clarify the concept rather than decorate it;
- checks remain subordinate and can be skipped;
- an interrupted session resumes at the correct conceptual point;
- future explanations benefit from compact prior context without overfitting to it.

The MVP is not judged by number of questions answered, review streaks, or precision of a mastery score.

## Non-goals

- concurrent learning sessions;
- cross-device synchronization;
- multi-user or cloud service operation;
- accurate BKT, IRT, DKT, or mastery percentages;
- mandatory spaced repetition;
- comprehensive curriculum graphs for arbitrary topics;
- certification, grading, or high-stakes assessment;
- preserving every conversational event;
- a full plugin or MCP distribution package.

## Risks and mitigations

### The explanation is confidently wrong

Use authoritative sources for unstable, niche, or high-stakes material. Preserve source links in topic memory when future resumption depends on them.

### Personalization overfits sparse evidence

Treat observations as scoped hypotheses with confidence and expiry. Prefer asking or starting conservatively over inventing a detailed learner model.

### “Explanation first” becomes a long monologue

Use coherent chunks with learner-controlled continuation. Explanation quality does not mean maximal length.

### The user feels tested

Keep the three-question default, explain why an extra question is needed, allow skipping, and do not attach scores.

### Resume loses the conceptual thread

Require every session snapshot to contain the goal and current explanation state, plus a resume cursor with the last delivered idea, unresolved confusion, next step, and a short reorientation message.

### Stored fragments become hard to retrieve

Use stable topic and concept keys plus aliases and simple full-text search. Keep the global learner record small; generate a readable profile view only for inspection.

## Validation

Behavioral acceptance scenarios are defined in [`evals/acceptance-scenarios.md`](../evals/acceptance-scenarios.md). The main output is evaluated with [`evals/explanation-quality-rubric.md`](../evals/explanation-quality-rubric.md), covering factual integrity, starting-point fit, the explanatory model, the worked example, representation choice, and repair after confusion. Diagnostic accuracy is not a release metric.

The learning-science rationale and open-source implementation comparison are summarized in [`docs/research-notes.md`](research-notes.md). The comparison is intentionally selective: local persistence and resume patterns are reusable, while fixed quizzes, exhaustive concept graphs, and question-first tutoring are not MVP defaults.
