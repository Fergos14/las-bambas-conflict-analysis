from __future__ import annotations

import math
import os
import tempfile
import time
from pathlib import Path

import geopandas as gpd
import numpy as np
import pandas as pd
import rasterio
import requests
from osgeo import gdal
from shapely.geometry import shape as shp_shape

gdal.UseExceptions()


def _to_gdf_4326(geom):
    if isinstance(geom, gpd.GeoDataFrame):
        gdf = geom.copy()
    elif isinstance(geom, gpd.GeoSeries):
        gdf = gpd.GeoDataFrame(geometry=geom)
    elif isinstance(geom, dict) and geom.get("type"):
        gdf = gpd.GeoDataFrame(geometry=[shp_shape(geom)])
    else:
        gdf = gpd.GeoDataFrame(geometry=[geom])

    if gdf.crs is None:
        gdf.set_crs(4326, inplace=True)
    return gdf.to_crs(4326)


def _safe_union_all(geometries):
    valid_geometries = geometries.dropna()
    if valid_geometries.empty:
        raise ValueError("The input geometry is empty after removing null shapes.")

    union_all_method = getattr(valid_geometries, "union_all", None)
    if callable(union_all_method):
        return union_all_method()

    return valid_geometries.unary_union


def _prepare_aoi_gdf(geom):
    gdf = _to_gdf_4326(geom)
    gdf = gdf[gdf.geometry.notna() & ~gdf.geometry.is_empty].copy()
    if gdf.empty:
        raise ValueError("The input AOI does not contain valid geometries.")

    if not gdf.geometry.is_valid.all():
        gdf["geometry"] = gdf.geometry.buffer(0)

    dissolved_geometry = _safe_union_all(gdf.geometry)
    return gpd.GeoDataFrame(geometry=[dissolved_geometry], crs=gdf.crs), gdf


def _infer_reference_label(source_gdf):
    for column in ("Year", "year"):
        if column in source_gdf.columns:
            values = pd.Series(source_gdf[column]).dropna().unique()
            if len(values) == 1:
                value = values[0]
                if isinstance(value, (int, np.integer)):
                    return f"ref_{int(value)}"
                if isinstance(value, float) and float(value).is_integer():
                    return f"ref_{int(value)}"
                return f"ref_{str(value).replace(' ', '_')}"

    xmin, ymin, xmax, ymax = source_gdf.total_bounds
    return (
        "aoi_"
        f"{abs(int(round(xmin * 1000)))}_"
        f"{abs(int(round(ymin * 1000)))}_"
        f"{abs(int(round(xmax * 1000)))}_"
        f"{abs(int(round(ymax * 1000)))}"
    )


def _fetch_tile_dict(year, initiative="peru", base="https://plataforma.agua.mapbiomas.org"):
    url = f"{base}/api/classification/map/{year}?initiative={initiative}"
    response = requests.get(url, timeout=120)
    response.raise_for_status()
    data = response.json()
    out = {key: value["url"] for key, value in data.items() if isinstance(value, dict) and "url" in value}
    if not out:
        raise ValueError(f"No layers found for {year} ({url})")
    return out


def _filter_layers(layer_dict, include_layers=None, exclude_layers=None):
    filtered_layers = dict(layer_dict)

    if include_layers is not None:
        include_set = {str(layer) for layer in include_layers}
        filtered_layers = {
            layer_name: layer_url
            for layer_name, layer_url in filtered_layers.items()
            if layer_name in include_set
        }

    if exclude_layers is not None:
        exclude_set = {str(layer) for layer in exclude_layers}
        filtered_layers = {
            layer_name: layer_url
            for layer_name, layer_url in filtered_layers.items()
            if layer_name not in exclude_set
        }

    return filtered_layers


def _pick_zoom_for_approx_res(lat_deg, target_res_m=30):
    lat_rad = math.radians(lat_deg)
    zoom = math.log2((156543.03392 * math.cos(lat_rad)) / max(0.01, target_res_m))
    return max(0, min(22, int(round(zoom))))


def _gdal_wms_xml(tiles_url, zoom):
    return f"""<GDAL_WMS>
  <Service name="TMS">
    <ServerUrl>{tiles_url.replace('{', '${').replace('}', '}')}</ServerUrl>
  </Service>
  <DataWindow>
    <UpperLeftX>-20037508.34</UpperLeftX>
    <UpperLeftY>20037508.34</UpperLeftY>
    <LowerRightX>20037508.34</LowerRightX>
    <LowerRightY>-20037508.34</LowerRightY>
    <TileLevel>{zoom}</TileLevel>
    <TileCountX>1</TileCountX>
    <TileCountY>1</TileCountY>
    <YOrigin>top</YOrigin>
  </DataWindow>
  <Projection>EPSG:3857</Projection>
  <BlockSizeX>256</BlockSizeX>
  <BlockSizeY>256</BlockSizeY>
  <BandsCount>4</BandsCount>
  <Cache/>
</GDAL_WMS>"""


def _tiles_to_bbox_tif(xml_path, bbox4326, out_tif):
    xmin, ymin, xmax, ymax = bbox4326
    src_ds = gdal.OpenEx(xml_path)
    if src_ds is None:
        raise RuntimeError(f"GDAL could not open the XML tile definition: {xml_path}")

    out_ds = gdal.Translate(
        out_tif,
        src_ds,
        options=gdal.TranslateOptions(
            projWin=[xmin, ymax, xmax, ymin],
            projWinSRS="EPSG:4326",
            format="GTiff",
        ),
    )
    src_ds = None

    if out_ds is None:
        raise RuntimeError(f"GDAL could not translate the tile subset to: {out_tif}")
    out_ds = None


def _warp_cut_equal_area(in_tif, aoi_geojson, out_tif, dst_srs="EPSG:6933", res_m=30):
    src_ds = gdal.OpenEx(in_tif)
    if src_ds is None:
        raise RuntimeError(f"GDAL could not open the intermediate raster: {in_tif}")

    out_ds = gdal.Warp(
        out_tif,
        src_ds,
        options=gdal.WarpOptions(
            dstSRS=dst_srs,
            xRes=res_m,
            yRes=res_m,
            cutlineDSName=aoi_geojson,
            cropToCutline=True,
            dstAlpha=True,
            resampleAlg="near",
        ),
    )
    src_ds = None

    if out_ds is None:
        raise RuntimeError(f"GDAL could not warp the raster to the AOI: {out_tif}")
    out_ds = None


def _area_m2_from_masked_tif(tif_path):
    with rasterio.open(tif_path) as src:
        alpha_idx = 4 if src.count >= 4 else None
        valid = (src.read(alpha_idx) > 0) if alpha_idx else (src.read(1) != src.nodata)
        resx, resy = src.res
        return int(np.count_nonzero(valid)) * abs(resx * resy), valid


def dynamic_water_tile_stats_by_geometry(
    geom,
    years=range(2007, 2025),
    target_res_m=30,
    out_dir=".",
    dst_equal_area="EPSG:6933",
    include_layers=None,
    exclude_layers=None,
    max_download_retries=3,
    retry_backoff_s=2.0,
    skip_failed_layers=False,
):
    """Download MapBiomas Agua layers and compute annual water-related areas."""
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    gdf, source_gdf = _prepare_aoi_gdf(geom)
    xmin, ymin, xmax, ymax = gdf.total_bounds
    lat0 = float(_safe_union_all(gdf.geometry).centroid.y)
    zoom = _pick_zoom_for_approx_res(lat0, target_res_m)
    reference_label = _infer_reference_label(source_gdf)

    tmp = tempfile.NamedTemporaryFile(suffix=".geojson", delete=False)
    tmp.close()
    gdf.to_file(tmp.name, driver="GeoJSON")

    rows = []
    try:
        for year in years:
            try:
                layers = _fetch_tile_dict(year)
            except Exception as exc:
                print(f"[{year}] no layers ({exc}); skipping.")
                continue

            layers = _filter_layers(
                layers,
                include_layers=include_layers,
                exclude_layers=exclude_layers,
            )
            if not layers:
                print(f"[{reference_label}] year {year}: no selected layers after filtering; skipping.")
                continue

            per_layer = {}
            union_mask = None
            sample_path = None

            for layer_name, tiles_url in layers.items():
                last_exception = None
                for attempt in range(1, max_download_retries + 1):
                    try:
                        with tempfile.TemporaryDirectory() as tmp_dir:
                            xml = Path(tmp_dir) / f"{layer_name}.xml"
                            xml.write_text(_gdal_wms_xml(tiles_url, zoom), encoding="utf-8")

                            bbox_tif = Path(tmp_dir) / f"{layer_name}_bbox.tif"
                            _tiles_to_bbox_tif(str(xml), (xmin, ymin, xmax, ymax), str(bbox_tif))

                            out_tif = out_dir / f"{reference_label}_{layer_name}_{year}.tif"
                            _warp_cut_equal_area(
                                str(bbox_tif),
                                tmp.name,
                                str(out_tif),
                                dst_srs=dst_equal_area,
                                res_m=target_res_m,
                            )

                            area_m2, mask = _area_m2_from_masked_tif(str(out_tif))
                            per_layer[f"m2_{layer_name}"] = area_m2
                            union_mask = mask if union_mask is None else (union_mask | mask)
                            if sample_path is None:
                                sample_path = str(out_tif)
                        last_exception = None
                        break
                    except Exception as exc:
                        last_exception = exc
                        if attempt < max_download_retries:
                            wait_seconds = retry_backoff_s * attempt
                            print(
                                f"[{reference_label}] year {year}, layer '{layer_name}' "
                                f"failed on attempt {attempt}/{max_download_retries}; "
                                f"retrying in {wait_seconds:.1f}s."
                            )
                            time.sleep(wait_seconds)

                if last_exception is not None:
                    if skip_failed_layers:
                        print(
                            f"[{reference_label}] year {year}, layer '{layer_name}' "
                            f"skipped after {max_download_retries} attempts: {last_exception}"
                        )
                        continue

                    raise RuntimeError(
                        "Water tile processing failed for "
                        f"reference '{reference_label}', analysis year {year}, layer '{layer_name}'."
                    ) from last_exception

            if union_mask is not None and sample_path:
                with rasterio.open(sample_path) as src:
                    resx, resy = src.res
                    m2_total = int(np.count_nonzero(union_mask)) * abs(resx * resy)
            else:
                m2_total = 0

            rows.append({"year": int(year), **per_layer, "m2_total": m2_total})
    finally:
        try:
            os.unlink(tmp.name)
        except OSError:
            pass

    return pd.DataFrame(rows).sort_values("year").reset_index(drop=True)
