# Explanation-first v1 acceptance scenarios

These scenarios validate observable product behavior. They do not require exact wording, reward longer lessons, or treat diagnostic accuracy and immediate quiz performance as learner mastery.

## A0. A focused question receives a focused answer

**Given** the learner asks a concrete, self-contained question rather than requesting an ongoing learning session.

**When** the Skill responds.

**Then** it answers the question directly and uses relevant conversational context without forcing goal selection, target-depth selection, persistence setup, or a three-question diagnostic first.

**Failure examples:** treating every question as course enrollment; withholding the answer until onboarding is complete; creating a persistent learning session for an incidental question.

## A1. An unknown learner starts a broad topic

**Given** no reliable relevant context exists and the learner explicitly starts learning a broad topic.

**When** the Skill determines the starting point.

**Then** it:

- clarifies the learning goal only when the learner has not already supplied it;
- presents three brief diagnostic questions together by default;
- gives every knowledge question an option equivalent to “I did not know before seeing these choices / I am mainly guessing”;
- separately gives non-simple questions an option equivalent to “I do not understand what these choices mean”;
- uses the answers only to choose the explanation's starting point and representation;
- displays no score, level, correctness percentage, or mastery estimate;
- briefly states the chosen starting point and begins a substantive explanation in the same response after the diagnosis is resolved.

If the learner refuses the questions, the Skill records the starting point conservatively as unknown and teaches immediately. Refusal does not trigger repeated persuasion or block content.

**Failure examples:** silently omitting starting-point diagnosis; a long placement test; merging “unknown” with “cannot understand the wording”; requiring an essay; showing an ability score; asking another questionnaire before teaching.

## A2. Relevant prior context contributes to diagnosis

**Given** stored context credibly describes a prerequisite relevant to the learner's new goal.

**When** the Skill determines the starting point.

**Then** it treats the scoped, current evidence as part of the diagnosis rather than silently skipping diagnosis. It briefly connects the chosen starting point to that evidence and asks at most one narrow validation question only when a consequential prerequisite is stale, contradictory, or uncertain.

The learner's current explicit statement overrides stored context. A prior explanation, one correct check, or the model's own summary is not sufficient by itself to prove durable knowledge.

**Failure examples:** mechanically repeating three questions despite strong relevant evidence; saying “no diagnosis needed” without a starting-point decision; trusting an unrelated similarly named concept; treating old topic memory as mastery; ignoring a current correction.

## A3. Explanation remains the main activity across domains

**Given** the starting point is sufficiently clear.

**When** teaching begins or continues.

**Then** the Skill explains the most important relationship through a coherent mental model and chooses a representation suited to the knowledge structure. It may use an execution trace for a system, runnable code for an API, an invariant and worked trace for an algorithm, symbol roles and a numerical example for a formula, or assumptions and scenarios for a financial concept.

Checks are brief and subordinate to explanation. A representation is used only when it makes the relationship clearer; no single formula, diagram, or lesson template is forced across topics.

**Failure examples:** explanation as a preface to a quiz; every paragraph ending in a mandatory question; forcing all topics into formulas; decorative diagrams; code with no execution explanation; financial calculations with unstated assumptions or boundaries.

## A4. Difficulty triggers a repaired explanation in the same turn

**Given** the learner says an explanation is too hard, too abstract, too fast, too detailed, or simply unclear.

**When** the Skill responds.

**Then** the same response materially changes the explanation by restoring a prerequisite, defining terminology, filling a skipped step, replacing the example, changing representation, or reducing irrelevant detail.

When the learner identifies the problem, the Skill repairs it directly. When the feedback is vague, it first supplies a safe simplified explanation and may then offer one short, low-friction choice to locate the remaining gap. The clarification is never a prerequisite for receiving help.

**Failure examples:** only asking “what did you not understand?”; repeating the same explanation with synonyms; merely shortening sentences; praising without repairing; launching a new diagnostic chain; wandering into an unrelated prerequisite course.

## A5. Completion items remain stable unless the learner changes scope

**Given** diagnosis has resolved and the Skill has created a small internal set of `completion_items` for the learner's stated goal.

**When** teaching adapts to feedback.

**Then** the Skill may reorder explanation units, change examples or representations, and insert the minimum prerequisite bridge without silently changing the goal boundary. Equivalent wording retains the same item identity, and an item is covered only after its promised explanation has observably reached the conversation.

When the learner explicitly asks to extend or change the goal, the Skill adds new uncovered items or starts a new goal; new material never inherits old coverage. Adjacent advanced content is optional until the learner chooses it.

For the same topic and purpose, `orientation`, `explain`, `apply`, and `independent` produce progressively different promised boundaries as defined by the design. A deeper value may add guided or lower-prompt application, but it never changes completion into a mastery score.

**Failure examples:** rewriting completion criteria after every turn; marking planned or unconfirmed content as covered; adding an advanced chapter without learner direction; shrinking the original goal after confusion; treating teaching order as a fixed public syllabus.

## A6. Pause and resume use the last confirmed conceptual boundary

**Given** the learner explicitly pauses, or the task ends with one explanation unit not yet confirmed by a later learner turn.

**When** the session is saved and later resumed.

**Then** the checkpoint contains the goal, covered and remaining completion items, unresolved confusion, the next teaching move, and at most one compact `unconfirmed_unit`. It does not require the raw conversation.

On resume, the Skill gives a short reorientation and continues from the last confirmed boundary without re-running the default diagnosis. If an unconfirmed unit exists, it conservatively restates its key idea before advancing and does not assume the learner saw or understood it.

If interruption occurs while diagnosis is still awaiting answers, the saved state contains the same structured questions and any selected answers, but no completion items, teaching state, or unconfirmed teaching unit. Resume presents the same unanswered choices instead of generating a new diagnostic set.

If the learner explicitly abandons an unfinished diagnosis, closing clears the open slot without creating topic memory, concept notes, or adaptation evidence for teaching that never happened.

**Failure examples:** a generic “continue learning” checkpoint; replaying the whole lesson; restarting or replacing an unfinished diagnostic; skipping past unconfirmed content; recording an unconfirmed unit as learned; keeping a second resume record that can diverge from the current snapshot.

## A7. One open learning session is never silently overwritten

**Given** one resumable learning session is open.

**When** the learner asks to begin another formal topic.

**Then** the Skill reports the existing session and obtains an explicit decision: resume it, keep it and decline the new session, or close/switch it before creating the new session. It never mixes topics or silently replaces resumable state.

A focused unrelated question may still be answered directly without opening a second session or modifying the current topic memory.

In deterministic integration tests, two starts against an empty slot result in exactly one open session, and a checkpoint using a stale `expected_revision` is rejected without changing stored state.

**Failure examples:** last-write-wins replacement; accepting a stale checkpoint; pretending multiple resumable sessions are supported; storing two topics in one session; forcing the learner to close a session merely to receive a focused side answer.

## A8. Adaptation signals evolve minimally and remain scoped

**Given** the Skill actually used a teaching strategy and received meaningful feedback about that strategy.

**When** adaptation memory is updated across sessions.

**Then** one scoped supporting observation creates a `candidate`; a second independent, clear supporting observation promotes it to `active`. Silence, continued conversation, or one correct answer is not supporting evidence.

Clear conflicting feedback immediately prevents the strategy from being prioritized for the rest of the current session and sets either a `candidate` or `active` signal to `inactive`. A later clear supporting observation may restart it as `candidate`; another independent supporting session is required before it becomes active again. Signals apply only when their topic scope and teaching condition match.

`candidate` is only a low-cost experiment under an exact scope-and-condition match; `active` may serve as the default tie-breaker when no current feedback conflicts. The lifecycle stage already encodes whether one or two independent supporting sessions exist, so no duplicate numeric support count is persisted.

**Failure examples:** creating a permanent preference from one weak interaction; counting the same session twice; reinforcing a strategy because the learner did not complain; applying a CS timing-diagram signal to unrelated financial learning; labeling the learner as a fixed “visual learner.”

## A9. Stored memory can be inspected, corrected, and forgotten

**Given** the learner asks what is remembered, corrects an assumption, or requests that a memory be forgotten.

**When** local data is inspected or changed.

**Then** explicit preferences, concept notes, topic memory, and inferred adaptation signals are distinguishable. A correction takes effect in the current session and future retrieval. Forgetting removes the targeted canonical record and derived lookup data so it is not returned later.

**Failure examples:** an opaque single profile; retaining a corrected statement in another active index; treating an explicit preference as an inference; requiring several contradictory observations before honoring a direct correction; reporting deletion while continuing to use the record.

## A10. Reaching the promised boundary triggers active closure

**Given** all current completion items have been covered and no directly related explicit confusion remains unresolved.

**When** the Skill decides the next move.

**Then** it proactively says that the agreed goal has been covered, gives a compact synthesis, and presents adjacent material only as an optional next goal. It does not wait for the learner to ask whether the lesson is over, and it does not equate delivered scope with mastery.

If the learner stops before the boundary, the session closes as stopped with remaining items and a useful next step preserved; it does not report completion.

**Failure examples:** automatically continuing into advanced material; asking another quiz before allowing closure; declaring mastery from immediate answers; making the learner determine whether the original goal was met; recording an early stop as completed.

## A11. The same data root works across projects, and storage failure does not block teaching

**Given** the learner has not initialized persistence yet.

**When** the Skill first needs to save a broad learning session.

**Then** it asks the learner to choose and authorize one local data directory, initializes it only after authorization succeeds, and does not claim that progress is recoverable before initialization succeeds.

**Given** the learner later invokes the Skill from another project directory.

**When** the Skill reads or writes learning state.

**Then** it uses the same approved data root, retrieves relevant context, and writes no canonical learner state into the current project. It does not require setup again merely because the working directory changed.

If the data root is unavailable or a save fails, the Skill continues teaching, clearly says that current progress is not reliably recoverable, and does not report that data was saved. When storage returns, temporary content is not silently merged into an older session.

**Failure examples:** writing before authorization; hidden per-project profiles; repeated initialization in every repository; silently selecting a different data root; refusing to explain because persistence failed; reporting recovery as available after a failed save; silently backfilling temporary teaching into stale state.

## Release gate

The v1 release must pass A0–A7 and A10–A11 in realistic end-to-end trials, A8–A9 in deterministic integration tests, and the representative prompts in [`explanation-quality-rubric.md`](explanation-quality-rubric.md).

Release evaluation focuses on useful explanations, same-turn repair, reliable pause/resume, honest scope closure, scoped correctable memory, and cross-project persistence. Diagnostic question count, learner answer rate, lesson length, and displayed mastery are not success metrics. Any behavior that turns the product into a quiz-first tutor, silently skips starting-point diagnosis, or expands indefinitely beyond the learner's goal is release-blocking.
