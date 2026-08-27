# Explanation-first MVP acceptance scenarios

These scenarios validate observable behavior. They intentionally avoid exact wording checks and do not reward the system for asking more questions, producing longer lessons, or claiming precise mastery.

## A0. A concrete question receives a concrete answer

**Given** the learner asks a focused question such as why a particular rule works.

**When** the Skill responds.

**Then** it begins with a useful explanation of that question and adapts from the conversation. It does not force purpose selection, target-depth selection, or a three-question placement flow first.

**Failure examples:** treating every question as enrollment in a course; asking what the learner already knows before answering a self-contained question; withholding the explanation until onboarding is complete.

## A1. Unknown learner starts a new topic

**Given** no relevant learner context exists and the learner asks to understand a new topic.

**When** the Skill starts the learning flow.

**Then** it:

- establishes the purpose or target depth with minimal friction;
- asks no more than three brief diagnostic questions by default;
- presents them together when practical, rather than spending three turns on them;
- gives each knowledge question a safe option such as “I did not know before seeing these choices / I am mainly guessing from them”;
- permits the learner to skip diagnosis;
- uses the answers only to choose the explanation's starting level;
- begins a useful explanation immediately after that orientation.

**Failure examples:** a ten-question placement test; a displayed ability score; requiring an essay before teaching; building a full curriculum before giving the first explanation.

## A2. Relevant prior context already exists

**Given** stored context credibly indicates that the learner understands the required prerequisite and the record is relevant to the current topic.

**When** the learner starts the topic.

**Then** the Skill skips the default diagnostic or asks only one narrow clarification when needed, explicitly connects the new explanation to the known prerequisite, and begins at the appropriate layer.

**Failure examples:** repeating the same three questions mechanically; treating an unrelated similarly named concept as prior knowledge; silently assuming all old knowledge is still current.

## A3. Three diagnostic answers remain inconclusive

**Given** the first three answers conflict or do not distinguish between two reasonable explanation levels.

**When** the Skill decides whether to ask another question.

**Then** it asks only the smallest useful addition, can state why it needs the extra distinction, records an extension reason, and still allows the learner to start with the simpler explanation instead.

**Failure examples:** automatically expanding into a full test; asking extra questions merely to increase confidence in a score; exceeding the configured maximum without stopping.

## A4. Explanation is the main activity

**Given** the learner's starting point is sufficiently clear.

**When** teaching begins.

**Then** the Skill constructs an explanation around a central mental model, connects it to relevant prior knowledge, and uses a suitable worked example or visual when it materially helps. Any check is brief, optional, and used to select the next teaching move.

**Failure examples:** explanation is a short preface to a quiz; every paragraph ends with a mandatory question; the worked example is withheld until after multiple tests; diagrams are decorative and unexplained.

## A5. The learner says “too hard” or “I don't understand”

**Given** the Skill has delivered an explanation and the learner reports difficulty.

**When** the Skill responds.

**Then** it identifies the likely failure mode with low-friction choices or a narrow question, and changes the explanation accordingly: restore a prerequisite, define a term, fill a skipped reasoning step, replace the example, reduce abstraction, or reduce detail.

The next response must contain a changed explanation, even when it also contains one narrow clarification.

**Failure examples:** repeating the same text; merely making the sentences shorter; praising the learner without repairing the explanation; launching an unrelated quiz.

## A6. The learner wants more depth

**Given** the learner understands the current layer and asks to go deeper.

**When** the Skill continues.

**Then** it preserves the established mental model, adds the next useful mechanism, boundary, formalism, or edge case, and avoids restarting from the beginner introduction.

**Failure examples:** repeating the overview; dumping every advanced detail without structure; changing examples in a way that breaks continuity.

## A7. The learner declines checks or practice

**Given** the learner wants an explanation but declines diagnostic questions, exercises, or review.

**When** the Skill continues.

**Then** it teaches from a conservative starting point, offers controls such as “continue”, “another example”, or “go deeper”, and does not block content or imply failure.

**Failure examples:** refusing to explain; repeatedly asking the same check in different words; lowering a visible score; ending the session automatically.

## A8. A small check reveals a gap

**Given** the Skill asks one optional prediction, distinction, or application because the next explanation step depends on it.

**When** the learner's answer reveals a gap.

**Then** the Skill returns to explanation, corrects the specific model or prerequisite, and keeps the check subordinate to teaching.

**Failure examples:** starting a sequence of unrelated questions; recording the result as long-term mastery; blaming the learner instead of revising the explanation.

## A9. The session is interrupted

**Given** a meaningful explanation unit has been completed, or the learner explicitly pauses at any point.

**When** the Skill saves the open-session snapshot.

**Then** the atomic snapshot stores the goal, diagnostic summary, and current explanation state. Its nested resume cursor stores the last delivered idea (which may truthfully be empty if teaching has not begun), unresolved confusion, exact next teaching move, and a short resume message. It distinguishes material that was merely delivered, that the learner reported clear, or that needs revisiting. Actual use may be kept in an optional note only when it changes the next explanation. It does not require storing the raw conversation.

**Failure examples:** cursor says only “continue learning”; snapshot contains a transcript but no next step; unresolved confusion is lost; an explanation delivered just before interruption is recorded as learned; state is updated after every token or trivial acknowledgement; resume combines stale topic memory with a newer session snapshot.

## A10. The learner resumes later

**Given** one paused session exists.

**When** the learner invokes resume.

**Then** the Skill gives a short reorientation, offers low-friction choices such as direct continuation, a short recap, or another explanation, and proceeds at the saved conceptual boundary without re-running the default diagnosis or replaying the full lesson.

**Failure examples:** starts from zero; asks the three diagnostic questions again; presents only a raw transcript; resumes after a step that had not actually been completed.

## A11. A different topic is requested while one session is open

**Given** the MVP allows one open learning session and the learner requests another topic.

**When** the Skill handles the request.

**Then** it snapshots the current session and requires the learner to resume or explicitly close it before starting the new topic. It does not silently overwrite resumable state or imply that multiple open sessions are supported.

**Failure examples:** last-write-wins replacement; mixing two topics into one session snapshot; pretending to support concurrent sessions.

## A12. Teaching preferences evolve without becoming labels

**Given** a diagram helped in two architecture explanations but has not been tested in other domains.

**When** a related architecture topic begins.

**Then** the Skill may prefer a diagram as a medium-confidence, scoped hypothesis. The learner can correct it, and the Skill does not generalize it into a permanent “visual learner” label.

**Failure examples:** always drawing diagrams; treating preference as proof of effectiveness; applying a software-specific signal to language learning; never expiring an unsupported inference.

## A13. The system closes a topic

**Given** the learner decides to stop or has reached the desired explanation depth.

**When** the session closes.

**Then** the Skill stores a compact topic memory containing the central model covered, useful and unhelpful explanation approaches, unresolved questions, and an optional next step. It may offer practice or review but does not require either.

**Failure examples:** declaring mastery from immediate performance; storing every quiz response; forcing a review schedule; losing the explanation approaches that mattered.

## A14. Stored context is inspected or corrected

**Given** the learner asks what the system remembers or identifies an incorrect assumption.

**When** the CLI exposes or updates local state.

**Then** explicit preferences, background claims, topic memory, and inferred adaptation signals are distinguishable; the learner can correct or delete them; derived explanations use the corrected state.

**Failure examples:** opaque profile; refusing deletion; rewriting a user-declared fact as an inference; retaining a corrected claim in another hidden store.

## A15. The Skill starts from any project directory

**Given** the learner completed one-time initialization of a fixed local data directory and later opens Codex in a different project folder.

**When** the learner invokes the Skill.

**Then** the local CLI uses the already approved data root, retrieves relevant learner/topic context, and writes no learner state into the current project. It does not request setup again. If the data root is temporarily unavailable, the Skill still teaches and clearly says that this session cannot be recovered unless storage becomes available.

**Failure examples:** creating a hidden profile in each project; requiring repeated directory setup; silently using an unrelated data root; refusing to explain because persistence failed; claiming session state was saved when it was not.

## Release gate

The vertical MVP should not be considered complete until A0, A1, A4, A5, A9, A10, A14, and A15 pass in realistic end-to-end trials, and representative outputs pass [`explanation-quality-rubric.md`](explanation-quality-rubric.md). Explanation quality and repair behavior are release-blocking; diagnostic accuracy is not. The product must not ship as a quiz-first tutor while claiming to be explanation-first.
