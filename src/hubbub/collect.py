"""Collect activity from a GitHub user's account via the REST API."""

from __future__ import annotations

import json
import os
import re
import sys
import urllib.error
import urllib.request
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlencode

import polars as pl

API = "https://api.github.com"
VALID_TYPES = ("commits", "stars", "issues", "prs")
WEEKDAYS = [
    "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday",
]

COMMIT_SCHEMA = {
    "repo": pl.String,
    "sha": pl.String,
    "timestamp": pl.Datetime("us", "UTC"),
    "author_name": pl.String,
    "author_email": pl.String,
    "message": pl.String,
}
STAR_SCHEMA = {
    "repo": pl.String,
    "stargazers_count": pl.Int64,
    "forks_count": pl.Int64,
    "watchers_count": pl.Int64,
    "language": pl.String,
    "description": pl.String,
    "created_at": pl.Datetime("us", "UTC"),
    "updated_at": pl.Datetime("us", "UTC"),
}
SEARCH_SCHEMA = {
    "repo": pl.String,
    "number": pl.Int64,
    "title": pl.String,
    "state": pl.String,
    "created_at": pl.Datetime("us", "UTC"),
    "closed_at": pl.Datetime("us", "UTC"),
    "url": pl.String,
}


def _log(msg: str) -> None:
    print(msg, file=sys.stderr)


def _get(path: str, params: dict[str, Any], limit: float = float("inf")) -> Any:
    """GET with Link header pagination. Lists are concatenated; search
    responses (dicts with ``items``) have their items concatenated."""
    token = os.environ.get("GITHUB_PAT") or os.environ.get("GITHUB_TOKEN")
    headers = {"Accept": "application/vnd.github+json", "User-Agent": "hubbub"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    url: str | None = f"{API}{path}?{urlencode(params)}"
    out: list[Any] = []
    is_search = False
    while url and len(out) < limit:
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req) as resp:
            page = json.load(resp)
            link = resp.headers.get("Link", "")
        if isinstance(page, dict):
            is_search = True
            page = page.get("items", [])
        out.extend(page)
        m = re.search(r'<([^>]+)>;\s*rel="next"', link)
        url = m.group(1) if m else None
    if limit != float("inf"):
        out = out[: int(limit)]
    return {"items": out} if is_search else out


def _iso(x: str | date | datetime | None) -> str | None:
    if x is None:
        return None
    if isinstance(x, str):
        x = datetime.fromisoformat(x)
    if not isinstance(x, datetime):
        x = datetime(x.year, x.month, x.day)
    if x.tzinfo is None:
        x = x.replace(tzinfo=timezone.utc)
    return x.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _local_tz() -> str:
    tz = os.environ.get("TZ")
    if tz:
        return tz
    try:
        target = str(Path("/etc/localtime").resolve())
        if "zoneinfo/" in target:
            return target.split("zoneinfo/", 1)[1]
    except OSError:
        pass
    return "UTC"


def _ts(col: str) -> pl.Expr:
    return pl.col(col).str.to_datetime(
        "%Y-%m-%dT%H:%M:%SZ", time_zone="UTC", strict=False
    )


def add_time_columns(df: pl.DataFrame, tz: str | None = None) -> pl.DataFrame:
    """Add local time columns to a commits DataFrame.

    Converts the UTC `timestamp` column to `tz` and adds `local_ts`, `date`,
    `hour`, `weekday` (a Monday to Sunday enum), and `year`.
    `collect_git_commits()` calls this for you; use it on commits loaded
    from a file.

    Parameters
    ----------
    df : polars.DataFrame
        Must have a time zone aware `timestamp` column.
    tz : str, optional
        IANA time zone name, such as `"America/Phoenix"`. Defaults to the
        system zone.

    Returns
    -------
    polars.DataFrame
    """
    tz = tz or _local_tz()
    return (
        df.with_columns(local_ts=pl.col("timestamp").dt.convert_time_zone(tz))
        .with_columns(
            date=pl.col("local_ts").dt.date(),
            hour=pl.col("local_ts").dt.hour().cast(pl.Int64),
            weekday=pl.col("local_ts").dt.strftime("%A").cast(pl.Enum(WEEKDAYS)),
            year=pl.col("local_ts").dt.year().cast(pl.Int64),
        )
    )


def _collect_commits(
    repos: list[dict[str, Any]],
    user: str,
    emails: list[str] | None,
    since: Any,
    until: Any,
    tz: str | None,
) -> pl.DataFrame:
    names = [r["name"] for r in repos]
    _log(f"Found {len(names)} repos for '{user}'.")
    rows: list[dict[str, Any]] = []
    for name in names:
        _log(f"Fetching {name} ...")
        for author in emails or [None]:
            params: dict[str, Any] = {"per_page": 100}
            if author:
                params["author"] = author
            if since is not None:
                params["since"] = _iso(since)
            if until is not None:
                params["until"] = _iso(until)
            try:
                commits = _get(f"/repos/{user}/{name}/commits", params)
            except urllib.error.URLError as e:
                _log(f"  skip {name} ({e})")
                continue
            for c in commits:
                a = (c.get("commit") or {}).get("author") or {}
                rows.append({
                    "repo": name,
                    "sha": c["sha"],
                    "timestamp": a.get("date"),
                    "author_name": a.get("name"),
                    "author_email": a.get("email"),
                    "message": (c.get("commit") or {}).get("message"),
                })
    if not rows:
        _log("Warning: no commits returned.")
        return pl.DataFrame(schema=COMMIT_SCHEMA)

    df = pl.DataFrame(rows, schema={**COMMIT_SCHEMA, "timestamp": pl.String})
    df = df.with_columns(timestamp=_ts("timestamp"))
    if emails:
        lower = [e.lower() for e in emails]
        df = df.filter(pl.col("author_email").str.to_lowercase().is_in(lower))
    df = df.unique(subset=["repo", "sha"], keep="first", maintain_order=True)
    return add_time_columns(df, tz).sort("timestamp")


def _collect_stars(repos: list[dict[str, Any]]) -> pl.DataFrame:
    if not repos:
        return pl.DataFrame(schema=STAR_SCHEMA)
    rows = [
        {
            "repo": r["name"],
            "stargazers_count": r.get("stargazers_count") or 0,
            "forks_count": r.get("forks_count") or 0,
            "watchers_count": r.get("watchers_count") or 0,
            "language": r.get("language"),
            "description": r.get("description"),
            "created_at": r.get("created_at"),
            "updated_at": r.get("updated_at"),
        }
        for r in repos
    ]
    schema = {**STAR_SCHEMA, "created_at": pl.String, "updated_at": pl.String}
    return (
        pl.DataFrame(rows, schema=schema)
        .with_columns(created_at=_ts("created_at"), updated_at=_ts("updated_at"))
        .sort("stargazers_count", descending=True, maintain_order=True)
    )


def _collect_search(user: str, kind: str, since: Any, until: Any) -> pl.DataFrame:
    q = f"author:{user} type:{kind}"
    if since is not None:
        q += f" created:>={str(since)[:10]}"
    if until is not None:
        q += f" created:<={str(until)[:10]}"
    try:
        items = _get("/search/issues", {"q": q, "per_page": 100}, limit=1000)["items"]
    except urllib.error.URLError as e:
        _log(f"  skip {kind} search ({e})")
        items = []
    if not items:
        return pl.DataFrame(schema=SEARCH_SCHEMA)
    rows = [
        {
            "repo": (x.get("repository_url") or "").split("/repos/", 1)[-1] or None,
            "number": x.get("number"),
            "title": x.get("title"),
            "state": x.get("state"),
            "created_at": x.get("created_at"),
            "closed_at": x.get("closed_at"),
            "url": x.get("html_url"),
        }
        for x in items
    ]
    schema = {**SEARCH_SCHEMA, "created_at": pl.String, "closed_at": pl.String}
    return (
        pl.DataFrame(rows, schema=schema)
        .with_columns(created_at=_ts("created_at"), closed_at=_ts("closed_at"))
        .sort("created_at", descending=True)
    )


def collect_git_commits(
    user: str,
    emails: str | list[str] | None = None,
    since: str | date | datetime | None = None,
    until: str | date | datetime | None = None,
    include_forks: bool = False,
    include: str | list[str] = "commits",
    tz: str | None = None,
) -> pl.DataFrame | dict[str, pl.DataFrame]:
    """Collect commits, stars, issues, and pull requests for a GitHub user.

    Calls the GitHub REST API. Set `GITHUB_PAT` or `GITHUB_TOKEN` first:
    unauthenticated calls are limited to 60 requests an hour, and the search
    endpoint (issues and PRs) returns at most 1000 results.

    Parameters
    ----------
    user : str
        GitHub username.
    emails : str or list of str, optional
        Author emails to keep (case insensitive). Applies to commits only.
    since, until : str, datetime.date, or datetime.datetime, optional
        Bounds. API filters for commits; `created_at` bounds for issues and PRs.
    include_forks : bool
        Include forked repos (affects commits and stars).
    include : str or list of str
        Any of `"commits"`, `"stars"`, `"issues"`, `"prs"`.
    tz : str, optional
        Time zone for the local time columns. Defaults to the system zone.

    Returns
    -------
    polars.DataFrame or dict of polars.DataFrame
        With the default `include="commits"`, one row per commit with columns
        `repo`, `sha`, `timestamp`, `author_name`, `author_email`, `message`,
        `local_ts`, `date`, `hour`, `weekday`, and `year`. Otherwise a dict keyed
        by type:

        - `stars`: the user's own repos with `stargazers_count`, `forks_count`,
          `watchers_count`, `language`, `description`, `created_at`, `updated_at`.
        - `issues`, `prs`: items authored by the user across GitHub, with
          `repo` (owner/name), `number`, `title`, `state`, `created_at`,
          `closed_at`, `url`.

    Examples
    --------
    >>> commits = collect_git_commits(
    ...     "mjfrigaard", emails="you@example.com"
    ... )  # doctest: +SKIP
    >>> stats = collect_git_commits(
    ...     "mjfrigaard", include=["commits", "stars", "issues", "prs"]
    ... )  # doctest: +SKIP
    """
    types = [include] if isinstance(include, str) else list(include)
    bad = [t for t in types if t not in VALID_TYPES]
    if bad:
        raise ValueError(f"Unknown include type(s) {bad}; choose from {VALID_TYPES}.")
    email_list = [emails] if isinstance(emails, str) else emails

    repos: list[dict[str, Any]] = []
    if {"commits", "stars"} & set(types):
        repos = _get(f"/users/{user}/repos", {"type": "owner", "per_page": 100})
        if not include_forks:
            repos = [r for r in repos if not r.get("fork")]

    result: dict[str, pl.DataFrame] = {}
    if "commits" in types:
        result["commits"] = _collect_commits(
            repos, user, email_list, since, until, tz
        )
    if "stars" in types:
        result["stars"] = _collect_stars(repos)
    if "issues" in types:
        result["issues"] = _collect_search(user, "issue", since, until)
    if "prs" in types:
        result["prs"] = _collect_search(user, "pr", since, until)

    if types == ["commits"]:
        return result["commits"]
    return result
