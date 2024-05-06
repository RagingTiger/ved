"""Test cases for fixtures."""
from pathlib import Path

import pytest

from ved.video.utils import extract_video_info


@pytest.mark.video
@pytest.mark.data
def test_video_dir_exists(video_directory_path: Path) -> None:
    """Confirm test video directory path exists."""
    # check exists
    assert video_directory_path.exists()


@pytest.mark.video
@pytest.mark.data
def test_video_file_exists(video_file_path: Path) -> None:
    """Confirm test video file exists."""
    # check exists
    assert video_file_path.exists()


@pytest.mark.video
@pytest.mark.data
def test_video_info(video_file_path: Path) -> None:
    """Confirm video info is correct."""
    # get video info
    length, fps = extract_video_info(str(video_file_path))

    # check length (in seconds) and fps
    assert int(length) == 20
    assert int(fps) == 50
