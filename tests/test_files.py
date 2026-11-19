import pytest
from PIL import Image

from hubbub import make_gif, use_profile_readme, use_profile_readme_action, who_am_i_gif


def _frames(d, n):
    for i in range(n):
        Image.new("RGB", (20, 10), (i * 40, 0, 0)).save(d / f"{i:04d}.png")


def test_make_gif(tmp_path):
    _frames(tmp_path, 4)
    out = make_gif(tmp_path, tmp_path / "a.gif", 40, 20, 1, 0.5, 3)
    with Image.open(out) as im:
        assert im.size == (40, 20)
        assert im.n_frames == 4
        durs = []
        for i in range(im.n_frames):
            im.seek(i)
            durs.append(im.info["duration"])
    assert durs == [1000, 500, 500, 3000]


def test_make_gif_single_frame(tmp_path):
    _frames(tmp_path, 1)
    out = make_gif(tmp_path, tmp_path / "a.gif", 20, 10, last_duration=2)
    with Image.open(out) as im:
        assert im.info["duration"] == 2000


def test_make_gif_no_frames(tmp_path):
    with pytest.raises(FileNotFoundError):
        make_gif(tmp_path, tmp_path / "a.gif", 20, 10)


def test_who_am_i_gif(tmp_path):
    out = who_am_i_gif("M", "a", "b", "c", "d", connect=False,
                       output=tmp_path / "intro.gif", width=200, height=100)
    with Image.open(out) as im:
        assert im.n_frames == 5
        assert im.size == (200, 100)


def test_use_profile_readme(tmp_path):
    out = use_profile_readme(name="Martin", username="mjfrigaard", path=tmp_path)
    text = out.read_text()
    assert 'name="Martin"' in text and 'username="mjfrigaard"' in text
    assert "{{" not in text
    with pytest.raises(FileExistsError):
        use_profile_readme(path=tmp_path)
    use_profile_readme(path=tmp_path, overwrite=True)


def test_build_readme_runs(tmp_path, monkeypatch):
    use_profile_readme(name="Martin", username="mjfrigaard", path=tmp_path)
    monkeypatch.chdir(tmp_path)
    exec(compile((tmp_path / "build_readme.py").read_text(), "b", "exec"), {})
    md = (tmp_path / "README.md").read_text()
    assert "Hi, my name is Martin." in md
    assert "username=mjfrigaard" in md


def test_use_profile_readme_action(tmp_path):
    out = use_profile_readme_action(cron="0 6 * * 1", repo="me/pkg", path=tmp_path)
    assert out == tmp_path / ".github" / "workflows" / "profile-readme.yaml"
    text = out.read_text()
    assert '"0 6 * * 1"' in text and "github.com/me/pkg" in text
    with pytest.raises(FileExistsError):
        use_profile_readme_action(path=tmp_path)


def test_who_am_i_gif_bad_emoji_font(tmp_path):
    with pytest.raises(OSError, match="emoji font"):
        who_am_i_gif("M", "a", "b", "c", "d", output=tmp_path / "x.gif",
                     emoji_font=tmp_path / "missing.ttf")


def test_who_am_i_gif_no_emoji_font_warns(tmp_path, monkeypatch):
    monkeypatch.setattr("hubbub.intro.EMOJI_FONTS", [])
    with pytest.warns(UserWarning, match="No color emoji font"):
        out = who_am_i_gif("M", "a", "b", "c", "d", output=tmp_path / "x.gif",
                           width=200, height=100)
    assert out.exists()


def test_who_am_i_gif_wraps_long_lines(tmp_path):
    from hubbub.intro import _layout, _messages

    msgs = _messages("M", "x " * 60, "b", "c", "d", True)
    font, blocks, indent, _, y0 = _layout(msgs, 400, 300, _font_path())
    assert len(blocks[1][1]) > 1
    avail = 400 * 0.9 - indent
    assert all(font.getlength(ln) <= avail for _, ls in blocks for ln in ls)
    assert y0 > 0


def _font_path():
    from matplotlib import font_manager

    return font_manager.findfont("DejaVu Sans Mono")
