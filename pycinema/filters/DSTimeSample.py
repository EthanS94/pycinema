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

        # Retained state between updates
        self._prev_header = None
        self._prev_input_rows = []
        self._prev_output_rows = []

    def _update(self):

        table = self.inputs.table.get()
        tableExtent = getTableExtent(table)
        if tableExtent[0]<1 or tableExtent[1]<1:
            self._clear_cache()
            return self.outputs.table.set([[]])

        header = table[0]
        input_rows = table[1:]

        # get .zarr files from table
        file_col = next((i for i, h in enumerate(header) if h == "file"), None)
        if file_col is None:
            self.outputs.table.set([[]])
            self._clear_cache()
            return 1

        # get xarray dataset column from table
        ds_col = next((i for i, h in enumerate(header) if h == "xr_dataset"), None)
        if ds_col is None:
            self.outputs.table.set([[]])
            self._clear_cache()
            return 1

        # get rolling_average from table
        rc_col = next((i for i, h in enumerate(header) if h == "Metric"), None)
        if rc_col is None:
            self.outputs.table.set([[]])
            self._clear_cache()
            return 1

        # get start and end datesfrom table
        date_col = next((i for i, h in enumerate(header) if h == "Time Span"), None)
        if date_col is None:
            self.outputs.table.set([[]])
            self._clear_cache()
            return 1
        dates = table[1][date_col]

        # get model_name from table
        mn_col = next((i for i, h in enumerate(header) if h == "Dataset"), None)
        if mn_col is None:
            print("Model name column (Model Name) not found in input table")
            self.outputs.table.set([])
            self._clear_cache()
            return 1

        # If header changed, invalidate retained rows
        header_changed = self._prev_header != header

        output_header = header[:-1] + ["xr_dataset"]
        output_rows = []

        for i, row in enumerate(input_rows):
            row_copy = list(row)

            # Reuse retained output row if the input row is unchanged
            can_reuse = (
                not header_changed
                and i < len(self._prev_input_rows)
                and i < len(self._prev_output_rows)
                and row_copy == self._prev_input_rows[i]
            )

            if can_reuse:
                retained_output_row = self._prev_output_rows[i]
                output_rows.append(retained_output_row)
                continue

            zarr_file = row[file_col]
            rolling_c = row[rc_col]
            rolling_c = int(rolling_c.split(' ')[0])
            ds = row[ds_col]
            print(f"Downsampling {row[mn_col]} by time...")
            ds = ds_time_sample(ds, dates, rolling_c, zarr_file)
            if ds != None:
                output_row = row_copy[:-1] + [ds]
            else:
                output_row = row_copy[:-1] + [None]
            output_rows.append(output_row)

        # Retain current input/output state for next update
        self._prev_header = list(header)
        self._prev_input_rows = [list(r) for r in input_rows]
        self._prev_output_rows = list(output_rows)

        self.outputs.table.set([output_header] + output_rows)

    def _clear_cache(self):
        self._prev_header = None
        self._prev_input_rows = []
        self._prev_output_rows = []

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
