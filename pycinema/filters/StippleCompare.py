from pycinema import Filter, Image

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

        # Just compare two historical models for now to figure out implementation
        row = historical_models[0]
        quants_ds = row[ds_col].quantile(quantile_value, dim="time").compute()

        row = observations[0]
        obs_quants = row[ds_col].quantile(quantile_value, dim="time").compute()
        obs_quants_min = obs_quants.min(dim="model")
        obs_quants_max = obs_quants.max(dim="model")

        mask = get_stipple_mask(quants_ds, obs_quants_min, obs_quants_max)
        lons = mask.lon.values
        lats = mask.lat.values
        lon_grid, lat_grid = np.meshgrid(lons, lats)

        f, axes = plt.subplots(1, 1, figsize=(30, 20), facecolor='w')
        cmap = "BuPu"
        robust = True

        fz = 26
        pad = 20
        stipple_size = 30
        stipple_spacing = 2

        quants_ds['pr'].plot.imshow(ax=axes, robust=robust, cmap=cmap)
        model_mask = get_stipple_mask(quants_ds, obs_quants_min, obs_quants_max)

        m = model_mask["pr"].isel(
            lat=slice(None, None, stipple_spacing),
            lon=slice(None, None, stipple_spacing)
        ).values

        lon_sub = lon_grid[::stipple_spacing, ::stipple_spacing]
        stipple_lons = lon_sub[m]

        lat_sub = lat_grid[::stipple_spacing, ::stipple_spacing]
        stipple_lats = lat_sub[m]

        axes.scatter(stipple_lons, stipple_lats, s=stipple_size, color="black", alpha=1, marker="o")

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
