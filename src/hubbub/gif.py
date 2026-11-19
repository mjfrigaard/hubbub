"""Assemble PNG frames into a GIF."""

from __future__ import annotations

from pathlib import Path

from PIL import Image


def make_gif(
    frame_dir: str | Path,
    output: str | Path,
    width: int,
    height: int,
    first_duration: float = 1,
    frame_duration: float = 0.4,
    last_duration: float = 4,
) -> Path:
    """Assemble a directory of PNG frames into a looping GIF.

    Frames are read in file name order, so name them `0001.png`, `0002.png`,
    and so on. The first and last frames get their own hold times.

    Parameters
    ----------
    frame_dir : str or pathlib.Path
        Directory holding the `.png` frames.
    output : str or pathlib.Path
        Path for the `.gif` file.
    width, height : int
        GIF size in pixels. Frames are resized to fit.
    first_duration : float
        Seconds to hold the first frame.
    frame_duration : float
        Seconds to show each middle frame.
    last_duration : float
        Seconds to hold the last frame.

    Returns
    -------
    pathlib.Path
        The output path.

    Raises
    ------
    FileNotFoundError
        If `frame_dir` has no PNG files.
    """
    files = sorted(Path(frame_dir).glob("*.png"))
    n = len(files)
    if n == 0:
        raise FileNotFoundError(f"No PNG frames found in: {frame_dir}")
    if n == 1:
        delays = [last_duration]
    else:
        delays = [first_duration] + [frame_duration] * (n - 2) + [last_duration]

    frames = [
        Image.open(f).convert("RGB").resize((width, height)) for f in files
    ]
    out = Path(output)
    frames[0].save(
        out,
        save_all=True,
        append_images=frames[1:],
        duration=[int(d * 1000) for d in delays],
        loop=0,
    )
    return out
