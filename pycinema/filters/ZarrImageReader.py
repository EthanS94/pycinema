from pycinema import Filter, Image

import cftime
import datetime as dt
import numpy as np
import pandas as pd
import re
import sys
import xarray as xr

from pycinema import getTableExtent

class ZarrImageReader(Filter):
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

        # get .zarr globs from table
        file_col = next((i for i, h in enumerate(table[0]) if h == "file"), None)
        if file_col is None:
            self.outputs.images.set([])
            return 1

        zarr_globs = list(set([row[file_col] for row in table[1:]]))

        # get rolling_average from table
        # FIXME: assume only one rolling_average is chosen at a time
        #        need to handle if a user selects multiple rolling_averages
        ra_col = next((i for i, h in enumerate(table[0]) if h == "Accumulation"), None)
        if ra_col is None:
            self.outputs.images.set([])
            return 1

        # rolling averages come in as strings ('1 day')
        # need to handle that
        rolling_averages = list(set([row[ra_col] for row in table[1:]]))
        rolling_averages = sorted([int(ra.split(' ')[0]) for ra in rolling_averages])

        images = []
        dates = [start_date, end_date]

        for g in zarr_globs:
            for ra in rolling_averages:
                image = zarr_to_images(g, dates, ra)
                if image != None:
                    images = images + image

        self.outputs.images.set(images)


def zarr_to_images(zarr_glob, dates=None, rolling_average=int(1)):
    """
    Returns: [{"PyCinemaImage": {"meta": {...}, "channels": {var: (lat,lon) float32}}}, ...]
    """

    ds = xr.open_dataset(zarr_glob, decode_times=True, engine='zarr')
    # Normalize T12:00:0000's to T00:00:0000's so selection works better
    ds = ds.assign_coords(time=ds.time.dt.floor("D"))

    t0 = ds.time[0].item()

    cftime_bool = False
    if isinstance(t0, cftime.DatetimeNoLeap):
        cftime_bool = True
        start_date = cftime.DatetimeNoLeap(dates[0].year, dates[0].month, dates[0].day)
        end_date = cftime.DatetimeNoLeap(dates[1].year, dates[1].month, dates[1].day)
    elif np.issubdtype(ds.time.dtype, np.datetime64):
        start_date = np.datetime64(dates[0])
        end_date = np.datetime64(dates[1])
    else:
        print("Unrecognized time format: ")
        print(ds.time.dtype)
        return None

    # Need to slice smartly if there is a rolling average > 1
    # Also need to move slice forward if trying to pick only the first date with a rolling average
    #   because first date - 3 will cause issues
    if rolling_average > 1:

        if not cftime_bool:
            start_date = cftime.DatetimeNoLeap(dates[0].year, dates[0].month, dates[0].day)
            end_date = cftime.DatetimeNoLeap(dates[1].year, dates[1].month, dates[1].day)
            t0 = pd.Timestamp(ds.time.values[0])
            t0 = cftime.DatetimeNoLeap(t0.year, t0.month, t0.day)

        # how many whole days we can actually go backwards
        back_avail = max(0, (start_date - t0).days)
        missing = max(0, rolling_average - back_avail - 1)

        if missing > 0:
            slice_start = start_date - dt.timedelta(days=min(rolling_average, back_avail))
            slice_end = end_date + dt.timedelta(days=missing) if start_date == end_date else end_date
        else:
            slice_start = start_date - dt.timedelta(days=rolling_average-1) if start_date == end_date else start_date
            slice_end = end_date

        slice_start = f"{slice_start.year:04d}-{slice_start.month:02d}-{slice_start.day:02d}"
        slice_end = f"{slice_end.year:04d}-{slice_end.month:02d}-{slice_end.day:02d}"

        ds_down = ds.sel(time=slice(slice_start, slice_end))
    else:
        if not cftime_bool:
            try:
                ds_down = ds.sel(time=[start_date])
            except:
                print(f"Could not select time, {start_date}, from xarray dataset below:")
                print(ds)
                return None
        else:
            start_date = f"{start_date.year:04d}-{start_date.month:02d}-{start_date.day:02d}"
            end_date = f"{end_date.year:04d}-{end_date.month:02d}-{end_date.day:02d}"
            ds_down = ds.sel(time=slice(start_date, end_date))

    lat = "lat" if "lat" in ds.dims else "latitude"
    lon = "lon" if "lon" in ds.dims else "longitude"
    tdim = "time" if "time" in ds.dims else None

    n_times = range(ds_down.sizes["time"])

    if tdim is None:
        tids = [0]
    else:
        tids = n_times

    out = []
    nt = len(tids)

    # Cache time coordinate once (avoid recomputing inside loop)
    time_coord = ds_down[tdim].values if tdim else None

    time_strings = (
        ds_down[tdim]
        .isel({tdim: tids})
        .dt.strftime("%Y-%m-%d")
        .values
    ) if tdim else None

    if rolling_average > 1:
        try:
            ds_down['pr'] = ds_down['pr'].rolling(time=rolling_average, center=False).sum(skipna=True)
        except:
            print(ds_down)
            return None

    for idx, ti in enumerate(tids):
        image = Image()
        chans = {}

        if idx < rolling_average - 1:
            continue

        for name, da in ds_down.data_vars.items():
            if lat in da.dims and lon in da.dims:
                if tdim and tdim in da.dims:
                    x = da.isel({tdim: ti})

                else:
                    x = da

                chans[name] = x.transpose(lat, lon).values.astype(np.float32)

        # Metadata block
        if tdim:
            if rolling_average and rolling_average > 1:
                start_idx = max(0, idx - rolling_average + 1)
                start_time = time_strings[start_idx]
                end_time = time_strings[idx]
                time_str = start_time if start_time == end_time else f"{start_time} to {end_time}"
            else:
                time_str = time_strings[idx]
            meta = {
                "FILE": zarr_glob,
                "time_index": ti,
                "time_range": time_str,
            }
        else:
            meta = {"FILE": zarr_glob}

        image.meta = meta
        image.channels = chans
        out.append(image)

    return out
