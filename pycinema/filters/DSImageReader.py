from pycinema import Filter, Image

import cftime
import datetime as dt
import numpy as np
import pandas as pd
import re
import sys
import xarray as xr

from pycinema import getTableExtent

class DSImageReader(Filter):
    def __init__(self):
        super().__init__(
            inputs={
                'table': [[]],
                'start_date': '',
                'end_date': ''
            },
            outputs={
                'images': []
            }
        )

    def _update(self):

        table = self.inputs.table.get()
        start_date = self.inputs.start_date.get()
        end_date = self.inputs.end_date.get()
        tableExtent = getTableExtent(table)
        if tableExtent[0]<1 or tableExtent[1]<1:
            return self.outputs.images.set([])

        # get .zarr files from table
        file_col = next((i for i, h in enumerate(table[0]) if h == "file"), None)
        if file_col is None:
            self.outputs.images.set([])
            return 1

        # get xarray dataset column from table
        ds_col = next((i for i, h in enumerate(table[0]) if h == "xr_dataset"), None)
        if ds_col is None:
            self.outputs.images.set([])
            return 1

        # get rolling_average from table
        rc_col = next((i for i, h in enumerate(table[0]) if h == "Accumulation"), None)
        if rc_col is None:
            self.outputs.images.set([])
            return 1

        images = []
        dates = [start_date, end_date]

        for row in table[1:]:
            zarr_file = row[file_col]
            rolling_c = row[rc_col]
            rolling_c = int(rolling_c.split(' ')[0])
            ds = row[ds_col]
            image = ds_to_image(ds, dates, rolling_c, zarr_file)
            if image != None:
                images = images + image

        self.outputs.images.set(images)


def ds_to_image(ds, dates=None, rolling_c=int(1), zarr_file="None"):
    """
    Returns: [{"PyCinemaImage": {"meta": {...}, "channels": {var: (lat,lon) float32}}}, ...]
    """

    lat = "lat" if "lat" in ds.dims else "latitude"
    lon = "lon" if "lon" in ds.dims else "longitude"
    tdim = "time" if "time" in ds.dims else None

    n_times = range(ds.sizes["time"])

    if tdim is None:
        tids = [0]
    else:
        tids = n_times

    out = []
    nt = len(tids)

    # Cache time coordinate once (avoid recomputing inside loop)
    time_coord = ds[tdim].values if tdim else None

    time_strings = (
        ds[tdim]
        .isel({tdim: tids})
        .dt.strftime("%Y-%m-%d")
        .values
    ) if tdim else None

    for idx, ti in enumerate(tids):
        image = Image()
        chans = {}

        if idx < rolling_c - 1:
            continue

        for name, da in ds.data_vars.items():
            if lat in da.dims and lon in da.dims:
                if tdim and tdim in da.dims:
                    x = da.isel({tdim: ti})

                else:
                    x = da

                chans[name] = x.transpose(lat, lon).values.astype(np.float32)

        # Metadata block
        if tdim:
            if rolling_c and rolling_c > 1:
                start_idx = max(0, idx - rolling_c + 1)
                start_time = time_strings[start_idx]
                end_time = time_strings[idx]
                time_str = start_time if start_time == end_time else f"{start_time} to {end_time}"
            else:
                time_str = time_strings[idx]
            meta = {
                "FILE": zarr_file,
                "time_index": ti,
                "time_range": time_str,
            }
        else:
            meta = {"FILE": zarr_file}

        image.meta = meta
        image.channels = chans
        out.append(image)

    return out
