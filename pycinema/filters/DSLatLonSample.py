from pycinema import Filter, Image

import cftime
import datetime as dt
import numpy as np
import pandas as pd
import re
import sys
import xarray as xr

from pycinema import getTableExtent

class DSLatLonSample(Filter):
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

        # get xarray dataset column from table
        ds_col = next((i for i, h in enumerate(table[0]) if h == "xr_dataset"), None)
        if ds_col is None:
            print("xarray dataset column (xr_dataset) not found in input table")
            self.outputs.table.set([[]])
            return 1

        # get lat from table
        lat_col = next((i for i, h in enumerate(table[0]) if h == "Latitude"), None)
        if lat_col is None:
            self.outputs.table.set([[]])
            return 1
        lats = table[1][lat_col]

        # get lon from table
        lon_col = next((i for i, h in enumerate(table[0]) if h == "Longitude"), None)
        if lon_col is None:
            self.outputs.table.set([[]])
            return 1
        lons = table[1][lon_col]

        # get model_name from table
        mn_col = next((i for i, h in enumerate(table[0]) if h == "Model Name"), None)
        if mn_col is None:
            print("Model name column (Model Name) not found in input table")
            self.outputs.table.set([])
            return 1

        ds_list = [['xr_dataset']]
        for row in table[1:]:
            ds = row[ds_col]
            if lats[0] > -90 or lats[1] < 90 or lons[0] > -180 or lons[1] < 180:
                ds = ds_latlon_sample(ds, lats, lons)
                if ds != None:
                    ds_list.append([ds.compute()])
                else:
                    ds_list.append([None])
            else:
                ds_list.append([ds])

        table = [input_row[:-1] + ds_row for input_row, ds_row in zip(table, ds_list)]

        self.outputs.table.set(table)

def ds_latlon_sample(ds, lats, lons):
    # downsample by lat lon if they are not the default
    if lats[0] > -90 or lats[1] < 90:
        print('down selecting lats')
        ds = ds.sel(lat=slice(lats[0], lats[1]))
    if lons[0] > -180 or lons[1] < 180:
        print('down selecting lons')
        ds = ds.sel(lon=slice(lons[0], lons[1]))
    return ds
