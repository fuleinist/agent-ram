"""Git integration for AgentRAM."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Optional
from dataclasses import dataclass


@dataclass
class GitContext:
    """Git context for a workspace."""
    commit_sha: str
    branch: str
    diff: str
    changed_files: list[str]
    repo_path: Path


class GitOps:
    """Git operations for AgentRAM."""

    def __init__(self, repo_path: Path | str | None = None):
        self.repo_path = Path(repo_path) if repo_path else Path.cwd()

    def is_repo(self) -> bool:
        """Check if the path is a git repository."""
        try:
            import git
            git.Repo(self.repo_path)
            return True
        except Exception:
            return False

    def get_context(self) -> Optional[GitContext]:
        """Get current git context (commit, branch, diff)."""
        if not self.is_repo():
            return None

        try:
            import git

            repo = git.Repo(self.repo_path)
            head = repo.head.commit
            branch = repo.active_branch.name
            diff = head.diff("HEAD~1") if repo.head.commit.parents else ""

            changed_files = [item.a_path for item in repo.index.diff(None)]
            if not changed_files:
                changed_files = [item.a_path for item in repo.index.iter_items()]

            return GitContext(
                commit_sha=head.hexsha[:8],
                branch=branch,
                diff=str(diff),
                changed_files=changed_files,
                repo_path=self.repo_path,
            )
        except Exception:
            return None

    def get_file_diff(self, file_path: str | Path) -> Optional[str]:
        """Get diff for a specific file."""
        if not self.is_repo():
            return None

        try:
            import git

            repo = git.Repo(self.repo_path)
            file_path = str(file_path)

            if file_path in repo.untracked_files:
                with open(file_path, "r", encoding="utf-8", errors="replace") as f:
                    return f"<new_file>\n{f.read()}"

            diff = repo.git.diff(file_path)
            return diff if diff else None
        except Exception:
            return None

    def get_recent_commits(self, count: int = 10) -> list[dict[str, str]]:
        """Get recent commit history."""
        if not self.is_repo():
            return []

        try:
            import git

            repo = git.Repo(self.repo_path)
            commits = list(repo.iter_commits(max_count=count))

            return [
                {
                    "sha": c.hexsha[:8],
                    "message": c.message.strip(),
                    "author": str(c.author),
                    "date": c.committed_datetime.isoformat(),
                }
                for c in commits
            ]
        except Exception:
            return []

    def get_workspace(self) -> str:
        """Get workspace identifier (repo root or cwd)."""
        if self.is_repo():
            try:
                import git
                repo = git.Repo(self.repo_path)
                return str(repo.working_dir)
            except Exception:
                pass
        return str(self.repo_path)
