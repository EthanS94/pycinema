import pycinema
import pycinema.filters
import pycinema.theater
import pycinema.theater.views
from pycinema.Core import Filter
from copy import copy

# pycinema settings
PYCINEMA = { 'VERSION' : '3.2.0'}

tabs = pycinema.theater.TabFrame()

zarr_stores = [
    ["Observation", "Historical (1980-2014)", "ERA5", None, None, 0],
    ["Observation", "Historical (1980-2014)", "MSWEP Gauge", None, None, 1],
    ["Observation", "Historical (1980-2014)", "MSWEP No-Gauge", None, None, 2],
    ["Observation", "Historical (1980-2014)", "NOAA CPC", None, "/home/oxygen/Downloads/zarr_stores/obs_1979_2024/NOAA_CPC_pr_1979_2024.zarr", 3],
    ["Multi-Model", "Historical (1980-2014)", "CESM2-WACCM", None, None, 4],
    ["Multi-Model", "Historical (1980-2014)", "CNRM-CM6-1", None, None, 5],
    ["Multi-Model", "Historical (1980-2014)", "CNRM-ESM2-1", None, None, 6],
    ["Multi-Model", "Historical (1980-2014)", "EC-Earth3", None, None, 7],
    ["Multi-Model", "Historical (1980-2014)", "EC-Earth3-Veg-LR", None, None, 8],
    ["Multi-Model", "Historical (1980-2014)", "GFDL-ESM4", None, None, 9],
    ["Multi-Model", "Historical (1980-2014)", "INM-CM4-8", None, None, 10],
    ["Multi-Model", "Historical (1980-2014)", "INM-CM5-0", None, None, 11],
    ["Multi-Model", "Historical (1980-2014)", "IPSL-CM6A-LR", None, None, 12],
    ["Multi-Model", "SSP3-7.0 (2015-2100)", "CESM2-WACCM", None, None, 14],
    ["Multi-Model", "SSP3-7.0 (2015-2100)", "CNRM-CM6-1", None, None, 15],
    ["Multi-Model", "SSP3-7.0 (2015-2100)", "CNRM-ESM2-1", None, None, 16],
    ["Multi-Model", "SSP3-7.0 (2015-2100)", "EC-Earth3", None, None, 17],
    ["Multi-Model", "SSP3-7.0 (2015-2100)", "EC-Earth3-Veg-LR", None, None, 18],
    ["Multi-Model", "SSP3-7.0 (2015-2100)", "GFDL-ESM4", None, None, 19],
    ["Multi-Model", "SSP3-7.0 (2015-2100)", "INM-CM4-8", None, None, 20],
    ["Multi-Model", "SSP3-7.0 (2015-2100)", "INM-CM5-0", None, None, 21],
    ["Multi-Model", "SSP3-7.0 (2015-2100)", "IPSL-CM6A-LR", None, None, 22],
    ["Multi-Model", "SSP2-4.5 (2015-2100)", "CESM2-WACCM", None, None, 24],
    ["Multi-Model", "SSP2-4.5 (2015-2100)", "CNRM-CM6-1", None, None, 25],
    ["Multi-Model", "SSP2-4.5 (2015-2100)", "CNRM-ESM2-1", None, None, 26],
    ["Multi-Model", "SSP2-4.5 (2015-2100)", "EC-Earth3", None, None, 27],
    ["Multi-Model", "SSP2-4.5 (2015-2100)", "EC-Earth3-Veg-LR", None, None, 28],
    ["Multi-Model", "SSP2-4.5 (2015-2100)", "GFDL-ESM4", None, None, 29],
    ["Multi-Model", "SSP2-4.5 (2015-2100)", "INM-CM4-8", None, None, 30],
    ["Multi-Model", "SSP2-4.5 (2015-2100)", "INM-CM5-0", None, None, 31],
    ["Multi-Model", "SSP2-4.5 (2015-2100)", "IPSL-CM6A-LR", None, None, 32],
    ["Large Ensemble", "Historical (1980-2014)", "GFDL-SPEAR-MED", None, None, 33],
    ["Large Ensemble", "SSP5-8.5 (2015-2100)", "GFDL-SPEAR-MED", None, None, 34]
]

data_structure = [["Collection", "Scenario", "Model", "Metric", "file", "id"]]

index = 0
for zarr_set in zarr_stores:
    for metric in ["1 Day", "3 Day", "5 Day"]:
        parallel_set = copy(zarr_set)
        parallel_set[3] = metric
        parallel_set[-1] = index
        data_structure.append(parallel_set)
        index += 1

editor_view = pycinema.theater.views.NodeEditorView()
editor_split_frame = pycinema.theater.SplitFrame()
editor_split_frame.insertView(0, editor_view)
tabs.insertTab(0, editor_split_frame)
tabs.setTabText(0, 'Filters Layout')

full_frame = pycinema.theater.SplitFrame()
full_frame.setHorizontalOrientation()
left_frame = pycinema.theater.SplitFrame()
left_frame.setVerticalOrientation()
right_frame = pycinema.theater.SplitFrame()
full_frame.insertView(0, left_frame)
full_frame.insertView(1, right_frame)

tabs.insertTab(0, full_frame)
tabs.setTabText(0, 'Data Explorer')

parallel_coords = pycinema.filters.ParallelCoordinates()
parallel_coords.inputs.compose.set("", False)
parallel_coords.inputs.table.set(data_structure)
parallel_coords_view = pycinema.theater.views.FilterView(parallel_coords)
left_frame.insertView(0, parallel_coords_view)

barrier = pycinema.filters.Barrier()
barrier.inputs.table.set(parallel_coords.outputs.table, False)

zarr_reader = pycinema.filters.ZarrDataReader()
zarr_reader.inputs.variable.set("pr", False)
zarr_reader.inputs.table.set(barrier.outputs.table, False)

data_figures = pycinema.filters.DataArrayFigure()
data_figures.inputs.data_array.set(zarr_reader.outputs.datasets)
data_figures.inputs.dates.set(["2010-01-01"])

image_viewer = pycinema.filters.ImageView()
image_viewer.inputs.images.set(data_figures.outputs.images, False)

figure_view = pycinema.theater.views.FilterView(image_viewer)
right_frame.insertView(1, figure_view)

barrier_view = pycinema.theater.views.FilterView(barrier)
left_frame.insertView(1, barrier_view)

pycinema.theater.Theater.instance.setCentralWidget(tabs)
parallel_coords.update()
