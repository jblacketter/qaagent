"""Tests for tools.py — CmdResult, run_command, which, ensure_dir."""
from pathlib import Path
from unittest.mock import patch, MagicMock

from qaagent.tools import CmdResult, run_command, which, ensure_dir


class TestCmdResult:
    def test_fields(self):
        result = CmdResult(returncode=0, stdout="out", stderr="err")
        assert result.returncode == 0
        assert result.stdout == "out"
        assert result.stderr == "err"


class TestWhich:
    @patch("qaagent.tools.shutil.which", return_value="/usr/bin/python")
    def test_found(self, mock_which):
        assert which("python") == "/usr/bin/python"

    @patch("qaagent.tools.shutil.which", return_value=None)
    def test_not_found(self, mock_which):
        assert which("nonexistent") is None


class TestRunCommand:
    @patch("qaagent.tools.subprocess.run")
    def test_success(self, mock_run):
        mock_run.return_value = MagicMock(
            returncode=0, stdout="hello", stderr=""
        )
        result = run_command(["echo", "hello"])

        assert result.returncode == 0
        assert result.stdout == "hello"
        assert result.stderr == ""

    @patch("qaagent.tools.subprocess.run")
    def test_failure(self, mock_run):
        mock_run.return_value = MagicMock(
            returncode=1, stdout="", stderr="error msg"
        )
        result = run_command(["false"])

        assert result.returncode == 1
        assert result.stderr == "error msg"

    @patch("qaagent.tools.subprocess.run")
    def test_timeout(self, mock_run):
        import subprocess
        mock_run.side_effect = subprocess.TimeoutExpired(cmd=["slow"], timeout=5)

        result = run_command(["slow"], timeout=5)

        assert result.returncode == -1
        assert "timed out" in result.stderr

    @patch("qaagent.tools.subprocess.run")
    def test_stdout_tail(self, mock_run):
        long_output = "x" * 10000
        mock_run.return_value = MagicMock(
            returncode=0, stdout=long_output, stderr=""
        )
        result = run_command(["cmd"], tail=100)

        assert len(result.stdout) == 100

    @patch("qaagent.tools.subprocess.run")
    def test_cwd_passed(self, mock_run, tmp_path):
        mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")

        run_command(["ls"], cwd=tmp_path)

        _, kwargs = mock_run.call_args
        assert kwargs["cwd"] == str(tmp_path)

    @patch("qaagent.tools.subprocess.run")
    def test_env_merged(self, mock_run):
        mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")

        run_command(["cmd"], env={"MY_VAR": "val"})

        _, kwargs = mock_run.call_args
        assert kwargs["env"]["MY_VAR"] == "val"

    @patch("qaagent.tools.subprocess.run")
    def test_empty_stdout_stderr(self, mock_run):
        mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")

        result = run_command(["cmd"])

        assert result.stdout == ""
        assert result.stderr == ""

    @patch("qaagent.tools.subprocess.run")
    def test_none_stdout_stderr(self, mock_run):
        mock_run.return_value = MagicMock(returncode=0, stdout=None, stderr=None)

        result = run_command(["cmd"])

        assert result.stdout == ""
        assert result.stderr == ""


class TestEnsureDir:
    def test_creates_directory(self, tmp_path):
        new_dir = tmp_path / "a" / "b" / "c"
        ensure_dir(new_dir)
        assert new_dir.is_dir()

    def test_existing_directory(self, tmp_path):
        existing = tmp_path / "exists"
        existing.mkdir()
        ensure_dir(existing)  # Should not raise
        assert existing.is_dir()
