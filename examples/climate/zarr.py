import pycinema
import pycinema.filters
import pycinema.theater
import pycinema.theater.views

# pycinema settings
PYCINEMA = { 'VERSION' : '3.2.0'}

# filters
ParallelCoordinates_0 = pycinema.filters.ParallelCoordinates()
ImageView_0 = pycinema.filters.ImageView()
Barrier_0 = pycinema.filters.Barrier()
ZarrTimeSpan_0 = pycinema.filters.ZarrTimeSpan()
ColorMapping_0 = pycinema.filters.ColorMapping()
DirSchema_0 = pycinema.filters.DirSchema()
ZarrImageReader_0 = pycinema.filters.ZarrImageReader()
ImageAnnotation_0 = pycinema.filters.ImageAnnotation()

# properties
ParallelCoordinates_0.inputs.table.set(DirSchema_0.outputs.table, False)
ParallelCoordinates_0.inputs.ignore.set(['^file', '^id'], False)
ParallelCoordinates_0.inputs.selection.set([12, 13, 14, 27, 28, 29], False)
ParallelCoordinates_0.inputs.compose.set("", False)
ImageView_0.inputs.images.set(ImageAnnotation_0.outputs.images, False)
ImageView_0.inputs.selection.set([], False)
Barrier_0.inputs.table.set(ParallelCoordinates_0.outputs.table, False)
ZarrTimeSpan_0.inputs.table.set(Barrier_0.outputs.table, False)
ZarrTimeSpan_0.inputs.ignore.set(['^id'], False)
ColorMapping_0.inputs.map.set("PuRd", False)
ColorMapping_0.inputs.nan.set((1, 1, 1, 1), False)
ColorMapping_0.inputs.range.set((0, 0.008787989), False)
ColorMapping_0.inputs.channel.set("pr", False)
ColorMapping_0.inputs.images.set(ZarrImageReader_0.outputs.images, False)
ColorMapping_0.inputs.composition_id.set(-1, False)
DirSchema_0.inputs.directory.set("/scratch/07644/oxygen/LANL_cleaned_data/zarr_stores", False)
ZarrImageReader_0.inputs.table.set(Barrier_0.outputs.table, False)
ZarrImageReader_0.inputs.start_date.set(ZarrTimeSpan_0.outputs.start_date, False)
ZarrImageReader_0.inputs.end_date.set(ZarrTimeSpan_0.outputs.end_date, False)
ImageAnnotation_0.inputs.images.set(ColorMapping_0.outputs.images, False)
ImageAnnotation_0.inputs.xy.set((20, 20), False)
ImageAnnotation_0.inputs.size.set(20, False)
ImageAnnotation_0.inputs.spacing.set(0, False)
ImageAnnotation_0.inputs.color.set((), False)
ImageAnnotation_0.inputs.ignore.set(['^file', '^id'], False)

# layout
tabFrame0 = pycinema.theater.TabFrame()
splitFrame0 = pycinema.theater.SplitFrame()
splitFrame0.setHorizontalOrientation()
view0 = pycinema.theater.views.NodeEditorView()
splitFrame0.insertView( 0, view0 )
splitFrame0.setSizes([1724])
tabFrame0.insertTab(0, splitFrame0)
tabFrame0.setTabText(0, 'Layout 1')
splitFrame1 = pycinema.theater.SplitFrame()
splitFrame1.setHorizontalOrientation()
splitFrame2 = pycinema.theater.SplitFrame()
splitFrame2.setVerticalOrientation()
view2 = pycinema.theater.views.FilterView( ParallelCoordinates_0 )
splitFrame2.insertView( 0, view2 )
view6 = pycinema.theater.views.FilterView( Barrier_0 )
splitFrame2.insertView( 1, view6 )
view8 = pycinema.theater.views.FilterView( ZarrTimeSpan_0 )
splitFrame2.insertView( 2, view8 )
view10 = pycinema.theater.views.FilterView( ColorMapping_0 )
splitFrame2.insertView( 3, view10 )
splitFrame2.setSizes([362, 76, 75, 189])
splitFrame1.insertView( 0, splitFrame2 )
view4 = pycinema.theater.views.FilterView( ImageView_0 )
splitFrame1.insertView( 1, view4 )
splitFrame1.setSizes([860, 860])
tabFrame0.insertTab(1, splitFrame1)
tabFrame0.setTabText(1, 'Layout 2')
tabFrame0.setCurrentIndex(1)
pycinema.theater.Theater.instance.setCentralWidget(tabFrame0)

# execute pipeline
ParallelCoordinates_0.update()
