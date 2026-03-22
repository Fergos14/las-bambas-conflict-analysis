from __future__ import annotations

from pathlib import Path

import contextily as ctx
import geopandas as gpd
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.lines import Line2D
from matplotlib.ticker import MaxNLocator
from shapely.geometry import Point

DEFAULT_CLUSTER_COLORS = {
    1: "#56B4E9",
    2: "#59A14F",
    3: "#E3A008",
}

DEFAULT_CLUSTER_EDGE = {
    1: "#2C7FB8",
    2: "#2E6E2E",
    3: "#9A6A00",
}

DEFAULT_CLUSTER_MARKERS = {
    1: "s",
    2: "o",
    3: "^",
}

DEFAULT_ZORDER_MAP = {
    1: 5,
    2: 4,
    3: 3,
}


def prepare_period(df, years):
    """Return a de-duplicated GeoDataFrame restricted to the selected years."""
    subset = df[df.FechaReporte.isin(years)].copy()
    return gpd.GeoDataFrame(
        subset[["cluster", "geometry"]].drop_duplicates(),
        geometry="geometry",
        crs="EPSG:4326",
    )


def plot_cluster_time(
    df_pivot,
    output_pdf_path,
    output_png_path=None,
    show=False,
    add_milestones=False,
    cluster_colors=None,
    cluster_edge=None,
    cluster_markers=None,
):
    """Plot cluster counts through time using the paper-ready style."""
    cluster_colors = cluster_colors or DEFAULT_CLUSTER_COLORS
    cluster_edge = cluster_edge or DEFAULT_CLUSTER_EDGE
    cluster_markers = cluster_markers or DEFAULT_CLUSTER_MARKERS

    output_pdf_path = Path(output_pdf_path)
    output_pdf_path.parent.mkdir(parents=True, exist_ok=True)
    if output_png_path is not None:
        output_png_path = Path(output_png_path)
        output_png_path.parent.mkdir(parents=True, exist_ok=True)

    years = df_pivot.index.to_numpy()
    df_plot = df_pivot.copy().replace(0, np.nan)

    fig, ax = plt.subplots(figsize=(8.2, 3.8))
    fig.patch.set_facecolor("white")
    ax.set_facecolor("white")

    draw_order = [2, 1, 3]
    zorders = {2: 2, 1: 3, 3: 4}
    sizes = {1: 7.5, 2: 10.5, 3: 7.0}

    for cluster in draw_order:
        ax.plot(
            years,
            df_plot[cluster],
            color=cluster_colors[cluster],
            marker=cluster_markers[cluster],
            markersize=sizes[cluster],
            markerfacecolor=cluster_colors[cluster],
            markeredgecolor=cluster_edge[cluster],
            markeredgewidth=0.6,
            linestyle="-",
            linewidth=1.6,
            label=f"Cluster {cluster}",
            alpha=0.95,
            zorder=zorders[cluster],
        )

    if add_milestones:
        milestones = {
            2012: "Construction",
            2014: "Transport\nchange",
            2016: "Operation",
        }
        y_top = max(np.nanmax(df_pivot.values), 1)
        for year, label in milestones.items():
            if year in years:
                ax.axvline(
                    x=year,
                    color="gray",
                    linestyle="--",
                    linewidth=0.75,
                    alpha=0.55,
                    zorder=1,
                )
                ax.text(
                    year + 0.03,
                    y_top + 0.15,
                    label,
                    rotation=90,
                    va="top",
                    ha="left",
                    fontsize=7,
                    color="dimgray",
                )

    ax.set_xlabel("Year", fontsize=9)
    ax.set_ylabel("Number of conflicts", fontsize=9)
    ax.set_xticks(years)
    ax.set_xticklabels([str(year) for year in years], fontsize=8)
    ax.tick_params(axis="y", labelsize=8)
    ax.yaxis.set_major_locator(MaxNLocator(integer=True))

    max_value = np.nanmax(df_pivot.values)
    ax.set_ylim(0.8, max_value + 0.5)
    ax.set_xlim(years.min() - 0.3, years.max() + 0.3)
    ax.grid(axis="y", color="lightgray", linestyle="--", linewidth=0.6, alpha=0.5)
    ax.grid(axis="x", visible=False)

    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.spines["left"].set_color("lightgray")
    ax.spines["bottom"].set_color("lightgray")
    ax.spines["left"].set_linewidth(0.8)
    ax.spines["bottom"].set_linewidth(0.8)

    handles, labels = ax.get_legend_handles_labels()
    desired_order = ["Cluster 1", "Cluster 2", "Cluster 3"]
    order = [labels.index(label) for label in desired_order if label in labels]

    legend = ax.legend(
        [handles[index] for index in order],
        [labels[index] for index in order],
        title="Cluster",
        loc="upper left",
        frameon=True,
        facecolor="white",
        edgecolor="lightgray",
        framealpha=0.95,
        fontsize=8,
        title_fontsize=9,
    )
    legend.get_frame().set_linewidth(0.8)

    plt.tight_layout()
    plt.savefig(output_pdf_path, bbox_inches="tight", dpi=600)
    if output_png_path is not None:
        plt.savefig(output_png_path, bbox_inches="tight", dpi=300)

    if show:
        plt.show()
    else:
        plt.close(fig)


def plot_cluster_points(
    gdf,
    name,
    out_dir,
    show_axes=False,
    use_basemap=True,
    show=False,
    cluster_colors=None,
    cluster_edge=None,
    cluster_markers=None,
    zorder_map=None,
):
    """Plot cluster points by period using the paper-ready cartographic style."""
    cluster_colors = cluster_colors or DEFAULT_CLUSTER_COLORS
    cluster_edge = cluster_edge or DEFAULT_CLUSTER_EDGE
    cluster_markers = cluster_markers or DEFAULT_CLUSTER_MARKERS
    zorder_map = zorder_map or DEFAULT_ZORDER_MAP

    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    gdf = gdf.copy()
    if gdf.crs is None:
        gdf = gdf.set_crs("EPSG:4326")
    gdf = gdf.to_crs(epsg=3857)

    grouped = gdf.groupby("geometry")["cluster"].apply(lambda x: list(sorted(set(x)))).reset_index()
    grouped = gpd.GeoDataFrame(grouped, geometry="geometry", crs=gdf.crs)
    unique_clusters = sorted(set(cluster for clusters in grouped["cluster"] for cluster in clusters))

    fig, ax = plt.subplots(figsize=(6.8, 6.8))
    fig.patch.set_facecolor("white")
    ax.set_facecolor("white")

    minx, miny, maxx, maxy = grouped.total_bounds
    xpad = (maxx - minx) * 0.08
    ypad = (maxy - miny) * 0.08
    ax.set_xlim(minx - xpad, maxx + xpad)
    ax.set_ylim(miny - ypad, maxy + ypad)

    if use_basemap:
        try:
            ctx.add_basemap(
                ax,
                source=ctx.providers.CartoDB.PositronNoLabels,
                attribution=False,
                zorder=0,
            )
        except Exception:
            ctx.add_basemap(
                ax,
                source=ctx.providers.CartoDB.Positron,
                attribution=False,
                zorder=0,
            )

    for _, row in grouped.iterrows():
        x, y = row.geometry.x, row.geometry.y
        clusters = row.cluster
        for offset, cluster in enumerate(reversed(clusters)):
            size = 95 - offset * 30
            ax.scatter(
                x,
                y,
                s=size,
                color=cluster_colors.get(cluster, "#999999"),
                edgecolors=cluster_edge.get(cluster, "black"),
                linewidth=0.55,
                marker=cluster_markers.get(cluster, "o"),
                alpha=0.95,
                zorder=zorder_map.get(cluster, 1),
            )

    legend_elements = [
        Line2D(
            [0],
            [0],
            marker=cluster_markers[cluster],
            color="w",
            label=f"Cluster {cluster}",
            markerfacecolor=cluster_colors[cluster],
            markeredgecolor=cluster_edge[cluster],
            markersize=8,
            linewidth=0,
        )
        for cluster in unique_clusters
    ]

    legend = ax.legend(
        handles=legend_elements,
        title="Cluster",
        loc="upper right",
        fontsize=8,
        title_fontsize=9,
        frameon=True,
        facecolor="white",
        edgecolor="lightgray",
        framealpha=0.95,
    )
    legend.get_frame().set_linewidth(0.8)

    if show_axes:
        xlim = ax.get_xlim()
        ylim = ax.get_ylim()
        xticks = np.linspace(xlim[0], xlim[1], 4)
        yticks = np.linspace(ylim[0], ylim[1], 4)

        xpoints = gpd.GeoSeries([Point(x, ylim[0]) for x in xticks], crs=3857).to_crs(epsg=4326)
        ypoints = gpd.GeoSeries([Point(xlim[0], y) for y in yticks], crs=3857).to_crs(epsg=4326)

        ax.set_xticks(xticks)
        ax.set_yticks(yticks)
        ax.set_xticklabels([f"{point.x:.2f}°" for point in xpoints], fontsize=8)
        ax.set_yticklabels([f"{point.y:.2f}°" for point in ypoints], fontsize=8)
        ax.set_xlabel("Longitude", fontsize=9)
        ax.set_ylabel("Latitude", fontsize=9)

        for spine in ax.spines.values():
            spine.set_edgecolor("lightgray")
            spine.set_linewidth(0.8)
    else:
        ax.set_xticks([])
        ax.set_yticks([])
        ax.set_xlabel("")
        ax.set_ylabel("")
        for spine in ax.spines.values():
            spine.set_visible(False)

    plt.tight_layout()

    out_pdf = out_dir / f"{name}.pdf"
    out_png = out_dir / f"{name}.png"
    plt.savefig(out_pdf, bbox_inches="tight", dpi=600)
    plt.savefig(out_png, bbox_inches="tight", dpi=300)

    if show:
        plt.show()
    else:
        plt.close(fig)

    print(f"Saved: {out_pdf}")
