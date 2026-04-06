1. clone and install climate branch

```
git clone https://github.com/EthanS94/pycinema.git
cd pycinema
git checkout -b climate origin/climate
cd ..
```

2. setup python venv with python 3.11 (expected to be 3.11 for zarr compatibilities)

```
python3.11 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install ./pycinema
```

3. transfer downsampled (first of each month) zarrs locally
```
mkdir data
cd data
rsync -av ls6.tacc.utexas.edu:/scratch/11355/stam/downsampled_zarrs/LANL_cleaned_data/interp_zarr_stores/ .
```

4. update `examples/climate/combine.py` example script to use correct path:
```
diff --git a/examples/climate/combined.py b/examples/climate/combined.py
index 4d1cc14..7397c06 100644
--- a/examples/climate/combined.py
+++ b/examples/climate/combined.py
@@ -8,8 +8,7 @@ from copy import copy
 # pycinema settings
 PYCINEMA = { 'VERSION' : '3.2.0'}
 
-#base_zarr_dir = "/scratch/07644/oxygen/LANL_cleaned_data/interp_zarr_stores/"
-base_zarr_dir = "/Users/stam/projects/visRandD_2026/utaustin_collab/03242026/data/interp_zarr_stores/"
+base_zarr_dir = "<YOUR-PATH-TO>/data/interp_zarr_stores/"
 CMIP6_FUTURE = base_zarr_dir + "cmip6_future-scenario_pr_2015-2100.zarr"
 CMIP6_HISTORICAL = base_zarr_dir + "cmip6_historical_pr_1850-2014.zarr"
 CMIP6_OBS = base_zarr_dir + "obs_cmip6-interp_pr_1980-2023.zarr"
```

5. run the combine.py example (Note that for the downsampled zarrs, 3 and 5 day accumulations won't work)
```
cinema pycinema/examples/climate/combine.py
```
