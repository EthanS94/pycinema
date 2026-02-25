import cftime
from pycinema import Filter
import logging as log
from os.path import exists
import xarray as xr
import numpy

class NetCDFReader(Filter):

    def __init__(self):
        super().__init__(
          inputs={
            'file': ''
          },
          outputs={
            'table': [[]],
            'file': ''
          }
        )

    def _update(self):

        table = []
        ncPath = self.inputs.file.get()

        if not ncPath:
            self.outputs.table.set([[]])
            self.outputs.file.set('')
            return 0

        if not exists(ncPath):
            log.error("file not found: '" + ncPath + "'")
            self.outputs.file.set('')
            self.outputs.table.set([[]])
            return 0

        times = []
        ids = []
        ds = xr.open_dataset(ncPath)
        if 'time' in ds.coords._names:
            reference_time = str(ds.coords['time'].data[0].strftime("%Y-%m-%d %H:%M:%S"))
            times = cftime.date2num(ds.coords['time'].data, "days since {start}".format(start=reference_time))
            times = times.tolist()
            ids = list(range(len(times)))
            times.insert(0, 'Day')
            ids.insert(0, 'id')
            table = numpy.column_stack((times, ids)).tolist()

        self.outputs.table.set(table)
        self.outputs.file.set(self.inputs.file.get())

        return 1
