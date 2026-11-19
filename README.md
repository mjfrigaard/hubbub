# hubbub

`hubbub` makes some noise on your GitHub profile README. It is the Python counterpart to the R package [ghreadme](https://mjfrigaard.github.io/ghreadme/): introduce yourself as text or an animated GIF, add profile badges, pull your commit history from the GitHub API, and chart it.

Documentation: <https://mjfrigaard.github.io/hubbub/>

## Installation

`hubbub` isn't on PyPI. Add the development version from GitHub with [uv](https://docs.astral.sh/uv/):

```bash
uv add git+https://github.com/mjfrigaard/hubbub
```

`hubbub` depends on `matplotlib`, `numpy`, `pillow`, and `polars`. Interactive scatter plots need the `plotly` extra (`hubbub[plotly]`).

## Example

```python
from hubbub import use_profile_readme, use_profile_readme_action

# in your <username>/<username> repo
use_profile_readme(name="Martin", username="mjfrigaard")  # writes build_readme.py
use_profile_readme_action(cron="0 6 * * 0")               # rebuilds it weekly
```

Run `uv run python build_readme.py` to write `README.md`.

```python
from hubbub import collect_git_commits, calendar_heatmap_plot, spiral_heatmap_plot

commits = collect_git_commits("mjfrigaard", emails="you@example.com")
calendar_heatmap_plot(commits).savefig("calendar.png")
spiral_heatmap_plot(commits, date_begin="2022-01-01").savefig("spiral.png")
```

Set `GITHUB_PAT` (or `GITHUB_TOKEN`) first; unauthenticated calls are limited to 60 requests an hour.

## Functions

| ghreadme (R) | hubbub (Python) |
|---|---|
| `who_am_i()`, `who_am_i_gif()` | same names |
| `gh_badges()`, `so_rep()` | same names, return strings |
| `make_gif()` | same, built on Pillow instead of gifski |
| `collect_git_commits()` | same, returns a polars DataFrame (or dict of them) |
| `calendar_heatmap_plot()`, `cumulative_line_plot()`, `punchcard_plot()`, `scatter_density_plot()` | same, return matplotlib Figures |
| `spiral_points_plot()`, `spiral_heatmap_plot()`, `spiral_horizon_plot()` | same, drawn with matplotlib polar axes |
| `use_profile_readme()` | writes `build_readme.py` instead of `README.Rmd` |
| `use_profile_readme_action()` | Action runs `build_readme.py` with uv |

## Development

`hubbub` uses uv. `uv sync` installs the package with the `dev` and `docs` groups:

```bash
uv sync
uv run pytest
uv run ruff check src tests
uv run great-docs build
uv run great-docs preview
```
