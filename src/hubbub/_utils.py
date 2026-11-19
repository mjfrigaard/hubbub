"""Shared helpers for plotting functions."""

from __future__ import annotations

from datetime import date
from typing import Any

import polars as pl


def _to_date(x: Any) -> date:
    return date.fromisoformat(x[:10]) if isinstance(x, str) else x


def filter_commits(
    commits: pl.DataFrame,
    repo: str | list[str] | None = None,
    date_begin: str | date | None = None,
    date_end: str | date | None = None,
) -> pl.DataFrame:
    """Subset by repo and date bounds; raise if nothing is left."""
    if repo is not None:
        repos = [repo] if isinstance(repo, str) else list(repo)
        commits = commits.filter(pl.col("repo").is_in(repos))
    if date_begin is not None:
        commits = commits.filter(pl.col("date") >= _to_date(date_begin))
    if date_end is not None:
        commits = commits.filter(pl.col("date") <= _to_date(date_end))
    if commits.height == 0:
        raise ValueError("No commits after filtering.")
    return commits


def default_title(repo: str | list[str] | None, title: str | None) -> str:
    if title is not None:
        return title
    if repo is None:
        return "All repos"
    return repo if isinstance(repo, str) else ", ".join(repo)


def per_day(commits: pl.DataFrame) -> pl.DataFrame:
    return commits.group_by("date").agg(commits=pl.len()).sort("date")
