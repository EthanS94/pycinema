1. clone and install climate branch

```
git clone git@github.com:EthanS94/pycinema.git
cd pycinema
git checkout -b climate climate
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

4. update example scripts to use the path to transferred zarrs:
```
diff --git a/examples/climate/quantile.py b/examples/climate/quantile.py
index 139beb3..594a7c2 100644
--- a/examples/climate/quantile.py
+++ b/examples/climate/quantile.py
@@ -9,7 +9,7 @@ from copy import copy
 PYCINEMA = { 'VERSION' : '3.2.0'}
 
 #base_zarr_dir = "/scratch/07644/oxygen/LANL_cleaned_data/interp_zarr_stores/"
-base_zarr_dir = "/Users/stam/projects/visRandD_2026/utaustin_collab/03242026/data/interp_zarr_stores/"
+base_zarr_dir = "<your-path-to>/data/interp_zarr_stores/"
 CMIP6_FUTURE = base_zarr_dir + "cmip6_future-scenario_pr_2015-2100.zarr"
 CMIP6_HISTORICAL = base_zarr_dir + "cmip6_historical_pr_1850-2014.zarr"
 CMIP6_OBS = base_zarr_dir + "obs_cmip6-interp_pr_1980-2023.zarr"
diff --git a/examples/climate/stipple.py b/examples/climate/stipple.py
index 7ecd69b..d6412d9 100644
--- a/examples/climate/stipple.py
+++ b/examples/climate/stipple.py
@@ -9,7 +9,7 @@ from copy import copy
 PYCINEMA = { 'VERSION' : '3.2.0'}
 
 #base_zarr_dir = "/scratch/07644/oxygen/LANL_cleaned_data/interp_zarr_stores/"
-base_zarr_dir = "/Users/stam/projects/visRandD_2026/utaustin_collab/03242026/data/interp_zarr_stores/"
+base_zarr_dir = "<your-path-to>/data/interp_zarr_stores/"
 CMIP6_FUTURE = base_zarr_dir + "cmip6_future-scenario_pr_2015-2100.zarr"
 CMIP6_HISTORICAL = base_zarr_dir + "cmip6_historical_pr_1850-2014.zarr"
 CMIP6_OBS = base_zarr_dir + "obs_cmip6-interp_pr_1980-2023.zarr"
```

5. run the examples (Note that for the downsampled zarrs, 3 and 5 day accumulations won't work)
```
cinema pycinema/examples/climate/stipple.py
#or
cinema pycinema/examples/climate/quantile.py
```
