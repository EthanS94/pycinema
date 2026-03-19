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
                'start_date': '',
                'end_date': ''
            },
            outputs={
                'images': {}
            }
        )

    def _update(self):

        table = self.inputs.table.get()
        start_date = self.inputs.start_date.get()
        end_date = self.inputs.end_date.get()

        # Needs an input
        quantile = 0.95

        # Doesn't need an input
        stipple_size = 10
        stipple_spacing = 2

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

        # defs that may be useful
        #quantile(ds, quantile)
        #matplotlib_plot_to_image(fig)
        #stipple_compare(model_quants, obs_quants)

        # Just compare two historical models for now to figure out implementation
        quants_ds = []
        for row in historical_models[:2]:
            quants_ds.append(row[ds_col].quantile(0.95, dim="time").compute())
        quants_ds = xr.concat(quants_ds, dim="model")
        print('model quantiles calculated')

        obs_quants = []
        for row in historical_models[2:]:
            obs_quants.append(row[ds_col].quantile(0.95, dim="time").compute())
        obs_quants = xr.concat(obs_quants, dim="model")
        obs_quants_min = obs_quants.min(dim="model")
        obs_quants_max = obs_quants.max(dim="model")
        print('observational quantiles calculated')

        mask = get_stipple_mask(quants_ds, obs_quants_min, obs_quants_max)
        print('mask created')
        lons = mask.lon.values
        lats = mask.lat.values
        lon_grid, lat_grid = np.meshgrid(lons, lats)

        f, axes = plt.subplots(2, 1, figsize=(30, 40), facecolor='w')
        cmap = "BuPu"
        quantile = 0.95
        robust = True

        fz = 26
        pad = 20
        stipple_size = 30
        stipple_spacing = 2

        for index, model in enumerate(quants_ds.model.values):
            print(index)
            print(model)
            #quants_ds["one_day_pr"].rename(cb_labels[0]).sel(model=model, quantile=quantile).plot.imshow(ax=axes[index,0], levels=one_day_levels, transform=transform, cmap=cmap, robust=robust)
            quants_ds['pr'].sel(model=model).plot.imshow(ax=axes[index], robust=robust, cmap=cmap)
            print(f"cmap plot {index} done")
            model_mask = get_stipple_mask(quants_ds.sel(model=model), obs_quants_min, obs_quants_max)

            t0 = time.time()
            print(model_mask["pr"])
            m = model_mask["pr"].isel(
                lat=slice(None, None, stipple_spacing),
                lon=slice(None, None, stipple_spacing)
            ).values
            print("mask:", time.time() - t0)
            
            t0 = time.time()
            lon_sub = lon_grid[::stipple_spacing, ::stipple_spacing]
            print("lon_sub:", time.time() - t0)
            
            t0 = time.time()
            stipple_lons = lon_sub[m]
            print("stipple_lons:", time.time() - t0)
            
            t0 = time.time()
            lat_sub = lat_grid[::stipple_spacing, ::stipple_spacing]
            print("lat_sub:", time.time() - t0)
            
            t0 = time.time()
            stipple_lats = lat_sub[m]
            print("stipple_lats:", time.time() - t0)

            axes[index].scatter(stipple_lons, stipple_lats, s=stipple_size, color="black", alpha=1, marker="o")

        f.savefig("figure.png")

        self.outputs.images.set([])
