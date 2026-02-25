import cftime
from pycinema import Filter
import logging as log
from os.path import exists
import xarray as xr

class NetCDFReader(Filter):

    def __init__(self):
        super().__init__(
          inputs={
            'file': ''
          },
          outputs={
            'table': [[]]
          }
        )

    def _update(self):

        table = []
        ncPath = self.inputs.file.get()

        if not ncPath:
            self.outputs.table.set([[]])
            return 0

        if not exists(ncPath):
            log.error("file not found: '" + ncPath + "'")
            self.outputs.table.set([[]])
            return 0

        ds = xr.open_dataset(ncPath)
        if 'time' in ds.coords._names:
            reference_time = str(ds.coords['time'].data[0].strftime("%Y-%m-%d %H:%M:%S"))
            numeric_date = cftime.date2num(ds.coords['time'].data, "days since {start}".format(start=reference_time))
            table.append(numeric_date.tolist())

        self.outputs.table.set(table)

        return 1
