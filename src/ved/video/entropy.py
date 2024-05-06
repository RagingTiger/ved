"""Measure information content of video files."""
from typing import Generator

from moviepy.editor import VideoFileClip
from PIL import Image


def iter_frames_entropy(video_path: str) -> Generator[float, None, None]:
    """Iterate over video file frames and calculate their entropy."""
    # get movie file
    with VideoFileClip(video_path) as vidfile:
        # iterate through frames
        for frame in vidfile.iter_frames():
            # get frame entropy
            yield Image.fromarray(frame, mode="RGB").entropy()


def video_entropy(video_path: str) -> float:
    """Get average entropy of each frame in video file."""
    # setup vars
    total_frames: int = 0
    total_entropy: float = 0

    # get entropy
    for frame_entropy in iter_frames_entropy(video_path):
        # update total entropy
        total_entropy += frame_entropy

        # update total frames
        total_frames += 1

    # calculage average entropy of entire video file
    return total_entropy / total_frames
