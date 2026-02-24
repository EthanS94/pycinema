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

        try:
            ds = xr.open_dataset(ncPath)
            df = ds.to_dataframe()
            table_2d = df.values.tolist()
        except:
            log.error("Unable to open file: '" + ncPath + "'")
            self.outputs.table.set([[]])
            return 0

        self.outputs.table.set(table_2d)

        return 1
