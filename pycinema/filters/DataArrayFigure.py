from pycinema import Filter, imageFromMatplotlibFigure
from xarray import DataArray
import matplotlib.pyplot as plt
import cartopy.crs as ccrs


class DataArrayFigure(Filter):
    def __init__(self):
        super().__init__(
            inputs={
                'data_array': None,
                'cmap': 'BuPu',
                'coastlines': True,
                'dates': [],
                'dpi': 120
            },
            outputs={
                'images': []
            }
        )
    
    def _update(self):
        images = []
        for data_array in self.inputs.data_array.get():
            for date in self.inputs.dates.get():
                data_array = data_array.sel(time=date, method='nearest')

                assert type(data_array) == DataArray
                assert "lat" in data_array.dims
                assert "lon" in data_array.dims

                proj = ccrs.Robinson()
                transform = ccrs.PlateCarree()

                fig, ax1 = plt.subplots(1, 1, figsize=(10, 8), facecolor='w', subplot_kw=dict(projection=proj))
                
                data_array.plot.contourf(ax=ax1, robust=True, transform=transform, cmap=self.inputs.cmap.get())

                if self.inputs.coastlines.get():
                    ax1.coastlines()

                images.append(imageFromMatplotlibFigure(fig, dpi=self.inputs.dpi.get()))
        self.outputs.images.set(images)

        