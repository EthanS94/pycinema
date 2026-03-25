import pycinema
import pycinema.filters
import pycinema.theater
import pycinema.theater.views

# pycinema settings
PYCINEMA = { 'VERSION' : '3.2.0'}

# filters
ParallelCoordinates_0 = pycinema.filters.ParallelCoordinates()
Barrier_0 = pycinema.filters.Barrier()
DirSchema_0 = pycinema.filters.DirSchema()
ZarrToDS_0 = pycinema.filters.ZarrToDS()
ZarrTimeSpan_0 = pycinema.filters.ZarrTimeSpan()
StippleCompare_0 = pycinema.filters.StippleCompare()
DSTimeSample_0 = pycinema.filters.DSTimeSample()
ImageView_0 = pycinema.filters.ImageView()

# properties
ParallelCoordinates_0.inputs.table.set(DirSchema_0.outputs.table, False)
ParallelCoordinates_0.inputs.ignore.set(['^file', '^id'], False)
ParallelCoordinates_0.inputs.selection.set([6, 9], False)
ParallelCoordinates_0.inputs.compose.set("Model Name", False)
Barrier_0.inputs.table.set(ZarrTimeSpan_0.outputs.table, False)
DirSchema_0.inputs.directory.set("/scratch/07644/oxygen/LANL_cleaned_data/interp_zarr_stores", False)
ZarrToDS_0.inputs.table.set(Barrier_0.outputs.table, False)
ZarrTimeSpan_0.inputs.table.set(ParallelCoordinates_0.outputs.table, False)
ZarrTimeSpan_0.inputs.ignore.set(['^id'], False)
StippleCompare_0.inputs.table.set(DSTimeSample_0.outputs.table, False)
DSTimeSample_0.inputs.table.set(ZarrToDS_0.outputs.table, False)
DSTimeSample_0.inputs.start_date.set("", False)
DSTimeSample_0.inputs.end_date.set("", False)
ImageView_0.inputs.images.set(StippleCompare_0.outputs.images, False)
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
