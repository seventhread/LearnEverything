# LearnEverything

English | [简体中文](README.zh-CN.md)

LearnEverything is a systematic learning skill for Codex. Tell it what you want to understand, and it
will identify your goal and starting point before explaining the topic through suitable examples,
representations, and pacing. Once it reaches the agreed scope, it closes the learning session instead of
turning it into an endless course.

Learning state stays in the current conversation. LearnEverything writes notes to your own Obsidian
Markdown vault only after the agreed material has been covered and you explicitly choose to save it.

## Installation

Node.js and npm are required for the installer. Install LearnEverything globally for Codex:

```bash
npx skills add seventhread/LearnEverything --skill learn-everything --agent codex --global --yes
```

Or choose the installation scope and any other compatible agent interactively:

```bash
npx skills add seventhread/LearnEverything
```

Installation adds the skill only; it does not create or modify learning data. You can start learning
immediately. When you want to save knowledge, say "Initialize LearnEverything" or use
`$learn-everything init`, then follow the prompts to select a vault.

## Usage

Learn a topic systematically:

```text
Help me understand Transformers systematically. I can write Python, but I have not studied deep learning.
```

Set a practical target:

```text
I want to understand Git's internal model well enough to diagnose common branch and rebase problems on my own.
```

Ask a focused question:

```text
Why does softmax subtract the maximum input value?
```

Focused questions receive focused answers instead of being expanded into a course. For systematic learning,
LearnEverything chooses a starting point from your goal and prior knowledge, then tells you where the session
will end.

## How it works

1. **Define the outcome**: distinguish systematic learning from a focused question and identify the result you want.
2. **Choose the starting point**: use the conversation, saved context, or a short diagnostic to avoid starting too shallow or too deep.
3. **Explain in connected units**: clarify what something is, why it exists, and how its parts relate, then ground the model in an example.
4. **Adapt immediately**: fill prerequisite gaps, change representations, switch examples, or restore missing reasoning steps when you get stuck.
5. **Close at the boundary**: summarize once the agreed material is covered, then let you save, reinforce, or explicitly expand the scope.

LearnEverything does not display mastery percentages, learner levels, or quiz scores, and it does not treat one
correct answer as proof of lasting mastery. If a learning session stops before completion, it leaves no partial
learning record behind.

## Saving to Obsidian

After initialization, the vault uses ordinary Markdown files:

```text
Vault/
├── Home.md
├── knowledge/   # Current knowledge wiki: concepts, relationships, and topic maps
├── learning/    # Records of completed learning sessions
├── profile/     # Teaching preferences supported by your explicit choices or direct feedback
└── sources/     # Sources actually used during learning
```

Knowledge pages connect through Obsidian wikilinks and work with Search, Backlinks, Properties, and Graph View.
Markdown is the source of truth for persistent content; there is no hidden database. The deterministic tools
bundled with the skill handle vault initialization, location, and structural checks. They do not generate
knowledge content for the model.

## Design principles

- **Explanation first**: diagnostics and exercises improve the next explanation rather than replacing it.
- **Explicit boundaries**: agree on the scope at the start and stop when it is complete instead of appending nearby material indefinitely.
- **Save by confirmation**: only material already delivered can enter the vault, and saving always requires an explicit choice.
- **Local, open format**: persistent content lives in a user-selected Markdown vault that is easy to read, move, and version.
- **Focused questions stay lightweight**: one specific question gets one specific answer without forcing a learning workflow.

## Development

- [Skill source](skills/learn-everything)
- [Design documentation](docs)
- [Acceptance scenarios](evals/acceptance-scenarios.md)
- [Explanation quality rubric](evals/explanation-quality-rubric.md)
- [Vault CLI reference](skills/learn-everything/references/vault-and-cli.md)

Run the tests:

```bash
python3 -m unittest discover -s tests -v
python3 -m py_compile skills/learn-everything/scripts/learn_everything_vault.py
```

The vault tooling uses only the Python standard library. For local development, you can symlink
`~/.codex/skills/learn-everything` to the repository's `skills/learn-everything` directory and keep this
repository as the only editable source.
