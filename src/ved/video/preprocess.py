"""Preprocess video files before editing."""
import pathlib
from typing import Optional

from moviepy.editor import VideoFileClip

from .utils import gen_split_part_info
from .utils import get_audio_codec


def create_clip(
    start: str, stop: Optional[str], video_path: str, out_path: str
) -> None:
    """Given a start/stop time and video_path, create clip to out_path."""
    # use context manager
    with VideoFileClip(video_path) as vidfile:
        # get sub clip
        clip = vidfile.subclip(start, stop)

        # check if requires a preferred audio codec
        acodec = get_audio_codec(video_path)

        # now write out new clip
        clip.write_videofile(out_path, audio_codec=acodec)


def convert_video(
    video_path: pathlib.Path,
    output_path: pathlib.Path,
    ext: str,
    acodec: Optional[str] = None,
) -> None:
    """Convert video from targert format to destination format."""
    # get file name
    new_outfile = f"{video_path.stem}.{ext}"

    # create new output file path
    new_outpath = output_path / new_outfile

    # use context mananger
    with VideoFileClip(str(video_path)) as vidfile:
        # convert
        vidfile.write_videofile(str(new_outpath), audio_codec=acodec)


def split_video(
    length: str,
    video_path: pathlib.Path,
    split_dir: pathlib.Path,
    suffix: str,
) -> None:
    """Split a video into clips of the specified length timestamp."""
    # packup generator args for readability purposes
    generator_args = (video_path, length, suffix)

    # now loop through part number
    for start, stop, clip_name in gen_split_part_info(*generator_args):
        # create clip path
        clip_path = split_dir / clip_name

        # finally ...
        create_clip(start, stop, str(video_path), str(clip_path))
