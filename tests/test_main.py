"""Test cases for the __main__ module."""
from pathlib import Path
from typing import Dict
from typing import Generator
from typing import Optional
from typing import Tuple

import pytest
from click.testing import CliRunner
from click.testing import Result

from ved import __main__
from ved.video.utils import extract_video_info
from tests.conftest import sha256_hash
from tests.types import MockParam
from tests.types import ParamsInput
from tests.types import ParamsInputTest
from tests.types import ParamsUsageErrorCase
from tests.types import ParamsUsageErrorDict
from tests.types import ParamsUsageMockArgsDict
from tests.types import RunnerArgs


TIME_STAMP_ERROR_CASES: Tuple[Tuple[ParamsInput, int], ...] = (
    ("str", 2),
    ("00:00:61", 2),
    ("00:61:00", 2),
    ("00:00.5:00", 2),
    ("00.5:00:00", 2),
    ("00::00", 2),
    (":00:00", 2),
    ("00:00:", 2),
    (":00:", 2),
    ("00::", 2),
    ("::00", 2),
    (":::", 2),
)

VIDEO_DIRECTORY_ERROR_CASES: Tuple[Tuple[ParamsInput, int], ...] = (
    ("/fake/dir/path", 2),
    (MockParam("non_video_file"), 2),
)

DIRECTORY_ONLY_ERROR_CASES: Tuple[Tuple[ParamsInput, int], ...] = ((" ", 2),)

# stores all possible opts/args usage errors cases
PARAMETERS_USAGE_ERRORS: ParamsUsageErrorDict = {
    "clip": {
        "-d": DIRECTORY_ONLY_ERROR_CASES,
        "start": TIME_STAMP_ERROR_CASES,
        "stop": TIME_STAMP_ERROR_CASES,
        "video_file": VIDEO_DIRECTORY_ERROR_CASES,
    },
    "list": {
        "video_path": VIDEO_DIRECTORY_ERROR_CASES,
    },
    "split": {
        "-d": DIRECTORY_ONLY_ERROR_CASES,
        "length": TIME_STAMP_ERROR_CASES,
        "video_path": VIDEO_DIRECTORY_ERROR_CASES,
    },
    "copy": {
        "video_path": VIDEO_DIRECTORY_ERROR_CASES,
        "output_path": DIRECTORY_ONLY_ERROR_CASES,
    },
    "convert": {
        "-d": DIRECTORY_ONLY_ERROR_CASES,
        "-a": (("str", 2),),
        "extension": (("str", 2),),
        "video_path": VIDEO_DIRECTORY_ERROR_CASES,
    },
}

# stores positional arguments position information
CLI_ARGUMENTS_SEQUENCES: Dict[str, Tuple[str, ...]] = {
    "clip": ("start", "stop", "video_file"),
    "list": ("video_path",),
    "split": ("length", "video_path"),
    "copy": ("video_path", "output_path"),
    "convert": ("extension", "video_path"),
}


def position_templator(
    prm: str, value: ParamsInputTest, sequence: Tuple[str, ...]
) -> Generator[ParamsInputTest, None, None]:
    """Correctly position parameters and mock all missing arguments."""
    # add parameter and its value if not in args sequence
    if prm not in sequence:
        yield prm
        yield value

    # now loop through each positional argument
    for item in sequence:
        # replace positional arg with its value
        if item == prm:
            yield value

        # or simply add mock parameter
        else:
            yield MockParam(item)


def mock_templator(
    positioned: Tuple[ParamsInputTest, ...],
    mock_dict: Dict[str, str],
) -> Generator[ParamsInputTest, None, None]:
    """Replace MockParam types with corresponding mock values."""
    # loop through previously generated position sequence
    for item in positioned:
        # if parameter is a mock param
        if isinstance(item, MockParam):
            # get actual mocked argument value for item
            yield mock_dict[item.key]

        # simply get parameter
        else:
            yield item


def gen_cli_params_cases(
    params_usage: ParamsUsageErrorDict = PARAMETERS_USAGE_ERRORS,
) -> Generator[ParamsUsageErrorCase, None, None]:
    """Flattens the nested params dictionary into pairs."""
    # get tuples pairs from flattened dictionary for a given cmd/opt pairs
    for cmd in params_usage:
        for prm in params_usage[cmd]:
            for value, code in params_usage[cmd][prm]:
                # make a nice tuple
                yield (cmd, prm, value, code)


def sanitize_runner_params(args: Tuple[RunnerArgs, ...], sep: str = " ") -> str:
    """Utility function to clean args and prepare for CliRunner."""
    # sanitized list
    sanitized = []

    # clean
    for arg in args:
        if arg is not None and type(arg) is not tuple:
            # update list
            sanitized.append(str(arg))

        elif type(arg) is tuple:
            # extend the list with the contents of arg list
            for element in arg:
                sanitized.append(str(element))

        else:
            # do nothing with empty arg (i.e a tuple)
            pass

    # finally
    return sep.join(sanitized)


def run_command(runner: CliRunner, *args: RunnerArgs) -> Result:
    """Utility function to run arbitray numbers of commands/options/values."""
    # remove empty tuples (i.e. args meant to be empty)
    sanitized = sanitize_runner_params(args)

    # get result
    return runner.invoke(__main__.main, sanitized)


@pytest.mark.parametrize(
    "cmd,opt,code",
    [(None, None, 0), ("clip", "-n", 0), ("list", "-n", 0), ("split", "-n", 0)],
)
def test_help_by_default_succeeds(
    runner: CliRunner, cmd: Optional[str], opt: Optional[str], code: int
) -> None:
    """Without arguments/options should print help message and exit."""
    # test if command exits normally
    result = run_command(runner, opt, cmd)

    # check code
    assert result.exit_code == code

    # check usage message printed
    assert "Usage" in result.output


@pytest.mark.parametrize("cmd,prm,value,code", gen_cli_params_cases())
def test_parameters_usage_check(
    runner: CliRunner,
    cmd: str,
    prm: str,
    value: ParamsInputTest,
    code: int,
    params_usage_mock_args: ParamsUsageMockArgsDict,
) -> None:
    """Test usage checks are working on cli parameters."""
    # generate position if necessary
    positioned = tuple(position_templator(prm, value, CLI_ARGUMENTS_SEQUENCES[cmd]))

    # match args with appropriate mock in appropriate position
    mocked_params = tuple(mock_templator(positioned, params_usage_mock_args))

    # get result
    result = run_command(runner, "-n", cmd, *mocked_params)

    # check exit code
    assert result.exit_code == code


@pytest.mark.slow
@pytest.mark.video
@pytest.mark.data
def test_clip_cmd(runner: CliRunner, video_file_path: Path, tmp_path: Path) -> None:
    """Confirm clip command process video file as expected."""
    # setup tmp clip dir
    clip_dir = tmp_path / "clip"

    # clip video from 5 to 15s mark
    result = run_command(
        runner,
        "clip",
        "-d",
        str(clip_dir),
        "00:00:05",
        "00:00:15",
        str(video_file_path),
    )

    # get clip file path
    clip_file = next(clip_dir.glob("**/*.mp4"))

    # get length/fps
    length, fps = extract_video_info(str(clip_file))

    # check result code
    assert result.exit_code == 0

    # make sure clip_dir created
    assert clip_dir.exists()

    # make sure clip file exists
    assert clip_file.exists()

    # make sure length is correct
    assert int(length) == 10

    # make sure fps unchanged
    assert int(fps) == 50


@pytest.mark.video
@pytest.mark.data
def test_list_cmd(
    runner: CliRunner, video_file_path: Path, video_directory_path: Path
) -> None:
    """Confirm list command finds video files as expected."""
    # list video file path
    video_file_results = run_command(
        runner,
        "list",
        "-l",
        str(video_file_path),
    )

    # list video directory path
    video_dir_results = run_command(
        runner,
        "list",
        "-l",
        str(video_directory_path),
    )

    # get results output pointers
    file_output = video_file_results.output
    dir_output = video_dir_results.output

    # confirm both commands ran
    assert video_file_results.exit_code == 0
    assert video_dir_results.exit_code == 0

    # confirm both get the same results
    assert file_output == dir_output

    # check both have the video file name in their output
    assert str(video_file_path) in file_output

    # check both have the same info printed out
    assert "20" in file_output.split()[0]
    assert "50" in file_output.split()[1]


@pytest.mark.video
@pytest.mark.data
def test_split_find_video_files(
    runner: CliRunner, video_file_path: Path, video_directory_path: Path
) -> None:
    """Confirm split command finds video files as expected."""
    # dry-run split test video file
    video_file_results = run_command(
        runner,
        "-n",
        "split",
        "00:00:10",
        str(video_file_path),
    )

    # dry-run split test video file given parent dir
    video_dir_results = run_command(
        runner,
        "-n",
        "split",
        "00:00:10",
        str(video_directory_path),
    )

    # get results output pointers
    file_output = video_file_results.output
    dir_output = video_dir_results.output

    # confirm both commands ran
    assert video_file_results.exit_code == 0
    assert video_dir_results.exit_code == 0

    # confirm both get the same results
    assert file_output == dir_output

    # check both have the video file name in their output
    assert str(video_file_path) in file_output


@pytest.mark.slow
@pytest.mark.video
@pytest.mark.data
def test_split_video_parts(
    runner: CliRunner, video_file_path: Path, tmp_path: Path
) -> None:
    """Confirm split command splits video into parts."""
    # setup tmp clip dir
    split_dir = tmp_path / "split"

    # actually plit test video file
    video_file_results = run_command(
        runner,
        "split",
        "-d",
        str(split_dir),
        "00:00:10",
        str(video_file_path),
    )

    # get parts
    parts = tuple(split_dir.glob("**/*.mp4"))

    # confirm exit code good
    assert video_file_results.exit_code == 0

    # check split dir created
    assert split_dir.exists()

    # assert correct number of parts
    assert len(parts) == 2

    # get part lengths
    part_1_len, _ = extract_video_info(str(parts[0]))
    part_2_len, _ = extract_video_info(str(parts[1]))

    # check lengths
    assert int(part_1_len) == int(part_2_len)
    assert int(part_1_len) == 10


@pytest.mark.video
@pytest.mark.data
def test_copy_cmd(
    runner: CliRunner, video_file_path: Path, video_file_hash: str, tmp_path: Path
) -> None:
    """Confirm copy command copies video to correct directory."""
    # create custom output path
    out_dir = tmp_path / "copied"

    # actually copy video file
    result = run_command(
        runner,
        "copy",
        str(video_file_path),
        str(out_dir),
    )

    # confirm output directory created
    assert out_dir.exists()

    # check exit code
    assert result.exit_code == 0

    # check file name in output message
    assert video_file_path.name in result.output

    # get path to copied video file
    copied_file_path = out_dir / video_file_path.name

    # check new copied file exists
    assert copied_file_path.exists()

    # check file names same
    assert copied_file_path.name == video_file_path.name

    # finally compare file hashes
    assert sha256_hash(str(copied_file_path)) == video_file_hash


@pytest.mark.slow
@pytest.mark.video
@pytest.mark.data
def test_convert_cmd(
    runner: CliRunner,
    video_file_path: Path,
    tmp_path: Path,
    params_usage_mock_args: ParamsUsageMockArgsDict,
) -> None:
    """Confirm convert command converts video to correct format."""
    # create custom output path
    out_dir = tmp_path / "converted"

    # get file format extension
    ext = params_usage_mock_args["extension"]

    # actually convert video file
    result = run_command(
        runner,
        "convert",
        "-d",
        str(out_dir),
        ext,
        str(video_file_path),
    )

    # confirm output directory created
    assert out_dir.exists()

    # check exit code
    assert result.exit_code == 0

    # check file name in output message
    assert video_file_path.name in result.output

    # get path to copied video file
    converted_file_path = out_dir / f"{video_file_path.stem}.{ext}"

    # check new copied file exists
    assert converted_file_path.exists()

    # check file names same
    assert converted_file_path.stem == video_file_path.stem

    # finally check correct extension
    assert ext in converted_file_path.suffix
