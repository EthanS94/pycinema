import pycinema
import pycinema.filters
import pycinema.theater
import pycinema.theater.views

from copy import copy

# pycinema settings
PYCINEMA = { 'VERSION' : '3.2.0'}

#base_zarr_dir = "/scratch/07644/oxygen/LANL_cleaned_data/interp_zarr_stores/"
base_zarr_dir = "/Users/stam/projects/visRandD_2026/utaustin_collab/03242026/data/interp_zarr_stores/"
CMIP6_FUTURE = base_zarr_dir + "cmip6_future-scenario_pr_2015-2100.zarr"
CMIP6_HISTORICAL = base_zarr_dir + "cmip6_historical_pr_1850-2014.zarr"
CMIP6_OBS = base_zarr_dir + "obs_cmip6-interp_pr_1980-2023.zarr"
GFDL_SPEAR_MED_FUTURE = base_zarr_dir + "GFDL-SPEAR-MED_ssp585_2015-2100.zarr"
GFDL_SPEAR_MED_HISTORICAL = base_zarr_dir + "GFDL-SPEAR-MED_historical_1921-2014.zarr"

zarr_stores = [
    ["Observation", "Historical (1980-2014)", "ERA5", None, CMIP6_OBS, 0],
    ["Observation", "Historical (1980-2014)", "MSWEP_G", None, CMIP6_OBS, 1],
    ["Observation", "Historical (1980-2014)", "MSWEP_NG", None, CMIP6_OBS, 2],
    ["Observation", "Historical (1980-2014)", "NOAA_CPC", None, CMIP6_OBS, 3],
    ["CMIP6", "Historical (1980-2014)", "CNRM-CM6-1", None, CMIP6_HISTORICAL, 5],
    ["CMIP6", "Historical (1980-2014)", "CNRM-ESM2-1", None, CMIP6_HISTORICAL, 6],
    ["CMIP6", "Historical (1980-2014)", "EC-Earth3", None, CMIP6_HISTORICAL, 7],
    ["CMIP6", "Historical (1980-2014)", "EC-Earth3-Veg-LR", None, CMIP6_HISTORICAL, 8],
    ["CMIP6", "Historical (1980-2014)", "GFDL-ESM4", None, CMIP6_HISTORICAL, 9],
    ["CMIP6", "Historical (1980-2014)", "INM-CM4-8", None, CMIP6_HISTORICAL, 10],
    ["CMIP6", "Historical (1980-2014)", "INM-CM5-0", None, CMIP6_HISTORICAL, 11],
    ["CMIP6", "Historical (1980-2014)", "IPSL-CM6A-LR", None, CMIP6_HISTORICAL, 12],
    ["CMIP6", "SSP3-7.0 (2015-2100)", "CESM2-WACCM", None, CMIP6_FUTURE, 14],
    ["CMIP6", "SSP3-7.0 (2015-2100)", "CNRM-CM6-1", None, CMIP6_FUTURE, 15],
    ["CMIP6", "SSP3-7.0 (2015-2100)", "CNRM-ESM2-1", None, CMIP6_FUTURE, 16],
    ["CMIP6", "SSP3-7.0 (2015-2100)", "EC-Earth3", None, CMIP6_FUTURE, 17],
    ["CMIP6", "SSP3-7.0 (2015-2100)", "EC-Earth3-Veg-LR", None, CMIP6_FUTURE, 18],
    ["CMIP6", "SSP3-7.0 (2015-2100)", "GFDL-ESM4", None, CMIP6_FUTURE, 19],
    ["CMIP6", "SSP3-7.0 (2015-2100)", "INM-CM4-8", None, CMIP6_FUTURE, 20],
    ["CMIP6", "SSP3-7.0 (2015-2100)", "INM-CM5-0", None, CMIP6_FUTURE, 21],
    ["CMIP6", "SSP3-7.0 (2015-2100)", "IPSL-CM6A-LR", None, CMIP6_FUTURE, 22],
    ["CMIP6", "SSP2-4.5 (2015-2100)", "CESM2-WACCM", None, CMIP6_FUTURE, 24],
    ["CMIP6", "SSP2-4.5 (2015-2100)", "CNRM-CM6-1", None, CMIP6_FUTURE, 25],
    ["CMIP6", "SSP2-4.5 (2015-2100)", "CNRM-ESM2-1", None, CMIP6_FUTURE, 26],
    ["CMIP6", "SSP2-4.5 (2015-2100)", "EC-Earth3", None, CMIP6_FUTURE, 27],
    ["CMIP6", "SSP2-4.5 (2015-2100)", "EC-Earth3-Veg-LR", None, CMIP6_FUTURE, 28],
    ["CMIP6", "SSP2-4.5 (2015-2100)", "GFDL-ESM4", None, CMIP6_FUTURE, 29],
    ["CMIP6", "SSP2-4.5 (2015-2100)", "INM-CM4-8", None, CMIP6_FUTURE, 30],
    ["CMIP6", "SSP2-4.5 (2015-2100)", "INM-CM5-0", None, CMIP6_FUTURE, 31],
    ["CMIP6", "SSP2-4.5 (2015-2100)", "IPSL-CM6A-LR", None, CMIP6_FUTURE, 32],
    ["Large Ensemble", "Historical (1980-2014)", "GFDL-SPEAR-MED", None, GFDL_SPEAR_MED_HISTORICAL, 33],
    ["Large Ensemble", "SSP5-8.5 (2015-2100)", "GFDL-SPEAR-MED", None, GFDL_SPEAR_MED_FUTURE, 34]
]

data_structure = [["Collection", "Scenario", "Dataset", "Metric", "file", "id"]]

zarr_stores = [
    ["ERA5", "Observation", "Historical (1980-2014)", None, CMIP6_OBS, 0],
    ["MSWEP_G", "Observation", "Historical (1980-2014)", None, CMIP6_OBS, 1],
    ["MSWEP_NG", "Observation", "Historical (1980-2014)", None, CMIP6_OBS, 2],
    ["NOAA_CPC", "Observation", "Historical (1980-2014)", None, CMIP6_OBS, 3],
    ["CNRM-CM6-1", "CMIP6", "Historical (1980-2014)", None, CMIP6_HISTORICAL, 4],
    ["CNRM-ESM2-1", "CMIP6", "Historical (1980-2014)", None, CMIP6_HISTORICAL, 5],
    ["EC-Earth3", "CMIP6", "Historical (1980-2014)", None, CMIP6_HISTORICAL, 6],
    ["EC-Earth3-Veg-LR", "CMIP6", "Historical (1980-2014)", None, CMIP6_HISTORICAL, 7],
    ["GFDL-ESM4", "CMIP6", "Historical (1980-2014)", None, CMIP6_HISTORICAL, 8],
    ["INM-CM4-8", "CMIP6", "Historical (1980-2014)", None, CMIP6_HISTORICAL, 9],
    ["INM-CM5-0", "CMIP6", "Historical (1980-2014)", None, CMIP6_HISTORICAL, 10],
    ["IPSL-CM6A-LR", "CMIP6", "Historical (1980-2014)", None, CMIP6_HISTORICAL, 11],
    ["CESM2-WACCM", "CMIP6", "SSP3-7.0 (2015-2100)", None, CMIP6_FUTURE, 12],
    ["CNRM-CM6-1", "CMIP6", "SSP3-7.0 (2015-2100)", None, CMIP6_FUTURE, 13],
    ["CNRM-ESM2-1", "CMIP6", "SSP3-7.0 (2015-2100)", None, CMIP6_FUTURE, 14],
    ["EC-Earth3", "CMIP6", "SSP3-7.0 (2015-2100)", None, CMIP6_FUTURE, 15],
    ["EC-Earth3-Veg-LR", "CMIP6", "SSP3-7.0 (2015-2100)", None, CMIP6_FUTURE, 16],
    ["GFDL-ESM4", "CMIP6", "SSP3-7.0 (2015-2100)", None, CMIP6_FUTURE, 17],
    ["INM-CM4-8", "CMIP6", "SSP3-7.0 (2015-2100)", None, CMIP6_FUTURE, 18],
    ["INM-CM5-0", "CMIP6", "SSP3-7.0 (2015-2100)", None, CMIP6_FUTURE, 19],
    ["IPSL-CM6A-LR", "CMIP6", "SSP3-7.0 (2015-2100)", None, CMIP6_FUTURE, 20],
    ["CESM2-WACCM", "CMIP6", "SSP2-4.5 (2015-2100)", None, CMIP6_FUTURE, 21],
    ["CNRM-CM6-1", "CMIP6", "SSP2-4.5 (2015-2100)", None, CMIP6_FUTURE, 22],
    ["CNRM-ESM2-1", "CMIP6", "SSP2-4.5 (2015-2100)", None, CMIP6_FUTURE, 23],
    ["EC-Earth3", "CMIP6", "SSP2-4.5 (2015-2100)", None, CMIP6_FUTURE, 24],
    ["EC-Earth3-Veg-LR", "CMIP6", "SSP2-4.5 (2015-2100)", None, CMIP6_FUTURE, 25],
    ["GFDL-ESM4", "CMIP6", "SSP2-4.5 (2015-2100)", None, CMIP6_FUTURE, 26],
    ["INM-CM4-8", "CMIP6", "SSP2-4.5 (2015-2100)", None, CMIP6_FUTURE, 27],
    ["INM-CM5-0", "CMIP6", "SSP2-4.5 (2015-2100)", None, CMIP6_FUTURE, 28],
    ["IPSL-CM6A-LR", "CMIP6", "SSP2-4.5 (2015-2100)", None, CMIP6_FUTURE, 29],
    ["GFDL-SPEAR-MED", "Large Ensemble", "Historical (1980-2014)", None, GFDL_SPEAR_MED_HISTORICAL, 30],
    ["GFDL-SPEAR-MED", "Large Ensemble", "SSP5-8.5 (2015-2100)", None, GFDL_SPEAR_MED_FUTURE, 31]
]

data_structure = [["Dataset", "Collection", "Scenario", "Metric", "file", "id"]]

index = 0
for zarr_set in zarr_stores:
    for metric in ["1 Day", "3 Day", "5 Day"]:
        parallel_set = copy(zarr_set)
        parallel_set[3] = metric
        parallel_set[-1] = index
        data_structure.append(parallel_set)
        index += 1

# filters
ParallelCoordinates_0 = pycinema.filters.ParallelCoordinates()
Barrier_0 = pycinema.filters.Barrier()
ZarrToDS_0 = pycinema.filters.ZarrToDS()
ZarrTimeSpan_0 = pycinema.filters.ZarrTimeSpan()
QuantilePlot_0 = pycinema.filters.QuantilePlot()
DSTimeSample_0 = pycinema.filters.DSTimeSample()
DSLatLonSample_0 = pycinema.filters.DSLatLonSample()
ImageView_0 = pycinema.filters.ImageView()

# properties
ParallelCoordinates_0.inputs.table.set(data_structure, False)
ParallelCoordinates_0.inputs.ignore.set(['^file', '^id'], False)
Barrier_0.inputs.table.set(ZarrTimeSpan_0.outputs.table, False)
ZarrToDS_0.inputs.table.set(Barrier_0.outputs.table, False)
ZarrTimeSpan_0.inputs.table.set(ParallelCoordinates_0.outputs.table, False)
ZarrTimeSpan_0.inputs.ignore.set(['^id'], False)
DSTimeSample_0.inputs.table.set(ZarrToDS_0.outputs.table, False)
DSLatLonSample_0.inputs.table.set(DSTimeSample_0.outputs.table, False)
QuantilePlot_0.inputs.table.set(DSLatLonSample_0.outputs.table, False)
ImageView_0.inputs.images.set(QuantilePlot_0.outputs.images, False)
ImageView_0.inputs.selection.set([], False)

# layout
tabFrame1 = pycinema.theater.TabFrame()
splitFrame1 = pycinema.theater.SplitFrame()
splitFrame1.setHorizontalOrientation()
view1 = pycinema.theater.views.NodeEditorView()
splitFrame1.insertView( 0, view1 )
splitFrame1.setSizes([640])
tabFrame1.insertTab(0, splitFrame1)
tabFrame1.setTabText(0, 'Layout 1')
splitFrame2 = pycinema.theater.SplitFrame()
splitFrame2.setHorizontalOrientation()
splitFrame3 = pycinema.theater.SplitFrame()
splitFrame3.setVerticalOrientation()
view2 = pycinema.theater.views.FilterView( ParallelCoordinates_0 )
splitFrame3.insertView( 0, view2 )
view3 = pycinema.theater.views.FilterView( Barrier_0 )
splitFrame3.insertView( 1, view3 )
view4 = pycinema.theater.views.FilterView( ZarrTimeSpan_0 )
splitFrame3.insertView( 2, view4 )
splitFrame3.setSizes([565, 114, 114])
splitFrame2.insertView( 0, splitFrame3 )
splitFrame2.setSizes([1018])
tabFrame1.insertTab(1, splitFrame2)
tabFrame1.setTabText(1, 'Layout 2')
splitFrame4 = pycinema.theater.SplitFrame()
splitFrame4.setHorizontalOrientation()
view5 = pycinema.theater.views.FilterView( ImageView_0 )
splitFrame4.insertView( 0, view5 )
splitFrame4.setSizes([640])
tabFrame1.insertTab(2, splitFrame4)
tabFrame1.setTabText(2, 'Layout 3')
tabFrame1.setCurrentIndex(1)
pycinema.theater.Theater.instance.setCentralWidget(tabFrame1)

# execute pipeline
ParallelCoordinates_0.update()
