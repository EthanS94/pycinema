from pycinema import Filter, Image

import sys
import numpy as np
import xarray as xr

from pycinema import getTableExtent

class NCImageReader(Filter):
    def __init__(self):
        super().__init__(
            inputs={
                'table': [[]],
                'file': ''
            },
            outputs={
                'images': []
            }
        )

    def _update(self):

        table = self.inputs.table.get()
        nc_path = self.inputs.file.get()
        tableExtent = getTableExtent(table)
        if tableExtent[0]<1 or tableExtent[1]<1:
            return self.outputs.images.set([])

        images = []
        # Get the column with id values
        col = None
        count = 0
        for col_name in table[:][0]:
            if col_name == "id":
                col = count
                break
            count = count + 1

        times = [int(row[col]) for row in table[1:]]

        images = nc_to_images(nc_path, times)
        self.outputs.images.set(images)


def nc_to_images(nc_path, times=None):
    """
    Returns: [{"PyCinemaImage": {"meta": {...}, "channels": {var: (lat,lon) float32}}}, ...]
    times: list of indexes
    """
    ds = xr.open_dataset(nc_path, decode_times=False)

    lat = "lat" if "lat" in ds.dims else "latitude"
    lon = "lon" if "lon" in ds.dims else "longitude"
    tdim = "time" if "time" in ds.dims else None

    if tdim is None:
        tids = [0]
    else:
        tids = times

    out = []
    for ti in tids:
        image = Image()
        chans = {}
        for name, da in ds.data_vars.items():
            if lat in da.dims and lon in da.dims:
                x = da.isel({tdim: ti}) if tdim and tdim in da.dims else da
                x = x.mean([d for d in x.dims if d not in (lat, lon)], skipna=True)
                chans[name] = x.transpose(lat, lon).values.astype(np.float32)
        meta = {"FILE": nc_path, "time_index": ti} if tdim else {"FILE": nc_path}
        image.meta = meta
        image.channels = chans
        out.append(image)
        #out.append({"PyCinemaImage": "meta": meta, "channels": chans})
    return out
