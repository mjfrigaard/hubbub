"""Make some noise on your GitHub profile README.

Python counterpart to the R package ghreadme.
"""

from .badges import gh_badges, so_rep
from .collect import add_time_columns, collect_git_commits
from .gif import make_gif
from .intro import who_am_i, who_am_i_gif
from .plots import (
    calendar_heatmap_plot,
    cumulative_line_plot,
    punchcard_plot,
    scatter_density_plot,
)
from .scaffold import use_profile_readme, use_profile_readme_action
from .spiral import spiral_heatmap_plot, spiral_horizon_plot, spiral_points_plot

__all__ = [
    "add_time_columns",
    "calendar_heatmap_plot",
    "collect_git_commits",
    "cumulative_line_plot",
    "gh_badges",
    "make_gif",
    "punchcard_plot",
    "scatter_density_plot",
    "so_rep",
    "spiral_heatmap_plot",
    "spiral_horizon_plot",
    "spiral_points_plot",
    "use_profile_readme",
    "use_profile_readme_action",
    "who_am_i",
    "who_am_i_gif",
]
