"""Reusable utilities for the Las Bambas conflict analysis notebooks."""

from .cluster_plots import plot_cluster_points, plot_cluster_time, prepare_period
from .paths import build_project_paths, ensure_output_directories, find_project_root
from .spatial_figures import export_minimal_polygon_map
from .spatial_geometry import (
    DEFAULT_MIN_DENSITY,
    adjust_density_by_type,
    generate_buffers,
    generate_conflict_areas,
)
from .water import dynamic_water_tile_stats_by_geometry

__all__ = [
    "DEFAULT_MIN_DENSITY",
    "adjust_density_by_type",
    "build_project_paths",
    "dynamic_water_tile_stats_by_geometry",
    "ensure_output_directories",
    "export_minimal_polygon_map",
    "find_project_root",
    "generate_buffers",
    "generate_conflict_areas",
    "plot_cluster_points",
    "plot_cluster_time",
    "prepare_period",
]
