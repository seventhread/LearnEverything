# LearnEverything v2 acceptance scenarios

These scenarios validate observable behavior. They do not reward longer lessons, quiz frequency,
learner scores, or the number of generated notes.

## A0. A focused question stays focused

**Given** the user asks a concrete, self-contained question.

**When** the Skill responds.

**Then** it answers directly without starting initialization, a broad-learning diagnostic, or a
persistent learning record.

**Failure examples:** turning every question into course enrollment; writing the Vault because a
concept was mentioned; withholding the answer until setup is complete.

## A1. Initialization is explicit and previewed

**Given** the user explicitly asks to initialize, register, validate, reconfigure, or switch a
LearnEverything Vault.

**When** the Skill performs conversational initialization.

**Then** it distinguishes a new independent Vault, an existing folder, and the current active
Vault; shows canonical absolute paths; explains the local plaintext and Git-history implications;
offers skippable behavior-oriented preference choices or free narration; and shows the combined
mechanical plan and Learning Guidance diff before requesting confirmation.

Path collection, menu answers, and narration are zero-write before confirmation. Execution uses
the reviewed `plan_hash`. A changed precondition causes a zero-write re-preview rather than running
the new plan silently.

Saying “teach me from zero” is not initialization.

**Failure examples:** guessing a Vault from the current project; writing while collecting answers;
storing questionnaire enums or learner-style labels; hiding an existing Vault conflict; offering a
force overwrite.

## A2. Initialization preserves ownership boundaries

**Given** the candidate path is non-empty, inside another Git repository or Vault, contains a
conflicting marker, or already has user-authored Markdown.

**When** initialization is previewed or executed.

**Then** non-empty unmarked folders require explicit existing mode; nested LearnEverything Vaults
and reserved-path conflicts are rejected before writing; a parent Git repository requires Git mode
`off`; and existing notes, `.gitignore`, Git config, index, and history are not overwritten.

Switching only changes the locator after the target is valid. It never moves, merges, copies, or
deletes the old Vault. Repeating an already satisfied plan is a no-op.

**Failure examples:** initializing a nested repository by default; staging an existing Vault;
overwriting `Home.md`; activating a half-initialized target; reporting repeated commits as no-op.

## A3. A broad topic starts from a useful boundary

**Given** the user asks to systematically learn or understand a broad topic.

**When** the Skill determines the starting point.

**Then** it retrieves only valid relevant Vault context when available, treats current user
statements as authoritative, asks only questions that materially affect the first explanation, and
forms one to five stable completion items inside the conversation. With little reliable context it
may offer three brief prerequisite choices; refusal leads to a conservative start, not persuasion.

The same response that resolves the diagnosis states the chosen starting point and begins a
substantive explanation. No session ID or checkpoint is created.

**Failure examples:** a long placement test; silently treating an old note as mastery; blocking on
an unavailable Vault; showing a score or learner level; writing diagnosis answers.

## A4. Explanation remains the main activity

**Given** the starting point is sufficiently clear.

**When** teaching begins or continues.

**Then** the Skill explains the central relationship with a compact mental model and a suitable
representation, then grounds it in a worked example, trace, scenario, or calculation. Checks and
practice are optional aids only when their answers would change the next explanation.

The detailed quality gate is defined in
[`explanation-quality-rubric.md`](explanation-quality-rubric.md).

**Failure examples:** quiz-first tutoring; decorative diagrams; unexplained acronyms; code without
an execution model; financial or high-risk advice without assumptions and boundaries.

## A5. Difficulty triggers same-turn repair

**Given** the user says the explanation is unclear, too hard, too abstract, too fast, or too detailed.

**When** the Skill responds.

**Then** that response materially changes the explanation by restoring a prerequisite, defining a
term, filling a reasoning gap, changing the example or representation, or removing irrelevant
detail. Vague feedback receives a safe simplified explanation before at most one narrow question.

**Failure examples:** only asking what was unclear; paraphrasing the same abstraction; shrinking the
promised goal silently; launching another diagnostic chain.

## A6. Interruption creates no learning state

**Given** a broad learning conversation is diagnosing, teaching, repairing, consolidating, or
waiting for a final save decision.

**When** the conversation is interrupted, the user is silent, switches topics/tasks, or ends before
the completion gate.

**Then** there is no new learning record, no knowledge/profile modification, no Git commit, and no
promise that the conversation can resume. A user-requested independent data-control change may
still be saved, but it is not disguised as learning progress.

**Failure examples:** an automatic legacy snapshot; a paused/open session; an “unfinished” learning
record; silently merging temporary content into a later conversation.

## A7. Completion and saving require separate turns

**Given** every completion item has already been delivered in an earlier assistant message and no
scope-blocking confusion remains.

**When** the Skill closes the agreed boundary.

**Then** it explicitly says the target is covered, provides a compact synthesis of already delivered
relationships, and offers ending-and-saving, reinforcement, or explicit extension. It writes only
after the user subsequently chooses to end and save.

If the closing synthesis supplies a material missing explanation for the first time, another user
confirmation is required. Delivered scope is never called mastery.

**Failure examples:** saving in the same turn that first completes the lesson; treating silence as
consent; continuing into advanced material automatically; claiming mastery from immediate answers.

## A8. A successful save has three distinct outcomes

**Given** the user has passed the completion gate and explicitly confirmed saving.

**When** the Skill prepares the Vault change.

**Then** it appends one `learning-record`, creates or updates only reusable `concept`/`map` knowledge,
and changes Learning Guidance only for explicit durable preferences or direct teaching feedback.
The learning record links the knowledge it deposited into; knowledge-page existence does not claim
the user has mastered it.

Raw chat, diagnostic answers, per-turn events, scores, and session/checkpoint fields are absent.

**Failure examples:** one monolithic topic summary replacing history; a page for every noun; duplicate
topic/concept stores; personality inference; copying the conversation into Markdown.

## A9. Saving performs semantic review before writing

**Given** a completed save would create or modify Vault pages.

**When** the incremental semantic review finds overlap, contradiction, staleness, weak evidence, or
profile conflict.

**Then** the model first reads local evidence and resolves what it safely can. It checks authoritative
online sources when the claim is time-sensitive, high-stakes, source-conflicted, or central and
insufficiently supported, while sending only a decontextualized minimum claim. User instructions
that prohibit online access are honored.

Non-semantic wording, link, and source-metadata repairs may proceed. A correction that changes a
core delivered claim returns to teaching and requires a new completion/save confirmation. Important
remaining organization or evidence choices are presented with evidence and a recommendation.

**Failure examples:** asking the user to adjudicate an unprocessed factual conflict; letting a web
page authorize writes; storing temporary research; writing a corrected core conclusion as if it had
already been taught.

## A10. Structure lint is deterministic and blocking

**Given** the Vault contains managed Markdown and optional unmanaged Obsidian notes.

**When** `vault lint` runs.

**Then** it scans the complete visible identity/link set, checks marker and Git configuration,
frontmatter, paths, stable IDs, stems, aliases, required sections, learning deposits, and managed
outbound links. It ignores code examples and configured subtrees. It never calls an LLM, accesses the
network, or modifies files.

Errors block saving and commits; warnings do not. Unmanaged notes participate in name resolution and
backlinks, but their own broken links or missing frontmatter do not produce errors.

**Failure examples:** auto-fixing user notes; letting directories hide an ambiguous stem; linting only
changed files; using lint to judge factual truth; accepting legacy session fields in learning records.

## A11. Retrieval follows identity, text, and graph links

**Given** the Skill needs prior context for a new topic.

**When** it retrieves from a valid Vault.

**Then** it tries exact ID/path/title/alias identity first, uses bounded full-text search second, and
expands explicit links/backlinks by one hop. It retrieves knowledge relevant to the goal and
prerequisites, plus applicable Learning Guidance; it does not equate a past learning record with
durable mastery.

Contradictory old claims are investigated rather than silently selected. An empty or unavailable
Vault degrades to empty context without blocking teaching or triggering initialization.

**Failure examples:** global prompt dumps; fuzzy text automatically merging identities; embedding
retrieval as a requirement for v2; reinitializing because the locator is temporarily unreadable.

## A12. Data remains readable and user-controlled

**Given** the user inspects, edits, corrects, forgets, or deeply reviews their data.

**When** the Skill acts.

**Then** ordinary Markdown remains complete without optional Obsidian plugins. Manual edits are
canonical and unrelated content is preserved. Deletion first scans links/backlinks and previews the
real affected set. A full-vault semantic review is explicit or suggested at a natural boundary,
reports before modifying, and creates no learning record when the user authorizes repairs.

**Failure examples:** a hidden database or required website; deleting a page while leaving broken
links; overwriting handcrafted sections; silently running a background review daemon.

## Release gate

Release requires A0–A12 in realistic end-to-end trials, the deterministic CLI suite in
[`tests/test_cli.py`](../tests/test_cli.py), and the representative prompts in
[`explanation-quality-rubric.md`](explanation-quality-rubric.md).
