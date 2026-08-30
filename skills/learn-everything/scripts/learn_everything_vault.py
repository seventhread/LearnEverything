#!/usr/bin/env python3
"""Deterministic Markdown Vault tooling for LearnEverything v2.

The tool owns only mechanical concerns: locating a Vault, planning and applying
initialization, and checking structural invariants.  Teaching, semantic review,
and Markdown knowledge synthesis remain the Skill's responsibility.
"""

from __future__ import annotations

import argparse
import csv
from dataclasses import dataclass
from datetime import date, datetime
import hashlib
import io
import json
import os
from pathlib import Path, PurePosixPath
import re
import shutil
import subprocess
import sys
import tempfile
import unicodedata
from typing import Any, Iterable
from urllib.parse import urlparse


SCHEMA_VERSION = 1
MARKER_REL = ".learn-everything/vault.json"
MANAGED_DIRS = ("knowledge", "learning", "profile", "sources")
STATIC_IGNORED_ROOTS = {".obsidian", ".learn-everything", ".trash", "templates"}
PROTECTED_IGNORED_ROOTS = {".learn-everything", *MANAGED_DIRS}
KINDS = {"index", "concept", "map", "learning-record", "profile", "source"}
GIT_MODES = {"managed", "external", "off"}
SLUG = r"[a-z0-9]+(?:-[a-z0-9]+)*"
ID_PATTERNS = {
    "index": re.compile(r"^index\.home$"),
    "concept": re.compile(rf"^knowledge\.{SLUG}$"),
    "map": re.compile(rf"^knowledge\.{SLUG}$"),
    "learning-record": re.compile(
        rf"^learning\.(\d{{4}}-\d{{2}}-\d{{2}})\.({SLUG})\.(\d+)$"
    ),
    "profile": re.compile(r"^profile\.learning-guidance$"),
    "source": re.compile(rf"^source\.{SLUG}$"),
}
FORBIDDEN_STEM = re.compile(r'[\\/:*?"<>|#^\[\]\x00-\x1f\x7f]')
WIKILINK_RE = re.compile(r"(!?)\[\[([^\]]+)\]\]")
RFC3339_RE = re.compile(
    r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:\d{2})$"
)


class ToolError(Exception):
    """A predictable configuration, argument, or I/O failure."""

    def __init__(
        self,
        code: str,
        message: str,
        *,
        details: dict[str, Any] | None = None,
        exit_code: int = 2,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.details = details or {}
        self.exit_code = exit_code


class Parser(argparse.ArgumentParser):
    def error(self, message: str) -> None:
        raise ToolError("INVALID_ARGUMENT", message)


@dataclass
class Note:
    path: str
    text: str
    managed: bool
    metadata: dict[str, Any] | None = None
    body: str = ""
    h1: str | None = None
    kind: str | None = None
    note_id: str | None = None
    aliases: list[str] | None = None
    body_line_offset: int = 0

    @property
    def stem(self) -> str:
        return Path(self.path).stem


def diagnostic(
    code: str,
    severity: str,
    message: str,
    *,
    path: str | None = None,
    line: int | None = None,
) -> dict[str, Any]:
    result: dict[str, Any] = {
        "code": code,
        "severity": severity,
        "message": message,
    }
    if path is not None:
        result["path"] = path
    if line is not None:
        result["line"] = line
    return result


def normalize_identity(value: str) -> str:
    return " ".join(unicodedata.normalize("NFKC", value).strip().split()).casefold()


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha256_json(value: Any) -> str:
    encoded = json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    return sha256_bytes(encoded)


def today() -> str:
    return date.today().isoformat()


def locator_path() -> Path:
    if sys.platform == "darwin":
        return Path.home() / "Library/Application Support/LearnEverything/config.json"
    if os.name == "nt":
        base = Path(os.environ.get("APPDATA", str(Path.home())))
        return base / "LearnEverything/config.json"
    base = Path(os.environ.get("XDG_CONFIG_HOME", str(Path.home() / ".config")))
    return base / "learn-everything/config.json"


def atomic_write(path: Path, content: str) -> None:
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        descriptor, temporary = tempfile.mkstemp(
            prefix=f".{path.name}.", suffix=".tmp", dir=str(path.parent)
        )
        temporary_path = Path(temporary)
        try:
            with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as handle:
                handle.write(content)
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temporary_path, path)
        finally:
            if temporary_path.exists():
                temporary_path.unlink()
    except OSError as error:
        raise ToolError(
            "IO_ERROR",
            f"Could not write {path}.",
            details={"path": str(path), "reason": str(error)},
        ) from error


def json_text(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n"


def canonical_root(raw: str) -> Path:
    supplied = Path(raw)
    if not supplied.is_absolute():
        raise ToolError(
            "INVALID_ROOT", "--root must be an absolute path.", details={"root": raw}
        )
    expanded = supplied.expanduser()
    try:
        if expanded.exists():
            return expanded.resolve(strict=True)
        parent = expanded.parent.resolve(strict=True)
        if not parent.is_dir():
            raise ToolError("INVALID_ROOT", "The parent path is not a directory.")
        return parent / expanded.name
    except OSError as error:
        raise ToolError(
            "INVALID_ROOT",
            "Could not canonicalize the Vault path.",
            details={"root": raw, "reason": str(error)},
        ) from error


def is_filesystem_root(path: Path) -> bool:
    return path == Path(path.anchor)


def validate_ignored_path(raw: str, root: Path) -> str:
    if not isinstance(raw, str) or not raw:
        raise ToolError("INVALID_CONFIG", "ignored_paths entries must be non-empty.")
    if (
        raw in {".", "./"}
        or raw.startswith("/")
        or raw.endswith("/")
        or "//" in raw
        or "\\" in raw
        or any(character in raw for character in "*?[]{}")
    ):
        raise ToolError(
            "INVALID_CONFIG",
            "ignored_paths must use canonical POSIX Vault-relative directories.",
            details={"ignored_path": raw},
        )
    parts = PurePosixPath(raw).parts
    if not parts or any(part in {"", ".", ".."} for part in parts):
        raise ToolError("INVALID_CONFIG", "ignored_paths cannot contain . or .. components.")
    if parts[0] in PROTECTED_IGNORED_ROOTS:
        raise ToolError(
            "INVALID_CONFIG",
            "ignored_paths cannot exclude a managed root.",
            details={"ignored_path": raw},
        )
    candidate = root.joinpath(*parts)
    if candidate.exists():
        try:
            resolved = candidate.resolve(strict=True)
            resolved.relative_to(root)
        except (OSError, ValueError) as error:
            raise ToolError(
                "INVALID_CONFIG",
                "ignored_paths cannot escape the Vault through a symlink.",
                details={"ignored_path": raw},
            ) from error
    return PurePosixPath(*parts).as_posix()


def validate_vault_config(value: Any, root: Path) -> dict[str, Any]:
    if not isinstance(value, dict) or value.get("schema_version") != SCHEMA_VERSION:
        raise ToolError("INVALID_CONFIG", "Unsupported or missing Vault schema_version.")
    ignored = value.get("ignored_paths")
    git = value.get("git")
    if not isinstance(ignored, list) or not all(isinstance(item, str) for item in ignored):
        raise ToolError("INVALID_CONFIG", "ignored_paths must be an array of strings.")
    normalized = [validate_ignored_path(item, root) for item in ignored]
    if len(normalized) != len(set(normalized)):
        raise ToolError("INVALID_CONFIG", "ignored_paths entries must be unique.")
    if not isinstance(git, dict):
        raise ToolError("INVALID_CONFIG", "git must be an object.")
    mode = git.get("mode")
    auto_commit = git.get("auto_commit")
    if mode not in GIT_MODES or not isinstance(auto_commit, bool):
        raise ToolError("INVALID_CONFIG", "Invalid git.mode or git.auto_commit.")
    if mode == "off" and auto_commit:
        raise ToolError("INVALID_CONFIG", "git.auto_commit cannot be true in off mode.")
    return {
        "schema_version": SCHEMA_VERSION,
        "ignored_paths": normalized,
        "git": {"mode": mode, "auto_commit": auto_commit},
    }


def read_json(path: Path, *, code: str) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as error:
        raise ToolError(code, f"Missing file: {path}", details={"path": str(path)}) from error
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise ToolError(
            code,
            f"Could not read valid JSON from {path}.",
            details={"path": str(path), "reason": str(error)},
        ) from error


def read_marker(root: Path) -> dict[str, Any] | None:
    marker = root / MARKER_REL
    if not marker.exists():
        return None
    try:
        if marker.is_symlink() or marker.parent.is_symlink():
            raise ToolError(
                "INVALID_MARKER",
                "The Vault marker cannot be reached through a symlink.",
            )
        marker.resolve(strict=True).relative_to(root)
    except (OSError, ValueError) as error:
        raise ToolError(
            "INVALID_MARKER",
            "The Vault marker escapes the Vault root.",
            details={"path": str(marker)},
        ) from error
    return validate_vault_config(read_json(marker, code="INVALID_MARKER"), root)


def read_locator(*, required: bool) -> dict[str, Any] | None:
    path = locator_path()
    if not path.exists():
        if required:
            raise ToolError(
                "NOT_INITIALIZED",
                "No active LearnEverything Vault is configured.",
                details={"config_path": str(path)},
            )
        return None
    value = read_json(path, code="INVALID_LOCATOR")
    if (
        not isinstance(value, dict)
        or value.get("schema_version") != SCHEMA_VERSION
        or not isinstance(value.get("vault_root"), str)
    ):
        raise ToolError("INVALID_LOCATOR", "The active Vault locator is invalid.")
    root = canonical_root(value["vault_root"])
    return {"schema_version": SCHEMA_VERSION, "vault_root": str(root)}


def strip_yaml_comment(raw: str) -> str:
    quote: str | None = None
    escaped = False
    for index, character in enumerate(raw):
        if quote == '"' and escaped:
            escaped = False
            continue
        if quote == '"' and character == "\\":
            escaped = True
            continue
        if quote:
            if character == quote:
                quote = None
            continue
        if character in {"'", '"'}:
            quote = character
            continue
        if character == "#" and (index == 0 or raw[index - 1].isspace()):
            return raw[:index].rstrip()
    return raw.rstrip()


def parse_scalar(raw: str) -> Any:
    value = strip_yaml_comment(raw).strip()
    if value.startswith("["):
        if not value.endswith("]"):
            raise ValueError("unterminated inline sequence")
        inner = value[1:-1].strip()
        if not inner:
            return []
        reader = csv.reader(io.StringIO(inner), skipinitialspace=True)
        return [parse_scalar(item) for item in next(reader)]
    if len(value) >= 2 and value[0] == value[-1] == '"':
        return json.loads(value)
    if len(value) >= 2 and value[0] == value[-1] == "'":
        return value[1:-1].replace("''", "'")
    if value in {"true", "false"}:
        return value == "true"
    if value in {"null", "~"}:
        return None
    return value


def parse_frontmatter(text: str) -> tuple[dict[str, Any], str, int]:
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        raise ValueError("Markdown must start with YAML frontmatter")
    try:
        end = next(index for index in range(1, len(lines)) if lines[index].strip() == "---")
    except StopIteration as error:
        raise ValueError("YAML frontmatter is not closed") from error
    metadata: dict[str, Any] = {}
    index = 1
    while index < end:
        line = lines[index]
        if not line.strip() or line.lstrip().startswith("#"):
            index += 1
            continue
        if line[:1].isspace() or ":" not in line:
            raise ValueError(f"unsupported YAML at line {index + 1}")
        key, raw = line.split(":", 1)
        key = key.strip()
        if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_-]*", key):
            raise ValueError(f"invalid YAML key at line {index + 1}")
        if key in metadata:
            raise ValueError(f"duplicate YAML key: {key}")
        raw_value = strip_yaml_comment(raw).strip()
        cursor = index + 1
        nested_lines: list[str] = []
        while cursor < end:
            nested = lines[cursor]
            if nested.strip() and not nested[:1].isspace():
                break
            nested_lines.append(nested)
            cursor += 1
        if raw_value in {"|", "|-", "|+", ">", ">-", ">+"}:
            content = [line.lstrip() for line in nested_lines]
            metadata[key] = "\n".join(content).strip()
            index = cursor
            continue
        if raw_value:
            metadata[key] = parse_scalar(raw_value)
            index += 1
            continue
        meaningful = [line for line in nested_lines if line.strip()]
        sequence: list[Any] = []
        sequence_only = bool(meaningful)
        for nested in meaningful:
            match = re.match(r"^\s+-\s+(.+)$", nested)
            if not match:
                sequence_only = False
                break
            item = match.group(1)
            if re.match(r"^[^'\"]+?:\s", item):
                sequence.append({"_yaml": "mapping"})
            else:
                sequence.append(parse_scalar(item))
        if sequence_only:
            metadata[key] = sequence
        elif meaningful:
            # Unknown nested YAML properties are allowed and preserved by writers.
            # Required LearnEverything fields still fail their scalar/list schema below.
            metadata[key] = {"_yaml": "complex"}
        else:
            metadata[key] = None
        index = cursor
    body = "\n".join(lines[end + 1 :])
    return metadata, body, end + 2


def markdown_h1(body: str) -> list[tuple[int, str]]:
    return [
        (number, match.group(1))
        for number, line in enumerate(strip_markdown_code(body).splitlines(), start=1)
        if (match := re.match(r"^#\s+(.+?)\s*$", line))
    ]


def markdown_sections(body: str) -> list[tuple[int, str]]:
    return [
        (number, match.group(1).strip())
        for number, line in enumerate(strip_markdown_code(body).splitlines(), start=1)
        if (match := re.match(r"^##\s+(.+?)\s*$", line))
    ]


def is_date(value: Any) -> bool:
    if not isinstance(value, str) or not re.fullmatch(r"\d{4}-\d{2}-\d{2}", value):
        return False
    try:
        date.fromisoformat(value)
        return True
    except ValueError:
        return False


def is_rfc3339(value: Any) -> bool:
    if not isinstance(value, str) or not RFC3339_RE.fullmatch(value):
        return False
    try:
        datetime.fromisoformat(value.replace("Z", "+00:00"))
        return True
    except ValueError:
        return False


def is_managed_markdown(relative: str) -> bool:
    path = PurePosixPath(relative)
    if relative == "Home.md":
        return True
    if path.suffix.casefold() != ".md":
        return False
    parts = path.parts
    if not parts:
        return False
    if parts[0] in {"knowledge", "learning", "sources"}:
        return len(parts) >= 2
    return parts[0] == "profile" and len(parts) == 2


def is_excluded(relative: str, ignored_paths: list[str]) -> bool:
    parts = PurePosixPath(relative).parts
    if not parts:
        return True
    if parts[0] in STATIC_IGNORED_ROOTS:
        return True
    if any(part.startswith(".") for part in parts[:-1]):
        return True
    for ignored in ignored_paths:
        ignored_parts = PurePosixPath(ignored).parts
        if parts[: len(ignored_parts)] == ignored_parts:
            return True
    return False


def collect_visible_files(root: Path, ignored_paths: list[str]) -> dict[str, Path]:
    if not root.exists():
        return {}
    output: dict[str, Path] = {}
    try:
        for directory, names, files in os.walk(root, followlinks=False):
            directory_path = Path(directory)
            relative_directory = directory_path.relative_to(root)
            kept: list[str] = []
            for name in names:
                candidate = relative_directory / name
                relative = candidate.as_posix()
                if name == ".git" or is_excluded(relative, ignored_paths):
                    continue
                kept.append(name)
            names[:] = kept
            for name in files:
                candidate = directory_path / name
                relative = candidate.relative_to(root).as_posix()
                if is_excluded(relative, ignored_paths):
                    continue
                output[relative] = candidate
    except OSError as error:
        raise ToolError(
            "IO_ERROR",
            "Could not scan the Vault.",
            details={"root": str(root), "reason": str(error)},
        ) from error
    return output


def read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except (OSError, UnicodeError) as error:
        raise ToolError(
            "IO_ERROR",
            f"Could not read UTF-8 text from {path}.",
            details={"path": str(path), "reason": str(error)},
        ) from error


def git_run(root: Path, *arguments: str, check: bool = False) -> subprocess.CompletedProcess[str]:
    completed = subprocess.run(
        ["git", "-C", str(root), *arguments],
        text=True,
        capture_output=True,
        check=False,
        timeout=20,
    )
    if check and completed.returncode != 0:
        raise ToolError(
            "GIT_ERROR",
            "Git command failed.",
            details={
                "arguments": list(arguments),
                "stderr": completed.stderr.strip(),
            },
        )
    return completed


def git_state(root: Path) -> dict[str, Any]:
    if not root.exists():
        return {
            "available": shutil.which("git") is not None,
            "top_level": None,
            "head": None,
            "status_hash": None,
            "staged": False,
        }
    if shutil.which("git") is None:
        return {
            "available": False,
            "top_level": None,
            "head": None,
            "status_hash": None,
            "staged": False,
        }
    top = git_run(root, "rev-parse", "--show-toplevel")
    if top.returncode != 0:
        return {
            "available": True,
            "top_level": None,
            "head": None,
            "status_hash": None,
            "staged": False,
        }
    top_level = str(Path(top.stdout.strip()).resolve())
    head_result = git_run(root, "rev-parse", "--verify", "HEAD")
    head = head_result.stdout.strip() if head_result.returncode == 0 else None
    status = git_run(root, "status", "--porcelain=v1", "-z", "--untracked-files=all")
    cached = git_run(root, "diff", "--cached", "--quiet")
    return {
        "available": True,
        "top_level": top_level,
        "head": head,
        "status_hash": sha256_bytes(status.stdout.encode("utf-8")),
        "staged": cached.returncode == 1,
    }


def baseline_paths(config: dict[str, Any]) -> list[str]:
    paths = [MARKER_REL, "Home.md"]
    if config["git"]["mode"] == "managed":
        paths.append(".gitignore")
    return paths


def git_baseline_valid(root: Path, config: dict[str, Any]) -> bool:
    state = git_state(root)
    if state["top_level"] != str(root) or not state["head"]:
        return False
    for relative in baseline_paths(config):
        tracked = git_run(root, "ls-files", "--error-unmatch", "--", relative)
        if tracked.returncode != 0:
            return False
    return True


def expected_kind(relative: str) -> set[str]:
    parts = PurePosixPath(relative).parts
    if relative == "Home.md":
        return {"index"}
    if parts[0] == "knowledge":
        return {"concept", "map"}
    if parts[0] == "learning":
        return {"learning-record"}
    if parts[0] == "profile":
        return {"profile"}
    if parts[0] == "sources":
        return {"source"}
    return set()


def strip_markdown_code(text: str) -> str:
    without_comments = re.sub(r"<!--.*?-->", "", text, flags=re.DOTALL)
    output: list[str] = []
    in_fence = False
    fence = ""
    for line in without_comments.splitlines():
        match = re.match(r"^\s*(```|~~~)", line)
        if match:
            marker = match.group(1)
            if not in_fence:
                in_fence = True
                fence = marker
            elif marker == fence:
                in_fence = False
            output.append("")
            continue
        if in_fence:
            output.append("")
        else:
            output.append(re.sub(r"`[^`]*`", "", line))
    return "\n".join(output)


def wikilinks(text: str) -> list[tuple[int, str, bool]]:
    clean = strip_markdown_code(text)
    links: list[tuple[int, str, bool]] = []
    for line_number, line in enumerate(clean.splitlines(), start=1):
        for match in WIKILINK_RE.finditer(line):
            links.append((line_number, match.group(2).strip(), bool(match.group(1))))
    return links


def split_link(raw: str) -> tuple[str, str | None, str | None]:
    target = raw.split("|", 1)[0].strip()
    heading: str | None = None
    block: str | None = None
    if "#" in target:
        target, heading = target.split("#", 1)
    if "^" in target:
        target, block = target.split("^", 1)
    elif heading and "^" in heading:
        heading, block = heading.split("^", 1)
    return target.strip(), heading, block


def resolve_note_target(
    target: str,
    *,
    path_index: dict[str, list[str]],
    stem_index: dict[str, list[str]],
) -> list[str]:
    normalized = target[:-3] if target.casefold().endswith(".md") else target
    if "/" in normalized:
        key = normalize_identity(PurePosixPath(normalized).as_posix())
        return path_index.get(key, [])
    return stem_index.get(normalize_identity(normalized), [])


def section_text(body: str, heading: str) -> str:
    lines = body.splitlines()
    clean_lines = strip_markdown_code(body).splitlines()
    collecting = False
    output: list[str] = []
    for line, clean_line in zip(lines, clean_lines):
        if re.match(r"^##\s+", clean_line):
            current = re.sub(r"^##\s+", "", clean_line).strip()
            if collecting:
                break
            collecting = current == heading
            continue
        if collecting:
            output.append(line)
    return "\n".join(output)


def source_access_date_warnings(note: Note) -> list[dict[str, Any]]:
    diagnostics: list[dict[str, Any]] = []
    current_section: str | None = None
    clean = strip_markdown_code(note.body)
    for line_number, line in enumerate(clean.splitlines(), start=1):
        section = re.match(r"^##\s+(.+?)\s*$", line)
        if section:
            current_section = section.group(1).strip()
            continue
        if current_section not in {"来源", "网络来源"}:
            continue
        if not re.match(r"^\s*[-+*]\s+", line) or not re.search(r"https?://\S+", line):
            continue
        dates = re.findall(r"(?<!\d)\d{4}-\d{2}-\d{2}(?!\d)", line)
        if not any(is_date(value) for value in dates):
            diagnostics.append(
                diagnostic(
                    "SOURCE_ACCESS_DATE_MISSING",
                    "warning",
                    "A source list item with an HTTP(S) URL should include an access date.",
                    path=note.path,
                    line=line_number + note.body_line_offset,
                )
            )
    return diagnostics


def validate_note_schema(note: Note, diagnostics: list[dict[str, Any]]) -> None:
    assert note.metadata is not None
    metadata = note.metadata
    allowed_kinds = expected_kind(note.path)
    kind = metadata.get("kind")
    note_id = metadata.get("id")
    if not isinstance(kind, str) or kind not in KINDS or kind not in allowed_kinds:
        diagnostics.append(
            diagnostic(
                "KIND_PATH_MISMATCH",
                "error",
                "kind is missing, unsupported, or incompatible with the managed path.",
                path=note.path,
            )
        )
        return
    note.kind = kind
    if not isinstance(note_id, str) or not ID_PATTERNS[kind].fullmatch(note_id):
        diagnostics.append(
            diagnostic(
                "INVALID_ID",
                "error",
                "id does not match the fixed syntax for this kind.",
                path=note.path,
            )
        )
    else:
        note.note_id = note_id
    aliases = metadata.get("aliases", [])
    if not isinstance(aliases, list) or not all(
        isinstance(alias, str) and alias.strip() for alias in aliases
    ):
        diagnostics.append(
            diagnostic(
                "INVALID_ALIASES",
                "error",
                "aliases must be a YAML sequence of non-empty strings.",
                path=note.path,
            )
        )
        aliases = []
    normalized_aliases = [normalize_identity(alias) for alias in aliases]
    if len(normalized_aliases) != len(set(normalized_aliases)):
        diagnostics.append(
            diagnostic(
                "DUPLICATE_ALIAS",
                "error",
                "aliases are duplicated after identity normalization.",
                path=note.path,
            )
        )
    note.aliases = aliases
    for field in ("created", "updated"):
        if field in metadata and not is_date(metadata[field]):
            diagnostics.append(
                diagnostic(
                    "INVALID_DATE",
                    "error",
                    f"{field} must be a real YYYY-MM-DD date.",
                    path=note.path,
                )
            )
    required_dates: tuple[str, ...]
    if kind == "index":
        required_dates = ("updated",)
    elif kind in {"concept", "map", "profile", "source"}:
        required_dates = ("created", "updated")
    else:
        required_dates = ()
    for field in required_dates:
        if field not in metadata:
            diagnostics.append(
                diagnostic(
                    "MISSING_FIELD", "error", f"Missing {field}.", path=note.path
                )
            )
    if kind == "source":
        parsed = urlparse(metadata.get("url") if isinstance(metadata.get("url"), str) else "")
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            diagnostics.append(
                diagnostic("INVALID_URL", "error", "source url must be absolute HTTP(S).", path=note.path)
            )
        if not is_date(metadata.get("accessed_at")):
            diagnostics.append(
                diagnostic(
                    "INVALID_DATE", "error", "accessed_at must be a real date.", path=note.path
                )
            )
    if kind == "learning-record":
        completed = metadata.get("completed_at")
        if not is_rfc3339(completed):
            diagnostics.append(
                diagnostic(
                    "INVALID_DATETIME",
                    "error",
                    "completed_at must be RFC 3339 with an explicit timezone.",
                    path=note.path,
                )
            )
        match = ID_PATTERNS[kind].fullmatch(note_id or "")
        filename = re.fullmatch(r"(\d{4}-\d{2}-\d{2}) (\d+) .+\.md", Path(note.path).name)
        parts = PurePosixPath(note.path).parts
        if not match or not filename or len(parts) != 3:
            diagnostics.append(
                diagnostic(
                    "LEARNING_PATH_MISMATCH",
                    "error",
                    "learning record path must include year, date, sequence, and title.",
                    path=note.path,
                )
            )
        else:
            record_date, _, sequence = match.groups()
            filename_date, filename_sequence = filename.groups()
            number = int(sequence)
            canonical_sequence = f"{number:02d}" if number < 10 else str(number)
            completed_date = completed[:10] if isinstance(completed, str) else None
            if (
                number < 1
                or parts[1] != record_date[:4]
                or filename_date != record_date
                or filename_sequence != canonical_sequence
                or sequence != canonical_sequence
                or completed_date != record_date
            ):
                diagnostics.append(
                    diagnostic(
                        "LEARNING_PATH_MISMATCH",
                        "error",
                        "learning id, path, filename, and completed_at disagree.",
                        path=note.path,
                    )
                )
        required_sections = {"本次目标", "已完成内容", "本次沉淀"}
        present = {heading for _, heading in markdown_sections(note.body)}
        for missing in sorted(required_sections - present):
            diagnostics.append(
                diagnostic(
                    "MISSING_SECTION",
                    "error",
                    f"Missing ## {missing}.",
                    path=note.path,
                )
            )
        legacy = {
            "status",
            "session_id",
            "checkpoint",
            "revision",
            "unconfirmed_unit",
            "open_session",
        }
        for field in sorted(legacy.intersection(metadata)):
            diagnostics.append(
                diagnostic(
                    "LEGACY_SESSION_FIELD",
                    "error",
                    f"Completed learning records cannot contain {field}.",
                    path=note.path,
                )
            )
    if kind == "profile":
        if note_id != "profile.learning-guidance":
            diagnostics.append(
                diagnostic("INVALID_PROFILE_ID", "error", "Profile id is fixed.", path=note.path)
            )
        sections = [heading for _, heading in markdown_sections(note.body)]
        for required in ("明确偏好", "教学反馈"):
            if sections.count(required) != 1:
                diagnostics.append(
                    diagnostic(
                        "PROFILE_SECTION_COUNT",
                        "error",
                        f"Profile must contain exactly one ## {required} section.",
                        path=note.path,
                    )
                )


def lint_vault(
    root: Path,
    *,
    config_override: dict[str, Any] | None = None,
    virtual_files: dict[str, str] | None = None,
    base: str | None = None,
    check_git: bool = True,
) -> dict[str, Any]:
    virtual_files = virtual_files or {}
    diagnostics: list[dict[str, Any]] = []
    try:
        config = config_override or read_marker(root)
        if config is None:
            raise ToolError("INVALID_MARKER", "The Vault marker is missing.")
        config = validate_vault_config(config, root)
    except ToolError as error:
        diagnostics.append(diagnostic(error.code, "error", error.message, path=MARKER_REL))
        config = {
            "schema_version": SCHEMA_VERSION,
            "ignored_paths": [],
            "git": {"mode": "off", "auto_commit": False},
        }
    for managed_root in MANAGED_DIRS:
        candidate = root / managed_root
        if candidate.is_symlink() or (candidate.exists() and not candidate.is_dir()):
            diagnostics.append(
                diagnostic(
                    "MANAGED_ROOT_INVALID",
                    "error",
                    "Managed roots must be real directories inside the Vault.",
                    path=managed_root,
                )
            )
    files = collect_visible_files(root, config["ignored_paths"])
    for relative in virtual_files:
        files.setdefault(relative, root / relative)
    notes: dict[str, Note] = {}
    unsafe_paths: set[str] = set()
    for relative, candidate in files.items():
        if relative in virtual_files:
            continue
        try:
            candidate.resolve(strict=True).relative_to(root)
        except (OSError, ValueError):
            diagnostics.append(
                diagnostic(
                    "PATH_ESCAPE",
                    "error",
                    "A visible path escapes the Vault or cannot be resolved.",
                    path=relative,
                )
            )
            unsafe_paths.add(relative)
    all_paths = sorted(set(files) - unsafe_paths)
    case_groups: dict[str, list[str]] = {}
    for relative in all_paths:
        case_groups.setdefault(normalize_identity(relative), []).append(relative)
        if Path(relative).suffix.casefold() != ".md":
            continue
        try:
            text = virtual_files.get(relative)
            if text is None:
                candidate = files[relative]
                text = read_text(candidate)
        except (OSError, ToolError) as error:
            message = error.message if isinstance(error, ToolError) else str(error)
            diagnostics.append(diagnostic("READ_ERROR", "error", message, path=relative))
            continue
        managed = is_managed_markdown(relative)
        note = Note(path=relative, text=text, managed=managed)
        notes[relative] = note
        if not managed:
            note.body = text
            if text.startswith("---\n") or text.startswith("---\r\n"):
                try:
                    _, note.body, offset = parse_frontmatter(text)
                    note.body_line_offset = offset - 1
                except ValueError:
                    pass
            continue
        try:
            metadata, body, offset = parse_frontmatter(text)
            note.metadata = metadata
            note.body = body
            note.body_line_offset = offset - 1
            h1s = markdown_h1(body)
            if len(h1s) != 1:
                diagnostics.append(
                    diagnostic(
                        "H1_COUNT",
                        "error",
                        "Managed Markdown must contain exactly one H1.",
                        path=relative,
                    )
                )
            else:
                note.h1 = h1s[0][1]
            validate_note_schema(note, diagnostics)
            if not note.stem or FORBIDDEN_STEM.search(note.stem):
                diagnostics.append(
                    diagnostic(
                        "INVALID_STEM",
                        "error",
                        "Managed file stem is empty or contains a forbidden character.",
                        path=relative,
                    )
                )
        except (ValueError, json.JSONDecodeError) as error:
            diagnostics.append(
                diagnostic("INVALID_FRONTMATTER", "error", str(error), path=relative)
            )
    for colliding in case_groups.values():
        if len(colliding) > 1 and any(is_managed_markdown(path) for path in colliding):
            for path in colliding:
                if is_managed_markdown(path):
                    diagnostics.append(
                        diagnostic(
                            "CASE_COLLISION",
                            "error",
                            "Visible paths collide after Unicode/case normalization.",
                            path=path,
                        )
                    )
    managed_notes = [note for note in notes.values() if note.managed]
    ids: dict[str, list[str]] = {}
    for note in managed_notes:
        if note.note_id:
            ids.setdefault(note.note_id, []).append(note.path)
    for note_id, paths in ids.items():
        if len(paths) > 1:
            for path in paths:
                diagnostics.append(
                    diagnostic("DUPLICATE_ID", "error", f"Duplicate id: {note_id}.", path=path)
                )
    profile_paths = [note.path for note in managed_notes if note.kind == "profile"]
    if len(profile_paths) > 1:
        for path in profile_paths:
            diagnostics.append(
                diagnostic("MULTIPLE_PROFILES", "error", "Only one profile page is allowed.", path=path)
            )
    daily_sequences: dict[tuple[str, int], list[str]] = {}
    for note in managed_notes:
        if note.kind != "learning-record" or not note.note_id:
            continue
        match = ID_PATTERNS["learning-record"].fullmatch(note.note_id)
        if match:
            daily_sequences.setdefault((match.group(1), int(match.group(3))), []).append(note.path)
    for (record_date, sequence), paths in daily_sequences.items():
        if len(paths) > 1:
            for path in paths:
                diagnostics.append(
                    diagnostic(
                        "DAILY_SEQUENCE_COLLISION",
                        "error",
                        f"Learning sequence {sequence} is repeated on {record_date}.",
                        path=path,
                    )
                )
    stem_index: dict[str, list[str]] = {}
    path_index: dict[str, list[str]] = {}
    attachment_names: dict[str, list[str]] = {}
    attachment_paths: dict[str, list[str]] = {}
    for relative in all_paths:
        suffix = Path(relative).suffix.casefold()
        if suffix == ".md":
            stem_index.setdefault(normalize_identity(Path(relative).stem), []).append(relative)
            without_suffix = PurePosixPath(relative).with_suffix("").as_posix()
            path_index.setdefault(normalize_identity(without_suffix), []).append(relative)
        else:
            attachment_names.setdefault(normalize_identity(Path(relative).name), []).append(relative)
            attachment_paths.setdefault(normalize_identity(relative), []).append(relative)
    for paths in stem_index.values():
        if len(paths) > 1 and any(is_managed_markdown(path) for path in paths):
            for path in paths:
                if is_managed_markdown(path):
                    diagnostics.append(
                        diagnostic(
                            "STEM_COLLISION",
                            "error",
                            "Managed file stem collides with another visible Markdown note.",
                            path=path,
                        )
                    )
    knowledge_tokens: dict[str, list[str]] = {}
    for note in managed_notes:
        if note.kind not in {"concept", "map"}:
            continue
        tokens = [note.stem]
        if note.h1:
            tokens.append(note.h1)
        tokens.extend(note.aliases or [])
        for token in {normalize_identity(value) for value in tokens}:
            knowledge_tokens.setdefault(token, []).append(note.path)
    for paths in knowledge_tokens.values():
        unique = sorted(set(paths))
        if len(unique) > 1:
            for path in unique:
                diagnostics.append(
                    diagnostic(
                        "KNOWLEDGE_IDENTITY_COLLISION",
                        "error",
                        "Knowledge stem, H1, or alias is ambiguous.",
                        path=path,
                    )
                )
    outgoing: dict[str, set[str]] = {path: set() for path in notes}
    backlinks: dict[str, set[str]] = {path: set() for path in notes}
    for note in notes.values():
        link_source = note.body if note.managed and note.metadata is not None else note.text
        for line, raw, embedded in wikilinks(link_source):
            display_line = line + note.body_line_offset if note.managed else line
            target, heading, block = split_link(raw)
            if not target:
                continue
            pure = PurePosixPath(target)
            if pure.is_absolute() or ".." in pure.parts or re.match(r"^[A-Za-z]:", target):
                if note.managed:
                    diagnostics.append(
                        diagnostic(
                            "UNSAFE_LINK",
                            "error",
                            "Wikilinks cannot be absolute or contain .. components.",
                            path=note.path,
                            line=display_line,
                        )
                    )
                continue
            suffix = Path(target).suffix.casefold()
            if suffix and suffix != ".md":
                if "/" in target:
                    candidates = attachment_paths.get(normalize_identity(target), [])
                else:
                    candidates = attachment_names.get(normalize_identity(Path(target).name), [])
                if len(candidates) == 1:
                    continue
                if note.managed and len(candidates) > 1:
                    diagnostics.append(
                        diagnostic(
                            "ATTACHMENT_LINK_ERROR",
                            "error",
                            "Attachment link is ambiguous.",
                            path=note.path,
                            line=display_line,
                        )
                    )
                    continue
                # A note stem may itself contain dots. If there is no actual
                # attachment with this name/path, resolve the target as a note.
            candidates = resolve_note_target(target, path_index=path_index, stem_index=stem_index)
            if note.managed and len(candidates) != 1:
                diagnostics.append(
                    diagnostic(
                        "NOTE_LINK_ERROR",
                        "error",
                        "Note link is missing or ambiguous.",
                        path=note.path,
                        line=display_line,
                    )
                )
                continue
            if len(candidates) != 1:
                continue
            resolved = candidates[0]
            outgoing.setdefault(note.path, set()).add(resolved)
            backlinks.setdefault(resolved, set()).add(note.path)
            if note.managed and resolved == note.path:
                diagnostics.append(
                    diagnostic(
                        "SELF_LINK",
                        "warning",
                        "Note links to itself.",
                        path=note.path,
                        line=display_line,
                    )
                )
            target_note = notes.get(resolved)
            if note.managed and target_note and heading:
                headings = {
                    normalize_identity(match.group(1))
                    for target_line in target_note.body.splitlines()
                    if (match := re.match(r"^#{1,6}\s+(.+?)\s*$", target_line))
                }
                if normalize_identity(heading) not in headings:
                    diagnostics.append(
                        diagnostic(
                            "MISSING_HEADING",
                            "warning",
                            "Linked heading does not exist.",
                            path=note.path,
                            line=display_line,
                        )
                    )
            if note.managed and target_note and block:
                if not re.search(rf"\^{re.escape(block)}(?:\s|$)", target_note.body, flags=re.MULTILINE):
                    diagnostics.append(
                        diagnostic(
                            "MISSING_BLOCK",
                            "warning",
                            "Linked block does not exist.",
                            path=note.path,
                            line=display_line,
                        )
                    )
    for note in managed_notes:
        diagnostics.extend(source_access_date_warnings(note))
        if note.kind == "learning-record":
            deposited = section_text(note.body, "本次沉淀")
            valid = False
            for _, raw, _ in wikilinks(deposited):
                target, _, _ = split_link(raw)
                candidates = resolve_note_target(target, path_index=path_index, stem_index=stem_index)
                if len(candidates) == 1:
                    linked = notes.get(candidates[0])
                    if linked and linked.managed and linked.kind in {"concept", "map"}:
                        valid = True
                        break
            if not valid:
                diagnostics.append(
                    diagnostic(
                        "LEARNING_DEPOSIT_MISSING",
                        "error",
                        "本次沉淀 must link an existing managed concept or map.",
                        path=note.path,
                    )
                )
        if note.kind in {"concept", "map"}:
            neighbors = (outgoing.get(note.path, set()) | backlinks.get(note.path, set())) - {note.path}
            if not neighbors and note.path not in outgoing.get("Home.md", set()):
                diagnostics.append(
                    diagnostic(
                        "ORPHAN_KNOWLEDGE",
                        "warning",
                        "Knowledge page has no links or backlinks.",
                        path=note.path,
                    )
                )
    if check_git:
        mode = config["git"]["mode"]
        if mode == "external" and not git_baseline_valid(root, config):
            diagnostics.append(
                diagnostic(
                    "EXTERNAL_GIT_INVALID",
                    "error",
                    "external Git mode requires a root-level repository with a tracked baseline.",
                    path=MARKER_REL,
                )
            )
        elif mode == "managed" and not git_baseline_valid(root, config):
            diagnostics.append(
                diagnostic(
                    "MANAGED_GIT_DEGRADED",
                    "warning",
                    "managed Git baseline is unavailable; automatic commits must be skipped.",
                    path=MARKER_REL,
                )
            )
    if base:
        diagnostics.extend(history_diagnostics(root, base, notes))
    diagnostics.sort(
        key=lambda item: (
            0 if item["severity"] == "error" else 1,
            item.get("path", ""),
            item.get("line", 0),
            item["code"],
        )
    )
    errors = sum(item["severity"] == "error" for item in diagnostics)
    warnings = sum(item["severity"] == "warning" for item in diagnostics)
    return {
        "schema_version": SCHEMA_VERSION,
        "operation": "vault.lint",
        "root": str(root),
        "summary": {"errors": errors, "warnings": warnings, "files": len(files)},
        "diagnostics": diagnostics,
    }


def history_diagnostics(root: Path, base: str, notes: dict[str, Note]) -> list[dict[str, Any]]:
    diagnostics: list[dict[str, Any]] = []
    if shutil.which("git") is None:
        return [
            diagnostic(
                "GIT_BASE_UNAVAILABLE",
                "warning",
                "Git is unavailable; --base history checks were skipped.",
            )
        ]
    verify = git_run(root, "rev-parse", "--verify", f"{base}^{{commit}}")
    if verify.returncode != 0:
        return [
            diagnostic(
                "GIT_BASE_UNAVAILABLE",
                "warning",
                "The requested Git base does not resolve to a commit.",
            )
        ]
    listing = git_run(root, "ls-tree", "-r", "--name-only", base)
    if listing.returncode != 0:
        return []
    base_notes: dict[str, tuple[str | None, str | None, str]] = {}
    for relative in listing.stdout.splitlines():
        if not is_managed_markdown(relative):
            continue
        shown = git_run(root, "show", f"{base}:{relative}")
        if shown.returncode != 0:
            continue
        try:
            metadata, body, _ = parse_frontmatter(shown.stdout)
            h1s = markdown_h1(body)
            base_notes[relative] = (
                metadata.get("id") if isinstance(metadata.get("id"), str) else None,
                h1s[0][1] if len(h1s) == 1 else None,
                shown.stdout,
            )
        except ValueError:
            continue
    current_by_id = {note.note_id: note for note in notes.values() if note.note_id}
    base_ids = {value[0] for value in base_notes.values() if value[0]}
    current_ids = set(current_by_id)
    for path, (old_id, old_h1, old_text) in base_notes.items():
        current = notes.get(path)
        if current and old_id and current.note_id and old_id != current.note_id:
            diagnostics.append(
                diagnostic(
                    "ID_CHANGED",
                    "error",
                    "An existing managed path changed its stable id.",
                    path=path,
                )
            )
        if old_id and old_id.startswith("learning."):
            if not current:
                diagnostics.append(
                    diagnostic(
                        "LEARNING_HISTORY_CHANGED",
                        "warning",
                        "An existing learning record was deleted.",
                        path=path,
                    )
                )
            elif current.text != old_text:
                diagnostics.append(
                    diagnostic(
                        "LEARNING_HISTORY_CHANGED",
                        "warning",
                        "An existing learning record was modified.",
                        path=path,
                    )
                )
        if old_id and old_id in current_by_id and old_h1:
            moved = current_by_id[old_id]
            if moved.h1 and normalize_identity(moved.h1) != normalize_identity(old_h1):
                aliases = {normalize_identity(alias) for alias in (moved.aliases or [])}
                if normalize_identity(old_h1) not in aliases:
                    diagnostics.append(
                        diagnostic(
                            "OLD_TITLE_NOT_ALIAS",
                            "warning",
                            "A changed title was not retained as an alias.",
                            path=moved.path,
                        )
                    )
    disappeared = base_ids - current_ids
    appeared = current_ids - base_ids
    if disappeared and appeared:
        diagnostics.append(
            diagnostic(
                "IDENTITIES_REPLACED",
                "warning",
                "Old managed identities disappeared while new identities appeared.",
            )
        )
    return diagnostics


def home_template() -> str:
    return f"""---
id: index.home
kind: index
updated: {today()}
---

# LearnEverything

- 在 `knowledge/` 中阅读概念页和主题 map；
- 在 `learning/` 中按年份查看已经完成并确认保存的学习记录；
- 使用 Obsidian backlinks 和 Graph View 查看知识关系。
"""


def gitignore_template() -> str:
    return ".obsidian/\n.learn-everything/cache/\n.trash/\n"


def config_text(config: dict[str, Any]) -> str:
    return json_text(config)


def locator_text(root: Path) -> str:
    return json_text({"schema_version": SCHEMA_VERSION, "vault_root": str(root)})


def directory_empty(path: Path) -> bool:
    try:
        return not any(path.iterdir())
    except OSError as error:
        raise ToolError(
            "IO_ERROR",
            "Could not inspect the target directory.",
            details={"path": str(path), "reason": str(error)},
        ) from error


def marker_descendants(root: Path) -> list[str]:
    if not root.exists():
        return []
    found: list[str] = []
    for directory, names, files in os.walk(root, followlinks=False):
        if ".git" in names:
            names.remove(".git")
        path = Path(directory)
        marker = path / MARKER_REL
        if marker.is_file() and path != root:
            found.append(str(path))
            names[:] = []
    return sorted(found)


def ancestor_marker(root: Path) -> Path | None:
    for parent in root.parents:
        if (parent / MARKER_REL).is_file():
            return parent
    return None


def parent_obidian_vault(root: Path) -> Path | None:
    for parent in root.parents:
        if (parent / ".obsidian").is_dir():
            return parent
    return None


def precondition_snapshot(
    root: Path,
    *,
    ignored_paths: list[str],
    candidate_config: dict[str, Any],
) -> dict[str, Any]:
    files: list[dict[str, Any]] = []
    if root.exists():
        visible = collect_visible_files(root, ignored_paths)
        for relative, path in sorted(visible.items()):
            try:
                stat = path.stat()
                record: dict[str, Any] = {
                    "path": relative,
                    "size": stat.st_size,
                    "mtime_ns": stat.st_mtime_ns,
                }
                if path.suffix.casefold() == ".md":
                    record["sha256"] = sha256_bytes(path.read_bytes())
                files.append(record)
            except OSError as error:
                raise ToolError(
                    "IO_ERROR",
                    "Could not fingerprint the Vault.",
                    details={"path": str(path), "reason": str(error)},
                ) from error
        for special in (root / MARKER_REL, root / ".gitignore"):
            if special.is_file():
                relative = special.relative_to(root).as_posix()
                if not any(item["path"] == relative for item in files):
                    files.append(
                        {
                            "path": relative,
                            "sha256": sha256_bytes(special.read_bytes()),
                        }
                    )
    locator = locator_path()
    locator_hash = sha256_bytes(locator.read_bytes()) if locator.is_file() else None
    return {
        "root_exists": root.exists(),
        "files": sorted(files, key=lambda item: item["path"]),
        "locator_path": str(locator),
        "locator_hash": locator_hash,
        "git": git_state(root),
        "candidate_config": candidate_config,
    }


def external_mode_valid(root: Path, config: dict[str, Any]) -> bool:
    return git_baseline_valid(root, config)


def effective_git_config(
    *,
    mode: str,
    current: dict[str, Any] | None,
    requested_mode: str | None,
    requested_auto: str | None,
    root: Path,
) -> dict[str, Any]:
    if mode == "new":
        git_mode = requested_mode or "managed"
        auto_commit = True if requested_auto is None else requested_auto == "on"
        if git_mode == "external":
            raise ToolError("INVALID_ARGUMENT", "New Vaults cannot use external Git mode.")
    elif mode == "register":
        if requested_mode not in {None, "off"} or requested_auto == "on":
            raise ToolError(
                "INVALID_ARGUMENT",
                "First-time existing registration is fixed to git off and auto-commit off.",
            )
        git_mode = "off"
        auto_commit = False
    else:
        assert current is not None
        git_mode = requested_mode or current["git"]["mode"]
        auto_commit = (
            current["git"]["auto_commit"]
            if requested_auto is None
            else requested_auto == "on"
        )
        if requested_mode == "managed" and current["git"]["mode"] != "managed":
            raise ToolError(
                "INVALID_ARGUMENT",
                "managed mode can only be retained by a Vault created in managed mode.",
            )
    if git_mode == "off":
        if requested_auto == "on":
            raise ToolError("INVALID_ARGUMENT", "auto-commit on conflicts with git off.")
        auto_commit = False
    candidate = {"mode": git_mode, "auto_commit": auto_commit}
    if git_mode == "external":
        trial = {
            "schema_version": SCHEMA_VERSION,
            "ignored_paths": (current or {}).get("ignored_paths", []),
            "git": candidate,
        }
        if not external_mode_valid(root, trial):
            raise ToolError(
                "INVALID_GIT_MODE",
                "external mode requires a root-level repository with a tracked baseline.",
            )
    return candidate


def plan_init(arguments: argparse.Namespace) -> dict[str, Any]:
    root = canonical_root(arguments.root)
    exists = root.exists()
    if exists and not root.is_dir():
        raise ToolError("INVALID_ROOT", "The Vault root must be a directory.")
    marker = read_marker(root) if exists else None
    if marker is not None:
        mode = "reconfigure"
    elif exists and directory_empty(root):
        if arguments.existing:
            raise ToolError("INVALID_ARGUMENT", "--existing cannot target an empty directory.")
        mode = "new"
    elif not exists:
        if arguments.existing:
            raise ToolError("INVALID_ARGUMENT", "--existing requires a non-empty directory.")
        mode = "new"
    else:
        if not arguments.existing:
            raise ToolError(
                "EXISTING_REQUIRED",
                "A non-empty uninitialized directory requires --existing.",
            )
        mode = "register"
    if mode == "register" and (is_filesystem_root(root) or root == Path.home().resolve()):
        raise ToolError("UNSAFE_ROOT", "Filesystem roots and the user home cannot be registered.")
    parent_marker = ancestor_marker(root)
    if parent_marker:
        raise ToolError(
            "NESTED_VAULT",
            "The target is inside another LearnEverything Vault.",
            details={"parent_vault": str(parent_marker)},
        )
    descendants = marker_descendants(root)
    if descendants:
        raise ToolError(
            "NESTED_VAULT",
            "The target contains another LearnEverything Vault.",
            details={"nested_vaults": descendants},
        )
    current = marker
    if arguments.clear_ignored_paths and arguments.ignored_path:
        raise ToolError(
            "INVALID_ARGUMENT", "--clear-ignored-paths conflicts with --ignored-path."
        )
    if arguments.clear_ignored_paths:
        ignored_paths: list[str] = []
    elif arguments.ignored_path:
        ignored_paths = [validate_ignored_path(item, root) for item in arguments.ignored_path]
        if len(ignored_paths) != len(set(ignored_paths)):
            raise ToolError("INVALID_ARGUMENT", "--ignored-path values must be unique.")
    elif current:
        ignored_paths = list(current["ignored_paths"])
    else:
        ignored_paths = []
    git = effective_git_config(
        mode=mode,
        current=current,
        requested_mode=arguments.git_mode,
        requested_auto=arguments.auto_commit,
        root=root,
    )
    candidate = {
        "schema_version": SCHEMA_VERSION,
        "ignored_paths": ignored_paths,
        "git": git,
    }
    parent_git = git_state(root.parent if not exists else root)
    if mode == "new" and parent_git["top_level"] and git["mode"] != "off":
        raise ToolError(
            "PARENT_GIT_REPOSITORY",
            "A new Vault inside a parent Git repository requires --git off.",
            details={"git_top_level": parent_git["top_level"]},
        )
    if (
        mode == "reconfigure"
        and git["mode"] != "off"
        and parent_git["top_level"]
        and parent_git["top_level"] != str(root)
    ):
        raise ToolError(
            "PARENT_GIT_REPOSITORY",
            "A Vault inside a parent Git repository must use --git off.",
            details={"git_top_level": parent_git["top_level"]},
        )
    conflicts: list[dict[str, Any]] = []
    actions: list[dict[str, Any]] = []
    virtual_files: dict[str, str] = {}
    for managed_dir in (*MANAGED_DIRS, ".learn-everything"):
        target = root / managed_dir
        if target.is_symlink():
            conflicts.append({"path": managed_dir, "reason": "reserved path cannot be a symlink"})
        elif target.exists() and not target.is_dir():
            conflicts.append({"path": managed_dir, "reason": "reserved path is not a directory"})
        elif not target.exists():
            actions.append({"action": "create_directory", "path": managed_dir})
    home = root / "Home.md"
    if home.exists():
        if not home.is_file():
            conflicts.append({"path": "Home.md", "reason": "reserved path is not a file"})
        elif mode == "register":
            try:
                metadata, _, _ = parse_frontmatter(read_text(home))
                if metadata.get("id") != "index.home" or metadata.get("kind") != "index":
                    conflicts.append(
                        {"path": "Home.md", "reason": "existing Home.md is not a LearnEverything index"}
                    )
            except ValueError:
                conflicts.append(
                    {"path": "Home.md", "reason": "existing Home.md has incompatible frontmatter"}
                )
    else:
        virtual_files["Home.md"] = home_template()
        actions.append({"action": "create_file", "path": "Home.md"})
    marker_path = root / MARKER_REL
    marker_directory = root / ".learn-everything"
    if mode == "register" and marker_directory.is_dir():
        try:
            existing_marker_files = [
                path.relative_to(root).as_posix()
                for path in marker_directory.rglob("*")
                if path.is_file()
            ]
        except OSError as error:
            raise ToolError(
                "IO_ERROR",
                "Could not inspect the reserved marker directory.",
                details={"reason": str(error)},
            ) from error
        if existing_marker_files:
            conflicts.append(
                {
                    "path": ".learn-everything",
                    "reason": "reserved marker directory is already non-empty",
                }
            )
    if marker_path.exists() and marker is None:
        conflicts.append({"path": MARKER_REL, "reason": "marker is invalid"})
    elif marker is None:
        actions.append({"action": "create_file", "path": MARKER_REL})
    elif marker != candidate:
        actions.append({"action": "update_file", "path": MARKER_REL})
    if git["mode"] == "managed":
        gitignore = root / ".gitignore"
        if not gitignore.exists():
            virtual_files[".gitignore"] = gitignore_template()
            actions.append({"action": "create_file", "path": ".gitignore"})
        elif not gitignore.is_file():
            conflicts.append({"path": ".gitignore", "reason": "reserved path is not a file"})
    if conflicts:
        raise ToolError("PATH_CONFLICT", "Reserved Vault paths conflict.", details={"conflicts": conflicts})
    virtual_files[MARKER_REL] = config_text(candidate)
    predicted = lint_vault(
        root,
        config_override=candidate,
        virtual_files=virtual_files,
        check_git=False,
    )
    if predicted["summary"]["errors"]:
        raise ToolError(
            "LINT_FAILED",
            "The planned Vault would fail structural lint.",
            details={"diagnostics": predicted["diagnostics"]},
        )
    locator_before: str | None = None
    try:
        locator = read_locator(required=False)
        locator_before = locator["vault_root"] if locator else None
    except ToolError as error:
        if error.code != "INVALID_LOCATOR":
            raise
    locator_status = "unchanged_active" if locator_before == str(root) else "planned_update"
    if locator_status == "planned_update":
        actions.append({"action": "update_locator", "path": str(locator_path())})
    git_action: dict[str, Any] = {"action": "none", "mode": git["mode"]}
    if git["mode"] == "managed" and not git_baseline_valid(root, candidate):
        git_action = {"action": "create_or_repair_baseline", "mode": "managed"}
        actions.insert(max(len(actions) - (locator_status == "planned_update"), 0), git_action)
    warnings = [item for item in predicted["diagnostics"] if item["severity"] == "warning"]
    obsidian_parent = parent_obidian_vault(root)
    if obsidian_parent and obsidian_parent != root:
        warnings.append(
            diagnostic(
                "NESTED_OBSIDIAN_VAULT",
                "warning",
                "Obsidian recommends using the parent Vault or a separate directory.",
                path=str(obsidian_parent),
            )
        )
    snapshot = precondition_snapshot(root, ignored_paths=ignored_paths, candidate_config=candidate)
    core = {
        "schema_version": SCHEMA_VERSION,
        "operation": "vault.init",
        "mode": mode,
        "root": str(root),
        "config": candidate,
        "locator": {
            "before": locator_before,
            "after": str(root),
            "status": locator_status,
        },
        "actions": actions,
        "git": git_action,
        "warnings": warnings,
        "conflicts": [],
    }
    plan_hash = sha256_json({"plan": core, "preconditions": snapshot})
    core["plan_hash"] = plan_hash
    core["no_op"] = not actions
    core["_virtual_files"] = virtual_files
    return core


def snapshot_preimages(root: Path, relatives: Iterable[str]) -> dict[str, bytes | None]:
    output: dict[str, bytes | None] = {}
    for relative in relatives:
        path = root / relative
        if path.is_file():
            output[relative] = path.read_bytes()
        else:
            output[relative] = None
    return output


def restore_preimages(root: Path, preimages: dict[str, bytes | None]) -> list[str]:
    failed: list[str] = []
    for relative, content in preimages.items():
        path = root / relative
        try:
            if content is None:
                if path.exists() and path.is_file():
                    path.unlink()
            else:
                path.parent.mkdir(parents=True, exist_ok=True)
                descriptor, temporary = tempfile.mkstemp(
                    prefix=f".{path.name}.", suffix=".restore", dir=str(path.parent)
                )
                temporary_path = Path(temporary)
                try:
                    with os.fdopen(descriptor, "wb") as handle:
                        handle.write(content)
                        handle.flush()
                        os.fsync(handle.fileno())
                    os.replace(temporary_path, path)
                finally:
                    if temporary_path.exists():
                        temporary_path.unlink()
        except OSError:
            failed.append(relative)
    return failed


def write_scaffold(root: Path, plan: dict[str, Any]) -> tuple[list[str], list[str]]:
    created_directories: list[str] = []
    written_files: list[str] = []
    for relative in (*MANAGED_DIRS, ".learn-everything"):
        path = root / relative
        if not path.exists():
            path.mkdir(parents=True)
            created_directories.append(relative)
    virtual = plan["_virtual_files"]
    home = root / "Home.md"
    if "Home.md" in virtual and not home.exists():
        atomic_write(home, virtual["Home.md"])
        written_files.append("Home.md")
    marker = root / MARKER_REL
    desired_marker = config_text(plan["config"])
    if not marker.exists() or marker.read_text(encoding="utf-8") != desired_marker:
        atomic_write(marker, desired_marker)
        written_files.append(MARKER_REL)
    if plan["config"]["git"]["mode"] == "managed":
        gitignore = root / ".gitignore"
        if not gitignore.exists():
            atomic_write(gitignore, gitignore_template())
            written_files.append(".gitignore")
    return created_directories, written_files


def remove_empty_directories(root: Path, relatives: Iterable[str]) -> None:
    for relative in sorted(relatives, key=lambda item: len(PurePosixPath(item).parts), reverse=True):
        path = root / relative
        try:
            path.rmdir()
        except OSError:
            pass


def establish_managed_baseline(root: Path, config: dict[str, Any]) -> dict[str, Any]:
    if shutil.which("git") is None:
        return {
            "status": "degraded",
            "baseline_created": False,
            "index_restored": True,
            "warning": "Git is unavailable.",
        }
    if git_baseline_valid(root, config):
        return {
            "status": "unchanged",
            "baseline_created": False,
            "index_restored": True,
        }
    initial_state = git_state(root)
    if initial_state["top_level"] == str(root) and initial_state["staged"]:
        return {
            "status": "degraded",
            "baseline_created": False,
            "index_restored": True,
            "warning": "Git already has staged changes; baseline creation was skipped.",
        }
    git_directory = root / ".git"
    created_repository = not git_directory.exists()
    before_cached = b""
    if not created_repository:
        cached = subprocess.run(
            ["git", "-C", str(root), "diff", "--cached", "--binary"],
            capture_output=True,
            check=False,
            timeout=20,
        )
        before_cached = cached.stdout
    initialized = git_run(root, "init", "-q")
    if initialized.returncode != 0:
        return {
            "status": "degraded",
            "baseline_created": False,
            "index_restored": True,
            "warning": initialized.stderr.strip() or "git init failed",
        }
    add = git_run(root, "add", "--", *baseline_paths(config))
    commit = git_run(
        root,
        "-c",
        "user.name=LearnEverything",
        "-c",
        "user.email=learn-everything@local",
        "commit",
        "-q",
        "-m",
        "vault: initialize",
    )
    if add.returncode == 0 and commit.returncode == 0:
        return {
            "status": "created",
            "baseline_created": True,
            "index_restored": True,
        }
    restored = True
    try:
        if created_repository:
            if git_directory.exists():
                shutil.rmtree(git_directory)
        else:
            git_run(root, "reset", "--mixed", "-q", check=True)
            if before_cached:
                applied = subprocess.run(
                    ["git", "-C", str(root), "apply", "--cached", "--binary", "-"],
                    input=before_cached,
                    capture_output=True,
                    check=False,
                    timeout=20,
                )
                restored = applied.returncode == 0
    except (OSError, ToolError):
        restored = False
    if not restored:
        raise ToolError(
            "GIT_ROLLBACK_FAILED",
            "Git baseline failed and the original index could not be restored.",
            details={"root": str(root)},
        )
    return {
        "status": "degraded",
        "baseline_created": False,
        "index_restored": True,
        "warning": commit.stderr.strip() or add.stderr.strip() or "git baseline failed",
    }


def apply_new_plan(plan: dict[str, Any]) -> dict[str, Any]:
    root = Path(plan["root"])
    parent = root.parent
    temporary = Path(tempfile.mkdtemp(prefix=f".{root.name}.learn-everything-", dir=str(parent)))
    git_result: dict[str, Any] = {
        "status": "disabled" if plan["config"]["git"]["mode"] == "off" else "pending",
        "baseline_created": False,
        "index_restored": True,
    }
    try:
        write_scaffold(temporary, plan)
        first_lint = lint_vault(
            temporary, config_override=plan["config"], check_git=False
        )
        if first_lint["summary"]["errors"]:
            raise ToolError(
                "LINT_FAILED",
                "The new Vault failed structural lint.",
                details={"diagnostics": first_lint["diagnostics"]},
                exit_code=1,
            )
        if plan["config"]["git"]["mode"] == "managed":
            git_result = establish_managed_baseline(temporary, plan["config"])
        final_lint = lint_vault(temporary, config_override=plan["config"])
        if final_lint["summary"]["errors"]:
            raise ToolError(
                "LINT_FAILED",
                "The new Vault failed final structural lint.",
                details={"diagnostics": final_lint["diagnostics"]},
                exit_code=1,
            )
        if root.exists():
            if not root.is_dir() or not directory_empty(root):
                raise ToolError("PLAN_MISMATCH", "The target is no longer an empty directory.")
            root.rmdir()
        os.replace(temporary, root)
        return {"final_lint": final_lint, "git": git_result}
    finally:
        if temporary.exists():
            shutil.rmtree(temporary, ignore_errors=True)


def apply_existing_plan(plan: dict[str, Any]) -> dict[str, Any]:
    root = Path(plan["root"])
    target_files = {MARKER_REL, "Home.md", ".gitignore"}
    preimages = snapshot_preimages(root, target_files)
    created_directories: list[str] = []
    try:
        created_directories, _ = write_scaffold(root, plan)
        first_lint = lint_vault(root, config_override=plan["config"], check_git=False)
        if first_lint["summary"]["errors"]:
            raise ToolError(
                "LINT_FAILED",
                "The initialized Vault failed structural lint.",
                details={"diagnostics": first_lint["diagnostics"]},
                exit_code=1,
            )
        git_result: dict[str, Any] = {
            "status": "disabled" if plan["config"]["git"]["mode"] == "off" else "unchanged",
            "baseline_created": False,
            "index_restored": True,
        }
        if plan["config"]["git"]["mode"] == "managed" and not git_baseline_valid(root, plan["config"]):
            git_result = establish_managed_baseline(root, plan["config"])
        final_lint = lint_vault(root, config_override=plan["config"])
        if final_lint["summary"]["errors"]:
            raise ToolError(
                "LINT_FAILED",
                "The initialized Vault failed final structural lint.",
                details={"diagnostics": final_lint["diagnostics"]},
                exit_code=1,
            )
        return {"final_lint": final_lint, "git": git_result}
    except ToolError as error:
        failed = restore_preimages(root, preimages)
        remove_empty_directories(root, created_directories)
        if failed:
            raise ToolError(
                "ROLLBACK_FAILED",
                "Initialization failed and some files could not be restored.",
                details={"affected_paths": failed, "original_error": error.code},
            ) from error
        raise


def update_locator(root: Path) -> str:
    current: str | None = None
    try:
        locator = read_locator(required=False)
        current = locator["vault_root"] if locator else None
    except ToolError as error:
        if error.code != "INVALID_LOCATOR":
            raise
    if current == str(root):
        return "unchanged_active"
    atomic_write(locator_path(), locator_text(root))
    return "updated"


def execute_init(arguments: argparse.Namespace, plan: dict[str, Any]) -> dict[str, Any]:
    if arguments.expect_plan != plan["plan_hash"]:
        raise ToolError(
            "PLAN_MISMATCH",
            "The approved plan no longer matches current Vault state.",
            details={"expected": arguments.expect_plan, "actual": plan["plan_hash"]},
        )
    if plan["no_op"]:
        return {
            **{key: value for key, value in plan.items() if not key.startswith("_")},
            "dry_run": False,
            "changed": False,
            "degraded": False,
            "vault_valid": True,
            "locator_updated": False,
        }
    if plan["mode"] == "new":
        applied = apply_new_plan(plan)
    else:
        applied = apply_existing_plan(plan)
    locator_status = update_locator(Path(plan["root"]))
    git_result = applied["git"]
    degraded = git_result.get("status") == "degraded"
    result = {key: value for key, value in plan.items() if not key.startswith("_")}
    result.update(
        {
            "dry_run": False,
            "changed": True,
            "degraded": degraded,
            "vault_valid": True,
            "locator": {**plan["locator"], "status": locator_status},
            "locator_updated": locator_status == "updated",
            "git": git_result,
            "final_lint": applied["final_lint"]["summary"],
        }
    )
    return result


def root_command() -> dict[str, Any]:
    locator = read_locator(required=True)
    assert locator is not None
    root = Path(locator["vault_root"])
    if not root.is_dir():
        raise ToolError(
            "VAULT_UNAVAILABLE",
            "The configured Vault directory is unavailable.",
            details={"root": str(root)},
        )
    config = read_marker(root)
    if config is None:
        raise ToolError(
            "VAULT_INVALID",
            "The configured directory is missing its Vault marker.",
            details={"root": str(root)},
        )
    return {
        "schema_version": SCHEMA_VERSION,
        "operation": "vault.root",
        "root": str(root),
        "config": config,
        "locator": {"path": str(locator_path()), "status": "active"},
    }


def render_text(payload: dict[str, Any]) -> str:
    if payload.get("ok") is False:
        error = payload["error"]
        return f"error [{error['code']}]: {error['message']}\n"
    operation = payload.get("operation")
    if operation == "vault.root":
        return f"{payload['root']}\n"
    if operation == "vault.lint":
        summary = payload["summary"]
        lines = [
            f"{summary['errors']} error(s), {summary['warnings']} warning(s), {summary['files']} file(s)"
        ]
        for item in payload["diagnostics"]:
            location = item.get("path", "<vault>")
            if item.get("line"):
                location += f":{item['line']}"
            lines.append(f"{item['severity']} {item['code']} {location}: {item['message']}")
        return "\n".join(lines) + "\n"
    if operation == "vault.init":
        lines = [
            f"mode: {payload['mode']}",
            f"root: {payload['root']}",
            f"plan: {payload['plan_hash']}",
            f"no-op: {str(payload.get('no_op', False)).lower()}",
        ]
        for action in payload.get("actions", []):
            lines.append(f"- {action['action']}: {action.get('path', action.get('mode', ''))}")
        return "\n".join(lines) + "\n"
    return json_text(payload)


def emit(payload: dict[str, Any], output_format: str) -> None:
    if output_format == "json":
        sys.stdout.write(json_text(payload))
    else:
        sys.stdout.write(render_text(payload))


def build_parser() -> Parser:
    parser = Parser(prog="learn-everything")
    top = parser.add_subparsers(dest="scope", required=True, parser_class=Parser)
    vault = top.add_parser("vault")
    commands = vault.add_subparsers(dest="command", required=True, parser_class=Parser)
    init = commands.add_parser("init")
    init.add_argument("--root", required=True)
    init.add_argument("--existing", action="store_true")
    init.add_argument("--git", dest="git_mode", choices=sorted(GIT_MODES))
    init.add_argument("--auto-commit", choices=("on", "off"))
    init.add_argument("--ignored-path", action="append", default=[])
    init.add_argument("--clear-ignored-paths", action="store_true")
    execution = init.add_mutually_exclusive_group(required=True)
    execution.add_argument("--dry-run", action="store_true")
    execution.add_argument("--expect-plan")
    init.add_argument("--format", choices=("text", "json"), required=True)
    root = commands.add_parser("root")
    root.add_argument("--format", choices=("text", "json"), required=True)
    lint = commands.add_parser("lint")
    lint.add_argument("--root")
    lint.add_argument("--base")
    lint.add_argument("--format", choices=("text", "json"), required=True)
    return parser


def requested_format(arguments: list[str]) -> str:
    try:
        index = arguments.index("--format")
        value = arguments[index + 1]
        return value if value in {"text", "json"} else "json"
    except (ValueError, IndexError):
        return "json"


def main(argv: list[str] | None = None) -> int:
    raw = list(sys.argv[1:] if argv is None else argv)
    output_format = requested_format(raw)
    try:
        arguments = build_parser().parse_args(raw)
        output_format = arguments.format
        if arguments.command == "root":
            payload = root_command()
            emit(payload, output_format)
            return 0
        if arguments.command == "lint":
            if arguments.root:
                root = canonical_root(arguments.root)
            else:
                locator = read_locator(required=True)
                assert locator is not None
                root = Path(locator["vault_root"])
            if not root.is_dir():
                raise ToolError("VAULT_UNAVAILABLE", "The Vault root is unavailable.")
            payload = lint_vault(root, base=arguments.base)
            emit(payload, output_format)
            return 1 if payload["summary"]["errors"] else 0
        try:
            plan = plan_init(arguments)
        except ToolError as error:
            state_sensitive = {
                "EXISTING_REQUIRED",
                "INVALID_CONFIG",
                "INVALID_GIT_MODE",
                "INVALID_MARKER",
                "LINT_FAILED",
                "NESTED_VAULT",
                "PARENT_GIT_REPOSITORY",
                "PATH_CONFLICT",
            }
            if arguments.expect_plan and error.code in state_sensitive:
                raise ToolError(
                    "PLAN_MISMATCH",
                    "The approved plan cannot be reproduced from current Vault state.",
                    details={"current_error": error.code},
                ) from error
            raise
        if arguments.dry_run:
            payload = {key: value for key, value in plan.items() if not key.startswith("_")}
            payload.update({"dry_run": True, "changed": False, "degraded": False})
        else:
            payload = execute_init(arguments, plan)
        emit(payload, output_format)
        return 0
    except ToolError as error:
        payload = {
            "schema_version": SCHEMA_VERSION,
            "ok": False,
            "error": {
                "code": error.code,
                "message": error.message,
                "details": error.details,
            },
        }
        emit(payload, output_format)
        return error.exit_code
    except (OSError, UnicodeError, subprocess.SubprocessError) as error:
        payload = {
            "schema_version": SCHEMA_VERSION,
            "ok": False,
            "error": {
                "code": "IO_ERROR",
                "message": "Unexpected local I/O failure.",
                "details": {"reason": str(error)},
            },
        }
        emit(payload, output_format)
        return 2
