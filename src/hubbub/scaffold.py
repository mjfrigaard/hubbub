"""Scaffold a profile README build script and a GitHub Action."""

from __future__ import annotations

from importlib.resources import files
from pathlib import Path


def _write_template(template: str, out: Path, subs: dict[str, str],
                    overwrite: bool) -> Path:
    if out.exists() and not overwrite:
        raise FileExistsError(
            f"{out} already exists. Use overwrite=True to replace it."
        )
    content = files("hubbub").joinpath("templates", template).read_text("utf-8")
    for key, val in subs.items():
        content = content.replace("{{" + key + "}}", val)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(content, encoding="utf-8")
    print(f"✔ Wrote {out}")
    return out


def use_profile_readme(
    name: str = "Your Name",
    likes: str = "your interests",
    learn: str = "what you're learning",
    work: str = "what you're working on",
    collab: str = "what you'd like to collaborate on",
    username: str = "your-github-username",
    path: str | Path = ".",
    overwrite: bool = False,
) -> Path:
    """Write a starter `build_readme.py` for your profile repo.

    The script calls `who_am_i()` and `gh_badges()` and writes `README.md`.
    Optional blocks for `who_am_i_gif()` and `so_rep()` are included.

    Parameters
    ----------
    name, likes, learn, work, collab : str
        Values filled into the `who_am_i()` call.
    username : str
        GitHub username filled into the `gh_badges()` call.
    path : str or pathlib.Path
        Directory to write into.
    overwrite : bool
        Replace an existing `build_readme.py`.

    Returns
    -------
    pathlib.Path
        Path to the new file.

    Raises
    ------
    FileExistsError
        If the file exists and `overwrite` is `False`.
    """
    out = _write_template(
        "build_readme.py", Path(path) / "build_readme.py",
        {"name": name, "likes": likes, "learn": learn, "work": work,
         "collab": collab, "username": username},
        overwrite,
    )
    print("ℹ Edit the placeholders, then run `python build_readme.py`.")
    return out


def use_profile_readme_action(
    cron: str = "0 6 * * 0",
    repo: str = "mjfrigaard/hubbub",
    path: str | Path = ".",
    overwrite: bool = False,
) -> Path:
    """Write a GitHub Action that rebuilds the profile README on a schedule.

    Creates `.github/workflows/profile-readme.yaml`. The workflow installs
    hubbub with uv, runs `build_readme.py`, and commits `README.md` and any
    GIFs that changed. It also runs on manual dispatch.

    Parameters
    ----------
    cron : str
        Cron schedule. The default, `"0 6 * * 0"`, is Sundays at 06:00 UTC.
    repo : str
        GitHub `owner/name` to install hubbub from.
    path : str or pathlib.Path
        Repo root to write into.
    overwrite : bool
        Replace an existing workflow file.

    Returns
    -------
    pathlib.Path
        Path to the workflow file.

    Raises
    ------
    FileExistsError
        If the file exists and `overwrite` is `False`.
    """
    out = _write_template(
        "profile-readme-action.yaml",
        Path(path) / ".github" / "workflows" / "profile-readme.yaml",
        {"cron": cron, "repo": repo},
        overwrite,
    )
    print(f"ℹ Action runs on cron '{cron}' and on manual dispatch.")
    return out
