"""Video utilities."""
import math
import pathlib
import random
from typing import Generator
from typing import Optional
from typing import Tuple

from moviepy.editor import VideoFileClip
from moviepy.tools import cvsecs
from moviepy.tools import extensions_dict


PREFERRED_AUDIO_CODEC = {
    "mp4": "aac",
}


def get_audio_codec(videofile: str) -> Optional[str]:
    """Gets any preferred audio codec if it exists."""
    # get path obj
    vid_path_obj = pathlib.Path(videofile)

    # get extension
    ext = vid_path_obj.suffix.lstrip(".")

    # check extension is in preferences
    return PREFERRED_AUDIO_CODEC[ext] if ext in PREFERRED_AUDIO_CODEC else None


def extract_video_info(path: str) -> Tuple[float, float]:
    """Get video info from VideoFileClip object."""
    # use context
    with VideoFileClip(str(path)) as clip:
        # must check types
        assert isinstance(clip.duration, float)
        assert isinstance(clip.fps, float)

        # now get video info
        return (clip.duration, clip.fps)


def gen_video_extensions() -> Generator[str, None, None]:
    """Generate video extensions from moviepy extensions_dict."""
    # begin loop
    for ext in extensions_dict.keys():
        # check if video type
        if extensions_dict[ext]["type"] == "video":
            yield ext


def gen_video_paths(video_dir: pathlib.Path) -> Generator[pathlib.Path, None, None]:
    """Find all video files in all sub directories of video directory."""
    # loop over extensions
    for ext in gen_video_extensions():
        # now loop over directory
        yield from video_dir.glob(f"**/*.{ext}")


def gen_video_paths_filter_ext(
    video_dir: pathlib.Path, ext: str
) -> Generator[pathlib.Path, None, None]:
    """Find all videos without extension in all sub directories of video directory."""
    # loop over video paths
    for path in gen_video_paths(video_dir):
        # check extension
        if path.suffix != ext:
            yield path


def gen_random_video_paths(
    video_dir: pathlib.Path, seed: Optional[int], max_items: Optional[int]
) -> Generator[pathlib.Path, None, None]:
    """Randomly sample from all video files returned from gen_video_paths()."""
    # first thing is to seed Random Number Generator
    random.seed(a=seed)

    # must generate sequence before sampling
    sequence = tuple(gen_video_paths(video_dir))

    # get k if none
    k = max_items if max_items is not None else random.randint(0, len(sequence))

    # yield random video paths
    yield from random.sample(sequence, k)


def convert_to_seconds(timestamp: str) -> float:
    """Wraps moviepy.tools.cvsecs and returns float."""
    return float(cvsecs(timestamp))


def gen_split_part_info(
    video_path: pathlib.Path, length: str, suffix: str
) -> Generator[Tuple[str, Optional[str], str], None, None]:
    """Calculates start/stop times and create clip name for split parts."""
    # convert time stamp to seconds
    part_len = convert_to_seconds(length)

    # get clip obj
    video_len, _ = extract_video_info(str(video_path))

    # get ratio of video length to part length
    part_ratio = video_len / part_len

    # get leftover video length
    leftover = math.fabs(part_ratio - int(part_ratio)) * part_len

    # get total number of parts
    parts_total = math.ceil(part_ratio) if leftover >= 1 else int(part_ratio)

    # determine termination time in seconds
    termination = None if leftover >= 1 else str(parts_total * part_len)

    # create part for each
    for part in range(parts_total):
        # create clip id
        clip_id = f"{suffix}{part+1}_of_{parts_total}"

        # get name
        clip_name = f"{video_path.stem}_{clip_id}{video_path.suffix}"

        # calculate start/stop times
        start = str(part_len * part)
        stop = str(part_len * (part + 1)) if part + 1 != parts_total else termination

        # get info
        yield (start, stop, clip_name)
