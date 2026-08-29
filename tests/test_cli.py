"""Black-box integration tests for the LearnEverything v1 CLI.

The suite intentionally invokes the extensionless script in a subprocess.  This
keeps the tests coupled to the public JSON/CLI contract rather than to storage
implementation details.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


REPO_ROOT = Path(__file__).resolve().parents[1]
CLI = REPO_ROOT / "skills" / "learn-everything" / "scripts" / "learn-everything"
MISSING = object()
NOW = "2026-08-27T08:00:00Z"


class LearnEverythingCliTests(unittest.TestCase):
    maxDiff = None

    def setUp(self) -> None:
        self._temporary_directory = tempfile.TemporaryDirectory()
        self.temp = Path(self._temporary_directory.name)
        self.config_path = self.temp / "config" / "learn-everything.json"
        self.data_root = self.temp / "learner-data"
        self.env = os.environ.copy()
        self.env["LEARN_EVERYTHING_CONFIG"] = str(self.config_path)

    def tearDown(self) -> None:
        self._temporary_directory.cleanup()

    def run_cli(
        self,
        *arguments: str,
        payload: object = MISSING,
        raw_input: str | None = None,
        cwd: Path | None = None,
        env: dict[str, str] | None = None,
    ) -> tuple[subprocess.CompletedProcess[str], dict[str, object]]:
        self.assertTrue(CLI.exists(), f"CLI script is missing: {CLI}")
        if payload is not MISSING and raw_input is not None:
            self.fail("Pass payload or raw_input, not both")
        stdin = raw_input
        if payload is not MISSING:
            stdin = json.dumps(payload, ensure_ascii=False)

        completed = subprocess.run(
            [sys.executable, str(CLI), *arguments],
            input=stdin,
            text=True,
            capture_output=True,
            cwd=str(cwd or REPO_ROOT),
            env=env or self.env,
            check=False,
            timeout=10,
        )
        try:
            document = json.loads(completed.stdout)
        except json.JSONDecodeError:
            self.fail(
                "CLI did not emit one JSON document.\n"
                f"command: {arguments!r}\n"
                f"exit: {completed.returncode}\n"
                f"stdout: {completed.stdout!r}\n"
                f"stderr: {completed.stderr!r}"
            )
        self.assertIsInstance(document, dict)
        return completed, document

    def ok(
        self,
        *arguments: str,
        payload: object = MISSING,
        raw_input: str | None = None,
        cwd: Path | None = None,
        env: dict[str, str] | None = None,
    ) -> object:
        completed, document = self.run_cli(
            *arguments,
            payload=payload,
            raw_input=raw_input,
            cwd=cwd,
            env=env,
        )
        self.assertEqual(
            completed.returncode,
            0,
            f"unexpected failure: {document!r}\nstderr: {completed.stderr}",
        )
        self.assertIs(document.get("ok"), True)
        self.assertIn("data", document)
        return document["data"]

    def error(
        self,
        code: str,
        *arguments: str,
        payload: object = MISSING,
        raw_input: str | None = None,
        cwd: Path | None = None,
        env: dict[str, str] | None = None,
    ) -> dict[str, object]:
        completed, document = self.run_cli(
            *arguments,
            payload=payload,
            raw_input=raw_input,
            cwd=cwd,
            env=env,
        )
        self.assertNotEqual(completed.returncode, 0, document)
        self.assertIs(document.get("ok"), False)
        error = document.get("error")
        self.assertIsInstance(error, dict)
        assert isinstance(error, dict)
        self.assertEqual(error.get("code"), code)
        self.assertIsInstance(error.get("message"), str)
        self.assertTrue(error["message"])
        return error

    @staticmethod
    def find_key(value: object, key: str) -> object | None:
        """Find a named value through harmless response wrapper objects."""
        if isinstance(value, dict):
            if key in value:
                return value[key]
            for child in value.values():
                found = LearnEverythingCliTests.find_key(child, key)
                if found is not None:
                    return found
        elif isinstance(value, list):
            for child in value:
                found = LearnEverythingCliTests.find_key(child, key)
                if found is not None:
                    return found
        return None

    def initialize(self, root: Path | None = None, cwd: Path | None = None) -> object:
        return self.ok("init", "--data-root", str(root or self.data_root), cwd=cwd)

    def get_session(self, cwd: Path | None = None) -> dict[str, object] | None:
        data = self.ok("session", "get", cwd=cwd)
        session = self.find_key(data, "open_session")
        if session is None and isinstance(data, dict) and "session_id" in data:
            session = data
        if session is None:
            return None
        self.assertIsInstance(session, dict)
        return session  # type: ignore[return-value]

    def inspect_state(self) -> dict[str, object]:
        data = self.ok("data", "inspect")
        state = self.find_key(data, "state")
        if isinstance(state, dict):
            return state
        self.assertIsInstance(data, dict)
        return data  # type: ignore[return-value]

    @staticmethod
    def awaiting_start(
        session_id: str = "session-attention-awaiting",
        topic_id: str = "topic-attention",
    ) -> dict[str, object]:
        def question(number: int) -> dict[str, object]:
            return {
                "question_id": f"q-{number}",
                "prompt": f"诊断问题 {number}",
                "options": [
                    {
                        "option_id": f"q-{number}-a",
                        "label": "一个知识答案",
                        "kind": "answer",
                    },
                    {
                        "option_id": f"q-{number}-unknown",
                        "label": "在看到选项前不知道，或主要靠猜",
                        "kind": "unknown_or_guessing",
                    },
                    {
                        "option_id": f"q-{number}-wording",
                        "label": "我看不懂这些选项在说什么",
                        "kind": "cannot_parse_options",
                    },
                ],
            }

        return {
            "session_id": session_id,
            "topic_id": topic_id,
            "topic_title": "Attention 机制",
            "goal": {},
            "diagnosis": {
                "phase": "awaiting_answers",
                "questions": [question(1), question(2), question(3)],
            },
        }

    @staticmethod
    def goal(status: str = "pending") -> dict[str, object]:
        return {
            "purpose": "看懂 Q/K/V 公式",
            "target_depth": "explain",
            "completion_items": [
                {
                    "item_id": "dw-01",
                    "description": "解释 Q、K、V 的来源和作用",
                    "status": status,
                }
            ],
        }

    @staticmethod
    def diagnosis_complete() -> dict[str, object]:
        return {
            "phase": "complete",
            "basis": "questions",
            "starting_point": "从向量点积如何表示匹配程度开始。",
            "summary": [
                {"concept_key": "linear_algebra.dot_product", "starting_state": "partial"}
            ],
        }

    @staticmethod
    def teaching_state() -> dict[str, object]:
        return {
            "confirmed_summary": None,
            "unresolved_confusions": [],
            "local_teaching_notes": [],
            "current_focus": "Q 与 K 的点积",
            "next_move": "用两个二维向量计算一组注意力分数。",
        }

    def complete_start(
        self,
        session_id: str,
        topic_id: str,
        item_status: str = "covered",
    ) -> dict[str, object]:
        payload = {
            "session_id": session_id,
            "topic_id": topic_id,
            "topic_title": f"Topic {topic_id}",
            "goal": self.goal(item_status),
            "diagnosis": self.diagnosis_complete(),
            "teaching_state": self.teaching_state(),
        }
        self.ok("session", "start", "--input", "-", payload=payload)
        session = self.get_session()
        assert session is not None
        return session

    def close_payload(
        self,
        session_id: str,
        item_status: str = "covered",
        close_reason: str = "scope_delivered",
        observations: list[dict[str, object]] | None = None,
        concept_notes: list[dict[str, object]] | None = None,
        include_next_step: bool = True,
    ) -> dict[str, object]:
        memory: dict[str, object] = {
            "goal": self.goal(item_status),
            "summary": "本次解释了 Q、K、V 的核心关系。",
            "unresolved_questions": [] if item_status == "covered" else ["还未解释 V"],
            "close_reason": close_reason,
        }
        if close_reason == "user_stopped" and include_next_step:
            memory["suggested_next_step"] = "下次从 V 的加权求和继续。"
        payload: dict[str, object] = {
            "session_id": session_id,
            "topic_memory": memory,
        }
        if observations is not None:
            payload["adaptation_observations"] = observations
        if concept_notes is not None:
            payload["concept_notes"] = concept_notes
        return payload

    @staticmethod
    def observation(
        outcome: str,
        summary: str,
        *,
        scope: str = "ml.transformer.attention",
        condition: str = "vector_relationship",
        strategy: str = "worked_numeric_example",
    ) -> dict[str, object]:
        return {
            "scope": scope,
            "condition": condition,
            "strategy": strategy,
            "outcome": outcome,
            "summary": summary,
            "observed_at": NOW,
        }

    def adaptation_signal(self) -> dict[str, object]:
        state = self.inspect_state()
        signals = self.find_key(state, "adaptation_signals")
        self.assertIsInstance(signals, list)
        assert isinstance(signals, list)
        matches = [
            signal
            for signal in signals
            if isinstance(signal, dict)
            and signal.get("scope") == "ml.transformer.attention"
            and signal.get("condition") == "vector_relationship"
            and signal.get("strategy") == "worked_numeric_example"
        ]
        self.assertEqual(len(matches), 1, signals)
        return matches[0]

    def test_requires_initialization_and_reports_unusable_storage(self) -> None:
        self.error("NOT_INITIALIZED", "session", "get")
        self.error(
            "NOT_INITIALIZED",
            "context",
            "get",
            "--input",
            "-",
            payload={"topic_terms": ["attention"]},
        )

        unusable_root = self.temp / "not-a-directory"
        unusable_root.write_text("occupied", encoding="utf-8")
        self.error("STORAGE_UNAVAILABLE", "init", "--data-root", str(unusable_root))

        config_directory = self.temp / "config-is-a-directory"
        config_directory.mkdir()
        broken_env = self.env.copy()
        broken_env["LEARN_EVERYTHING_CONFIG"] = str(config_directory)
        self.error("STORAGE_UNAVAILABLE", "session", "get", env=broken_env)

    def test_database_open_failure_reports_the_configured_location(self) -> None:
        self.data_root.mkdir(parents=True)
        database = self.data_root / "learn-everything.sqlite3"
        database.write_text("not a sqlite database", encoding="utf-8")
        self.config_path.parent.mkdir(parents=True)
        self.config_path.write_text(
            json.dumps(
                {"config_version": "1", "data_root": str(self.data_root)},
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )

        error = self.error("STORAGE_UNAVAILABLE", "session", "get")
        details = error.get("details")
        self.assertIsInstance(details, dict)
        assert isinstance(details, dict)
        self.assertEqual(details.get("data_root"), str(self.data_root.resolve()))
        self.assertEqual(details.get("database_path"), str(database.resolve()))
        self.assertIsInstance(details.get("reason"), str)
        self.assertTrue(details["reason"])

    def test_init_is_idempotent_but_does_not_silently_switch_roots(self) -> None:
        self.initialize()
        self.initialize()
        other_root = self.temp / "other-learner-data"
        self.error("ALREADY_INITIALIZED", "init", "--data-root", str(other_root))
        self.assertFalse(other_root.exists())

    def test_awaiting_diagnosis_survives_cwd_change_and_blocks_second_start(self) -> None:
        project_a = self.temp / "project-a"
        project_b = self.temp / "project-b"
        project_a.mkdir()
        project_b.mkdir()
        self.initialize(cwd=project_a)

        first = self.awaiting_start()
        self.ok("session", "start", "--input", "-", payload=first, cwd=project_a)
        restored = self.get_session(cwd=project_b)
        self.assertIsNotNone(restored)
        assert restored is not None
        self.assertEqual(restored["session_id"], first["session_id"])
        self.assertEqual(restored["revision"], 1)
        self.assertEqual(restored["status"], "active")
        self.assertEqual(restored["diagnosis"], first["diagnosis"])
        self.assertEqual(restored["goal"], {})
        self.assertNotIn("teaching_state", restored)
        self.assertNotIn("unconfirmed_unit", restored)

        second = self.awaiting_start("session-other", "topic-other")
        self.error(
            "OPEN_SESSION_EXISTS",
            "session",
            "start",
            "--input",
            "-",
            payload=second,
            cwd=project_b,
        )
        still_open = self.get_session(cwd=project_a)
        assert still_open is not None
        self.assertEqual(still_open["session_id"], first["session_id"])
        self.assertEqual(list(project_a.iterdir()), [])
        self.assertEqual(list(project_b.iterdir()), [])

    def test_target_depth_choice_persists_beside_three_knowledge_questions(self) -> None:
        self.initialize()
        start = self.awaiting_start(
            "session-depth-choice", "topic-depth-choice"
        )
        diagnosis = start["diagnosis"]
        assert isinstance(diagnosis, dict)
        questions = diagnosis["questions"]
        assert isinstance(questions, list)
        questions.append(
            {
                "question_id": "goal-depth",
                "prompt": "学完这次，你希望自己能做到哪一步？",
                "options": [
                    {
                        "option_id": "orientation",
                        "label": "建立地图",
                        "kind": "answer",
                    },
                    {
                        "option_id": "explain",
                        "label": "讲清机制",
                        "kind": "answer",
                    },
                    {
                        "option_id": "apply",
                        "label": "带提示使用",
                        "kind": "answer",
                    },
                    {
                        "option_id": "independent",
                        "label": "独立迁移",
                        "kind": "answer",
                    },
                    {
                        "option_id": "unsure",
                        "label": "不确定，请根据我的学习目的推荐",
                        "kind": "unknown_or_guessing",
                    },
                ],
            }
        )

        self.ok("session", "start", "--input", "-", payload=start)
        restored = self.get_session()
        assert restored is not None
        restored_diagnosis = restored["diagnosis"]
        assert isinstance(restored_diagnosis, dict)
        restored_questions = restored_diagnosis["questions"]
        assert isinstance(restored_questions, list)
        self.assertEqual(len(restored_questions), 4)
        self.assertEqual(restored_questions[-1]["question_id"], "goal-depth")

        questions[-1]["selected_option_id"] = "unsure"
        checkpoint = {
            "session_id": start["session_id"],
            "status": "active",
            "goal": {},
            "diagnosis": diagnosis,
        }
        self.ok(
            "session",
            "checkpoint",
            "--expected-revision",
            "1",
            "--input",
            "-",
            payload=checkpoint,
        )
        resumed = self.get_session()
        assert resumed is not None
        resumed_diagnosis = resumed["diagnosis"]
        assert isinstance(resumed_diagnosis, dict)
        resumed_questions = resumed_diagnosis["questions"]
        assert isinstance(resumed_questions, list)
        self.assertEqual(resumed_questions[-1]["selected_option_id"], "unsure")
        self.assertEqual(resumed["goal"], {})

    def test_checkpoint_completes_diagnosis_pauses_and_rejects_stale_revision(self) -> None:
        self.initialize()
        start = self.awaiting_start()
        self.ok("session", "start", "--input", "-", payload=start)
        checkpoint = {
            "session_id": start["session_id"],
            "status": "paused",
            "goal": self.goal("pending"),
            "diagnosis": self.diagnosis_complete(),
            "teaching_state": self.teaching_state(),
            "unconfirmed_unit": {
                "summary": "即将用一个二维例子解释点积分数。",
                "may_cover": ["dw-01"],
            },
        }
        self.ok(
            "session",
            "checkpoint",
            "--expected-revision",
            "1",
            "--input",
            "-",
            payload=checkpoint,
        )
        paused = self.get_session()
        assert paused is not None
        self.assertEqual(paused["revision"], 2)
        self.assertEqual(paused["status"], "paused")
        self.assertEqual(paused["unconfirmed_unit"], checkpoint["unconfirmed_unit"])

        stale = dict(checkpoint)
        stale["status"] = "active"
        self.error(
            "REVISION_CONFLICT",
            "session",
            "checkpoint",
            "--expected-revision",
            "1",
            "--input",
            "-",
            payload=stale,
        )
        unchanged = self.get_session()
        self.assertEqual(unchanged, paused)

        without_unconfirmed = dict(checkpoint)
        without_unconfirmed["status"] = "active"
        without_unconfirmed["unconfirmed_unit"] = None
        self.ok(
            "session",
            "checkpoint",
            "--expected-revision",
            "2",
            "--input",
            "-",
            payload=without_unconfirmed,
        )
        resumed = self.get_session()
        assert resumed is not None
        self.assertEqual(resumed["revision"], 3)
        self.assertEqual(resumed["status"], "active")
        self.assertNotIn("unconfirmed_unit", resumed)

    def test_awaiting_state_rejects_teaching_fields_including_null_unconfirmed(self) -> None:
        self.initialize()
        invalid_start = self.awaiting_start(
            "session-invalid-awaiting-start", "topic-invalid-awaiting-start"
        )
        invalid_start["unconfirmed_unit"] = None
        self.error(
            "INVALID_INPUT",
            "session",
            "start",
            "--input",
            "-",
            payload=invalid_start,
        )
        self.assertIsNone(self.get_session())

        awaiting = self.awaiting_start(
            "session-invalid-awaiting-checkpoint", "topic-invalid-awaiting-checkpoint"
        )
        self.ok("session", "start", "--input", "-", payload=awaiting)
        original = self.get_session()
        assert original is not None
        base_checkpoint = {
            "session_id": awaiting["session_id"],
            "status": "paused",
            "goal": awaiting["goal"],
            "diagnosis": awaiting["diagnosis"],
        }
        forbidden_fields = [
            {"teaching_state": self.teaching_state()},
            {
                "unconfirmed_unit": {
                    "summary": "诊断阶段不能存在待确认讲解。",
                    "may_cover": [],
                }
            },
            {"unconfirmed_unit": None},
        ]
        for forbidden in forbidden_fields:
            with self.subTest(forbidden=forbidden):
                self.error(
                    "INVALID_INPUT",
                    "session",
                    "checkpoint",
                    "--expected-revision",
                    "1",
                    "--input",
                    "-",
                    payload={**base_checkpoint, **forbidden},
                )
                self.assertEqual(self.get_session(), original)

    def test_awaiting_diagnosis_can_be_discarded_without_creating_memory(self) -> None:
        self.initialize()
        awaiting = self.awaiting_start("session-discard-diagnosis", "topic-discard-diagnosis")
        self.ok("session", "start", "--input", "-", payload=awaiting)

        self.error(
            "INVALID_INPUT",
            "session",
            "close",
            "--expected-revision",
            "0",
            "--input",
            "-",
            payload={"session_id": awaiting["session_id"]},
        )
        forbidden_memory = {
            "title": awaiting["topic_title"],
            "goal": self.goal("covered"),
            "summary": "诊断尚未完成，因此不应保存这段主题记忆。",
            "unresolved_questions": [],
            "close_reason": "scope_delivered",
        }
        self.error(
            "INVALID_INPUT",
            "session",
            "close",
            "--expected-revision",
            "1",
            "--input",
            "-",
            payload={
                "session_id": awaiting["session_id"],
                "topic_memory": forbidden_memory,
            },
        )
        self.assertEqual(self.get_session()["session_id"], awaiting["session_id"])

        result = self.ok(
            "session",
            "close",
            "--expected-revision",
            "1",
            "--input",
            "-",
            payload={"session_id": awaiting["session_id"]},
        )
        self.assertIsInstance(result, dict)
        assert isinstance(result, dict)
        self.assertIn("topic_memory", result)
        self.assertIsNone(result["topic_memory"])
        self.assertIsNone(self.get_session())
        memories = self.find_key(self.inspect_state(), "topic_memories")
        self.assertEqual(memories, [])

        complete = self.complete_start("session-complete-needs-memory", "topic-complete-needs-memory")
        self.error(
            "INVALID_INPUT",
            "session",
            "close",
            "--expected-revision",
            str(complete["revision"]),
            "--input",
            "-",
            payload={"session_id": complete["session_id"]},
        )
        still_open = self.get_session()
        self.assertIsNotNone(still_open)
        assert still_open is not None
        self.assertEqual(still_open["session_id"], complete["session_id"])

    def test_close_enforces_scope_delivered_and_persists_topic_and_concept(self) -> None:
        self.initialize()
        session = self.complete_start(
            "session-honest-close", "topic-attention-honest", item_status="pending"
        )
        self.error(
            "INVALID_INPUT",
            "session",
            "close",
            "--expected-revision",
            str(session["revision"]),
            "--input",
            "-",
            payload=self.close_payload(
                session["session_id"], item_status="pending", close_reason="scope_delivered"
            ),
        )
        self.assertIsNotNone(self.get_session())

        covered_goal = self.goal("covered")
        checkpoint = {
            "session_id": session["session_id"],
            "status": "active",
            "goal": covered_goal,
            "diagnosis": self.diagnosis_complete(),
            "teaching_state": {
                **self.teaching_state(),
                "confirmed_summary": "已经交付 Q、K、V 的来源和作用。",
            },
        }
        self.ok(
            "session",
            "checkpoint",
            "--expected-revision",
            str(session["revision"]),
            "--input",
            "-",
            payload=checkpoint,
        )
        concept = {
            "concept_key": "ml.attention.qkv",
            "aliases": ["QKV"],
            "summary": "用户已经收到 Q、K、V 角色的完整解释。",
            "state": "partial",
            "basis": "closed_topic",
            "last_observed_at": NOW,
        }
        self.ok(
            "session",
            "close",
            "--expected-revision",
            "2",
            "--input",
            "-",
            payload=self.close_payload(
                session["session_id"],
                item_status="covered",
                close_reason="scope_delivered",
                concept_notes=[concept],
            ),
        )
        self.assertIsNone(self.get_session())
        state = self.inspect_state()
        memories = self.find_key(state, "topic_memories")
        notes = self.find_key(state, "concept_notes")
        self.assertIsInstance(memories, list)
        self.assertIsInstance(notes, list)
        assert isinstance(memories, list)
        assert isinstance(notes, list)
        stored_memory = next(
            memory
            for memory in memories
            if isinstance(memory, dict) and memory.get("topic_id") == "topic-attention-honest"
        )
        self.assertEqual(stored_memory["close_reason"], "scope_delivered")
        self.assertTrue(
            all(item["status"] == "covered" for item in stored_memory["goal"]["completion_items"])
        )
        self.assertIn(concept, notes)

    def test_user_stopped_requires_pending_work_and_a_next_step(self) -> None:
        self.initialize()
        session = self.complete_start(
            "session-user-stopped", "topic-attention-stopped", item_status="pending"
        )
        invalid = self.close_payload(
            session["session_id"],
            item_status="pending",
            close_reason="user_stopped",
            include_next_step=False,
        )
        self.error(
            "INVALID_INPUT",
            "session",
            "close",
            "--expected-revision",
            "1",
            "--input",
            "-",
            payload=invalid,
        )
        self.ok(
            "session",
            "close",
            "--expected-revision",
            "1",
            "--input",
            "-",
            payload=self.close_payload(
                session["session_id"],
                item_status="pending",
                close_reason="user_stopped",
            ),
        )
        state = self.inspect_state()
        memories = self.find_key(state, "topic_memories")
        assert isinstance(memories, list)
        memory = next(
            item
            for item in memories
            if isinstance(item, dict) and item.get("topic_id") == "topic-attention-stopped"
        )
        self.assertEqual(memory["close_reason"], "user_stopped")
        self.assertTrue(memory["suggested_next_step"])
        self.assertTrue(
            any(item["status"] == "pending" for item in memory["goal"]["completion_items"])
        )

    def test_adaptation_lifecycle_uses_independent_sessions_and_direct_feedback(self) -> None:
        self.initialize()

        first = self.complete_start("adapt-session-1", "adapt-topic-1")
        helped = self.observation("helped", "用户明确说数值例子让向量关系变清楚。")
        self.ok(
            "session",
            "close",
            "--expected-revision",
            str(first["revision"]),
            "--input",
            "-",
            payload=self.close_payload(
                first["session_id"], observations=[helped]
            ),
        )
        signal = self.adaptation_signal()
        self.assertEqual(signal["status"], "candidate")
        self.assertEqual(signal["last_evidence_session_id"], "adapt-session-1")

        second = self.complete_start("adapt-session-2", "adapt-topic-2")
        self.ok(
            "session",
            "close",
            "--expected-revision",
            str(second["revision"]),
            "--input",
            "-",
            payload=self.close_payload(
                second["session_id"],
                observations=[self.observation("helped", "另一次会话中用户再次明确认可。")],
            ),
        )
        signal = self.adaptation_signal()
        self.assertEqual(signal["status"], "active")
        self.assertEqual(signal["last_evidence_session_id"], "adapt-session-2")

        third = self.complete_start("adapt-session-3", "adapt-topic-3")
        self.ok(
            "session",
            "close",
            "--expected-revision",
            str(third["revision"]),
            "--input",
            "-",
            payload=self.close_payload(
                third["session_id"],
                observations=[self.observation("hindered", "用户明确说数字遮住了核心关系。")],
            ),
        )
        signal = self.adaptation_signal()
        self.assertEqual(signal["status"], "inactive")
        context = self.ok(
            "context",
            "get",
            "--input",
            "-",
            payload={"scopes": ["ml.transformer.attention"]},
        )
        returned_signals = self.find_key(context, "adaptation_signals")
        self.assertIsInstance(returned_signals, list)
        assert isinstance(returned_signals, list)
        self.assertFalse(any(item.get("status") == "inactive" for item in returned_signals))

        fourth = self.complete_start("adapt-session-4", "adapt-topic-4")
        self.ok(
            "session",
            "close",
            "--expected-revision",
            str(fourth["revision"]),
            "--input",
            "-",
            payload=self.close_payload(
                fourth["session_id"],
                observations=[self.observation("helped", "后来用户又明确表示同一策略有帮助。")],
            ),
        )
        signal = self.adaptation_signal()
        self.assertEqual(signal["status"], "candidate")
        self.assertEqual(signal["last_evidence_session_id"], "adapt-session-4")

    def test_context_get_filters_scoped_records_and_excludes_inactive_signals(self) -> None:
        self.initialize()
        records = [
            (
                "explicit_preference",
                {
                    "preference_id": "pref-global-language",
                    "scope": "global",
                    "instruction": "使用中文讲解。",
                    "updated_at": NOW,
                },
            ),
            (
                "explicit_preference",
                {
                    "preference_id": "pref-attention-example",
                    "scope": "ml.transformer.attention",
                    "instruction": "先使用小型数值例子。",
                    "updated_at": NOW,
                },
            ),
            (
                "explicit_preference",
                {
                    "preference_id": "pref-finance",
                    "scope": "finance",
                    "instruction": "先讲现金流。",
                    "updated_at": NOW,
                },
            ),
            (
                "concept_note",
                {
                    "concept_key": "linear_algebra.dot_product",
                    "aliases": ["点积"],
                    "summary": "能算点积，但不熟悉几何含义。",
                    "state": "partial",
                    "basis": "diagnostic_observation",
                    "last_observed_at": NOW,
                },
            ),
            (
                "concept_note",
                {
                    "concept_key": "finance.discount_rate",
                    "summary": "与当前主题无关。",
                    "state": "known",
                    "basis": "user_declared",
                    "last_observed_at": NOW,
                },
            ),
            (
                "adaptation_signal",
                {
                    "signal_id": "signal-active-example",
                    "scope": "ml.transformer.attention",
                    "condition": "vector_relationship",
                    "strategy": "worked_numeric_example",
                    "status": "active",
                    "last_evidence_session_id": "old-session-2",
                    "basis_summary": "两个独立会话中有直接正反馈。",
                    "last_observed_at": NOW,
                },
            ),
            (
                "adaptation_signal",
                {
                    "signal_id": "signal-inactive-diagram",
                    "scope": "ml.transformer.attention",
                    "condition": "vector_relationship",
                    "strategy": "dense_diagram",
                    "status": "inactive",
                    "last_evidence_session_id": "old-session-3",
                    "basis_summary": "用户明确说图太密。",
                    "last_observed_at": NOW,
                },
            ),
        ]
        for record_type, record in records:
            self.ok(
                "data",
                "correct",
                "--input",
                "-",
                payload={"record_type": record_type, "record": record},
            )

        session = self.complete_start("context-session", "topic-attention-memory")
        close = self.close_payload(session["session_id"])
        close["topic_memory"]["aliases"] = ["self-attention"]
        self.ok(
            "session",
            "close",
            "--expected-revision",
            "1",
            "--input",
            "-",
            payload=close,
        )

        context = self.ok(
            "context",
            "get",
            "--input",
            "-",
            payload={
                "topic_terms": ["self-attention"],
                "concept_keys": ["linear_algebra.dot_product"],
                "scopes": ["ml.transformer.attention"],
            },
        )
        preferences = self.find_key(context, "explicit_preferences")
        notes = self.find_key(context, "concept_notes")
        signals = self.find_key(context, "adaptation_signals")
        memories = self.find_key(context, "topic_memories")
        self.assertIsInstance(preferences, list)
        self.assertIsInstance(notes, list)
        self.assertIsInstance(signals, list)
        self.assertIsInstance(memories, list)
        assert isinstance(preferences, list)
        assert isinstance(notes, list)
        assert isinstance(signals, list)
        assert isinstance(memories, list)
        self.assertEqual(
            {item["preference_id"] for item in preferences},
            {"pref-global-language", "pref-attention-example"},
        )
        self.assertEqual([item["concept_key"] for item in notes], ["linear_algebra.dot_product"])
        self.assertEqual([item["signal_id"] for item in signals], ["signal-active-example"])
        self.assertEqual([item["topic_id"] for item in memories], ["topic-attention-memory"])

    def test_data_records_can_be_inspected_corrected_and_forgotten(self) -> None:
        self.initialize()
        original = {
            "concept_key": "cs.hash_table",
            "aliases": ["hash map"],
            "summary": "用户说自己熟悉哈希表。",
            "state": "known",
            "basis": "user_declared",
            "last_observed_at": NOW,
        }
        self.ok(
            "data",
            "correct",
            "--input",
            "-",
            payload={"record_type": "concept_note", "record": original},
        )
        inspected = self.ok(
            "data",
            "inspect",
            "--input",
            "-",
            payload={"record_type": "concept_note", "record_id": "cs.hash_table"},
        )
        records = self.find_key(inspected, "records")
        if records is None:
            records = self.find_key(inspected, "matches")
        if records is None:
            records = self.find_key(inspected, "concept_notes")
        self.assertIsInstance(records, list)
        assert isinstance(records, list)
        self.assertEqual(records, [original])

        corrected = {
            **original,
            "summary": "用户纠正：只知道用途，不清楚冲突处理。",
            "state": "needs_revisit",
        }
        self.ok(
            "data",
            "correct",
            "--input",
            "-",
            payload={"record_type": "concept_note", "record": corrected},
        )
        state = self.inspect_state()
        notes = self.find_key(state, "concept_notes")
        assert isinstance(notes, list)
        matches = [item for item in notes if item["concept_key"] == "cs.hash_table"]
        self.assertEqual(matches, [corrected])

        self.ok(
            "data",
            "forget",
            "--input",
            "-",
            payload={"record_type": "concept_note", "record_id": "cs.hash_table"},
        )
        context = self.ok(
            "context",
            "get",
            "--input",
            "-",
            payload={"concept_keys": ["cs.hash_table"]},
        )
        notes = self.find_key(context, "concept_notes")
        self.assertEqual(notes, [])

    def test_malformed_and_structurally_invalid_input_is_machine_readable(self) -> None:
        self.initialize()
        self.error(
            "INVALID_INPUT",
            "session",
            "start",
            "--input",
            "-",
            raw_input="{this is not JSON",
        )
        invalid_diagnosis = self.awaiting_start()
        invalid_diagnosis["diagnosis"]["questions"][0]["options"] = [
            {"option_id": "only-answer", "label": "答案", "kind": "answer"},
            {"option_id": "another-answer", "label": "另一个答案", "kind": "answer"},
        ]
        self.error(
            "INVALID_INPUT",
            "session",
            "start",
            "--input",
            "-",
            payload=invalid_diagnosis,
        )
        self.error(
            "INVALID_INPUT",
            "data",
            "correct",
            "--input",
            "-",
            payload={"record_type": "concept_note"},
        )

    def test_escaped_lone_surrogates_return_one_safe_json_error(self) -> None:
        self.initialize()
        raw_documents = [
            '{"topic_terms":["\\ud800"]}',
            '{"\\ud800":"value"}',
        ]
        for raw_document in raw_documents:
            with self.subTest(raw_document=raw_document):
                completed, document = self.run_cli(
                    "context",
                    "get",
                    "--input",
                    "-",
                    raw_input=raw_document,
                )
                self.assertEqual(completed.returncode, 2)
                self.assertIs(document.get("ok"), False)
                error = document.get("error")
                self.assertIsInstance(error, dict)
                assert isinstance(error, dict)
                self.assertEqual(error.get("code"), "INVALID_INPUT")
                self.assertNotIn("Traceback", completed.stdout)
                self.assertNotIn("Traceback", completed.stderr)

    def test_timestamps_and_absolute_uris_use_rfc3339_contract(self) -> None:
        self.initialize()
        for invalid_timestamp in (
            "2026-W35-4T08:00:00Z",
            "2026-08-27 08:00:00Z",
        ):
            with self.subTest(invalid_timestamp=invalid_timestamp):
                self.error(
                    "INVALID_INPUT",
                    "data",
                    "correct",
                    "--input",
                    "-",
                    payload={
                        "record_type": "explicit_preference",
                        "record": {
                            "preference_id": "pref-invalid-time",
                            "scope": "global",
                            "instruction": "这个时间格式不应被接受。",
                            "updated_at": invalid_timestamp,
                        },
                    },
                )

        topic_memory = {
            "topic_id": "topic-uri-validation",
            "title": "URI validation",
            "goal": self.goal("covered"),
            "summary": "用于验证来源链接格式。",
            "unresolved_questions": [],
            "source_links": ["https://example.com/attention", "urn:example:attention:qkv"],
            "close_reason": "scope_delivered",
            "closed_at": NOW,
        }
        self.error(
            "INVALID_INPUT",
            "data",
            "correct",
            "--input",
            "-",
            payload={
                "record_type": "topic_memory",
                "record": {**topic_memory, "source_links": ["not a uri:foo"]},
            },
        )
        self.ok(
            "data",
            "correct",
            "--input",
            "-",
            payload={"record_type": "topic_memory", "record": topic_memory},
        )
        state = self.inspect_state()
        memories = self.find_key(state, "topic_memories")
        assert isinstance(memories, list)
        stored = next(item for item in memories if item["topic_id"] == "topic-uri-validation")
        self.assertEqual(stored["source_links"], topic_memory["source_links"])

    def test_session_mutations_fail_cleanly_when_no_session_is_open(self) -> None:
        self.initialize()
        checkpoint = {
            "session_id": "missing-session",
            "status": "paused",
            "goal": self.goal(),
            "diagnosis": self.diagnosis_complete(),
            "teaching_state": self.teaching_state(),
        }
        self.error(
            "NO_OPEN_SESSION",
            "session",
            "checkpoint",
            "--expected-revision",
            "1",
            "--input",
            "-",
            payload=checkpoint,
        )
        self.error(
            "NO_OPEN_SESSION",
            "session",
            "close",
            "--expected-revision",
            "1",
            "--input",
            "-",
            payload=self.close_payload("missing-session"),
        )


if __name__ == "__main__":
    unittest.main()
