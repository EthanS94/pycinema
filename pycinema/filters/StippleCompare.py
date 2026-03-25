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

import time

from pycinema import getTableExtent

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

def get_stipple_mask(model_da, lower_da, upper_da):
    return (model_da >= lower_da) & (model_da <= upper_da)

class StippleCompare(Filter):
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
        if tableExtent[0]<1 or tableExtent[1]<1:
            return self.outputs.images.set([])

        # get column with xarray datasets
        ds_col = next((i for i, h in enumerate(table[0]) if h == "xr_dataset"), None)
        if ds_col is None:
            print("No xarray dataset column found in table.")
            self.outputs.images.set([])
            return 1

        # get historical column
        hist_col = next((i for i, h in enumerate(table[0]) if h == "Historical"), None)
        if hist_col is None:
            print("No historical column found in table.")
            self.outputs.images.set([])
            return 1

        # get rolling_accumulation from table
        rc_col = next((i for i, h in enumerate(table[0]) if h == "Accumulation"), None)
        if rc_col is None:
            self.outputs.table.set([[]])
            return 1

        historical_models = []
        observations = []
        ssp_245 = []
        ssp_370 = []

        for row in table[1:]:
            if row[hist_col] == 'model':
                historical_models.append(row)
            elif row[hist_col] == 'observational':
                observations.append(row)
            else:
                pass

        quantile_value = 0.95

        # Organize ds into 1, 3, and 5 day accumulations
        quants_ds_dict = {1: [], 3: [], 5: []}
        for row in historical_models:
            rolling_c = row[rc_col]
            rolling_c = int(rolling_c.split(' ')[0])
            quants_ds_dict[rolling_c].append(row[ds_col].quantile(quantile_value, dim="time").compute())

        # Organize ds into 1, 3, and 5 day accumulations
        obs_ds_dict = {1: None, 3: None, 5: None}
        obs_min_dict = {1: None, 3: None, 5: None}
        obs_max_dict = {1: None, 3: None, 5: None}
        for row in observations:
            rolling_c = row[rc_col]
            rolling_c = int(rolling_c.split(' ')[0])
            obs_ds_dict[rolling_c] = (row[ds_col].quantile(quantile_value, dim="time").compute())
            obs_min_dict[rolling_c] = (obs_ds_dict[rolling_c].min(dim="model"))
            obs_max_dict[rolling_c] = (obs_ds_dict[rolling_c].max(dim="model"))

        mask_dict = {1: [], 3: [], 5: []}
        calc_latlons = True
        for rc, models in quants_ds_dict.items():
            model_count = 0
            for model in models:
                mask_dict[rc].append(get_stipple_mask(model, obs_min_dict[rc], obs_max_dict[rc]))
                # calc mask lat lon once, can we assume they should be the same for all?
                if calc_latlons is True:
                    lons = mask_dict[rc][0].lon.values
                    lats = mask_dict[rc][0].lat.values
                    lon_grid, lat_grid = np.meshgrid(lons, lats)
                    calc_latlons = False

        # subplot rows is accumulation (1 row for each accumulation value)
        subplot_dim_row = sum(1 for v in quants_ds_dict.values() if v)

        # subplot column is the number of models per accumulation value
        subplot_dim_column = max(len(quants_ds_dict[1]), len(quants_ds_dict[3]), len(quants_ds_dict[5]))

        # each subplot will have this size
        row_size = subplot_dim_row * 20
        column_size = subplot_dim_column * 10

        proj = WinkelTripel()
        f, axes = plt.subplots(subplot_dim_column, subplot_dim_row, figsize=(row_size, column_size), facecolor='w', squeeze=False, subplot_kw=dict(projection=proj))
        cmap = "BuPu"
        robust = True

        transform = ccrs.PlateCarree()
        fz = 26
        pad = 20
        stipple_size = 30
        stipple_spacing = 2

        rc_count = 0
        for rc, models in quants_ds_dict.items():
            model_count = 0
            for model in models:
                model['pr'].plot.imshow(ax=axes[model_count, rc_count], robust=robust, cmap=cmap, transform=transform)
                model_mask = mask_dict[rc][model_count]

                m = model_mask["pr"].isel(
                    lat=slice(None, None, stipple_spacing),
                    lon=slice(None, None, stipple_spacing)
                ).values

                lon_sub = lon_grid[::stipple_spacing, ::stipple_spacing]
                stipple_lons = lon_sub[m]

                lat_sub = lat_grid[::stipple_spacing, ::stipple_spacing]
                stipple_lats = lat_sub[m]

                axes[model_count, rc_count].scatter(stipple_lons, stipple_lats, s=stipple_size, color="black", alpha=1, marker="o", transform=transform)

                axes[0, 0].text(-0.2, 0.1 + (-1.2*model_count), model.attrs.get("title"), rotation=90, transform=axes[0, 0].transAxes, fontsize=22)

                axes[model_count, rc_count].coastlines()

                model_count += 1

            axes[0, rc_count].set_title(f"{rc}-Day Precp.", fontsize=fz, pad=pad)

            rc_count += 1

        f.suptitle(f"{int(quantile_value*100)}th Percentile Precip. Metrics for CMIP6 Datasets", fontsize=45)

        f.canvas.draw()

        # Get width and height
        w, h = f.canvas.get_width_height()

        # Convert to numpy array (RGBA)
        img = np.frombuffer(f.canvas.buffer_rgba(), dtype=np.uint8)
        img = img.reshape((h, w, 4))

        image = Image()
        chans = {}
        chans['rgba'] = img
        image.channels = chans

        self.outputs.images.set([image])
