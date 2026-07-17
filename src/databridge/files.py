# %%
from collections.abc import Iterable
import logging
from pathlib import Path
from datetime import datetime, date
from shutil import copy2

import dateparser

_logger_ = logging.getLogger(__name__)


# %%
def scan_path(path: str | Path, glob_pattern: str = "*") -> list[Path]:
    """Scan a directory for files matching a glob pattern.

    Args:
        path (str | Path): The directory to scan.
        glob_pattern (str): The glob pattern to match files against.

    Returns:
        list[Path]: A list of Path objects representing the matching files.
    """
    path = Path(path)
    _logger_.info(f"Scanning path: {path} with pattern: {glob_pattern}")
    if not path.exists():
        _logger_.warning(f"Path {path} does not exist.")
        raise FileNotFoundError(f"Path {path} does not exist.")
    # for file in path.glob(glob_pattern):
    #     yield file
    files = list(path.glob(glob_pattern))
    _logger_.info(f"\t...found {len(files)} files.")
    return files


def filter_by_date(
    files: Iterable[Path], start: str | date | datetime, end: str | date | datetime
) -> list[Path]:
    """Filter a list of files by their modification datetime.

    Args:
        files (Iterable[Path]): An iterable of Path objects representing the files to filter.
        start (date | datetime): The start date or datetime for filtering.
        end (date | datetime): The end date or datetime for filtering.

    Returns:
        list[Path]: A list of Path objects representing the filtered files.
    """
    if isinstance(start, str):
        start = dateparser.parse(start).date()
    elif isinstance(start, datetime):
        start = start.date()

    if isinstance(end, str):
        end = dateparser.parse(end).date()
    elif isinstance(end, datetime):
        end = end.date()

    _logger_.info(f"Filtering files between {start} and {end}")
    filtered_files = []
    for file in files:
        mod_time = datetime.fromtimestamp(file.stat().st_mtime).date()
        if start <= mod_time <= end:
            filtered_files.append(file)
    _logger_.info(f"\t...found {len(filtered_files)} files after filtering.")
    return filtered_files


def copy_files(
    files: Iterable[Path],
    destination: str | Path,
    relative_to: str | Path,
    dry_run: bool = True,
) -> None:
    """Copy a list of files to a destination directory.

    Args:
        files (Iterable[Path]): An iterable of Path objects representing the files to copy.
        destination (str | Path): The destination directory to copy the files to.
    """
    _logger_.info(f"Copying files to {destination}")
    if dry_run:
        _logger_.warning(
            "\t[red]...[bold]DRY RUN[/bold]: No files will be copied.[/red]"
        )
    destination = Path(destination)
    if not destination.exists():
        _logger_.info(f"Creating destination directory: {destination}")
        if not dry_run:
            destination.mkdir(parents=True, exist_ok=True)

    for file in files:
        if relative_to is None:
            relative_to = file.parent
        dest_file = destination / Path(file).relative_to(relative_to)
        _logger_.info(
            f"Copying 'file://{file.as_posix()}' --> 'file://{dest_file.as_posix()}'"  # , extra={"highlighter": None}
        )
        if not dest_file.parent.exists():
            _logger_.info(f"Creating directory: {dest_file.parent}")
            if not dry_run:
                dest_file.parent.mkdir(parents=True, exist_ok=True)
        if not dry_run:
            copy2(file, dest_file)
