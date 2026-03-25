from pycinema import Filter, Image

import cftime
import datetime as dt
import numpy as np
import pandas as pd
import re
import sys
import xarray as xr

from pycinema import getTableExtent

ds_cached = None

def read_zarr_auto(path, max_points=2_000_000, **open_kwargs):
    ds = xr.open_zarr(
        path,
        chunks="auto",
        create_default_indexes=False,
        **open_kwargs,
    )

    lat_dim = "lat" if "lat" in ds.dims else None
    lon_dim = "lon" if "lon" in ds.dims else None

    if lat_dim and lon_dim:
        nlat = ds.sizes[lat_dim]
        nlon = ds.sizes[lon_dim]

        step = 1
        while (nlat // step) * (nlon // step) > max_points:
            step += 1

        ds = ds.isel(
            **{
                lat_dim: slice(None, None, step),
                lon_dim: slice(None, None, step),
            }
        )

    return ds

class ZarrToDS(Filter):
    def __init__(self):
        super().__init__(
            inputs={
                'table': [[]],
            },
            outputs={
                'table': [[]]
            }
        )

    def _update(self):

        table = self.inputs.table.get()
        tableExtent = getTableExtent(table)
        if tableExtent[0]<1 or tableExtent[1]<1:
            return self.outputs.table.set([])

        # get .zarr globs from table
        file_col = next((i for i, h in enumerate(table[0]) if h == "file"), None)
        if file_col is None:
            print("File column (file) not found in input table")
            self.outputs.table.set([])
            return 1

        # get rolling_cumulation from table
        rc_col = next((i for i, h in enumerate(table[0]) if h == "Accumulation"), None)
        if rc_col is None:
            print("Accumulation column (Acuumulation) not found in input table")
            self.outputs.table.set([])
            return 1

        ds_list = [['xr_dataset']]
        zarr_file = ''
        for row in table[1:]:
            # if zarr_file was just read, re-use the ds instead of reloading again
            if zarr_file == row[file_col]:
                rolling_c = row[rc_col]
                print(f'reading {zarr_file} at {rolling_c} accumulation...')
                rolling_c = int(rolling_c.split(' ')[0])
                ds = zarr_to_ds(zarr_file, rolling_c, reuse=True)
            else:
                zarr_file = row[file_col]
                rolling_c = row[rc_col]
                print(f'reading {zarr_file} at {rolling_c} accumulation...')
                rolling_c = int(rolling_c.split(' ')[0])
                ds = zarr_to_ds(zarr_file, rolling_c, reuse=False)
            if ds != None:
                ds_list.append([ds])
            else:
                ds_list.append([None])

        table = [input_row + ds_row for input_row, ds_row in zip(table, ds_list)]

        self.outputs.table.set(table)


def zarr_to_ds(zarr_path, rolling_c=int(1), reuse=False):
    """
    Returns: xarray dataset by reading in zarr_path
    """
    global ds_cached

    if reuse:
        ds = ds_cached
    else:
        try:
            ds = xr.open_zarr(zarr_path, decode_times=True)
            # Remove history var if it exists
            ds = ds.drop_vars("history", errors="ignore")
            # Select scenario if it exists
            if "scenario" in ds.dims:
                ds = ds.isel(scenario=0)
            # Normalize T12:00:0000's to T00:00:0000's so selection works better
            ds = ds.assign_coords(time=ds.time.dt.floor("D"))
        except Exception as e:
            print(e)
            ds_cached = None
            return None

    if rolling_c > 1:
        try:
            ds_rolled = ds.assign(
                pr=ds['pr'].rolling(time=rolling_c, center=False).sum(skipna=True)
            )
            return ds_rolled
        except Exception as e:
            print(e)
            ds_cached = None
            return None

    ds_cached = ds
    return ds

