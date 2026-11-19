"""Markdown and HTML badges for a profile README."""

from __future__ import annotations

_BADGES = {
    "details": "profile-details",
    "commit_lang": "most-commit-language",
    "ptime": "productive-time",
    "repo_lang": "repos-per-language",
    "stats": "stats",
}
_THEMES = {"default": "default", "dark": "github_dark", "light": "github_light"}
_CARD_URL = "http://github-profile-summary-cards.vercel.app/api/cards"


def gh_badges(username: str, badge: str | list[str], theme: str = "default") -> str:
    """Markdown image links for GitHub profile summary cards.

    Cards come from [github-profile-summary-cards](https://github-profile-summary-cards.vercel.app/demo.html).

    Parameters
    ----------
    username : str
        GitHub username.
    badge : str or list of str
        One or more of `"details"`, `"commit_lang"`, `"ptime"`, `"repo_lang"`,
        or `"stats"`.
    theme : str
        `"default"`, `"dark"`, or `"light"`.

    Returns
    -------
    str
        Markdown, one badge per line.

    Raises
    ------
    ValueError
        If a badge or theme name is unknown.

    Examples
    --------
    >>> print(gh_badges("mjfrigaard", ["details", "stats"], theme="dark"))
    ![](http://github-profile-summary-cards.vercel.app/api/cards/profile-details?username=mjfrigaard&theme=github_dark)
    ![](...stats?username=mjfrigaard&theme=github_dark)
    """
    badges = [badge] if isinstance(badge, str) else list(badge)
    bad = [b for b in badges if b not in _BADGES]
    if bad:
        raise ValueError(f"Unknown badge(s) {bad}; choose from {list(_BADGES)}.")
    if theme not in _THEMES:
        raise ValueError(f"Unknown theme {theme!r}; choose from {list(_THEMES)}.")
    return "\n".join(
        f"![]({_CARD_URL}/{_BADGES[b]}?username={username}&theme={_THEMES[theme]})"
        for b in badges
    )


def so_rep(username: str, user_id: str | int) -> str:
    """HTML for a Stack Overflow reputation badge.

    Parameters
    ----------
    username : str
        Stack Overflow username (the slug in your profile URL).
    user_id : str or int
        Stack Overflow user ID.

    Returns
    -------
    str
        An `<a>` tag wrapping the badge image.

    Examples
    --------
    >>> print(so_rep("martin-frigaard", 4926446))  # doctest: +ELLIPSIS
    <a href='https://stackoverflow.com/users/4926446/martin-frigaard' target='_blank'>
    ...
    """
    return (
        f"<a href='https://stackoverflow.com/users/{user_id}/{username}' "
        "target='_blank'>\n"
        "<img alt='StackOverflow'\n"
        f"src='https://stackoverflow-badge.vercel.app/?userID={user_id}' />\n"
        "</a>"
    )
