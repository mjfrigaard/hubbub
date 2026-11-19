"""Introduce yourself, as text or as an animated GIF."""

from __future__ import annotations

import re
import tempfile
import time
import warnings
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from .gif import make_gif


def _messages(
    name: str, likes: str, learn: str, work: str, collab: str, connect: bool
) -> list[str]:
    msgs = [
        f"\U0001f44b Hi, my name is {name}.",
        f"\U0001f440 I like {likes}",
        f"\U0001f331 I'm learning about {learn}",
        f"\U0001f4e6 I'm currently working on {work}",
        f"\U0001f49e I'd love to collaborate on {collab}",
    ]
    if connect:
        msgs.append("\U0001f4eb Want to connect? Use the badges below...")
    return msgs


def who_am_i(
    name: str,
    likes: str,
    learn: str,
    work: str,
    collab: str,
    connect: bool = True,
    delay: float = 1.5,
    quiet: bool = False,
) -> list[str]:
    """Introduce yourself, one line at a time.

    Parameters
    ----------
    name : str
        Your name.
    likes : str
        What you like.
    learn : str
        What you are learning.
    work : str
        What you are working on.
    collab : str
        What you would like to collaborate on.
    connect : bool
        Add the "Want to connect?" line.
    delay : float
        Seconds to pause between lines. Use `0` for none.
    quiet : bool
        Skip printing (useful when building README text).

    Returns
    -------
    list of str
        The introduction lines.

    Examples
    --------
    >>> lines = who_am_i("Martin", "#rstats.", "Python.", "packages.",
    ...                  "data science.", delay=0)  # doctest: +ELLIPSIS
    👋 Hi, my name is Martin.
    ...
    >>> len(lines)
    6
    """
    msgs = _messages(name, likes, learn, work, collab, connect)
    for i, msg in enumerate(msgs):
        if not quiet:
            print(msg, flush=True)
        if delay and i < len(msgs) - 1:
            time.sleep(delay)
    return msgs


EMOJI_FONTS = [
    "/System/Library/Fonts/Apple Color Emoji.ttc",
    "/usr/share/fonts/truetype/noto/NotoColorEmoji.ttf",
    "/usr/share/fonts/noto/NotoColorEmoji.ttf",
    "/usr/share/fonts/google-noto-emoji/NotoColorEmoji.ttf",
    "C:/Windows/Fonts/seguiemj.ttf",
]
# bitmap emoji fonts only load at their native strike sizes
_EMOJI_SIZES = (160, 109, 136, 96, 64, 48)
_EMOJI_RE = re.compile("([\U0001F000-\U0001FAFF\u2600-\u27BF]\uFE0F?)")


def _emoji_font(path: str | Path | None) -> ImageFont.FreeTypeFont | None:
    candidates = [path] if path else EMOJI_FONTS
    for cand in candidates:
        if not Path(cand).exists():
            continue
        for size in _EMOJI_SIZES:
            try:
                return ImageFont.truetype(str(cand), size)
            except OSError:
                continue
    if path:
        raise OSError(f"Could not load emoji font: {path}")
    warnings.warn("No color emoji font found; emoji are left out of the GIF.",
                  stacklevel=3)
    return None


def _emoji_image(char: str, font: ImageFont.FreeTypeFont, px: int) -> Image.Image:
    left, top, right, bottom = font.getbbox(char)
    img = Image.new("RGBA", (right - left, bottom - top), (0, 0, 0, 0))
    ImageDraw.Draw(img).text((-left, -top), char, font=font, embedded_color=True)
    img = img.crop(img.getbbox() or (0, 0, img.width, img.height))
    scale = px / max(img.size)
    return img.resize((max(1, round(img.width * scale)),
                       max(1, round(img.height * scale))), Image.LANCZOS)


def _draw_line(
    canvas: Image.Image, xy: tuple[int, int], line: str,
    text_font: ImageFont.FreeTypeFont, emoji_font: ImageFont.FreeTypeFont | None,
    color: str,
) -> None:
    draw = ImageDraw.Draw(canvas)
    x, y = xy
    px = round(text_font.size * 1.1)
    for part in _EMOJI_RE.split(line):
        if not part:
            continue
        if _EMOJI_RE.fullmatch(part):
            if emoji_font is None:
                continue
            em = _emoji_image(part, emoji_font, px)
            canvas.paste(em, (x, y - em.height // 2), em)
            x += em.width + text_font.size // 3
        else:
            draw.text((x, y), part, font=text_font, fill=color, anchor="lm")
            x += round(draw.textlength(part, font=text_font))


def _wrap(text: str, font: ImageFont.FreeTypeFont, avail: float) -> list[str]:
    lines: list[str] = []
    cur = ""
    for word in text.split():
        trial = f"{cur} {word}".strip()
        if cur and font.getlength(trial) > avail:
            lines.append(cur)
            cur = word
        else:
            cur = trial
    return lines + [cur] if cur else lines


def _layout(
    msgs: list[str], width: int, height: int, font_path: str
) -> tuple[ImageFont.FreeTypeFont, list[tuple[str, list[str]]], int, float, float]:
    """Wrap each message to the frame width, shrinking the font until the
    whole introduction fits. Returns font, (emoji, lines) blocks, text indent,
    line height, and the y of the first line."""
    for size in range(max(10, height // 22), 7, -1):
        font = ImageFont.truetype(font_path, size)
        indent = round(size * 1.1) + round(size * 0.7)
        avail = width * 0.9 - indent
        blocks = []
        for msg in msgs:
            m = _EMOJI_RE.match(msg)
            emoji, text = (m.group(1), msg[m.end():].strip()) if m else ("", msg)
            blocks.append((emoji, _wrap(text, font, avail)))
        line_h = size * 1.4
        gap = size * 1.6
        total = sum(len(ls) for _, ls in blocks) * line_h + (len(blocks) - 1) * gap
        fits = all(font.getlength(ln) <= avail for _, ls in blocks for ln in ls)
        if fits and total <= height * 0.9:
            break
    return font, blocks, indent, line_h, (height - total) / 2 + line_h / 2


def who_am_i_gif(
    name: str,
    likes: str,
    learn: str,
    work: str,
    collab: str,
    connect: bool = True,
    output: str | Path = "intro.gif",
    width: int = 800,
    height: int = 400,
    frame_duration: float = 1.5,
    first_duration: float = 1,
    last_duration: float = 4,
    emoji_font: str | Path | None = None,
) -> Path:
    """Render the `who_am_i()` lines as a terminal style GIF.

    Each frame adds one line. Emoji come from the system color emoji font
    (Apple Color Emoji, Noto Color Emoji, or Segoe UI Emoji).

    Parameters
    ----------
    name, likes, learn, work, collab : str
        Passed to the introduction lines (see `who_am_i()`).
    connect : bool
        Add the "Want to connect?" line.
    output : str or pathlib.Path
        Path for the `.gif` file.
    width, height : int
        GIF size in pixels.
    frame_duration : float
        Seconds to show each middle frame.
    first_duration : float
        Seconds to hold the first frame.
    last_duration : float
        Seconds to hold the last frame.
    emoji_font : str or pathlib.Path, optional
        A color emoji font file to use instead of the system one.

    Returns
    -------
    pathlib.Path
        The output path.

    Warns
    -----
    UserWarning
        If no emoji font is found; emoji are left out.
    """
    from matplotlib import font_manager

    msgs = _messages(name, likes, learn, work, collab, connect)
    n = len(msgs)
    bg, fg = "#1e1e1e", "#d4d4d4"
    font, blocks, indent, line_h, y0 = _layout(
        msgs, width, height, font_manager.findfont("DejaVu Sans Mono")
    )
    efont = _emoji_font(emoji_font)
    x0 = round(width * 0.05)
    # fixed y position for every line, so earlier lines never move
    positions = []
    y = y0
    for _, lines in blocks:
        positions.append([round(y + k * line_h) for k in range(len(lines))])
        y += len(lines) * line_h + font.size * 1.6
    with tempfile.TemporaryDirectory(prefix="who-am-i-frames-") as frame_dir:
        for i in range(1, n + 1):
            canvas = Image.new("RGB", (width, height), bg)
            for (emoji, lines), ys in zip(blocks[:i], positions):
                if emoji:
                    _draw_line(canvas, (x0, ys[0]), emoji, font, efont, fg)
                for line, yy in zip(lines, ys):
                    _draw_line(canvas, (x0 + indent, yy), line, font, efont, fg)
            canvas.save(Path(frame_dir) / f"{i:04d}.png")
        return make_gif(
            frame_dir, output, width, height,
            first_duration=first_duration,
            frame_duration=frame_duration,
            last_duration=last_duration,
        )
