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

        quantile_value = 0.95

        # For each accumulation, store a list of plotting entries:
        # {"label": ..., "q": ..., "mask": ...}
        quants_ds_dict = {1: [], 3: [], 5: []}

        # -----------------------------
        # model prep
        # -----------------------------
        gen_time_string = True
        for row in table[1:]:
            rc = int(str(row[rc_col]).split(" ")[0])
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
                        "label": str(model_name + ' -- ' + row[scen_col]),
                        "q": q.sel(model=model_name)
                    })
            else:
                # One dataset, one model
                quants_ds_dict[rc].append({
                    "label": str(row[mn_col] + ' -- ' + row[scen_col]),
                    "q": q
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

        # subplot rows is accumulation count with data
        subplot_dim_row = sum(1 for v in quants_ds_dict.values() if v)

        # subplot columns is max number of models in any accumulation
        subplot_dim_column = max(len(quants_ds_dict[1]), len(quants_ds_dict[3]), len(quants_ds_dict[5]))
        if subplot_dim_row == 0 or subplot_dim_column == 0:
            self.outputs.images.set([])
            return 1

        row_size = subplot_dim_row * 20
        column_size = subplot_dim_column * 10

        #proj = WinkelTripel()
        proj = ccrs.PlateCarree()
        transform = ccrs.PlateCarree()

        cmap = "BuPu"
        robust = True

        fz = 26
        pad = 20
        stipple_size = 1
        stipple_spacing = 2

        f, axes = plt.subplots(
            subplot_dim_column,
            subplot_dim_row,
            figsize=(row_size, column_size),
            facecolor="w",
            squeeze=False,
            subplot_kw=dict(projection=proj),
        )

        # Extent for imshow
        x0 = float(lons.min())
        x1 = float(lons.max())
        y0 = float(lats.min())
        y1 = float(lats.max())
        img_extent = [x0, x1, y0, y1]

        print("Plotting...")
        rc_count = 0
        for rc, entries in quants_ds_dict.items():
            if not entries:
                continue

            for model_count, entry in enumerate(entries):
                model = entry["q"]
                label = entry["label"]
                ax = axes[model_count, rc_count]

                print(f"imshow on {label}")
                data_land = model["pr"].where(land_mask)

                data_land.plot.imshow(
                    ax=ax,
                    robust=robust,
                    cmap=cmap,
                    transform=transform
                )

                axes[model_count, 0].text(
                    -0.15,
                    0.5,
                    label,
                    rotation=90,
                    va="center",
                    ha="right",
                    transform=axes[model_count, 0].transAxes,
                    fontsize=22
                )

                print(f"applying coastlines on {label}")
                ax.coastlines(resolution="110m")

            axes[0, rc_count].set_title(f"{rc}-Day Precp.", fontsize=fz, pad=pad)
            rc_count += 1

        f.suptitle(
            f"{int(quantile_value * 100)}th Percentile Precip. Metrics ({title_time})",
            fontsize=35
        )

        f.canvas.draw()

        # Get width and height
        w, h = f.canvas.get_width_height()

        # Convert to numpy array (RGBA)
        img = np.frombuffer(f.canvas.buffer_rgba(), dtype=np.uint8)
        img = img.reshape((h, w, 4))

        image = Image()
        image.channels = {"rgba": img}

        self.outputs.images.set([image])

        print("Done plotting.")

        plt.close(f)
