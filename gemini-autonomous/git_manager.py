import subprocess
from pathlib import Path
from typing import Optional, Tuple

class GitManager:
    def __init__(self, project_dir: Path):
        self.project_dir = project_dir
        self.ensure_repo()

    def _run_git(self, args: list) -> Tuple[int, str]:
        """Run a git command and return (exit_code, output)."""
        try:
            result = subprocess.run(
                ["git"] + args,
                cwd=self.project_dir,
                capture_output=True,
                text=True
            )
            return result.returncode, result.stdout.strip()
        except Exception as e:
            return -1, str(e)

    def ensure_repo(self):
        """Initialize git repo if it doesn't exist."""
        if not (self.project_dir / ".git").exists():
            print(f"Initializing Git repository in {self.project_dir}...")
            self._run_git(["init"])
            # Initial commit to start history
            self._run_git(["add", "."])
            self._run_git(["commit", "-m", "[GAE] Initial commit"])

    def get_last_commit_msg(self) -> Optional[str]:
        """Get the last commit message."""
        code, output = self._run_git(["log", "-1", "--pretty=%B"])
        if code == 0:
            return output.strip()
        return None

    def is_clean(self) -> bool:
        """Check if working directory is clean."""
        code, output = self._run_git(["status", "--porcelain"])
        return code == 0 and not output

    def commit(self, message: str) -> bool:
        """Stage all changes and commit."""
        self._run_git(["add", "."])
        code, output = self._run_git(["commit", "-m", f"[GAE] {message}"])
        if code == 0:
            print(f"\n[Git] Committed: {message}")
            return True
        else:
            if "nothing to commit" in output:
                return True # No changes is fine
            print(f"\n[Git] Commit failed: {output}")
            return False

    def rollback(self) -> bool:
        """Hard reset to previous commit."""
        print("\n[Git] Rolling back to previous commit...")
        code, output = self._run_git(["reset", "--hard", "HEAD~1"])
        if code == 0:
            print("[Git] Rollback successful.")
            return True
        else:
            print(f"[Git] Rollback failed: {output}")
            return False
