from pycinema import Filter, Image

import cftime
import datetime as dt
import numpy as np
import pandas as pd
import re
import sys
import xarray as xr

from pycinema import getTableExtent

class DSTimeSample(Filter):
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
            return self.outputs.table.set([[]])

        # get .zarr files from table
        file_col = next((i for i, h in enumerate(table[0]) if h == "file"), None)
        if file_col is None:
            self.outputs.table.set([[]])
            return 1

        # get xarray dataset column from table
        ds_col = next((i for i, h in enumerate(table[0]) if h == "xr_dataset"), None)
        if ds_col is None:
            self.outputs.table.set([[]])
            return 1

        # get rolling_average from table
        rc_col = next((i for i, h in enumerate(table[0]) if h == "Accumulation"), None)
        if rc_col is None:
            self.outputs.table.set([[]])
            return 1

        # get start and end datesfrom table
        date_col = next((i for i, h in enumerate(table[0]) if h == "Time Span"), None)
        if date_col is None:
            self.outputs.table.set([[]])
            return 1
        dates = table[1][date_col]

        # get model_name from table
        mn_col = next((i for i, h in enumerate(table[0]) if h == "Model Name"), None)
        if mn_col is None:
            print("Model name column (Model Name) not found in input table")
            self.outputs.table.set([])
            return 1

        ds_list = [['xr_dataset']]
        for row in table[1:]:
            zarr_file = row[file_col]
            rolling_c = row[rc_col]
            rolling_c = int(rolling_c.split(' ')[0])
            ds = row[ds_col]
            print(f"Downsampling {row[mn_col]} by time...")
            ds = ds_time_sample(ds, dates, rolling_c, zarr_file)
            if ds != None:
                ds_list.append([ds.compute()])
            else:
                ds_list.append([None])

        table = [input_row[:-1] + ds_row for input_row, ds_row in zip(table, ds_list)]

        self.outputs.table.set(table)

def ds_time_sample(ds, dates=None, rolling_c=int(1), zarr_file="None"):
    """
    Returns: ds_down time sampled ds by start_date and end_date
    """

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
    if rolling_c > 1:

        if not cftime_bool:
            start_date = cftime.DatetimeNoLeap(dates[0].year, dates[0].month, dates[0].day)
            end_date = cftime.DatetimeNoLeap(dates[1].year, dates[1].month, dates[1].day)
            t0 = pd.Timestamp(ds.time.values[0])
            t0 = cftime.DatetimeNoLeap(t0.year, t0.month, t0.day)

        # how many whole days we can actually go backwards
        back_avail = max(0, (start_date - t0).days)
        missing = max(0, rolling_c - back_avail - 1)

        if missing > 0:
            slice_start = start_date - dt.timedelta(days=min(rolling_c, back_avail))
            slice_end = end_date + dt.timedelta(days=missing) if start_date == end_date else end_date
        else:
            slice_start = start_date - dt.timedelta(days=rolling_c-1) if start_date == end_date else start_date
            slice_end = end_date

        slice_start = f"{slice_start.year:04d}-{slice_start.month:02d}-{slice_start.day:02d}"
        slice_end = f"{slice_end.year:04d}-{slice_end.month:02d}-{slice_end.day:02d}"

        try:
            ds_down = ds.sel(time=slice(slice_start, slice_end))
        except:
            print(f"Could not select time, {start_date}, from xarray dataset below:")
    else:
        if not cftime_bool:
            try:
                ds_down = ds.sel(time=slice(start_date, end_date))
            except:
                print(f"Could not select time, {start_date}, from xarray dataset below:")
                print(ds)
                return None
        else:
            start_date = f"{start_date.year:04d}-{start_date.month:02d}-{start_date.day:02d}"
            end_date = f"{end_date.year:04d}-{end_date.month:02d}-{end_date.day:02d}"
            try:
                ds_down = ds.sel(time=slice(start_date, end_date))
            except:
                print(f"Could not select time, {start_date}, from xarray dataset below:")
                print(ds)
                return None

    return ds_down
