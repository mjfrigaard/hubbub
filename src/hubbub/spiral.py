"""Spiral charts of daily commits: one turn per year, inside out.

A matplotlib take on the R spiralize charts used by ghreadme.
"""

from __future__ import annotations

from datetime import date
from typing import Any

import matplotlib.pyplot as plt
import numpy as np
import polars as pl
from matplotlib.colors import Normalize
from matplotlib.figure import Figure

from ._utils import default_title, filter_commits, per_day


def _spiral_coords(days: list[date]) -> tuple[np.ndarray, np.ndarray, int]:
    """Angle (clockwise from top) and radius for each date; one turn a year."""
    y0 = days[0].year
    frac = np.array(
        [(d.timetuple().tm_yday - 1) / (366 if d.year % 4 == 0 else 365)
         for d in days]
    )
    years = np.array([d.year - y0 for d in days])
    theta = 2 * np.pi * frac
    r = 1 + years + frac
    return theta, r, days[-1].year - y0 + 1


def _setup(n_turns: int) -> tuple[Figure, plt.Axes]:
    fig = plt.figure(figsize=(7, 7))
    ax = fig.add_subplot(projection="polar")
    ax.set_theta_zero_location("N")
    ax.set_theta_direction(-1)
    ax.set_ylim(0, n_turns + 1.6)
    ax.set_xticks(np.linspace(0, 2 * np.pi, 12, endpoint=False),
                  ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
                   "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"])
    ax.set_yticks([])
    ax.spines["polar"].set_visible(False)
    ax.grid(alpha=0.25)
    # the spiral guide line
    t = np.linspace(0, 2 * np.pi * (n_turns + 1), 600)
    ax.plot(t, 1 + t / (2 * np.pi), color="0.85", linewidth=0.8, zorder=0)
    return fig, ax


def _label_years(ax: plt.Axes, days: list[date]) -> None:
    y0 = days[0].year
    for yr in range(y0, days[-1].year + 1):
        ax.text(0, 1 + yr - y0, str(yr), fontsize=6, ha="center", va="center")


def _prep(commits: pl.DataFrame, repo, date_begin, date_end, title):  # type: ignore[no-untyped-def]
    commits = filter_commits(commits, repo, date_begin, date_end)
    df = per_day(commits)
    days = df["date"].to_list()
    n = df["commits"].to_numpy()
    max_commit = max(30, n.max() * 0.9)
    return df, days, n, max_commit, default_title(repo, title)


def _plotly_spiral(
    kind: str, days: list[date], n: np.ndarray, max_commit: float, title: str,
    n_bands: int = 4,
) -> Any:
    """Interactive plotly version of the spiral charts."""
    try:
        import plotly.graph_objects as go
    except ImportError as e:
        raise ImportError("Install the 'plotly' extra: hubbub[plotly]") from e
    from matplotlib.colors import to_hex

    theta, r, turns = _spiral_coords(days)
    deg = np.degrees(theta)
    hover = [f"{d:%a %b %d, %Y}<br>{c} commits" for d, c in zip(days, n)]
    total = f"{title} commits (total {int(n.sum())})"
    fig = go.Figure()
    t = np.linspace(0, 360 * (turns + 1), 600)
    fig.add_trace(go.Scatterpolar(
        theta=t % 360, r=1 + t / 360, mode="lines",
        line={"color": "#d9d9d9", "width": 1}, hoverinfo="skip", showlegend=False,
    ))
    width = 360 / 365
    if kind == "points":
        size = np.clip((20 - 1) / (max_commit - 2) * (n - 2) + 1, 1, 20)
        fig.add_trace(go.Scatterpolar(
            theta=deg, r=r, mode="markers", text=hover, hoverinfo="text",
            marker={"size": size, "color": "black", "opacity": 0.8},
            showlegend=False,
        ))
    elif kind == "heatmap":
        fig.add_trace(go.Barpolar(
            theta=deg, r=np.full(len(n), 0.8), base=r - 0.4, width=width,
            text=hover, hoverinfo="text", showlegend=False,
            marker={"color": n, "colorscale": "Spectral", "reversescale": True,
                    "cmin": 2, "cmax": max_commit, "line": {"width": 0},
                    "colorbar": {"title": {"text": "commits"}}},
        ))
    else:
        y = np.minimum(n, max_commit)
        band_size = max_commit / n_bands
        band = np.minimum((y // band_size).astype(int), n_bands - 1)
        colors = [to_hex(c) for c in
                  plt.get_cmap("Blues")(np.linspace(0.35, 1, n_bands))]
        heights = ((y - band * band_size) / band_size) * 0.8
        for b in range(n_bands):
            m = band == b
            if not m.any():
                continue
            fig.add_trace(go.Barpolar(
                theta=deg[m], r=heights[m], base=r[m] - 0.4, width=width,
                text=[h for h, keep in zip(hover, m) if keep], hoverinfo="text",
                marker={"color": colors[b], "line": {"width": 0}},
                name=f"{b * band_size:.0f}-{(b + 1) * band_size:.0f}",
            ))
    y0 = days[0].year
    years = list(range(y0, days[-1].year + 1))
    fig.add_trace(go.Scatterpolar(
        theta=[0] * len(years), r=[1 + yr - y0 for yr in years], mode="text",
        text=[str(yr) for yr in years], textfont={"size": 9},
        hoverinfo="skip", showlegend=False,
    ))
    fig.update_layout(
        title={"text": total, "x": 0.02},
        template="plotly_white",
        height=650,
        legend={"title": {"text": "commits"}},
        polar={
            "angularaxis": {
                "rotation": 90, "direction": "clockwise",
                "tickvals": np.linspace(0, 360, 12, endpoint=False).tolist(),
                "ticktext": ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
                             "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"],
            },
            "radialaxis": {"visible": False, "range": [0, turns + 1.6]},
            "bargap": 0,
        },
    )
    return fig


def _check_plot_type(plot_type: str) -> None:
    if plot_type not in ("matplotlib", "plotly"):
        raise ValueError('plot_type must be "matplotlib" or "plotly".')


def spiral_points_plot(
    commits: pl.DataFrame,
    repo: str | list[str] | None = None,
    date_begin: str | date | None = None,
    date_end: str | date | None = None,
    title: str | None = None,
    plot_type: str = "matplotlib",
) -> Any:
    """Spiral of daily commits drawn as points sized by count.

    Parameters
    ----------
    commits : polars.DataFrame
        Commits from `collect_git_commits()`.
    repo : str or list of str, optional
        Repo name(s) to keep. `None` uses all repos.
    date_begin, date_end : str or datetime.date, optional
        Inclusive date bounds (`"YYYY-MM-DD"` strings work).
    title : str, optional
        Legend title. Defaults to the repo name(s) or `"All repos"`.
    plot_type : str
        `"matplotlib"` for a static figure or `"plotly"` for an interactive one
        with hover labels (needs `hubbub[plotly]`).

    Returns
    -------
    matplotlib.figure.Figure or plotly.graph_objects.Figure

    Notes
    -----
    The spiral makes one turn per year, starting at the center, with January
    at the top and months running clockwise.
    """
    _check_plot_type(plot_type)
    df, days, n, max_commit, title = _prep(commits, repo, date_begin, date_end, title)
    if plot_type == "plotly":
        return _plotly_spiral("points", days, n, max_commit, title)
    theta, r, turns = _spiral_coords(days)

    def size(x: np.ndarray) -> np.ndarray:
        s = (20 - 1) / (max_commit - 2) * (x - 2) + 1
        return np.clip(s, 1, 20) ** 2 / 4

    fig, ax = _setup(turns)
    ax.scatter(theta, r, s=size(n), color="black", alpha=0.8, linewidths=0)
    _label_years(ax, days)
    breaks = np.unique(np.linspace(n.min(), n.max(), 4).round())
    handles = [ax.scatter([], [], s=size(np.array([b])), color="black") for b in breaks]
    ax.legend(handles, [f"{int(b)}" for b in breaks], loc="upper left",
              bbox_to_anchor=(-0.15, 1.12), frameon=False,
              title=f"{title} commits\n(total {int(n.sum())})")
    return fig


def spiral_heatmap_plot(
    commits: pl.DataFrame,
    repo: str | list[str] | None = None,
    date_begin: str | date | None = None,
    date_end: str | date | None = None,
    title: str | None = None,
    plot_type: str = "matplotlib",
) -> Any:
    """Spiral of daily commits drawn as tiles colored by count.

    Parameters
    ----------
    commits : polars.DataFrame
        Commits from `collect_git_commits()`.
    repo : str or list of str, optional
        Repo name(s) to keep. `None` uses all repos.
    date_begin, date_end : str or datetime.date, optional
        Inclusive date bounds (`"YYYY-MM-DD"` strings work).
    title : str, optional
        Colorbar title. Defaults to the repo name(s) or `"All repos"`.
    plot_type : str
        `"matplotlib"` for a static figure or `"plotly"` for an interactive one
        with hover labels (needs `hubbub[plotly]`).

    Returns
    -------
    matplotlib.figure.Figure or plotly.graph_objects.Figure

    Notes
    -----
    The spiral makes one turn per year, starting at the center, with January
    at the top and months running clockwise.
    """
    _check_plot_type(plot_type)
    df, days, n, max_commit, title = _prep(commits, repo, date_begin, date_end, title)
    if plot_type == "plotly":
        return _plotly_spiral("heatmap", days, n, max_commit, title)
    theta, r, turns = _spiral_coords(days)
    cmap = plt.get_cmap("Spectral_r")
    norm = Normalize(vmin=2, vmax=max_commit, clip=True)
    fig, ax = _setup(turns)
    ax.bar(theta, 0.8, width=2 * np.pi / 365, bottom=r - 0.4,
           color=cmap(norm(n)), linewidth=0)
    _label_years(ax, days)
    fig.colorbar(plt.cm.ScalarMappable(norm=norm, cmap=cmap), ax=ax, shrink=0.5,
                 pad=0.08, label=f"{title} commits (total {int(n.sum())})")
    return fig


def spiral_horizon_plot(
    commits: pl.DataFrame,
    repo: str | list[str] | None = None,
    date_begin: str | date | None = None,
    date_end: str | date | None = None,
    title: str | None = None,
    n_bands: int = 4,
    plot_type: str = "matplotlib",
) -> Any:
    """Spiral horizon chart of daily commits.

    Counts are split into `n_bands` bands. Each bar's height shows the count
    within its band and its shade shows the band, so busy days read darker.

    Parameters
    ----------
    commits : polars.DataFrame
        Commits from `collect_git_commits()`.
    repo : str or list of str, optional
        Repo name(s) to keep. `None` uses all repos.
    date_begin, date_end : str or datetime.date, optional
        Inclusive date bounds (`"YYYY-MM-DD"` strings work).
    title : str, optional
        Legend title. Defaults to the repo name(s) or `"All repos"`.
    n_bands : int
        Number of shade bands.
    plot_type : str
        `"matplotlib"` for a static figure or `"plotly"` for an interactive one
        with hover labels (needs `hubbub[plotly]`).

    Returns
    -------
    matplotlib.figure.Figure or plotly.graph_objects.Figure

    Notes
    -----
    The spiral makes one turn per year, starting at the center, with January
    at the top and months running clockwise.
    """
    _check_plot_type(plot_type)
    df, days, n, max_commit, title = _prep(commits, repo, date_begin, date_end, title)
    if plot_type == "plotly":
        return _plotly_spiral("horizon", days, n, max_commit, title, n_bands)
    theta, r, turns = _spiral_coords(days)
    y = np.minimum(n, max_commit)
    band_size = max_commit / n_bands
    band = np.minimum((y // band_size).astype(int), n_bands - 1)
    colors = plt.get_cmap("Blues")(np.linspace(0.35, 1, n_bands))
    heights = ((y - band * band_size) / band_size) * 0.8

    fig, ax = _setup(turns)
    ax.bar(theta, heights, width=2 * np.pi / 365, bottom=r - 0.4,
           color=colors[band], linewidth=0)
    _label_years(ax, days)
    handles = [plt.Rectangle((0, 0), 1, 1, color=c) for c in colors]
    labels = [f"{i * band_size:.0f}-{(i + 1) * band_size:.0f}" for i in range(n_bands)]
    ax.legend(handles, labels, loc="upper left", bbox_to_anchor=(-0.15, 1.12),
              frameon=False, title=f"{title} commits\n(total {int(n.sum())})")
    return fig
