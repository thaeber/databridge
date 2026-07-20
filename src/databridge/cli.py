import logging
from datetime import datetime

import omegaconf
import rich_click as click
from rich.logging import RichHandler

from databridge.files import copy_files, filter_by_date, scan_path
from databridge.pipe import Pipe
from databridge.shell_command import execute_shell_command
from databridge.ssh_command import scp_command

_logger_ = logging.getLogger(__name__)

logging.basicConfig(
    level=logging.INFO,
    format="%(message)s",
    handlers=[RichHandler(rich_tracebacks=True, markup=True, omit_repeated_times=True)],
)


def end_output_callback(ctx, param, value):
    if value is not None:
        return value

    if start := ctx.params.get("start"):
        return start

    return value


class DatetimeParamType(click.ParamType[datetime]):
    name = "datetime"

    def convert(self, value, param, ctx):
        from dateparser import parse

        dt = parse(value)
        if dt is None:
            self.fail(f"Invalid datetime value: {value}", param, ctx)
        return dt


def get_task(task: omegaconf.DictConfig):
    ctx = click.get_current_context()
    match task.run:
        case "scan_path":
            return lambda value: scan_path(path=task.path, glob_pattern=task.pattern)
        case "filter_by_date":
            return lambda value: filter_by_date(value, start=task.start, end=task.end)
        case "copy_files":
            return lambda value: copy_files(
                value,
                destination=task.target,
                relative_to=task.get("relative_to", None),
                dry_run=ctx.params.get("dry_run", False) if ctx else False,
            )
        case "execute_shell_command":
            return lambda value: execute_shell_command(
                task.command,
                dry_run=ctx.params.get("dry_run", False) if ctx else False,
            )
        case "scp":
            return lambda value: scp_command(
                source=task.source,
                target=task.target,
                host=task.host,
                user=ctx.params.get("user") if ctx else None,
                password=ctx.params.get("password") if ctx else None,
            )
        case _:
            return lambda value: list(value)  # No operation for unrecognized tasks


def process_task_group(group: omegaconf.ListConfig):
    pipe = Pipe(None)
    for task in group:
        pipe = pipe.then(get_task(task))

    # _logger_.info(f"Final result: {pipe.unwrap()}")


@click.command()
@click.version_option(package_name="databridge")
@click.option(
    "--config",
    default="config.yaml",
    type=click.File("r", lazy=True),
    help="Path to the configuration file.",
    show_default=True,
)
@click.option(
    "--destination",
    default=".",
    help="Destination directory for collected data.",
    type=click.Path(file_okay=False, dir_okay=True, writable=True),
    show_default=True,
)
@click.option(
    "--start",
    default="today",
    help="Start date for filtering files.",
    type=DatetimeParamType(),
    show_default=True,
)
@click.option(
    "--end",
    default=None,
    help="End date for filtering files.",
    type=DatetimeParamType(),
    callback=end_output_callback,
    show_default="same as --start if not provided",
)
@click.option(
    "--dry-run",
    is_flag=True,
    default=False,
    help="Perform a dry run without copying files.",
)
@click.option("--user", default=None, help="Username for remote server authentication.")
@click.option(
    "--password",
    prompt=True,
    hide_input=True,
    default=None,
    help="Password for remote server authentication.",
)
def cli(
    config,
    destination: str,
    start: datetime,
    end: datetime,
    dry_run: bool,
    user: str,
    password: str,
):
    """DataBridge is a Python tool that automatically collects measurement
    data from distributed devices and applications, stores it in a central
    location, and optionally synchronizes it with a remote server for easy
    management and backup."""

    # load configuration from the specified file
    _logger_.info(f"Loading configuration from {config.name}")
    conf = omegaconf.OmegaConf.load(config)
    assert isinstance(conf, omegaconf.DictConfig), "Configuration must be a DictConfig"

    # inject command line parameters into the configuration
    _logger_.info("Injecting command line parameters into configuration")
    yaml = omegaconf.OmegaConf.to_yaml(conf, resolve=True).format(
        destination=destination, start=start, end=end, user=user
    )
    conf = omegaconf.OmegaConf.create(yaml)
    _logger_.info(f"Configuration after injection:\n{yaml}")

    # process task groups defined in the configuration
    for key in conf["groups"]:  # type: ignore
        _logger_.info(f"Processing task group: [bold]{key}[/bold]")
        group = conf["groups"][key]  # type: ignore
        # assert isinstance(group, omegaconf.ListConfig)
        process_task_group(group)
