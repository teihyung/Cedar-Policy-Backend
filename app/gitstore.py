"""
Git-backed storage for Cedar policy file content.

Layout: {GIT_REPO_PATH}/{tenant_id}/{filename}
One commit per write/delete operation -> `git log` is a readable audit trail.

Postgres (PolicyFile) is the query index: tenant_id, filename, current_commit_hash.
Git is the source of truth for content: given a commit_hash you can always
retrieve exactly what was uploaded, even after later edits.
"""

import os
import re
import subprocess
from pathlib import Path

GIT_REPO_PATH = Path(os.environ.get("GIT_REPO_PATH", "./git_repo")).resolve()

# Only allow simple, safe filenames: letters, digits, dot, dash, underscore.
# Blocks path traversal (../), absolute paths, null bytes, slashes, etc.
_SAFE_FILENAME_RE = re.compile(r"^[A-Za-z0-9._-]+$")


class GitStoreError(Exception):
    """Raised on any git storage failure (bad filename, git command failure, missing file)."""


def _run_git(*args: str, cwd: Path) -> subprocess.CompletedProcess:
    result = subprocess.run(
        ["git", *args],
        cwd=cwd,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise GitStoreError(f"git {' '.join(args)} failed: {result.stderr.strip()}")
    return result


def _validate_filename(filename: str) -> None:
    if not filename or not _SAFE_FILENAME_RE.match(filename):
        raise GitStoreError(
            "Invalid filename. Only letters, digits, '.', '-', and '_' are allowed "
            "(no path separators or '..')."
        )


def _tenant_dir(tenant_id: str) -> Path:
    # tenant_id comes from Postgres (a UUID we generated), never from raw user input,
    # so it's inherently safe as a path component -- but resolve() + is_relative_to()
    # gives us defense in depth against any future misuse of this function.
    d = (GIT_REPO_PATH / tenant_id).resolve()
    if not d.is_relative_to(GIT_REPO_PATH):
        raise GitStoreError("Invalid tenant path")
    return d


def init_repo() -> None:
    """Idempotent: create + git-init the repo directory if it doesn't exist yet."""
    GIT_REPO_PATH.mkdir(parents=True, exist_ok=True)
    if not (GIT_REPO_PATH / ".git").exists():
        _run_git("init", cwd=GIT_REPO_PATH)
        _run_git("config", "user.email", "smartverify@local", cwd=GIT_REPO_PATH)
        _run_git("config", "user.name", "SmartVerify", cwd=GIT_REPO_PATH)


def write_policy_file(tenant_id: str, filename: str, content: str, actor_username: str) -> str:
    """
    Write (create or overwrite) a policy file's content and commit it.
    Returns the new commit hash.
    """
    _validate_filename(filename)
    tenant_dir = _tenant_dir(tenant_id)
    tenant_dir.mkdir(parents=True, exist_ok=True)

    file_path = tenant_dir / filename
    file_path.write_text(content, encoding="utf-8")

    rel_path = f"{tenant_id}/{filename}"
    _run_git("add", rel_path, cwd=GIT_REPO_PATH)
    _run_git(
        "commit", "-m", f"upload: {rel_path} by {actor_username}",
        "--allow-empty-message", "--author", f"{actor_username} <{actor_username}@local>",
        cwd=GIT_REPO_PATH,
    )
    commit_hash = _run_git("rev-parse", "HEAD", cwd=GIT_REPO_PATH).stdout.strip()
    return commit_hash


def read_policy_file(tenant_id: str, filename: str) -> str:
    """Read current content of a policy file from the working tree."""
    _validate_filename(filename)
    file_path = _tenant_dir(tenant_id) / filename
    if not file_path.is_file():
        raise GitStoreError(f"File not found in git store: {tenant_id}/{filename}")
    return file_path.read_text(encoding="utf-8")


def delete_policy_file(tenant_id: str, filename: str, actor_username: str) -> None:
    """Hard delete: git rm the file and commit the removal."""
    _validate_filename(filename)
    rel_path = f"{tenant_id}/{filename}"
    file_path = GIT_REPO_PATH / rel_path
    if not file_path.is_file():
        raise GitStoreError(f"File not found in git store: {rel_path}")

    _run_git("rm", rel_path, cwd=GIT_REPO_PATH)
    _run_git(
        "commit", "-m", f"delete: {rel_path} by {actor_username}",
        "--author", f"{actor_username} <{actor_username}@local>",
        cwd=GIT_REPO_PATH,
    )