"""Level verification engine."""
import logging
import re
from typing import Any

from app.models.level import Level, VerificationRule, VerificationType

logger = logging.getLogger(__name__)


class VerificationEngine:
    """Verifies level completion by checking sandbox state."""

    def __init__(self, sandbox: Any):  # LocalSandbox or GameSandbox
        self.sandbox = sandbox

    async def check_level_complete(self, level: Level) -> bool:
        """Check if all verification rules pass."""
        for rule in level.verification:
            if not await self._check_rule(rule):
                return False
        return True

    async def get_progress(self, level: Level) -> dict:
        """Get detailed progress for each rule."""
        results = []
        for rule in level.verification:
            passed = await self._check_rule(rule)
            results.append({
                "type": rule.type.value,
                "passed": passed,
                "tool_name": rule.tool_name,
                "path": rule.path,
            })
        return {
            "rules": results,
            "completed": all(r["passed"] for r in results),
            "passed_count": sum(1 for r in results if r["passed"]),
            "total_count": len(results),
        }

    async def _check_rule(self, rule: VerificationRule) -> bool:
        """Check a single verification rule."""
        try:
            if rule.type == VerificationType.MESSAGE_EXISTS:
                return await self._check_message_exists()
            elif rule.type == VerificationType.TOOL_CALLED:
                return await self._check_tool_called(rule.tool_name, rule.min_count)
            elif rule.type == VerificationType.FILE_EXISTS:
                return await self._check_file_exists(rule.path)
            elif rule.type == VerificationType.FILE_CONTAINS:
                return await self._check_file_contains(rule.path, rule.pattern)
            elif rule.type == VerificationType.FILE_CHANGED:
                return await self._check_file_changed(rule.path)
            elif rule.type == VerificationType.COMMIT_EXISTS:
                return await self._check_commit_exists(rule.pattern)
            elif rule.type == VerificationType.COMMAND_OUTPUT:
                return await self._check_command_output(rule.command, rule.expected_output)
            elif rule.type == VerificationType.MIN_USER_MESSAGES:
                return await self._check_min_user_messages(rule.min_count)
            elif rule.type == VerificationType.GLOB_EXISTS:
                return await self._check_glob_exists(rule.pattern)
            elif rule.type == VerificationType.HOME_GLOB_EXISTS:
                return await self._check_home_glob_exists(rule.pattern)
            elif rule.type == VerificationType.TOOL_CALLED_WITH_PATH:
                return await self._check_tool_called_with_path(rule.tool_name, rule.pattern)
            return False
        except Exception as e:
            logger.error(f"Error checking rule {rule.type}: {e}")
            return False

    async def _check_message_exists(self) -> bool:
        """Check if any assistant message exists."""
        messages = await self.sandbox.read_messages_log()
        return any(m.get("type") == "assistant" for m in messages)

    async def _check_tool_called(self, tool_name: str | None, min_count: int | None = None) -> bool:
        """Check if Claude called a specific tool (optionally at least N times)."""
        if not tool_name:
            return False

        messages = await self.sandbox.read_messages_log()
        count = 0

        for msg in messages:
            if msg.get("type") != "assistant":
                continue

            content = msg.get("message", {}).get("content", [])
            for block in content:
                if block.get("type") == "tool_use" and block.get("name") == tool_name:
                    count += 1
                    # If no min_count required, return True on first match
                    if min_count is None:
                        return True

        # If min_count specified, check we have enough
        if min_count is not None:
            return count >= min_count

        return False

    async def _check_file_exists(self, path: str | None) -> bool:
        """Check if a file exists in sandbox."""
        if not path:
            return False

        # For LocalSandbox, check workspace_dir directly
        if hasattr(self.sandbox, 'workspace_dir') and self.sandbox.workspace_dir:
            from pathlib import Path
            file_path = self.sandbox.workspace_dir / path
            exists = file_path.exists()
            logger.debug(f"file_exists check: {file_path} -> {exists}")
            return exists

        # Fallback for Modal sandbox
        full_path = f"/workspace/{path}" if not path.startswith("/") else path
        stdout, stderr, returncode = await self.sandbox.exec_command(
            "test", "-f", full_path
        )
        return returncode == 0

    async def _check_file_contains(self, path: str | None, pattern: str | None) -> bool:
        """Check if file contains pattern."""
        if not path or not pattern:
            return False

        # For LocalSandbox, read file directly
        if hasattr(self.sandbox, 'workspace_dir') and self.sandbox.workspace_dir:
            from pathlib import Path
            file_path = self.sandbox.workspace_dir / path
            if not file_path.exists():
                logger.debug(f"file_contains check: {file_path} does not exist")
                return False
            content = file_path.read_text()
            matches = bool(re.search(pattern, content))
            logger.debug(f"file_contains check: {file_path} pattern={pattern} -> {matches}")
            return matches

        # Fallback for Modal sandbox
        full_path = f"/workspace/{path}" if not path.startswith("/") else path
        stdout, stderr, returncode = await self.sandbox.exec_command("cat", full_path)
        if returncode != 0:
            return False
        return bool(re.search(pattern, stdout))

    async def _check_file_changed(self, path: str | None) -> bool:
        """Check if file was modified (via Edit tool in messages)."""
        if not path:
            return False

        messages = await self.sandbox.read_messages_log()

        for msg in messages:
            if msg.get("type") != "assistant":
                continue

            content = msg.get("message", {}).get("content", [])
            for block in content:
                if block.get("type") == "tool_use" and block.get("name") == "Edit":
                    tool_input = block.get("input", {})
                    if path in tool_input.get("file_path", ""):
                        return True

        return False

    async def _check_commit_exists(self, pattern: str | None) -> bool:
        """Check if a git commit exists (optionally matching message pattern)."""
        if not self.sandbox.workspace_dir:
            return False

        stdout, stderr, returncode = await self.sandbox.exec_command(
            "git", "log", "--oneline", "-n", "10"
        )
        if returncode != 0:
            return False

        if pattern:
            return bool(re.search(pattern, stdout, re.IGNORECASE))
        return bool(stdout.strip())  # Any commit exists

    async def _check_command_output(self, command: str | None, expected: str | None) -> bool:
        """Check if command output matches expected pattern."""
        if not command:
            return False

        import shlex
        args = shlex.split(command)

        stdout, stderr, returncode = await self.sandbox.exec_command(*args)

        if expected:
            return bool(re.search(expected, stdout + stderr))
        return returncode == 0  # Just check success

    async def _check_min_user_messages(self, min_count: int | None) -> bool:
        """Check if user has sent at least N messages."""
        if not min_count:
            return True

        messages = await self.sandbox.read_messages_log()
        user_count = sum(1 for m in messages if m.get("type") == "human")
        return user_count >= min_count

    async def _check_glob_exists(self, pattern: str | None) -> bool:
        """Check if any file matches the glob pattern."""
        if not pattern:
            return False

        # For LocalSandbox, use glob directly
        if hasattr(self.sandbox, 'workspace_dir') and self.sandbox.workspace_dir:
            import glob
            full_pattern = str(self.sandbox.workspace_dir / pattern)
            matches = glob.glob(full_pattern, recursive=True)
            logger.debug(f"glob_exists check: {full_pattern} -> {len(matches)} matches")
            return len(matches) > 0

        # Fallback for Modal sandbox - use find command
        stdout, stderr, returncode = await self.sandbox.exec_command(
            "find", "/workspace", "-path", f"/workspace/{pattern}", "-type", "f"
        )
        return bool(stdout.strip())

    async def _check_home_glob_exists(self, pattern: str | None) -> bool:
        """Check if any file matches glob pattern in ~/.claude/ directory."""
        if not pattern:
            return False

        import glob
        from pathlib import Path

        home_dir = Path.home()
        full_pattern = str(home_dir / ".claude" / pattern)
        matches = glob.glob(full_pattern, recursive=True)
        logger.debug(f"home_glob_exists check: {full_pattern} -> {len(matches)} matches")
        return len(matches) > 0

    async def _check_tool_called_with_path(self, tool_name: str | None, path_pattern: str | None) -> bool:
        """Check if a tool was called with a file_path matching the pattern."""
        if not tool_name or not path_pattern:
            return False

        messages = await self.sandbox.read_messages_log()

        for msg in messages:
            if msg.get("type") != "assistant":
                continue

            content = msg.get("message", {}).get("content", [])
            for block in content:
                if block.get("type") == "tool_use" and block.get("name") == tool_name:
                    tool_input = block.get("input", {})
                    file_path = tool_input.get("file_path", "")
                    if re.search(path_pattern, file_path):
                        logger.debug(f"tool_called_with_path: {tool_name} with {file_path} matches {path_pattern}")
                        return True

        return False
