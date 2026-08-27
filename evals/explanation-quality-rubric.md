# Explanation quality rubric

This is the primary quality evaluation for LearnEverything. It judges the teaching output, not the learner. Diagnostic accuracy, quiz scores, lesson length, and number of generated artifacts do not earn points here.

Use a three-point scale per dimension:

- `0` — harmful, missing, or seriously mismatched;
- `1` — usable but incomplete or generic;
- `2` — clear, well-fitted, and instructionally strong.

## First-explanation rubric

### 1. Factual integrity

- `0`: contains a material error, fabricated source, or unsafe unsupported claim.
- `1`: broadly correct but imprecise at an important boundary.
- `2`: correct at the promised depth; qualifies uncertainty and uses authoritative sources when the topic is unstable, niche, or high-stakes.

### 2. Starting-point fit

- `0`: ignores known prerequisites or assumes missing ones.
- `1`: broadly level-appropriate but generic.
- `2`: begins from a relevant known anchor, skips unnecessary basics, and bridges only the prerequisite actually needed.

### 3. Explanatory model

- `0`: gives labels, definitions, or steps without explaining the important relationship or cause.
- `1`: states the central idea but leaves a key connection implicit.
- `2`: gives the learner a compact model of what the thing is, why it exists, and how its important parts or causes relate.

### 4. Worked example

- `0`: has no concrete example when one is needed, or the example is disconnected from the explanation.
- `1`: gives an example but skips a consequential step or does not map it back to the model.
- `2`: traces a concrete, goal-relevant case and explicitly connects each important step to the central model.

### 5. Representation choice

- `0`: uses an unexplained or decorative visual/analogy, or omits a representation needed to make the relationship intelligible.
- `1`: the representation helps but includes irrelevant detail or an unstated analogy limit.
- `2`: chooses text, comparison, diagram, or analogy for a clear explanatory job; labels the relationship and states important limits. Correctly omitting a visual can earn `2`.

### 6. Progressive clarity and agency

- `0`: produces an overwhelming monologue, fragments a coherent explanation into interrogation, or blocks continuation on an answer.
- `1`: understandable but poorly chunked or offers generic next steps.
- `2`: delivers one coherent layer at a useful density and offers low-friction control such as continue, another example, prerequisite, or deeper treatment.

### First-explanation release threshold

- Factual integrity must be `2`.
- No dimension may be `0`.
- Total must be at least `9/12` across representative topics and target depths.

The numeric score evaluates the product's generated explanation; it must never be shown as a score about the learner.

## Explanation-repair rubric

Evaluate the first response after the learner says “too hard”, “too abstract”, or “I still don't understand”.

### 1. Locates the failure cheaply

The response uses available context or at most one narrow clarification to identify a missing prerequisite, term, reasoning step, unsuitable example, excessive abstraction, or excessive detail.

### 2. Changes the representation

It changes at least one material dimension—abstraction level, example, diagram/comparison, causal detail, or chunk size—instead of paraphrasing the same explanation.

### 3. Supplies help immediately

The response contains a useful repaired explanation in the same turn. It does not start a diagnostic chain, assign blame, or require a correct answer before help.

### 4. Preserves the thread

It reconnects the repaired prerequisite or example to the original learning goal rather than wandering into a new mini-course.

Score each dimension `0–2`; no dimension may be `0`, and the repair must total at least `6/8`.

## Representative acceptance prompts

1. **Broad unfamiliar topic:** “我想理解 JavaScript event loop，目标是能看懂异步代码的执行顺序。” Assume the learner knows functions and callbacks but not microtasks.
2. **Focused question:** “为什么 React Hook 不能放在条件分支里？” Assume the learner knows components and basic Hook usage. The response must answer directly, not run onboarding.
3. **Non-code topic:** “帮我理解机会成本，我想用于日常决策。” Assume no economics background and a ten-minute time budget.
4. **Repair turn:** after an abstract explanation of Bayes' theorem, the learner says “太抽象了，我看不懂公式”。 The next response must change representation and still explain the underlying relationship.
5. **Advanced learner:** “解释数据库 MVCC 的 snapshot isolation anomaly；我已经熟悉事务和锁。” The response must not restart from ACID basics.

For each prompt, keep the learner context fixed and compare outputs on this rubric. A longer answer does not outrank a shorter answer unless the added material improves one of the dimensions above.
