"""Matplotlib charts of commit activity from collect_git_commits()."""

from __future__ import annotations

import calendar
from datetime import date, timedelta
from typing import Any

import matplotlib.pyplot as plt
import numpy as np
import polars as pl
from matplotlib.colors import LinearSegmentedColormap, Normalize
from matplotlib.figure import Figure

from ._utils import default_title, filter_commits, per_day

WEEKDAYS = [
    "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday",
]


def calendar_heatmap_plot(
    commits: pl.DataFrame,
    repo: str | list[str] | None = None,
    date_begin: str | date | None = None,
    date_end: str | date | None = None,
    title: str | None = None,
    week_start: str = "Sunday",
    low: str = "#ebedf0",
    high: str = "#216e39",
) -> Figure:
    """GitHub style calendar heatmap of daily commits, one row per year.

    Parameters
    ----------
    commits : polars.DataFrame
        Commits from `collect_git_commits()`.
    repo : str or list of str, optional
        Repo name(s) to keep. `None` uses all repos.
    date_begin, date_end : str or datetime.date, optional
        Inclusive date bounds (`"YYYY-MM-DD"` strings work).
    title : str, optional
        Plot title. Defaults to the repo name(s) or `"All repos"`.
    week_start : str
        `"Sunday"` (GitHub's layout) or `"Monday"` (ISO weeks).
    low, high : str
        Colors for zero commits and the busiest day.

    Returns
    -------
    matplotlib.figure.Figure
    """
    if week_start not in ("Sunday", "Monday"):
        raise ValueError('week_start must be "Sunday" or "Monday".')
    commits = filter_commits(commits, repo, date_begin, date_end)
    title = default_title(repo, title)
    counts = dict(per_day(commits).iter_rows())
    start, end = min(counts), max(counts)

    days = WEEKDAYS if week_start == "Monday" else WEEKDAYS[-1:] + WEEKDAYS[:-1]
    wfmt = "%W" if week_start == "Monday" else "%U"
    years = list(range(start.year, end.year + 1))
    cmap = LinearSegmentedColormap.from_list("gh", [low, high]).with_extremes(
        bad="white"
    )
    norm = Normalize(vmin=0, vmax=max(counts.values()))

    fig, axes = plt.subplots(
        len(years), 1, figsize=(11, 1.8 * len(years) + 0.6), squeeze=False
    )
    total = 0
    for ax, yr in zip(axes[:, 0], years):
        grid = np.full((7, 54), np.nan)
        d = max(start, date(yr, 1, 1))
        last = min(end, date(yr, 12, 31))
        while d <= last:
            row = d.weekday() if week_start == "Monday" else (d.weekday() + 1) % 7
            n = counts.get(d, 0)
            grid[row, int(d.strftime(wfmt))] = n
            total += n
            d += timedelta(days=1)
        ax.pcolormesh(
            np.ma.masked_invalid(grid), cmap=cmap, norm=norm,
            edgecolors="white", linewidth=0.5,
        )
        ax.invert_yaxis()
        ax.set_aspect("equal")
        ax.set_yticks(np.arange(7) + 0.5, days, fontsize=7)
        ax.set_xticks(
            [int(date(yr, m, 1).strftime(wfmt)) + 0.5 for m in range(1, 13)],
            calendar.month_abbr[1:], fontsize=8,
        )
        ax.set_ylabel(str(yr), rotation=0, ha="right", va="center", fontweight="bold")
        ax.tick_params(length=0)
        for s in ax.spines.values():
            s.set_visible(False)
    fig.colorbar(
        plt.cm.ScalarMappable(norm=norm, cmap=cmap), ax=axes[:, 0].tolist(),
        label="commits", shrink=0.6,
    )
    fig.suptitle(f"{title} — {total} commits", x=0.02, ha="left")
    return fig


def cumulative_line_plot(
    commits: pl.DataFrame,
    repo: str | list[str] | None = None,
    date_begin: str | date | None = None,
    date_end: str | date | None = None,
    top_n: int = 10,
    show_other: bool = True,
    title: str | None = None,
) -> Figure:
    """Cumulative commits over time, one step line per repo.

    Parameters
    ----------
    commits : polars.DataFrame
        Commits from `collect_git_commits()`.
    repo : str or list of str, optional
        Repo name(s) to keep. `None` uses all repos.
    date_begin, date_end : str or datetime.date, optional
        Inclusive date bounds (`"YYYY-MM-DD"` strings work).
    top_n : int
        Number of most active repos drawn as their own lines.
    show_other : bool
        Roll the remaining repos into an `"Other"` line.
    title : str, optional
        Plot title. Defaults to the repo name(s) or `"All repos"`.

    Returns
    -------
    matplotlib.figure.Figure
    """
    commits = filter_commits(commits, repo, date_begin, date_end)
    title = default_title(repo, title)
    totals = commits.group_by("repo").agg(n=pl.len()).sort(
        ["n", "repo"], descending=[True, False]
    )
    top = totals["repo"].head(top_n).to_list()
    commits = commits.with_columns(
        repo_group=pl.when(pl.col("repo").is_in(top))
        .then(pl.col("repo"))
        .otherwise(pl.lit("Other"))
    )
    if not show_other:
        commits = commits.filter(pl.col("repo_group") != "Other")

    daily = (
        commits.group_by("repo_group", "date").agg(commits=pl.len())
        .sort("repo_group", "date")
        .with_columns(cumulative=pl.col("commits").cum_sum().over("repo_group"))
    )
    order = (
        daily.group_by("repo_group").agg(total=pl.col("cumulative").max())
        .sort(["total", "repo_group"], descending=[True, False])["repo_group"]
        .to_list()
    )
    if "Other" in order:
        order = [g for g in order if g != "Other"] + ["Other"]

    fig, ax = plt.subplots(figsize=(10, 5))
    for g in order:
        sub = daily.filter(pl.col("repo_group") == g)
        ax.step(sub["date"].to_list(), sub["cumulative"].to_list(),
                where="post", linewidth=1.2, label=g)
    ax.set_title(f"{title} — cumulative commits", loc="left")
    ax.set_ylabel("Cumulative commits")
    ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda v, _: f"{v:,.0f}"))
    ax.grid(alpha=0.3)
    ax.legend(title="repo", loc="center left", bbox_to_anchor=(1, 0.5), frameon=False)
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    fig.tight_layout()
    return fig


def punchcard_plot(
    commits: pl.DataFrame,
    repo: str | list[str] | None = None,
    date_begin: str | date | None = None,
    date_end: str | date | None = None,
    title: str | None = None,
    point_color: str = "#1f6feb",
) -> Figure:
    """Punchcard of commits by weekday and hour of day.

    Circle area is proportional to the number of commits.

    Parameters
    ----------
    commits : polars.DataFrame
        Commits from `collect_git_commits()`.
    repo : str or list of str, optional
        Repo name(s) to keep. `None` uses all repos.
    date_begin, date_end : str or datetime.date, optional
        Inclusive date bounds (`"YYYY-MM-DD"` strings work).
    title : str, optional
        Plot title. Defaults to the repo name(s) or `"All repos"`.
    point_color : str
        Fill color for the circles.

    Returns
    -------
    matplotlib.figure.Figure
    """
    commits = filter_commits(commits, repo, date_begin, date_end)
    title = default_title(repo, title)
    cells = (
        commits.with_columns(weekday=pl.col("weekday").cast(pl.String))
        .group_by("weekday", "hour").agg(commits=pl.len())
    )
    cells = cells.filter(pl.col("commits") > 0)
    rows = [WEEKDAYS.index(w) for w in cells["weekday"]]
    n = cells["commits"].to_numpy()

    fig, ax = plt.subplots(figsize=(11, 4))
    ax.scatter(
        cells["hour"].to_list(), rows, s=n / n.max() * 500,
        color=point_color, edgecolors="white", linewidths=0.6,
    )
    ax.set_xlim(-0.5, 23.5)
    ax.set_ylim(6.6, -0.6)
    ax.set_yticks(range(7), WEEKDAYS)
    ax.set_xticks(range(0, 24, 2), [f"{h:02d}:00" for h in range(0, 24, 2)],
                  fontsize=9)
    ax.grid(color="0.92")
    ax.set_axisbelow(True)
    for s in ax.spines.values():
        s.set_visible(False)
    ax.set_title(f"{title} — {int(n.sum())} commits", loc="left")
    fig.tight_layout()
    return fig


def _axis_values(df: pl.DataFrame, var: str) -> tuple[Any, list[str] | None]:
    """Numeric (or date) positions for an axis plus category labels if any."""
    if var == "date":
        return df["date"].to_list(), None
    if var == "time":
        ts = df["local_ts"]
        return (ts.dt.hour() + ts.dt.minute() / 60).to_numpy(), None
    if var == "weekday":
        labels = [w for w in WEEKDAYS if w in set(df["weekday"].cast(pl.String))]
        codes = [labels.index(w) for w in df["weekday"].cast(pl.String)]
    else:
        labels = sorted(df["repo"].unique().to_list())
        codes = [labels.index(r) for r in df["repo"]]
    return np.asarray(codes, dtype=float), labels


def _kde(values: np.ndarray, grid: np.ndarray) -> np.ndarray:
    values = values[~np.isnan(values)]
    bw = 1.06 * values.std() * len(values) ** -0.2 or 1.0
    z = (grid[:, None] - values[None, :]) / bw
    return np.exp(-0.5 * z**2).sum(axis=1) / (len(values) * bw * np.sqrt(2 * np.pi))


def scatter_density_plot(
    commits: pl.DataFrame,
    repo: str | list[str] | None = None,
    date_begin: str | date | None = None,
    date_end: str | date | None = None,
    x: str = "date",
    y: str = "time",
    plot_type: str = "matplotlib",
    top_n: int = 15,
    title: str | None = None,
    seed: int | None = 1,
) -> Any:
    """Scatter of commits across two of repo, time, date, and weekday.

    Categorical axes (repo, weekday) are jittered so stacked commits stay
    visible.

    Parameters
    ----------
    commits : polars.DataFrame
        Commits from `collect_git_commits()`.
    repo : str or list of str, optional
        Repo name(s) to keep. `None` uses all repos.
    date_begin, date_end : str or datetime.date, optional
        Inclusive date bounds (`"YYYY-MM-DD"` strings work).
    x, y : str
        Each one of `"repo"`, `"time"`, `"date"`, `"weekday"`; they must differ.
    plot_type : str
        `"matplotlib"`, `"plotly"` (interactive; needs `hubbub[plotly]`), or
        `"density"` (matplotlib with marginal density curves).
    top_n : int
        When `"repo"` is an axis and `repo` is `None`, keep this many of the most
        active repos.
    title : str, optional
        Plot title. Defaults to the repo name(s) or `"All repos"`.
    seed : int, optional
        Seed for the jitter.

    Returns
    -------
    matplotlib.figure.Figure or plotly.graph_objects.Figure
    """
    allowed = ("repo", "time", "date", "weekday")
    if x == y or x not in allowed or y not in allowed:
        raise ValueError(f"x and y must each be one of {allowed} and must differ.")
    if plot_type not in ("matplotlib", "plotly", "density"):
        raise ValueError('plot_type must be "matplotlib", "plotly", or "density".')
    commits = filter_commits(commits, repo, date_begin, date_end)
    if repo is None and "repo" in (x, y):
        keep = (
            commits.group_by("repo").agg(n=pl.len())
            .sort(["n", "repo"], descending=[True, False])["repo"].head(top_n)
        )
        commits = commits.filter(pl.col("repo").is_in(keep.to_list()))
    title = default_title(repo, title)
    time_short = commits["local_ts"].dt.strftime("%H:%M").to_list()

    if plot_type == "plotly":
        try:
            import plotly.express as px
        except ImportError as e:
            raise ImportError("Install the 'plotly' extra: hubbub[plotly]") from e
        data = {
            "repo": commits["repo"].to_list(),
            "date": commits["date"].to_list(),
            "time": commits["local_ts"].dt.strftime("1970-01-01 %H:%M").to_list(),
            "weekday": commits["weekday"].cast(pl.String).to_list(),
            "time_short": time_short,
        }
        fig = px.strip(data, x=x, y=y, color="repo", hover_data=["time_short"],
                       title=title)
        if "weekday" in (x, y):
            orders = [w for w in WEEKDAYS if w in set(data["weekday"])]
            fig.update_layout({f"{'x' if x == 'weekday' else 'y'}axis": {
                "categoryorder": "array", "categoryarray": orders}})
        return fig

    rng = np.random.default_rng(seed)
    xv, xlab = _axis_values(commits, x)
    yv, ylab = _axis_values(commits, y)
    if xlab is not None:
        xv = xv + rng.uniform(-0.2, 0.2, len(xv))
    if ylab is not None:
        yv = yv + rng.uniform(-0.2, 0.2, len(yv))

    if plot_type == "density":
        fig = plt.figure(figsize=(10, 7))
        gs = fig.add_gridspec(2, 2, width_ratios=(5, 1), height_ratios=(1, 5),
                              wspace=0.03, hspace=0.03)
        ax = fig.add_subplot(gs[1, 0])
        ax_top = fig.add_subplot(gs[0, 0], sharex=ax)
        ax_right = fig.add_subplot(gs[1, 1], sharey=ax)
    else:
        fig, ax = plt.subplots(figsize=(10, 6))

    repos = commits["repo"].to_list()
    uniq = sorted(set(repos))
    cmap = plt.get_cmap("tab20", max(len(uniq), 1))
    for i, r in enumerate(uniq):
        m = np.array([rr == r for rr in repos])
        ax.scatter(np.asarray(xv, dtype=object)[m] if x == "date" else xv[m],
                   np.asarray(yv, dtype=object)[m] if y == "date" else yv[m],
                   s=40, color=cmap(i), edgecolors="#555555", alpha=0.85, label=r)

    for var, lab, axis in ((x, xlab, ax.xaxis), (y, ylab, ax.yaxis)):
        if lab is not None:
            axis.set_ticks(range(len(lab)), lab)
        elif var == "time":
            axis.set_ticks(range(0, 24, 2), [f"{h:02d}:00" for h in range(0, 24, 2)])
    if x in ("repo", "weekday"):
        plt.setp(ax.get_xticklabels(), rotation=45, ha="right")
    ax.grid(alpha=0.3)
    ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.15),
              ncol=min(len(uniq), 5), frameon=False, fontsize=8)

    if plot_type == "density":
        import matplotlib.dates as mdates

        def num(v: Any, var: str) -> np.ndarray:
            return (np.asarray(mdates.date2num(v)) if var == "date"
                    else np.asarray(v, dtype=float))

        xn, yn = num(xv, x), num(yv, y)
        gx = np.linspace(xn.min(), xn.max(), 200)
        gy = np.linspace(yn.min(), yn.max(), 200)
        ax_top.plot(gx, _kde(xn, gx), color="0.3")
        ax_right.plot(_kde(yn, gy), gy, color="0.3")
        for a in (ax_top, ax_right):
            a.axis("off")
        ax_top.set_title(title, loc="left")
    else:
        ax.set_title(title, loc="left")
    fig.tight_layout() if plot_type != "density" else None
    return fig
