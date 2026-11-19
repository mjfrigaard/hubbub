import pytest
from matplotlib.figure import Figure

from hubbub import (
    calendar_heatmap_plot,
    cumulative_line_plot,
    punchcard_plot,
    scatter_density_plot,
    spiral_heatmap_plot,
    spiral_horizon_plot,
    spiral_points_plot,
)

ALL = [
    calendar_heatmap_plot,
    cumulative_line_plot,
    punchcard_plot,
    scatter_density_plot,
    spiral_heatmap_plot,
    spiral_horizon_plot,
    spiral_points_plot,
]


@pytest.mark.parametrize("fn", ALL)
def test_returns_figure(fn, commits):
    assert isinstance(fn(commits), Figure)


@pytest.mark.parametrize("fn", ALL)
def test_filters(fn, commits):
    assert isinstance(
        fn(commits, repo="repo-a", date_begin="2023-01-01", date_end="2024-12-31"),
        Figure,
    )


@pytest.mark.parametrize("fn", ALL)
def test_empty_after_filter_raises(fn, commits):
    with pytest.raises(ValueError, match="No commits after filtering"):
        fn(commits, repo="nope")


def test_default_titles(commits):
    fig = punchcard_plot(commits)
    assert fig.axes[0].get_title(loc="left") == "All repos — 30 commits"
    fig = punchcard_plot(commits, repo=["repo-a", "repo-b"])
    assert fig.axes[0].get_title(loc="left").startswith("repo-a, repo-b")


def test_calendar_week_start(commits):
    assert isinstance(calendar_heatmap_plot(commits, week_start="Monday"), Figure)
    with pytest.raises(ValueError):
        calendar_heatmap_plot(commits, week_start="Friday")


def test_calendar_one_axis_per_year(commits):
    fig = calendar_heatmap_plot(commits)
    assert sum(ax.get_ylabel() in ("2023", "2024") for ax in fig.axes) == 2


def test_cumulative_top_n(commits):
    fig = cumulative_line_plot(commits, top_n=1)
    labels = [t.get_text() for t in fig.axes[0].get_legend().get_texts()]
    assert labels == ["repo-a", "Other"]
    fig = cumulative_line_plot(commits, top_n=1, show_other=False)
    labels = [t.get_text() for t in fig.axes[0].get_legend().get_texts()]
    assert labels == ["repo-a"]


@pytest.mark.parametrize(
    "x,y", [("date", "time"), ("repo", "weekday"), ("weekday", "time"),
            ("time", "date")]
)
def test_scatter_axes(commits, x, y):
    assert isinstance(scatter_density_plot(commits, x=x, y=y), Figure)


def test_scatter_density(commits):
    fig = scatter_density_plot(commits, plot_type="density")
    assert len(fig.axes) == 3


def test_scatter_bad_args(commits):
    with pytest.raises(ValueError):
        scatter_density_plot(commits, x="date", y="date")
    with pytest.raises(ValueError):
        scatter_density_plot(commits, x="foo")
    with pytest.raises(ValueError):
        scatter_density_plot(commits, plot_type="bar")


def test_scatter_plotly(commits):
    pytest.importorskip("plotly")
    fig = scatter_density_plot(commits, x="weekday", y="time", plot_type="plotly")
    assert fig.layout.title.text == "All repos"


@pytest.mark.parametrize(
    "fn", [spiral_heatmap_plot, spiral_horizon_plot, spiral_points_plot]
)
def test_spiral_plotly(fn, commits):
    pytest.importorskip("plotly")
    fig = fn(commits, plot_type="plotly")
    assert "commits (total 30)" in fig.layout.title.text
    with pytest.raises(ValueError):
        fn(commits, plot_type="ggplot")
