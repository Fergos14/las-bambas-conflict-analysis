from __future__ import annotations

from pathlib import Path

import geopandas as gpd
import matplotlib.pyplot as plt


def export_minimal_polygon_map(
    polygon_gdf=None,
    geographic_feature_points=None,
    built_environment_points=None,
    mine_points=None,
    population_center_points=None,
    base_name="minimal_map",
    out_dir=".",
    polygon_color="#cc6677",
    polygon_alpha=0.18,
    padding_factor=0.08,
    save_pdf=True,
    save_png=True,
    dpi_pdf=300,
    dpi_png=300,
    **kwargs,
):
    """Export a minimalist polygon map with the point layers used in the paper."""
    if polygon_gdf is None and "gdf_poligono" in kwargs:
        polygon_gdf = kwargs.pop("gdf_poligono")

    if kwargs:
        unexpected = ", ".join(sorted(kwargs))
        raise TypeError(f"Unexpected keyword argument(s): {unexpected}")

    if polygon_gdf is None:
        raise TypeError("polygon_gdf is required")

    def reproject_points(point_list):
        if point_list and len(point_list) > 0:
            unique_points = list(set(point_list))
            return gpd.GeoDataFrame(geometry=unique_points, crs="EPSG:4326").to_crs(epsg=3857)
        return None

    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    polygon_gdf_3857 = polygon_gdf.to_crs(epsg=3857).copy()
    total_area_km2 = polygon_gdf_3857.geometry.area.sum() / 1e6

    geographic_features_gdf = reproject_points(geographic_feature_points)
    built_environment_gdf = reproject_points(built_environment_points)
    mines_gdf = reproject_points(mine_points)
    population_centers_gdf = reproject_points(population_center_points)

    fig, ax = plt.subplots(figsize=(6.8, 6.8))
    fig.patch.set_facecolor("white")
    ax.set_facecolor("white")

    polygon_gdf_3857.plot(
        ax=ax,
        edgecolor=polygon_color,
        facecolor=polygon_color,
        alpha=polygon_alpha,
        linewidth=1.8,
        zorder=1,
    )

    point_styles = {
        "Geographic features": {"gdf": geographic_features_gdf, "color": "#5aae61", "size": 18},
        "Built environment": {"gdf": built_environment_gdf, "color": "#b88a1b", "size": 18},
        "Mines": {"gdf": mines_gdf, "color": "#ca0020", "size": 24},
        "Population centers": {"gdf": population_centers_gdf, "color": "#1f3b73", "size": 20},
    }

    for label, cfg in point_styles.items():
        if cfg["gdf"] is not None and not cfg["gdf"].empty:
            cfg["gdf"].plot(
                ax=ax,
                color=cfg["color"],
                markersize=cfg["size"],
                edgecolor="white",
                linewidth=0.35,
                alpha=0.95,
                label=label,
                zorder=2,
            )

    xmin, ymin, xmax, ymax = polygon_gdf_3857.total_bounds
    xpad = (xmax - xmin) * padding_factor
    ypad = (ymax - ymin) * padding_factor
    ax.set_xlim(xmin - xpad, xmax + xpad)
    ax.set_ylim(ymin - ypad, ymax + ypad)

    ax.set_xticks([])
    ax.set_yticks([])
    ax.set_xlabel("")
    ax.set_ylabel("")
    for spine in ax.spines.values():
        spine.set_visible(False)

    ax.text(
        0.98,
        0.98,
        f"Area: {total_area_km2:.2f} km$^2$",
        transform=ax.transAxes,
        ha="right",
        va="top",
        fontsize=8.5,
        bbox=dict(
            boxstyle="round,pad=0.25",
            facecolor="white",
            edgecolor="lightgray",
            alpha=0.95,
        ),
        zorder=3,
    )

    legend = ax.legend(
        loc="lower left",
        fontsize=8,
        frameon=True,
        framealpha=0.95,
        borderpad=0.4,
        handletextpad=0.4,
    )
    legend.get_frame().set_edgecolor("lightgray")
    legend.get_frame().set_linewidth(0.8)

    plt.tight_layout()

    if save_pdf:
        pdf_path = out_dir / f"{base_name}.pdf"
        plt.savefig(pdf_path, dpi=dpi_pdf, bbox_inches="tight")
        print(f"PDF saved: {pdf_path}")

    if save_png:
        png_path = out_dir / f"{base_name}.png"
        plt.savefig(png_path, dpi=dpi_png, bbox_inches="tight")
        print(f"PNG saved: {png_path}")

    plt.close(fig)
