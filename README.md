# Las Bambas Conflict Analysis

This repository documents the analytical workflow behind the reported results for the Las Bambas case study. The project is organized so that the notebooks read inputs from `Data/`, write reproducible outputs to `Results/`, and reuse shared Python utilities stored in `src/`.

## Structure

```text
.
|-- Code/
|   |-- Cluster_AssociationRules.ipynb
|   `-- Spatial_Analysis.ipynb
|-- src/
|   `-- las_bambas_analysis/
|       |-- cluster_plots.py
|       |-- paths.py
|       |-- spatial_figures.py
|       |-- spatial_geometry.py
|       `-- water.py
|-- Data/
|   |-- Conflicto_bambas.csv
|   |-- ReporteFechaxConflicto_bambas.csv
|   |-- geometriasxcasoxminabambas.gpkg
|   `-- Área en Operación Minera.geojson
|-- CITATION.cff
|-- environment.yml
|-- environment-lock.yml
|-- pyproject.toml
|-- requirements.txt
|-- requirements-lock.txt
`-- Results/
    |-- cluster_association_rules/
    `-- spatial_analysis/
```

## Inputs in `Data/`

The original source file names were preserved to maintain provenance and avoid breaking links to the underlying materials.

- `Conflicto_bambas.csv`: base conflict matrix by group. It includes identifiers (`Grupo`, `GrupoID`), case metadata, and the binary thematic variables used for clustering and association rules.
- `ReporteFechaxConflicto_bambas.csv`: time series of reports by `GrupoID` and `FechaReporte`, including conflict status and descriptive fields from the monthly monitoring process.
- `geometriasxcasoxminabambas.gpkg`: main geopackage used in the spatial analysis. The notebook reads the `Carretera`, `Mina`, `Puente`, `Rio_Quebrada`, and `Centros_Poblados` layers.
- `Área en Operación Minera.geojson`: mining operation polygons used as an additional spatial reference for land-cover and water analyses.

## Reusable Modules

The repository includes a lightweight Python package in `src/las_bambas_analysis/` to keep the notebooks shorter and easier to audit.

- `paths.py`: repository-root discovery and centralized output-path creation.
- `cluster_plots.py`: paper-style temporal and spatial cluster plotting helpers.
- `spatial_geometry.py`: buffer generation and yearly conflict-area construction.
- `spatial_figures.py`: minimalist polygon-map export helper.
- `water.py`: MapBiomas Agua tile download and yearly water-area statistics.

## Notebooks

### `Code/Spatial_Analysis.ipynb`

This notebook reconstructs the spatial and environmental trajectory of the Las Bambas case. Its sections follow the notebook headings:

- `Yearly Polygon Construction`: builds yearly conflict/influence polygons from the geopackage and the temporal report file.
- `Dynamic Visualization of Map Evolution`: prepares a time-enabled visualization of the conflict polygon.
- `Figures > Map Evolution`: exports yearly maps of the polygon and associated spatial features.
- `Figures > Link to Number of Population Centers`: relates influence area, active conflicts, and affected population centers.
- `MapBiomas > Land Cover`: extracts and plots land-cover classes for selected reference years.
- `MapBiomas > Figure: Map by Period`: exports land-cover maps for key years.
- `MapBiomas > Transitions`: summarizes year-to-year land-cover change and exports a transition dynamics figure.
- `Water`: downloads thematic layers, computes natural and mining-related water area, and exports comparison figures.

Inputs used:

- `Data/geometriasxcasoxminabambas.gpkg`
- `Data/ReporteFechaxConflicto_bambas.csv`
- `Data/Área en Operación Minera.geojson`

Main outputs in `Results/spatial_analysis/`:

- `maps/poligono_anual_bambas/`
- `figures/land_cover/`
- `maps/land_cover_clases_journal/`
- `figures/transiciones/`
- `figures/agua/`
- `intermediate/serie_temporal_poligonos.geojson`
- `intermediate/agua_tiles_out/`

Shared helpers imported from `src/las_bambas_analysis/`:

- `paths.py`
- `spatial_geometry.py`
- `spatial_figures.py`
- `water.py`

### `Code/Cluster_AssociationRules.ipynb`

This notebook covers the typological and temporal components of the conflict:

- `File Inputs`: loads the conflict matrix and the temporal report file.
- `Clusters > Method Comparison`: compares clustering techniques using Jaccard distance.
- `Final Hierarchical Cluster`: defines the final clustering solution used for substantive interpretation.
- `Temporal Visualization`: builds the yearly time series of conflicts by cluster.
- `Spatial Map`: links clusters to population centers and exports maps by period.
- `FP-Growth`: identifies frequent itemsets and association rules among conflict types.

Inputs used:

- `Data/Conflicto_bambas.csv`
- `Data/ReporteFechaxConflicto_bambas.csv`
- `Data/geometriasxcasoxminabambas.gpkg`

Main outputs in `Results/cluster_association_rules/`:

- `figures/cluster_time.pdf`
- `figures/cluster_time.png`
- `maps/clusters_temporales/`

Shared helpers imported from `src/las_bambas_analysis/`:

- `paths.py`
- `cluster_plots.py`

## Reproducibility

The repository provides four dependency files with different purposes:

- `environment.yml`: recommended setup file. It captures the curated environment that was validated for this repository.
- `environment-lock.yml`: exact `conda env export --no-builds` snapshot of the validated environment.
- `requirements.txt`: exact `pip` dependency list matching the validated environment.
- `requirements-lock.txt`: raw `pip freeze` snapshot from the validated environment, kept only for audit and traceability.

Recommended setup:

1. `conda env create -f environment.yml`
2. `conda activate las-bambas-analysis`

Optional secondary route:

1. Create or activate your own Python environment.
2. `pip install -r requirements.txt`

Then:

1. Open the notebooks in `Code/`.
2. Run the cells in order.
3. Both notebooks automatically detect the project root, import reusable helpers from `src/`, read inputs from `Data/`, and write outputs inside `Results/`.

Notes:

- The MapBiomas sections require prior Google Earth Engine authentication.
- Validated baseline: `Python 3.11`, `NumPy 2.4.3`, and `pandas 2.3.3`.
- The geospatial stack (`GDAL`, `GeoPandas`, `Fiona`, `Rasterio`, `Shapely`) is the most fragile part of the setup on Windows, so the curated `environment.yml` is the recommended installation path.
- The curated `environment.yml` keeps the compiled geospatial stack in `conda` and installs the remaining scientific and Earth Engine packages through `pip` inside the same environment because that combination proved more reliable than a single-step solver attempt.
- The `pip install -r requirements.txt` route is best treated as a secondary option for environments that can already resolve the compiled geospatial dependencies cleanly.
- `environment-lock.yml` and `requirements-lock.txt` are archival snapshots of the validated environment. They are useful for audit and traceability, but they are more verbose and less portable than the curated files.
- `requirements-lock.txt` is not intended as the primary installation file because `pip freeze` may contain local build references from the validating machine.
- Avoid running `pip install ...` inside the notebooks, because that can desynchronize compiled dependencies already installed in the active kernel.
- Both `environment.yml` and `requirements.txt` install the local package in editable mode (`-e .`) so the notebooks can reuse the shared modules.
- Outputs are written inside `Results/` so the project does not depend on external Colab-style paths.

## Citation

The repository includes a `CITATION.cff` file with the metadata of the associated study so citation information is available in a standard format for archival or public release.
