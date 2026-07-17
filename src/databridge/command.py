import logging
import re
import shlex

from winpty import PtyProcess

_logger_ = logging.getLogger(__name__)


def strip_ansi(text):
    return re.sub(r"\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])", "", text)


def execute_shell_command(command: str, dry_run: bool = False) -> int:
    """
    Execute a given shell command and return its exit code.

    Args:
        command: The shell command to execute as a string.
        dry_run: If True, the command will be logged but not executed.

    Returns:
        The exit code of the command.
    """
    _logger_.info(f"Executing shell command: {command}")
    parts = shlex.split(command)
    _logger_.debug(f"Command parts: {parts}")

    if dry_run:
        _logger_.warning("[red]Dry run enabled. Command will not be executed.[/red]")
        return 0
    # use PtyProcess to spawn the command and capture its output
    proc = PtyProcess.spawn(parts)

    while proc.isalive():
        try:
            data = proc.read(1024).strip()
            data = strip_ansi(data)
            if data:
                _logger_.info(data)
        except EOFError:
            break

    proc.wait()
    if proc.exitstatus != 0:
        _logger_.error(f"Command '{command}' failed with exit code {proc.exitstatus}")
    return proc.exitstatus
