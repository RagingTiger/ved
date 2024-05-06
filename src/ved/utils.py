"""Common utilities."""
import secrets
from pathlib import Path

import pathvalidate


def random_filename(file_path: Path, tmplt: str = "{0}", length: int = 16) -> Path:
    """Generates random alphanumeric filename from file_path."""
    # account for hexadecimal digits
    num_chars = int(length / 2)

    # create random string
    random_part = secrets.token_hex(num_chars)

    # apply template
    new_file_name = tmplt.format(random_part, file_path.stem) + file_path.suffix

    # return new file path
    return file_path.parents[0] / new_file_name


def sanitized_filename(file_path: Path) -> Path:
    """Create a new sanitary file name from file path."""
    # sanitize old file name
    new_file_name = pathvalidate.sanitize_filename(file_path.name)

    # return new file path
    return file_path.parents[0] / new_file_name
