import pytest

from hubbub import gh_badges, so_rep, who_am_i

ARGS = dict(name="Martin", likes="a", learn="b", work="c", collab="d")


def test_gh_badges_single():
    assert gh_badges("mjfrigaard", "stats", "dark") == (
        "![](http://github-profile-summary-cards.vercel.app/api/cards/stats"
        "?username=mjfrigaard&theme=github_dark)"
    )


def test_gh_badges_multiple():
    out = gh_badges("u", ["details", "ptime"], "light").splitlines()
    assert len(out) == 2
    assert "profile-details" in out[0] and "productive-time" in out[1]
    assert all("theme=github_light" in line for line in out)


def test_gh_badges_bad():
    with pytest.raises(ValueError):
        gh_badges("u", "nope")
    with pytest.raises(ValueError):
        gh_badges("u", "stats", "neon")


def test_so_rep():
    out = so_rep("martin-frigaard", 4926446)
    assert "users/4926446/martin-frigaard" in out
    assert "userID=4926446" in out


def test_who_am_i_prints(capsys):
    lines = who_am_i(**ARGS, delay=0)
    out = capsys.readouterr().out.splitlines()
    assert out == lines and len(lines) == 6
    assert lines[0].endswith("Hi, my name is Martin.")


def test_who_am_i_no_connect_quiet(capsys):
    lines = who_am_i(**ARGS, connect=False, delay=0, quiet=True)
    assert len(lines) == 5
    assert capsys.readouterr().out == ""


def test_who_am_i_sleeps(monkeypatch):
    calls = []
    monkeypatch.setattr("hubbub.intro.time.sleep", calls.append)
    who_am_i(**ARGS, quiet=True)
    assert calls == [1.5] * 5
