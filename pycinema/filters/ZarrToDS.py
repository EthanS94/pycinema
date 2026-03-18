from pycinema import Filter, Image

import cftime
import datetime as dt
import numpy as np
import pandas as pd
import re
import sys
import xarray as xr

from pycinema import getTableExtent

class ZarrToDS(Filter):
    def __init__(self):
        super().__init__(
            inputs={
                'table': [[]],
            },
            outputs={
                'table': []
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
        for row in table[1:]:
            zarr_file = row[file_col]
            rolling_c = row[rc_col]
            rolling_c = int(rolling_c.split(' ')[0])
            ds = zarr_to_ds(zarr_file, rolling_c)
            if ds != None:
                ds_list.append([ds])
            else:
                ds_list.append([None])

        table = [input_row + ds_row for input_row, ds_row in zip(table, ds_list)]

        self.outputs.table.set(table)


def zarr_to_ds(zarr_path, rolling_c=int(1)):
    """
    Returns: xarray dataset by reading in zarr_path
    """

    try:
        ds = xr.open_dataset(zarr_path, decode_times=True, engine='zarr')
        # Normalize T12:00:0000's to T00:00:0000's so selection works better
        ds = ds.assign_coords(time=ds.time.dt.floor("D"))
    except Exception as e:
        print(e)
        return None

    if rolling_c > 1:
        try:
            ds['pr'] = ds['pr'].rolling(time=rolling_c, center=False).sum(skipna=True)
        except Exception as e:
            print(e)
            return None

    return ds

