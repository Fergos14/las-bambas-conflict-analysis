from __future__ import annotations

import geopandas as gpd
import numpy as np
import pandas as pd
import shapely
from shapely.geometry import GeometryCollection, MultiPoint, Point

DEFAULT_MIN_DENSITY = 3000


def _safe_union_all(geometries):
    """Return a dissolved geometry across GeoPandas/Shapely versions."""
    valid_geometries = geometries.dropna()
    if valid_geometries.empty:
        return GeometryCollection()

    union_all_method = getattr(valid_geometries, "union_all", None)
    if callable(union_all_method):
        return union_all_method()

    return valid_geometries.unary_union


def adjust_density_by_type(row, min_density=DEFAULT_MIN_DENSITY):
    """Enforce a minimum density for urban population centers."""
    if row["AREA_17"]:
        return max(row["densidad_poblacional"], min_density)
    return row["densidad_poblacional"]


def generate_buffers(layers, buffer_rules, target_mine, path, min_density=DEFAULT_MIN_DENSITY):
    """Load layers from the geopackage and apply the notebook buffer logic."""
    filtered_buffer_gdfs = {}

    for layer in layers:
        gdf = gpd.read_file(path, layer=layer)

        if "Minas_list" in gdf.columns:
            gdf = gdf[gdf["Minas_list"] == target_mine]

        if layer in buffer_rules:
            distance = buffer_rules[layer]
            gdf = gdf.to_crs(epsg=32718)
            gdf["geometry"] = gdf.geometry.buffer(distance)
            gdf = gdf.to_crs(epsg=4326)
        elif layer == "Centros_Poblados":
            gdf["densidad_ajustada"] = gdf.apply(
                lambda row: adjust_density_by_type(row, min_density=min_density),
                axis=1,
            )
            gdf["Población Total"] = gdf["Población Total"].fillna(1)
            gdf["Area_Estimada"] = gdf["Población Total"] / gdf["densidad_ajustada"]

            gdf_proj = gdf.to_crs(epsg=32718)
            gdf_proj["Area_m2"] = gdf_proj["Area_Estimada"] * 1e6
            gdf_proj["radio_m"] = np.sqrt(gdf_proj["Area_m2"] / np.pi)
            gdf_proj["geometry"] = gdf_proj.buffer(gdf_proj["radio_m"])
            gdf = gdf_proj.to_crs(epsg=4326)

        filtered_buffer_gdfs[layer] = gdf

    return filtered_buffer_gdfs


def _collect_geometry_points(geom):
    """Return a list of points representing the input geometry."""
    if geom.geom_type == "Point":
        return [geom]
    if geom.geom_type == "MultiPoint":
        return list(geom.geoms)
    if geom.geom_type == "Polygon":
        return [Point(x, y) for x, y in geom.exterior.coords]
    if geom.geom_type == "MultiPolygon":
        points = []
        for polygon in geom.geoms:
            points.extend([Point(x, y) for x, y in polygon.exterior.coords])
        return points
    if geom.geom_type == "LineString":
        return [Point(x, y) for x, y in geom.coords]
    if geom.geom_type == "MultiLineString":
        points = []
        for line in geom.geoms:
            points.extend([Point(x, y) for x, y in line.coords])
        return points
    raise ValueError(f"Unsupported geometry type: {geom.geom_type}")


def generate_conflict_areas(
    filtered_buffer_gdfs,
    ratios_by_year,
    years,
    layer_category_map,
    conflict_report_df,
    excluded_mines_gdf,
):
    """Build the annual conflict polygons and the point collections used in the paper."""
    total = []
    geographic_feature_points = {}
    built_environment_points = {}
    population_center_points = {}
    mine_points_by_year = {}

    excluded_mines_union = _safe_union_all(excluded_mines_gdf.geometry)

    for year in years:
        points = []
        geographic_features = []
        built_environment = []
        population_centers = []
        mine_points = []

        for layer_name, gdf in filtered_buffer_gdfs.items():
            layer_gdf = gdf

            if layer_name != "Mina":
                try:
                    layer_gdf = layer_gdf.merge(
                        conflict_report_df,
                        left_on="GRUPO_ID",
                        right_on="GrupoID",
                        how="inner",
                    )
                except KeyError:
                    layer_gdf = layer_gdf.merge(
                        conflict_report_df,
                        left_on="GRUPOID",
                        right_on="GrupoID",
                        how="inner",
                    )

                layer_gdf["Year"] = pd.to_datetime(
                    layer_gdf["FechaReporte"],
                    format="%d/%m/%Y",
                    errors="coerce",
                ).dt.year
                layer_gdf = layer_gdf[layer_gdf.Year == year]

            for geom in layer_gdf.geometry.dropna().unique():
                geometry_points = _collect_geometry_points(geom)
                points.extend(geometry_points)

                category = layer_category_map[layer_name]
                if category == "accidente_geografico":
                    geographic_features.extend(geometry_points)
                elif category == "construcciones_humanas":
                    built_environment.extend(geometry_points)
                elif category == "centros_poblados":
                    population_centers.extend(geometry_points)
                elif category == "mina":
                    mine_points.extend(geometry_points)

        multipoint = MultiPoint(points)
        hull = shapely.concave_hull(multipoint, ratios_by_year[year])
        filtered_hull = hull.difference(excluded_mines_union)
        influence_gdf = gpd.GeoDataFrame(geometry=[filtered_hull], crs=layer_gdf.crs)
        influence_gdf["Year"] = year
        total.append(influence_gdf)

        geographic_feature_points[year] = geographic_features
        built_environment_points[year] = built_environment
        population_center_points[year] = population_centers
        mine_points_by_year[year] = mine_points

    return (
        total,
        geographic_feature_points,
        built_environment_points,
        population_center_points,
        mine_points_by_year,
    )
