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
    ["Observation", "ERA5", "Historical (1980-2014)", None, CMIP6_OBS, 0],
    ["Observation", "MSWEP_G", "Historical (1980-2014)", None, CMIP6_OBS, 1],
    ["Observation", "MSWEP_NG", "Historical (1980-2014)", None, CMIP6_OBS, 2],
    ["Observation", "NOAA_CPC", "Historical (1980-2014)", None, CMIP6_OBS, 3],
    ["CMIP6", "CNRM-CM6-1", "Historical (1980-2014)", None, CMIP6_HISTORICAL, 5],
    ["CMIP6", "CNRM-ESM2-1", "Historical (1980-2014)", None, CMIP6_HISTORICAL, 6],
    ["CMIP6", "EC-Earth3", "Historical (1980-2014)", None, CMIP6_HISTORICAL, 7],
    ["CMIP6", "EC-Earth3-Veg-LR", "Historical (1980-2014)", None, CMIP6_HISTORICAL, 8],
    ["CMIP6", "GFDL-ESM4", "Historical (1980-2014)", None, CMIP6_HISTORICAL, 9],
    ["CMIP6", "INM-CM4-8", "Historical (1980-2014)", None, CMIP6_HISTORICAL, 10],
    ["CMIP6", "INM-CM5-0", "Historical (1980-2014)", None, CMIP6_HISTORICAL, 11],
    ["CMIP6", "IPSL-CM6A-LR", "Historical (1980-2014)", None, CMIP6_HISTORICAL, 12],
    ["CMIP6", "CESM2-WACCM", "SSP3-7.0 (2015-2100)", None, CMIP6_FUTURE, 14],
    ["CMIP6", "CNRM-CM6-1", "SSP3-7.0 (2015-2100)", None, CMIP6_FUTURE, 15],
    ["CMIP6", "CNRM-ESM2-1", "SSP3-7.0 (2015-2100)", None, CMIP6_FUTURE, 16],
    ["CMIP6", "EC-Earth3", "SSP3-7.0 (2015-2100)", None, CMIP6_FUTURE, 17],
    ["CMIP6", "EC-Earth3-Veg-LR", "SSP3-7.0 (2015-2100)", None, CMIP6_FUTURE, 18],
    ["CMIP6", "GFDL-ESM4", "SSP3-7.0 (2015-2100)", None, CMIP6_FUTURE, 19],
    ["CMIP6", "INM-CM4-8", "SSP3-7.0 (2015-2100)", None, CMIP6_FUTURE, 20],
    ["CMIP6", "INM-CM5-0", "SSP3-7.0 (2015-2100)", None, CMIP6_FUTURE, 21],
    ["CMIP6", "IPSL-CM6A-LR", "SSP3-7.0 (2015-2100)", None, CMIP6_FUTURE, 22],
    ["CMIP6", "CESM2-WACCM", "SSP2-4.5 (2015-2100)", None, CMIP6_FUTURE, 24],
    ["CMIP6", "CNRM-CM6-1", "SSP2-4.5 (2015-2100)", None, CMIP6_FUTURE, 25],
    ["CMIP6", "CNRM-ESM2-1", "SSP2-4.5 (2015-2100)", None, CMIP6_FUTURE, 26],
    ["CMIP6", "EC-Earth3", "SSP2-4.5 (2015-2100)", None, CMIP6_FUTURE, 27],
    ["CMIP6", "EC-Earth3-Veg-LR", "SSP2-4.5 (2015-2100)", None, CMIP6_FUTURE, 28],
    ["CMIP6", "GFDL-ESM4", "SSP2-4.5 (2015-2100)", None, CMIP6_FUTURE, 29],
    ["CMIP6", "INM-CM4-8", "SSP2-4.5 (2015-2100)", None, CMIP6_FUTURE, 30],
    ["CMIP6", "INM-CM5-0", "SSP2-4.5 (2015-2100)", None, CMIP6_FUTURE, 31],
    ["CMIP6", "IPSL-CM6A-LR", "SSP2-4.5 (2015-2100)", None, CMIP6_FUTURE, 32],
    ["Large Ensemble", "GFDL-SPEAR-MED", "Historical (1980-2014)", None, GFDL_SPEAR_MED_HISTORICAL, 33],
    ["Large Ensemble", "GFDL-SPEAR-MED", "SSP5-8.5 (2015-2100)", None, GFDL_SPEAR_MED_FUTURE, 34]
]

data_structure = [["Collection", "Dataset", "Scenario", "Metric", "file", "id"]]

index = 0
for zarr_set in zarr_stores:
    for metric in ["1 Day", "3 Day", "5 Day"]:
        parallel_set = copy(zarr_set)
        parallel_set[3] = metric
        parallel_set[-1] = index
        data_structure.append(parallel_set)
        index += 1

# --- START QUANTILE WORKFLOW ---

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
tabFrame1.setTabText(0, 'Filter Node Graph')
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
tabFrame1.setTabText(1, 'Quantile Selection')
splitFrame4 = pycinema.theater.SplitFrame()
splitFrame4.setHorizontalOrientation()
view5 = pycinema.theater.views.FilterView( ImageView_0 )
splitFrame4.insertView( 0, view5 )
splitFrame4.setSizes([640])
tabFrame1.insertTab(2, splitFrame4)
tabFrame1.setTabText(2, 'Quantile Plot')
tabFrame1.setCurrentIndex(1)
pycinema.theater.Theater.instance.setCentralWidget(tabFrame1)

# execute pipeline
ParallelCoordinates_0.update()

# --- END QUANTILE WORKFLOW ---


# --- START STIPPLE WORKFLOW ---
s_data_structure = [["Collection", "Dataset", "Scenario", "Metric", "file", "id"]]

index = 0
for zarr_set in zarr_stores:
    if "Historical" not in zarr_set[2]:
        continue
    for metric in ["1 Day", "3 Day", "5 Day"]:
        parallel_set = copy(zarr_set)
        parallel_set[3] = metric
        parallel_set[-1] = index
        s_data_structure.append(parallel_set)
        index += 1

# filters
s_ParallelCoordinates_0 = pycinema.filters.ParallelCoordinates()
s_Barrier_0 = pycinema.filters.Barrier()
s_ZarrToDS_0 = pycinema.filters.ZarrToDS()
s_ZarrTimeSpan_0 = pycinema.filters.ZarrTimeSpan()
s_StippleCompare_0 = pycinema.filters.StippleCompare()
s_DSTimeSample_0 = pycinema.filters.DSTimeSample()
s_DSLatLonSample_0 = pycinema.filters.DSLatLonSample()
s_ImageView_0 = pycinema.filters.ImageView()

# properties
s_ParallelCoordinates_0.inputs.table.set(s_data_structure, False)
s_ParallelCoordinates_0.inputs.ignore.set(['^file', '^id'], False)
s_Barrier_0.inputs.table.set(s_ZarrTimeSpan_0.outputs.table, False)
s_ZarrToDS_0.inputs.table.set(s_Barrier_0.outputs.table, False)
s_ZarrTimeSpan_0.inputs.table.set(s_ParallelCoordinates_0.outputs.table, False)
s_ZarrTimeSpan_0.inputs.ignore.set(['^id'], False)
s_DSTimeSample_0.inputs.table.set(s_ZarrToDS_0.outputs.table, False)
s_DSLatLonSample_0.inputs.table.set(s_DSTimeSample_0.outputs.table, False)
s_StippleCompare_0.inputs.table.set(s_DSLatLonSample_0.outputs.table, False)
s_ImageView_0.inputs.images.set(s_StippleCompare_0.outputs.images, False)
s_ImageView_0.inputs.selection.set([], False)

# layout
s_splitFrame2 = pycinema.theater.SplitFrame()
s_splitFrame2.setHorizontalOrientation()
s_splitFrame3 = pycinema.theater.SplitFrame()
s_splitFrame3.setVerticalOrientation()
s_view2 = pycinema.theater.views.FilterView( s_ParallelCoordinates_0 )
s_splitFrame3.insertView( 0, s_view2 )
s_view3 = pycinema.theater.views.FilterView( s_Barrier_0 )
s_splitFrame3.insertView( 1, s_view3 )
s_view4 = pycinema.theater.views.FilterView( s_ZarrTimeSpan_0 )
s_splitFrame3.insertView( 2, s_view4 )
s_splitFrame3.setSizes([565, 114, 114])
s_splitFrame2.insertView( 0, s_splitFrame3 )
s_splitFrame2.setSizes([1018])
tabFrame1.insertTab(3, s_splitFrame2)
tabFrame1.setTabText(3, 'Stipple Selection')
s_splitFrame4 = pycinema.theater.SplitFrame()
s_splitFrame4.setHorizontalOrientation()
s_view5 = pycinema.theater.views.FilterView( s_ImageView_0 )
s_splitFrame4.insertView( 0, s_view5 )
s_splitFrame4.setSizes([640])
tabFrame1.insertTab(4, s_splitFrame4)
tabFrame1.setTabText(4, 'Stipple Plot')
tabFrame1.setCurrentIndex(1)

# execute pipeline
s_ParallelCoordinates_0.update()

# --- END STIPPLE WORKFLOW ---
