import logging
import os
import re
import shlex
import getpass
import signal

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
    try:
        proc = PtyProcess.spawn(parts)

        while proc.isalive():
            try:
                data = proc.read(1024).strip()
                data = strip_ansi(data)
                if data:
                    _logger_.info(data)

                if "password" in data.lower():
                    password = getpass.getpass(prompt="Enter password: ")
                    proc.write(password + "\n")
            except EOFError:
                break

        _logger_.info(f"Command '{command}' finished with exit code {proc.exitstatus}")
        proc.wait()
        if proc.exitstatus != 0:
            _logger_.error(
                f"Command '{command}' failed with exit code {proc.exitstatus}"
            )
            raise RuntimeError(
                f"Command '{command}' failed with exit code {proc.exitstatus}"
            )

    except KeyboardInterrupt as e:
        _logger_.warning(f"Command '{command}' interrupted by user.")
        if proc is not None and proc.isalive():
            os.kill(proc.pid, signal.SIGTERM)
        raise e
