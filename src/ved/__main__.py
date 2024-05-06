"""Command-line interface."""
import os
import pathlib
import shutil
import sys
from typing import Any
from typing import Optional
from typing import Tuple

import click

from .utils import random_filename
from .utils import sanitized_filename
from .video.preprocess import convert_video
from .video.preprocess import create_clip
from .video.preprocess import split_video
from .video.utils import convert_to_seconds
from .video.utils import extract_video_info
from .video.utils import gen_random_video_paths
from .video.utils import gen_split_part_info
from .video.utils import gen_video_extensions
from .video.utils import gen_video_paths
from .video.utils import gen_video_paths_filter_ext


class VideoPath(click.Path):
    """Confirms that the given file path is indeed a video file."""

    name = "video file(s) path"

    def convert(
        self,
        value: Any,
        param: Optional[click.Parameter],
        ctx: Optional[click.Context],
    ) -> Any:
        """Attempt to validate video file path."""
        # get converted type from parent click.Tuple
        converted = super().convert(value, param, ctx)

        # get path object
        if isinstance(converted, str):
            # create from string
            video_path = pathlib.Path(converted)

        elif isinstance(converted, bytes):
            # decode to bytest to string
            video_path = pathlib.Path(converted.decode())

        elif isinstance(converted, pathlib.Path):
            # already pathlib Path obj
            video_path = converted

        # check extension
        if video_path.is_file():
            # get extensions
            exts = tuple(gen_video_extensions())

            # check extension
            if video_path.suffix.lstrip(".") not in exts:
                self.fail(
                    f"File extension {video_path.suffix!r}"
                    " "
                    f"not found in known video file format extensions: {exts}"
                )

        # get converted type
        return converted


class TimeStamp(click.ParamType):
    """Confirms that the given time stamp is H:M:S format."""

    name = "hour:minute:second time stamp"

    def convert(
        self,
        value: Any,
        param: Optional[click.Parameter],
        ctx: Optional[click.Context],
    ) -> Any:
        """Confirm given value is in time stamp format."""
        # attempt to get time stamp info
        try:
            converted = str(value)
            hour, min, sec = converted.split(":")
        except ValueError:
            # notify of format error
            self.fail(
                f"{converted!r} is not an acceptable time stamp format."
                " "
                "Time stamp requires the following format: HOUR:MINUTE:SECOND."
            )

        # make sure hour/min values are ints and sec can be float/int
        try:
            int(hour)
            int(min)
            float(sec)
        except ValueError:
            # notify of error with actual time numbers
            self.fail(
                f"{converted!r} are not the correct numeric type."
                " "
                f"HOUR/MINUTE must be integer, while SECOND can be integer or float."
            )

        # make sure appropriate range is considered
        try:
            assert int(min) <= 60 and float(sec) <= 60
        except AssertionError:
            # notify of range errors
            self.fail(
                f"{converted!r} are not within the correct range."
                " "
                f"MINUTE/SECOND must be less than or equal to 60 (i.e. m/s <= 60)."
            )

        # get converted type
        return converted


@click.group(invoke_without_command=True, no_args_is_help=True)
@click.version_option()
@click.option("-n", "--dry-run", is_flag=True, help="Simulates running commands.")
@click.option("-e", "--debug", is_flag=True, help="Turn on debugging features.")
@click.pass_context
def main(ctx: click.Context, dry_run: bool, debug: bool) -> None:
    """Femme Phile Core."""
    # check context is from __name__ == __main__
    ctx.ensure_object(dict)

    # update dry run key
    ctx.obj["DRY_RUN"] = dry_run
    ctx.obj["DEBUG"] = debug


def sync_main_flags(ctx: click.Context) -> Tuple[bool, bool]:
    """Simply sync flags from main with subcommands flags."""
    # sync flags
    return ctx.obj["DRY_RUN"], ctx.obj["DEBUG"]


@main.command(
    "clip",
    no_args_is_help=True,
    short_help="Extract clip from video file using start/stop time points.",
)
@click.option(
    "-d",
    "--clip-dir",
    type=click.Path(dir_okay=True, file_okay=False, path_type=pathlib.Path),
    default=pathlib.Path(os.getcwd()) / "clip",
    show_default=True,
    help="Directory path to write video clip to.",
)
@click.argument("start", type=TimeStamp())
@click.argument("stop", type=TimeStamp())
@click.argument(
    "video_file",
    type=VideoPath(exists=True, file_okay=True, dir_okay=False, path_type=pathlib.Path),
)
@click.pass_context
def clip(
    ctx: click.Context,
    clip_dir: pathlib.Path,
    start: str,
    stop: str,
    video_file: pathlib.Path,
) -> None:
    """Extract clip from video file using start/stop time points."""
    # get dry_run and debug info if any
    dry_run, debug = sync_main_flags(ctx)

    # create clip id
    clip_id = f"clip_{''.join(start.split(':'))}_{''.join(stop.split(':'))}"

    # get name
    clip_name = f"{video_file.stem}_{clip_id}{video_file.suffix}"

    # get destination path/name for new clip
    clip_path = clip_dir / clip_name

    # now write new clip file out to disk
    if not dry_run:
        # check clip dir exists
        if not clip_dir.exists():
            # must wrap with try block for permission errors
            try:
                clip_dir.mkdir(parents=True, exist_ok=True)
            except PermissionError as e:
                sys.exit(str(e))

        # attempt to create subclip
        try:
            create_clip(start, stop, str(video_file), str(clip_path))

        # something goes wrong ...
        except BaseException as e:
            # notify of error
            sys.exit(str(e))

    # dry-run toggled
    else:
        # just print final clip name/path
        click.echo(clip_path)


@main.command(
    "list",
    no_args_is_help=True,
    short_help="Show video file(s) in selected path along with optional information.",
)
@click.option(
    "-l", "--long", is_flag=True, help="Print additional video file information."
)
@click.argument(
    "video_path",
    type=VideoPath(exists=True, file_okay=True, dir_okay=True, path_type=pathlib.Path),
)
@click.pass_context
def list(ctx: click.Context, long: bool, video_path: pathlib.Path) -> None:
    """Show video file(s) in selected path along with optional information."""
    # get dry_run and debug info if any
    dry_run, debug = sync_main_flags(ctx)

    # create options function list
    option_funcs = []

    # see if -l passed for additional video information
    if long:
        # wrap info extracting func with formatting func
        def format_vid_info(v: str) -> str:
            """Format extracted video info into string."""
            return "{:10.2f}s {:6.2f}fps".format(*extract_video_info(str(v)))

        # add func
        option_funcs.append(format_vid_info)

    # check if file
    if video_path.is_file():
        # set final output string
        output_str = ""

        # check option funcs
        for func in option_funcs:
            # add to output string
            output_str += func(str(video_path)) + " "

        # finally add file path string
        output_str += str(video_path)

        # now print
        click.echo(output_str)

    else:
        # loop over video file paths
        for match in gen_video_paths(video_path):
            # set final output string
            output_str = ""

            # apply options
            for func in option_funcs:
                # add output string from optional information function
                output_str += func(str(match)) + " "

            # finally add file path string
            output_str += str(match)

            # now print
            click.echo(output_str)


def dry_run_split(
    length: str,
    video_path: pathlib.Path,
    split_dir: pathlib.Path,
    suffix: str,
) -> None:
    """Only for dry-run purposes does not actually split video files."""
    # packup generator args for readability purposes
    generator_args = (video_path, length, suffix)

    # now loop through part number
    for start, stop, clip_name in gen_split_part_info(*generator_args):
        # create clip path
        clip_path = split_dir / clip_name

        # print out
        click.echo(f"{start:>10} {str(stop):>10} {clip_path}")


@main.command(
    "split",
    no_args_is_help=True,
    short_help="Split video file(s) into parts of maximum length.",
)
@click.option(
    "-s",
    "--suffix",
    type=str,
    default="_part_",
    show_default=True,
    help="Set suffix for parts.",
)
@click.option(
    "-d",
    "--split-dir",
    type=click.Path(dir_okay=True, file_okay=False, path_type=pathlib.Path),
    default=pathlib.Path(os.getcwd()) / "split",
    show_default=True,
    help="Directory path to write split files to.",
)
@click.argument(
    "length",
    type=TimeStamp(),
)
@click.argument(
    "video_path",
    type=VideoPath(exists=True, file_okay=True, dir_okay=True, path_type=pathlib.Path),
)
@click.pass_context
def split(
    ctx: click.Context,
    suffix: str,
    split_dir: pathlib.Path,
    length: str,
    video_path: pathlib.Path,
) -> None:
    """Split video file(s) into parts of maximum length."""
    # get dry_run and debug info if any
    dry_run, debug = sync_main_flags(ctx)

    # check if path is a file
    if video_path.is_file():
        # set generator for a single file
        path_generator = (path for path in [video_path])

    else:
        # set generator for directory
        path_generator = gen_video_paths(video_path)

    # check if dry-run toggled
    if not dry_run:
        # set correct splitting func
        split_func = split_video

        # check split dir exists
        if not split_dir.exists():
            # must wrap with try block for permission errors
            try:
                split_dir.mkdir(parents=True, exist_ok=True)
            except PermissionError as e:
                sys.exit(str(e))

    else:
        # use dummy video splitting func
        split_func = dry_run_split

    vids = [vid for vid in path_generator]

    total_videos = len(vids)

    # loop over video file paths
    for idx, match in enumerate(vids):
        # convert to second
        len_secs = convert_to_seconds(length)

        # notify user of file being processed
        click.echo(f"Splitting file #{idx+1}/{total_videos}")

        # actually split the video file into parts (if not dry-run)
        split_func(length, match, split_dir, suffix)

        # add new line
        click.echo()


@main.command(
    "copy",
    no_args_is_help=True,
    short_help="Copy video file(s) from one directory to another.",
)
@click.argument(
    "video_path",
    type=VideoPath(exists=True, file_okay=True, dir_okay=True, path_type=pathlib.Path),
)
@click.argument(
    "output_path",
    type=click.Path(dir_okay=True, file_okay=False, path_type=pathlib.Path),
)
@click.pass_context
def copy(
    ctx: click.Context,
    video_path: pathlib.Path,
    output_path: pathlib.Path,
) -> None:
    """Copy video file(s) from one directory to another."""
    # get dry_run and debug info if any
    dry_run, debug = sync_main_flags(ctx)

    # check if path is a file
    if video_path.is_file():
        # set generator for a single file
        path_generator = (path for path in [video_path])

    else:
        # set generator for directory
        path_generator = gen_video_paths(video_path)

    # check if dry-run toggled
    if not dry_run:
        # set correct copy function
        copy_func = shutil.copy

        # check split dir exists
        if not output_path.exists():
            # must wrap with try block for permission errors
            try:
                output_path.mkdir(parents=True, exist_ok=True)
            except PermissionError as e:
                sys.exit(str(e))

    else:
        # create debug copy func
        def debug_copy(video_path: str, output_path: str) -> None:
            """Does nothing for debugging purposes."""
            pass

        # assing to copy func pointer
        copy_func = debug_copy  # type: ignore

    # loop over video file paths
    for match in path_generator:
        # notify user of file being processed
        click.echo(f"Copying file: {match} -> {output_path}")

        # actually copies the video to output path if not dry-run)
        copy_func(str(match), str(output_path))


@main.command(
    "convert",
    no_args_is_help=True,
    short_help="Convert video file(s) from one format to another.",
)
@click.option(
    "-d",
    "--convert-dir",
    type=click.Path(dir_okay=True, file_okay=False, path_type=pathlib.Path),
    default=pathlib.Path(os.getcwd()) / "converted",
    show_default=True,
    help="Directory path to write converted files to.",
)
@click.option(
    "-e", "--all-extensions", is_flag=True, help="Include all video file extensions."
)
@click.option(
    "-a",
    "--audio-codec",
    type=click.Choice(("aac", "libmp3lame", "libvorbis"), case_sensitive=False),
    default=None,
    show_default=True,
    help="Audio encoding to use.",
)
@click.argument(
    "extension",
    type=click.Choice(tuple(gen_video_extensions()), case_sensitive=False),
)
@click.argument(
    "video_path",
    type=VideoPath(exists=True, file_okay=True, dir_okay=True, path_type=pathlib.Path),
)
@click.pass_context
def convert(
    ctx: click.Context,
    convert_dir: pathlib.Path,
    all_extensions: bool,
    audio_codec: Optional[str],
    extension: str,
    video_path: pathlib.Path,
) -> None:
    """Convert video file(s) from one format to another."""
    # get dry_run and debug info if any
    dry_run, debug = sync_main_flags(ctx)

    # check if path is a file
    if video_path.is_file():
        # set generator for a single file
        path_generator = (path for path in [video_path])

    else:
        # set generator for directory
        if all_extensions:
            # do no filtering of existing video files with target extension
            path_generator = gen_video_paths(video_path)

        else:
            # filter any existing video files with extension
            path_generator = gen_video_paths_filter_ext(video_path, extension)

    # check if dry-run toggled
    if not dry_run:
        # set correct copy function
        convert_func = convert_video

        # check split dir exists
        if not convert_dir.exists():
            # must wrap with try block for permission errors
            try:
                convert_dir.mkdir(parents=True, exist_ok=True)
            except PermissionError as e:
                sys.exit(str(e))

    else:
        # create debug copy func
        def debug_convert(
            video_path: pathlib.Path,
            output_path: pathlib.Path,
            ext: str,
            acodec: Optional[str] = None,
        ) -> None:
            """Does nothing for debugging purposes."""
            pass

        # assing to copy func pointer
        convert_func = debug_convert

    # notify user of output directory
    click.echo(f"Converted files will be written to: {convert_dir}")

    # loop over video file paths
    for match in path_generator:
        # get new file path
        new_file = convert_dir / f"{match.stem}.{extension}"

        # notify user of file being processed
        click.echo(f"Converting file {match} to {new_file}")

        # actually copies the video to output path if not dry-run)
        convert_func(match, convert_dir, extension, audio_codec)


@main.command(
    "random",
    no_args_is_help=True,
    short_help="Select video file(s) at random from video directory.",
)
@click.option(
    "-s",
    "--seed",
    type=click.IntRange(0, min_open=True),
    default=None,
    show_default=True,
    help="Integer value used to seed the Random Number Generator.",
)
@click.option(
    "-k",
    "--max-items",
    type=int,
    default=None,
    show_default=True,
    help="Maximum number of video paths to return.",
)
@click.option(
    "-d",
    "--output-dir",
    type=click.Path(dir_okay=True, file_okay=False, path_type=pathlib.Path),
    default=pathlib.Path(os.getcwd()) / "random",
    show_default=True,
    help="Directory path to copy randomly selected files to.",
)
@click.argument(
    "video_path",
    type=VideoPath(exists=True, file_okay=True, dir_okay=True, path_type=pathlib.Path),
)
@click.pass_context
def random(
    ctx: click.Context,
    seed: Optional[int],
    max_items: Optional[int],
    output_dir: pathlib.Path,
    video_path: pathlib.Path,
) -> None:
    """Select video file(s) at random from video directory."""
    # get dry_run and debug info if any
    dry_run, debug = sync_main_flags(ctx)

    # check if path is a file
    if video_path.is_file():
        # set generator for a single file
        path_generator = (path for path in [video_path])

    else:
        # set generator for directory
        path_generator = gen_random_video_paths(video_path, seed, max_items)

    # check if dry-run toggled
    if not dry_run:
        # set correct copy function
        copy_func = shutil.copy

        # check split dir exists
        if not output_dir.exists():
            # must wrap with try block for permission errors
            try:
                output_dir.mkdir(parents=True, exist_ok=True)
            except PermissionError as e:
                sys.exit(str(e))

    else:
        # create debug copy func
        def debug_copy(video_path: str, output_path: str) -> None:
            """Does nothing for debugging purposes."""
            pass

        # assing to copy func pointer
        copy_func = debug_copy  # type: ignore

    # loop over video file paths
    for match in path_generator:
        # notify user of file being processed
        click.echo(f"{match}")

        # actually copies the video to output path if not dry-run)
        copy_func(str(match), str(output_dir))


@main.command(
    "rename",
    no_args_is_help=True,
    short_help="Rename video file(s) using various patterns.",
)
@click.option(
    "-a",
    "--append",
    type=click.Choice(("prefix", "suffix"), case_sensitive=False),
    default=None,
    show_default=True,
    help="Append random name to existing name.",
)
@click.option(
    "-p",
    "--separator",
    type=str,
    default="_",
    show_default='"_"',
    help="Character used to separate new filename parts.",
)
@click.option(
    "-l",
    "--length",
    type=click.IntRange(0, min_open=True),
    default=16,
    show_default=True,
    help="Number of characters desired in random alphanumeric filename.",
)
@click.argument(
    "video_path",
    type=VideoPath(exists=True, file_okay=True, dir_okay=True, path_type=pathlib.Path),
)
@click.argument(
    "pattern",
    type=click.Choice(("random", "sanitize"), case_sensitive=False),
)
@click.pass_context
def rename(
    ctx: click.Context,
    append: Optional[str],
    separator: str,
    length: int,
    video_path: pathlib.Path,
    pattern: str,
) -> None:
    """Rename video file(s) using various patterns."""
    # get dry_run and debug info if any
    dry_run, debug = sync_main_flags(ctx)

    # check if appending
    if append is not None:
        # setup prefix/suffix templates
        prefix = "{0}" + f"{separator}" + "{1}"
        suffix = "{1}" + f"{separator}" + "{0}"

        # check prefix/suffix
        filename_tmplt = prefix if append == "prefix" else suffix

    else:
        # do not keep original filename
        filename_tmplt = "{0}"

    # get correct pattern function
    pattern_function, pattern_args = {
        "random": (random_filename, (filename_tmplt, length)),
        "sanitize": (sanitized_filename, ()),
    }[pattern]

    # check if path is a file
    if video_path.is_file():
        # set generator for a single file
        path_generator = (path for path in [video_path])

    else:
        # set generator for directory
        path_generator = gen_video_paths(video_path)

    # check if dry-run toggled
    if not dry_run:
        # set correct copy function
        rename_func = shutil.move

    else:
        # create debug copy func
        def debug_rename(src: str, dst: str) -> None:
            """Does nothing for debugging purposes."""
            click.echo(f"Renaming: {src} -> {dst}")

        # assing to copy func pointer
        rename_func = debug_rename  # type: ignore

    # loop over video file paths
    for match in path_generator:
        # get new file name
        new_file_path = pattern_function(match, *pattern_args)  # type: ignore

        # actually copies the video to output path if not dry-run)
        rename_func(str(match), str(new_file_path))


if __name__ == "__main__":
    main(prog_name="core")  # pragma: no cover
