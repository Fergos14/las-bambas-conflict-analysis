from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class SpatialPaths:
    output_dir: Path
    figures_dir: Path
    maps_dir: Path
    intermediate_dir: Path
    polygon_maps_dir: Path
    land_cover_dir: Path
    land_cover_class_maps_dir: Path
    transitions_dir: Path
    water_figures_dir: Path
    water_tiles_dir: Path
    serie_poligonos_path: Path
    mining_development_figure: Path


@dataclass(frozen=True)
class ClusterPaths:
    output_dir: Path
    figures_dir: Path
    maps_dir: Path
    temporal_maps_dir: Path


@dataclass(frozen=True)
class ProjectPaths:
    project_root: Path
    src_dir: Path
    data_dir: Path
    results_dir: Path
    spatial: SpatialPaths
    cluster: ClusterPaths
    gpkg_path: Path
    conflict_report_path: Path
    conflict_matrix_path: Path
    mining_area_path: Path


def find_project_root(start_path: Path) -> Path:
    """Walk upward until the repository root is found."""
    start_path = start_path.resolve()
    for candidate in [start_path, *start_path.parents]:
        if (candidate / "Code").exists() and (candidate / "Data").exists():
            return candidate
    raise FileNotFoundError(
        "Could not locate the repository root containing both 'Code' and 'Data'."
    )


def build_project_paths(project_root: Path) -> ProjectPaths:
    """Create the path layout used by the notebooks."""
    project_root = project_root.resolve()
    src_dir = project_root / "src"
    data_dir = project_root / "Data"
    results_dir = project_root / "Results"

    spatial_output_dir = results_dir / "spatial_analysis"
    spatial_figures_dir = spatial_output_dir / "figures"
    spatial_maps_dir = spatial_output_dir / "maps"
    spatial_intermediate_dir = spatial_output_dir / "intermediate"

    cluster_output_dir = results_dir / "cluster_association_rules"
    cluster_figures_dir = cluster_output_dir / "figures"
    cluster_maps_dir = cluster_output_dir / "maps"

    mining_area_matches = list(data_dir.glob("*Minera.geojson"))
    if not mining_area_matches:
        raise FileNotFoundError("Could not locate the mining area GeoJSON inside Data/.")

    spatial_paths = SpatialPaths(
        output_dir=spatial_output_dir,
        figures_dir=spatial_figures_dir,
        maps_dir=spatial_maps_dir,
        intermediate_dir=spatial_intermediate_dir,
        polygon_maps_dir=spatial_maps_dir / "poligono_anual_bambas",
        land_cover_dir=spatial_figures_dir / "land_cover",
        land_cover_class_maps_dir=spatial_maps_dir / "land_cover_clases_journal",
        transitions_dir=spatial_figures_dir / "transiciones",
        water_figures_dir=spatial_figures_dir / "agua",
        water_tiles_dir=spatial_intermediate_dir / "agua_tiles_out",
        serie_poligonos_path=spatial_intermediate_dir / "serie_temporal_poligonos.geojson",
        mining_development_figure=spatial_figures_dir / "mining_development_python_final.pdf",
    )
    cluster_paths = ClusterPaths(
        output_dir=cluster_output_dir,
        figures_dir=cluster_figures_dir,
        maps_dir=cluster_maps_dir,
        temporal_maps_dir=cluster_maps_dir / "clusters_temporales",
    )

    return ProjectPaths(
        project_root=project_root,
        src_dir=src_dir,
        data_dir=data_dir,
        results_dir=results_dir,
        spatial=spatial_paths,
        cluster=cluster_paths,
        gpkg_path=data_dir / "geometriasxcasoxminabambas.gpkg",
        conflict_report_path=data_dir / "ReporteFechaxConflicto_bambas.csv",
        conflict_matrix_path=data_dir / "Conflicto_bambas.csv",
        mining_area_path=mining_area_matches[0],
    )


def ensure_output_directories(project_paths: ProjectPaths) -> ProjectPaths:
    """Create the output directories expected by the notebooks."""
    folders = [
        project_paths.results_dir,
        project_paths.spatial.output_dir,
        project_paths.spatial.figures_dir,
        project_paths.spatial.maps_dir,
        project_paths.spatial.intermediate_dir,
        project_paths.spatial.polygon_maps_dir,
        project_paths.spatial.land_cover_dir,
        project_paths.spatial.land_cover_class_maps_dir,
        project_paths.spatial.transitions_dir,
        project_paths.spatial.water_figures_dir,
        project_paths.spatial.water_tiles_dir,
        project_paths.cluster.output_dir,
        project_paths.cluster.figures_dir,
        project_paths.cluster.maps_dir,
        project_paths.cluster.temporal_maps_dir,
    ]
    for folder in folders:
        folder.mkdir(parents=True, exist_ok=True)
    return project_paths
