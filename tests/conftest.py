from datetime import datetime, timezone

import matplotlib
import polars as pl
import pytest

matplotlib.use("Agg")

from hubbub.collect import add_time_columns  # noqa: E402


def make_commits(n_repos=3, n_commits=30, start="2023-01-15", end="2024-12-15"):
    names = [f"repo-{c}" for c in "abcdefghij"[:n_repos]]
    repos = [names[i % n_repos] for i in range(n_commits)]
    t0 = datetime.fromisoformat(f"{start}T09:00:00").replace(tzinfo=timezone.utc)
    t1 = datetime.fromisoformat(f"{end}T17:00:00").replace(tzinfo=timezone.utc)
    step = (t1 - t0) / (n_commits - 1)
    df = pl.DataFrame({
        "repo": sorted(repos),
        "sha": [f"sha{i:04d}" for i in range(1, n_commits + 1)],
        "timestamp": [t0 + step * i for i in range(n_commits)],
        "author_name": "Test User",
        "author_email": "test@example.com",
        "message": [f"commit {i}" for i in range(1, n_commits + 1)],
    }).with_columns(pl.col("timestamp").dt.cast_time_unit("us"))
    return add_time_columns(df, "UTC")


@pytest.fixture
def commits():
    return make_commits()


@pytest.fixture(autouse=True)
def close_figs():
    yield
    import matplotlib.pyplot as plt

    plt.close("all")
