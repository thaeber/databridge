import logging
import shlex
from pathlib import Path

import click
from fabric import Connection
from paramiko.ssh_exception import AuthenticationException, SSHException
from rich.progress import (
    BarColumn,
    Progress,
    TaskProgressColumn,
    TextColumn,
    TimeRemainingColumn,
)

_logger_ = logging.getLogger(__name__)


def scp_command(
    source: str | Path,
    target: str | Path,
    host: str,
    user: None | str = None,
    password: None | str = None,
):
    # check input parameters
    if isinstance(source, str):
        source = Path(source)
    if isinstance(target, str):
        target = Path(target)

    _logger_.info(f"Connecting to {host} as {user}")
    try:
        connection = Connection(host=host, user=user)
        connection.open()
    except AuthenticationException, SSHException:
        if password is None:
            password = click.prompt(
                "Password for remote server authentication",
                hide_input=True,
            )
        connection = Connection(
            host=host, user=user, connect_kwargs={"password": password}
        )

    # create the destination directory if it doesn't exist
    _logger_.info(f"Creating destination directory {target} on {host}")
    connection.run(f"mkdir -p {shlex.quote(str(target.as_posix()))}")

    sftp = connection.sftp()

    with Progress(
        BarColumn(),
        TaskProgressColumn(),
        TimeRemainingColumn(),
        TextColumn("[progress.description]{task.description}"),
    ) as progress:
        files = list(source.rglob("*"))
        current_task = progress.add_task(
            "[green]Current file", total=100, visible=False
        )
        total_task = progress.add_task(
            "[cyan]Uploading files",
            total=len(files),
        )
        for path in files:
            progress.update(
                total_task,
                advance=1,
                description=f"[cyan]Uploading files ({progress.tasks[total_task].completed}/{len(files)})",
            )

            rel = path.relative_to(source)
            remote_path = (target / rel).as_posix()

            if path.is_dir():
                try:
                    sftp.mkdir(remote_path)
                except IOError:
                    pass
            else:
                connection.run(
                    f"mkdir -p {shlex.quote(Path(remote_path).parent.as_posix())}"
                )
                progress.update(
                    current_task,
                    description=f"[green]Uploading {rel.name}",
                    total=path.stat().st_size,
                    completed=0,
                    visible=True,
                )
                sftp.put(
                    str(path),
                    remote_path,
                    callback=lambda sent, total: progress.update(
                        current_task,
                        advance=sent,
                        total=total,
                    ),
                )

            _logger_.info(f"Uploaded 'file://{rel}'")

        progress.update(
            total_task,
            current=len(files),
            description=f"[cyan]Uploading files ({len(files)}/{len(files)})",
        )
        progress.remove_task(current_task)

    # close the connection
    _logger_.info(f"Closing connection to {host}")
    connection.close()
