from pycinema import Filter, Image

import cartopy.crs as ccrs
import cftime
import datetime as dt
import numpy as np
import pandas as pd
import re
import sys
import xarray as xr
import matplotlib.pyplot as plt
import matplotlib

# imports for land mask
import cartopy.feature as cfeature
from shapely.geometry import Point
from shapely.prepared import prep
from shapely.ops import unary_union

import time

from pycinema import getTableExtent

def build_land_mask(lons, lats):
    """
    Return a 2D boolean mask that is True over land and False over ocean.
    Assumes lons/lats are 1D coordinate arrays.
    """
    land_geom = unary_union(list(cfeature.NaturalEarthFeature(
        "physical", "land", "110m"
    ).geometries()))
    land_geom = prep(land_geom)

    lon_grid, lat_grid = np.meshgrid(lons, lats)

    mask = np.zeros(lon_grid.shape, dtype=bool)
    for j in range(lat_grid.shape[0]):
        for i in range(lon_grid.shape[1]):
            mask[j, i] = land_geom.contains(Point(float(lon_grid[j, i]), float(lat_grid[j, i])))

    return mask

def collapse_member_dims(x, mean_dims=("members", "member", "realization")):
    dims_to_mean = [d for d in mean_dims if d in x.dims]
    if dims_to_mean:
        x = x.mean(dim=dims_to_mean)
    return x

def unique_in_order(values):
    seen = set()
    out = []
    for v in values:
        if v not in seen:
            seen.add(v)
            out.append(v)
    return out

def build_index_lookup(values):
    return {value: i for i, value in enumerate(values)}

def score_orientation(plot_entries, unique_values, rows_dim, cols_dim, grid_dim=None):
    """
    Score a layout orientation.

    Lower is better.

    The score penalizes:
    - empty cells
    - sparse columns more heavily than sparse rows
    - completely empty columns/rows
    - uneven fill patterns

    This helps avoid layouts where a scenario becomes a lonely mostly-empty column.
    """
    if grid_dim is None:
        grid_values = [None]
    else:
        grid_values = unique_values[grid_dim]

    total_score = 0.0

    for grid_value in grid_values:
        row_values = unique_values[rows_dim]
        col_values = unique_values[cols_dim]

        row_lookup = build_index_lookup(row_values)
        col_lookup = build_index_lookup(col_values)

        occupancy = np.zeros((len(row_values), len(col_values)), dtype=int)

        for entry in plot_entries:
            if grid_dim is not None and entry[grid_dim] != grid_value:
                continue

            r = row_lookup[entry[rows_dim]]
            c = col_lookup[entry[cols_dim]]
            occupancy[r, c] = 1

        row_fills = occupancy.sum(axis=1)
        col_fills = occupancy.sum(axis=0)

        empty_cells = occupancy.size - occupancy.sum()

        sparse_rows = np.sum(row_fills <= 1)
        sparse_cols = np.sum(col_fills <= 1)

        empty_rows = np.sum(row_fills == 0)
        empty_cols = np.sum(col_fills == 0)

        # unevenness
        row_std = float(np.std(row_fills)) if len(row_fills) > 1 else 0.0
        col_std = float(np.std(col_fills)) if len(col_fills) > 1 else 0.0

        # Weight sparse columns more heavily than sparse rows.
        # This tends to prefer scenario-as-rows if a scenario column is mostly empty.
        score = (
            1.0 * empty_cells +
            1.5 * sparse_rows +
            4.0 * sparse_cols +
            3.0 * empty_rows +
            6.0 * empty_cols +
            0.5 * row_std +
            1.0 * col_std
        )

        total_score += score

    return total_score

def choose_layout(plot_entries, unique_values, priority=("dataset", "scenario", "rc")):
    """
    Decide which dimension becomes rows, columns, and grid (separate figures).

    Rules:
    - only dimensions with >1 unique value are considered active
    - 0 active dims -> single axes
    - 1 active dim  -> rows only
    - 2 active dims -> choose better of the two row/col orientations
    - 3 active dims -> keep the third priority dim as separate figure grid,
                       then choose better row/col orientation for the first two
    """
    counts = {k: len(v) for k, v in unique_values.items()}
    active_dims = [dim for dim in priority if counts.get(dim, 1) > 1]

    layout = {
        "rows_dim": None,
        "cols_dim": None,
        "grid_dim": None,
        "nrows": 1,
        "ncols": 1,
        "ngrids": 1,
        "active_dims": active_dims,
        "counts": counts,
    }

    if len(active_dims) == 0:
        return layout

    if len(active_dims) == 1:
        layout["rows_dim"] = active_dims[0]
        layout["nrows"] = counts[active_dims[0]]
        return layout

    if len(active_dims) == 2:
        d1, d2 = active_dims

        score_12 = score_orientation(plot_entries, unique_values, d1, d2, None)
        score_21 = score_orientation(plot_entries, unique_values, d2, d1, None)

        if score_12 <= score_21:
            layout["rows_dim"] = d1
            layout["cols_dim"] = d2
        else:
            layout["rows_dim"] = d2
            layout["cols_dim"] = d1

        layout["nrows"] = counts[layout["rows_dim"]]
        layout["ncols"] = counts[layout["cols_dim"]]
        return layout

    # Three or more active dims: keep the third priority dim as grid,
    # and score the two row/col orientations of the first two dims.
    d1, d2, d3 = active_dims[:3]

    score_12 = score_orientation(plot_entries, unique_values, d1, d2, d3)
    score_21 = score_orientation(plot_entries, unique_values, d2, d1, d3)

    if score_12 <= score_21:
        layout["rows_dim"] = d1
        layout["cols_dim"] = d2
    else:
        layout["rows_dim"] = d2
        layout["cols_dim"] = d1

    layout["grid_dim"] = d3
    layout["nrows"] = counts[layout["rows_dim"]]
    layout["ncols"] = counts[layout["cols_dim"]]
    layout["ngrids"] = counts[d3]

    print("Layout orientation scores:")
    print(f"  rows={d1}, cols={d2}, grid={d3} -> {score_12}")
    print(f"  rows={d2}, cols={d1}, grid={d3} -> {score_21}")

    return layout

def set_outer_titles(fig, axes, layout, unique_values, grid_value=None, fz=26, pad=20):
    rows_dim = layout["rows_dim"]
    cols_dim = layout["cols_dim"]
    grid_dim = layout["grid_dim"]

    if cols_dim is not None:
        for col_idx, col_value in enumerate(unique_values[cols_dim]):
            axes[0, col_idx].set_title(str(col_value), fontsize=fz, pad=pad)

    if rows_dim is not None:
        for row_idx, row_value in enumerate(unique_values[rows_dim]):
            axes[row_idx, 0].text(
                -0.15,
                0.5,
                str(row_value),
                rotation=90,
                va="center",
                ha="right",
                transform=axes[row_idx, 0].transAxes,
                fontsize=22
            )

    if grid_dim is not None and grid_value is not None:
        fig.text(
            0.5,
            0.97,
            f"{grid_value}",
            ha="center",
            va="top",
            fontsize=fz
        )

def hide_unused_axes(axes, used_positions):
    nrows, ncols = axes.shape
    for r in range(nrows):
        for c in range(ncols):
            if (r, c) not in used_positions:
                axes[r, c].set_visible(False)

class WinkelTripel(ccrs._WarpedRectangularProjection):
	"""
	Winkel-Tripel projection implementation for Cartopy
	"""

	def __init__(self, central_longitude=0.0, central_latitude=0.0, globe=None):
		globe = globe or ccrs.Globe(semimajor_axis=ccrs.WGS84_SEMIMAJOR_AXIS)
		proj4_params = [('proj', 'wintri'),
						('lon_0', central_longitude),
						('lat_0', central_latitude)]

		super(WinkelTripel, self).__init__(proj4_params, central_longitude, globe=globe)

	@property
	def threshold(self):
		return 1e4

class QuantilePlot(Filter):
    def __init__(self):
        super().__init__(
            inputs={
                'table': [[]],
            },
            outputs={
                'images': {}
            }
        )

    def _update(self):

        table = self.inputs.table.get()

        tableExtent = getTableExtent(table)
        if tableExtent[0] < 1 or tableExtent[1] < 1:
            return self.outputs.images.set([])

        # get columns
        headers = table[0]
        col_idx = {h: i for i, h in enumerate(headers)}

        ds_col = col_idx.get("xr_dataset")
        if ds_col is None:
            print("No xarray dataset column found in table.")
            self.outputs.images.set([])
            return 1

        hist_col = col_idx.get("Collection")
        if hist_col is None:
            print("No collection column found in table.")
            self.outputs.images.set([])
            return 1

        scen_col = col_idx.get("Scenario")
        if scen_col is None:
            print("No Scenario column found in table.")
            self.outputs.images.set([])
            return 1

        rc_col = col_idx.get("Metric")
        if rc_col is None:
            print("No accumulation column found in table.")
            self.outputs.images.set([])
            return 1

        # get model_name from table
        mn_col = next((i for i, h in enumerate(table[0]) if h == "Dataset"), None)
        if mn_col is None:
            print("Model name column (Dataset) not found in input table")
            self.outputs.images.set([])
            return 1

        # get lat from table
        lat_col = next((i for i, h in enumerate(table[0]) if h == "Latitude"), None)
        if lat_col is None:
            self.outputs.images.set([])
            return 1
        lats = table[1][lat_col]

        # get lon from table
        lon_col = next((i for i, h in enumerate(table[0]) if h == "Longitude"), None)
        if lon_col is None:
            self.outputs.images.set([])
            return 1
        lons = table[1][lon_col]

        # create table to use for subplot orientation
        subplot_counts = {
            "dataset": 0,
            "scenario": 0,
            "rc": 0,
        }
        dataset_subplots = []
        scenario_subplots = []
        rc_subplots = []
        for row in table[1:]:
            if row[mn_col] not in dataset_subplots:
                subplot_counts["dataset"] += 1
                dataset_subplots.append(row[mn_col])
            if row[scen_col] not in scenario_subplots:
                subplot_counts["scenario"] += 1
                scenario_subplots.append(row[scen_col])
            if row[rc_col] not in rc_subplots:
                subplot_counts["rc"] += 1
                rc_subplots.append(row[rc_col])

        # Active dimensions in plot
        active_dims = [name for name, count in subplot_counts.items() if count > 1]

        quantile_value = 0.95

        # For each accumulation, store a list of plotting entries:
        # {"label": ..., "q": ..., "dataset": ..., "scenario": ..., "rc": ...}
        quants_ds_dict = {}

        # -----------------------------
        # model prep
        # -----------------------------
        gen_time_string = True
        for row in table[1:]:
            rc_raw = row[rc_col]
            rc_match = re.match(r"(\d+)", str(rc_raw))
            if rc_match is None:
                print(f"Could not parse accumulation from Metric value: {rc_raw}")
                continue
            rc = int(rc_match.group(1))

            if rc not in quants_ds_dict:
                quants_ds_dict[rc] = []

            # Rechunk so time is a single chunk (improves performance of quantile over time)
            ds = row[ds_col].chunk({"time": -1})

            # one time only -- generate time string to use in plot
            if gen_time_string:
                tmin = ds.time.min().item()
                tmax = ds.time.max().item()

                tmin_str = f"{tmin.year:04d}-{tmin.month:02d}-{tmin.day:02d}"
                tmax_str = f"{tmax.year:04d}-{tmax.month:02d}-{tmax.day:02d}"
                if tmin_str != tmax_str:
                    title_time = str(tmin_str + ' -- ' + tmax_str)
                else:
                    title_time = str(tmin_str)

                gen_time_string = False

            # Compute quantile once for the full dataset
            print(f"Calculating quantile for {row[mn_col]}")
            q = ds.quantile(quantile_value, dim="time").compute()
            # If the dataset has members, collapse them to the mean
            q = collapse_member_dims(q)

            if "model" in q.dims:
                # One dataset, many models
                for model_name in q.model.values:
                    quants_ds_dict[rc].append({
                        "label": str(model_name),
                        "q": q.sel(model=model_name),
                        "dataset": str(model_name),
                        "scenario": str(row[scen_col]),
                        "rc": str(row[rc_col]),
                    })
            else:
                # One dataset, one model
                quants_ds_dict[rc].append({
                    "label": str(row[mn_col]),
                    "q": q,
                    "dataset": str(row[mn_col]),
                    "scenario": str(row[scen_col]),
                    "rc": str(row[rc_col]),
                })

        # -----------------------------
        # Determine lon/lat once from the first available entry
        # -----------------------------
        lons = None
        lats = None
        for rc, entries in quants_ds_dict.items():
            if not entries:
                continue
            first_q = entries[0]["q"]
            lons = first_q.lon.values
            lats = first_q.lat.values
            break

        if lons is None or lats is None:
            self.outputs.images.set([])
            return 1

        # build land mask
        lons_mask = ((lons + 180) % 360) - 180
        land_mask = build_land_mask(lons_mask, lats)

        # -----------------------------
        # Build unique values from actual plotting entries
        # -----------------------------
        plot_entries = []
        for rc, entries in quants_ds_dict.items():
            plot_entries.extend(entries)

        if not plot_entries:
            self.outputs.images.set([])
            return 1

        unique_values = {
            "dataset": unique_in_order(entry["dataset"] for entry in plot_entries),
            "scenario": unique_in_order(entry["scenario"] for entry in plot_entries),
            "rc": unique_in_order(entry["rc"] for entry in plot_entries),
        }

        layout = choose_layout(plot_entries, unique_values, priority=("dataset", "scenario", "rc"))

        print("Unique plotting values:")
        print(unique_values)
        print("Chosen layout:")
        print(layout)

        row_lookup = (
            build_index_lookup(unique_values[layout["rows_dim"]])
            if layout["rows_dim"] is not None else {}
        )
        col_lookup = (
            build_index_lookup(unique_values[layout["cols_dim"]])
            if layout["cols_dim"] is not None else {}
        )
        grid_lookup = (
            build_index_lookup(unique_values[layout["grid_dim"]])
            if layout["grid_dim"] is not None else {}
        )

        if layout["nrows"] == 0 or layout["ncols"] == 0 or layout["ngrids"] == 0:
            self.outputs.images.set([])
            return 1

        #proj = WinkelTripel()
        proj = ccrs.PlateCarree()
        transform = ccrs.PlateCarree()

        cmap = "BuPu"
        robust = True

        fz = 26
        pad = 20
        stipple_size = 1
        stipple_spacing = 2

        # Size scales with actual grid shape
        row_size = layout["ncols"] * 10
        column_size = layout["nrows"] * 5

        figures = []
        for _ in range(layout["ngrids"]):
            f, axes = plt.subplots(
                layout["nrows"],
                layout["ncols"],
                figsize=(row_size, column_size),
                facecolor="w",
                squeeze=False,
                subplot_kw=dict(projection=proj),
            )
            figures.append((f, axes))

        # Extent for imshow
        x0 = float(lons.min())
        x1 = float(lons.max())
        y0 = float(lats.min())
        y1 = float(lats.max())
        img_extent = [x0, x1, y0, y1]

        print("Plotting...")
        used_positions_per_grid = [set() for _ in range(layout["ngrids"])]

        for entry in plot_entries:
            if layout["rows_dim"] is None:
                row_idx = 0
            else:
                row_idx = row_lookup[entry[layout["rows_dim"]]]

            if layout["cols_dim"] is None:
                col_idx = 0
            else:
                col_idx = col_lookup[entry[layout["cols_dim"]]]

            if layout["grid_dim"] is None:
                grid_idx = 0
            else:
                grid_idx = grid_lookup[entry[layout["grid_dim"]]]

            f, axes = figures[grid_idx]
            ax = axes[row_idx, col_idx]

            label = entry["label"]
            model = entry["q"]

            print(f"imshow on {label} -> grid={grid_idx}, row={row_idx}, col={col_idx}")
            data_land = model["pr"].where(land_mask)

            data_land.plot.imshow(
                ax=ax,
                robust=robust,
                cmap=cmap,
                transform=transform
            )

            print(f"applying coastlines on {label}")
            ax.coastlines(resolution="110m")
            used_positions_per_grid[grid_idx].add((row_idx, col_idx))

        images = []

        for grid_idx, (f, axes) in enumerate(figures):
            grid_value = None
            if layout["grid_dim"] is not None:
                grid_value = unique_values[layout["grid_dim"]][grid_idx]

            set_outer_titles(
                f,
                axes,
                layout,
                unique_values,
                grid_value=grid_value,
                fz=fz,
                pad=pad,
            )

            hide_unused_axes(axes, used_positions_per_grid[grid_idx])

            f.suptitle(
                f"{int(quantile_value * 100)}th Percentile Precip. Metrics ({title_time})",
                fontsize=35,
                y=0.93 if grid_value is not None else 0.98
            )

            f.tight_layout(rect=[0.04, 0.04, 0.98, 0.90])

            f.canvas.draw()

            # Get width and height
            w, h = f.canvas.get_width_height()

            # Convert to numpy array (RGBA)
            img = np.frombuffer(f.canvas.buffer_rgba(), dtype=np.uint8)
            img = img.reshape((h, w, 4))

            image = Image()
            image.channels = {"rgba": img}
            images.append(image)

            plt.close(f)

        self.outputs.images.set(images)

        print("Done plotting.")
