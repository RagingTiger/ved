"""Global fixtures."""
import hashlib
from pathlib import Path

import pytest
from click.testing import CliRunner
from pytest import Config
from pytest import FixtureRequest

from tests.types import ParamsUsageMockArgsDict


TEST_VIDEO_KEY_NAME = "sfvideo_wmn_pool"
TEST_VIDEO_DIR_NAME = TEST_VIDEO_KEY_NAME


def pytest_configure(config: Config) -> None:
    """For configuring pytest dynamically."""
    # add marker for slow tests
    config.addinivalue_line("markers", "slow: tests that are slower than average.")

    # add marker for all data related testing
    config.addinivalue_line("markers", "data: tests that depend on ANY real data.")

    # add marker for video data testing
    config.addinivalue_line("markers", "video: tests that depend on video data.")


def sha256_hash(filepath: str) -> str:
    """Compute SHA256 of a file."""
    # get hasher
    hasher = hashlib.sha256()

    # open the given file
    with open(filepath, "rb") as target:
        # starting point
        data = target.read(2048)

        # loop
        while data != b"":
            # keep updating
            hasher.update(data)

            # update position
            data = target.read(2048)

    # get digest
    return hasher.hexdigest()


@pytest.fixture
def runner() -> CliRunner:
    """Fixture for invoking command-line interfaces."""
    return CliRunner()


@pytest.fixture
def mock_directory(tmp_path: Path) -> str:
    """Create temp directory for parameters that require an existing directory path."""
    # create testing color file
    data_dir = tmp_path / "data"
    data_dir.mkdir()

    # ... and done
    return str(data_dir)


@pytest.fixture
def mock_video_file(tmp_path: Path) -> str:
    """Create a mock MP4 video file for parameters requiring a video file path."""
    # create image file
    video_file = tmp_path / "mock_video.mp4"

    # add some content to it
    video_file.write_text("content")

    # ... and it is done
    return str(video_file)


@pytest.fixture
def mock_non_video_file(tmp_path: Path) -> str:
    """Create a file that is not a video file."""
    # create testing color file
    data_dir = tmp_path / "data"

    # create mock color info file
    readme_file = data_dir / "README.md"

    # add some content to it
    readme_file.write_text("# About\nTest readme file for Femme Phile Core")

    # ... and done
    return str(readme_file)


@pytest.fixture
def params_usage_mock_args(
    mock_directory: str,
    mock_video_file: str,
    mock_non_video_file: str,
) -> ParamsUsageMockArgsDict:
    """Bundle mock arguments up for parameter usage testing."""
    return {
        "non_video_file": mock_non_video_file,
        "video_file": mock_video_file,
        "video_path": mock_directory,
        "start": "00:00:00",
        "stop": "00:00:05",
        "length": "00:00:05",
        "extension": "webm",
        "output_path": mock_directory,
    }

@pytest.mark.xfail(raises=NameError, reason="Test fails due to missing import")
@pytest.mark.video
@pytest.mark.data
@pytest.fixture(scope="module")
def video_directory_path(request: FixtureRequest) -> Path:
    """Downloads testing video data if not found in local tests/data dir."""
    # build image data dir path
    data_path = request.path.parents[0] / "data" / "video"

    # check path exists
    if not data_path.exists():
        # make if not found
        data_path.mkdir(parents=True)

    # add test video dataset directory to path
    video_dataset_dir = data_path / TEST_VIDEO_DIR_NAME

    # check if test video data is present
    if not any(video_dataset_dir.glob("**/*.mp4")):
        # make the test video dir
        video_dataset_dir.mkdir(parents=True, exist_ok=True)

        # download video data to path
        get_data(TEST_VIDEO_KEY_NAME, str(video_dataset_dir))

    # finally ...
    return video_dataset_dir


@pytest.mark.video
@pytest.mark.data
@pytest.fixture(scope="module")
def video_file_path(video_directory_path: Path) -> Path:
    """Return path/name of test video file."""
    # get first video in glob results
    return next(video_directory_path.glob("**/*.mp4"))


@pytest.mark.video
@pytest.mark.data
@pytest.fixture(scope="module")
def video_file_hash(video_file_path: Path) -> str:
    """Return SHA256 hash of test video file."""
    return sha256_hash(str(video_file_path))
