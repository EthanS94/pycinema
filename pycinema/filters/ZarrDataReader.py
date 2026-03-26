from pycinema import Filter
import xarray as xr
from os.path import isdir


class ZarrDataReader(Filter):
    def __init__(self):
        super().__init__(
            inputs={
                'table': [[]],
                'variable': None
            },
            outputs={
                'datasets': []
            }
        )
    
    def _update(self):
        paths = [path for sublist in self.inputs.table.get() for path in sublist]
        datasets = []
        for zarr_path in paths:
            if isdir(zarr_path):
                datasets.append(xr.open_zarr(zarr_path)[self.inputs.variable.get()])
        self.outputs.datasets.set(datasets)