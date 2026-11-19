import urllib.error

import polars as pl
import pytest

from hubbub import collect, collect_git_commits

REPOS = [
    {"name": "a", "fork": False, "stargazers_count": 2, "forks_count": 1,
     "watchers_count": 2, "language": "R", "description": None,
     "created_at": "2020-01-01T00:00:00Z", "updated_at": "2024-01-01T00:00:00Z"},
    {"name": "b", "fork": False, "stargazers_count": 9, "forks_count": None,
     "watchers_count": 9, "language": "Python", "description": "x",
     "created_at": "2021-01-01T00:00:00Z", "updated_at": "2024-01-01T00:00:00Z"},
    {"name": "f", "fork": True},
]


def _commit(sha, email, date="2024-03-04T15:30:00Z"):
    return {"sha": sha, "commit": {"author": {"date": date, "name": "M",
                                              "email": email},
                                   "message": "msg"}}


@pytest.fixture
def fake_api(monkeypatch):
    calls = []

    def fake_get(path, params, limit=float("inf")):
        calls.append((path, params))
        if path.endswith("/repos"):
            return REPOS
        if path == "/repos/u/a/commits":
            return [_commit("1", "Me@x.com"), _commit("2", "other@x.com")]
        if path == "/repos/u/b/commits":
            raise urllib.error.HTTPError(path, 409, "empty", {}, None)
        if path == "/search/issues":
            return {"items": [{
                "repository_url": "https://api.github.com/repos/o/r",
                "number": 5, "title": "t", "state": "open",
                "created_at": "2024-01-02T00:00:00Z", "closed_at": None,
                "html_url": "https://github.com/o/r/issues/5"}]}
        raise AssertionError(path)

    monkeypatch.setattr(collect, "_get", fake_get)
    return calls


def test_commits_default(fake_api):
    df = collect_git_commits("u", emails="me@x.com", tz="UTC")
    assert isinstance(df, pl.DataFrame)
    assert df["sha"].to_list() == ["1"]
    row = df.row(0, named=True)
    assert row["hour"] == 15 and row["weekday"] == "Monday" and row["year"] == 2024
    assert not any(p.startswith("/repos/u/f") for p, _ in fake_api)


def test_commits_forks_and_since(fake_api):
    with pytest.raises(AssertionError):
        collect_git_commits("u", include_forks=True)
    fake_api.clear()
    collect_git_commits("u", since="2024-01-01", tz="UTC")
    params = dict(fake_api)["/repos/u/a/commits"]
    assert params["since"] == "2024-01-01T00:00:00Z"


def test_all_types(fake_api):
    out = collect_git_commits("u", include=["commits", "stars", "issues", "prs"],
                              tz="UTC")
    assert set(out) == {"commits", "stars", "issues", "prs"}
    assert out["stars"]["repo"].to_list() == ["b", "a"]
    assert out["stars"]["forks_count"].to_list() == [0, 1]
    assert out["issues"]["repo"].to_list() == ["o/r"]
    queries = [p["q"] for path, p in fake_api if path == "/search/issues"]
    assert queries == ["author:u type:issue", "author:u type:pr"]


def test_search_only_skips_repo_listing(fake_api):
    out = collect_git_commits("u", include="issues", since="2024-01-01")
    assert list(out) == ["issues"]
    assert fake_api == [("/search/issues",
                         {"q": "author:u type:issue created:>=2024-01-01",
                          "per_page": 100})]


def test_bad_include():
    with pytest.raises(ValueError):
        collect_git_commits("u", include="gists")
