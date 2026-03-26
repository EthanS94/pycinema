from pycinema import Filter, Image

import cftime
import datetime as dt
import numpy as np
import pandas as pd
import re
import sys
import xarray as xr

from pycinema import getTableExtent

# Optional: cache opened datasets by zarr path
ds_cache = {}


def read_zarr_auto(path, max_points=2_000_000, **open_kwargs):
    ds = xr.open_zarr(
        path,
        chunks="auto",
        create_default_indexes=False,
        **open_kwargs,
    )

    lat_dim = "lat" if "lat" in ds.dims else None
    lon_dim = "lon" if "lon" in ds.dims else None

    if lat_dim and lon_dim:
        nlat = ds.sizes[lat_dim]
        nlon = ds.sizes[lon_dim]

        step = 1
        while (nlat // step) * (nlon // step) > max_points:
            step += 1

        ds = ds.isel(
            **{
                lat_dim: slice(None, None, step),
                lon_dim: slice(None, None, step),
            }
        )

    return ds


class ZarrToDS(Filter):
    def __init__(self):
        super().__init__(
            inputs={
                "table": [[]],
            },
            outputs={
                "table": [[]]
            }
        )

        # Retained state between updates
        self._prev_header = None
        self._prev_input_rows = []
        self._prev_output_rows = []

    def _update(self):
        table = self.inputs.table.get()
        tableExtent = getTableExtent(table)

        if tableExtent[0] < 1 or tableExtent[1] < 1:
            self._clear_cache()
            return self.outputs.table.set([])

        header = table[0]
        input_rows = table[1:]

        # get .zarr globs from table
        file_col = next((i for i, h in enumerate(header) if h == "file"), None)
        if file_col is None:
            print("File column (file) not found in input table")
            self._clear_cache()
            self.outputs.table.set([])
            return 1

        # get rolling_cumulation from table
        rc_col = next((i for i, h in enumerate(header) if h == "Accumulation"), None)
        if rc_col is None:
            print("Accumulation column (Accumulation) not found in input table")
            self._clear_cache()
            self.outputs.table.set([])
            return 1

        # get model_name from table
        mn_col = next((i for i, h in enumerate(header) if h == "Model Name"), None)
        if mn_col is None:
            print("Model name column (Model Name) not found in input table")
            self._clear_cache()
            self.outputs.table.set([])
            return 1

        # If header changed, invalidate retained rows
        header_changed = self._prev_header != header

        output_header = header + ["xr_dataset"]
        output_table = [output_header]
        new_output_rows = []

        for i, row in enumerate(input_rows):
            row_copy = list(row)

            # Reuse retained output row if the input row is unchanged
            can_reuse = (
                not header_changed
                and i < len(self._prev_input_rows)
                and i < len(self._prev_output_rows)
                and row_copy == self._prev_input_rows[i]
            )

            if can_reuse:
                retained_output_row = self._prev_output_rows[i]
                output_table.append(retained_output_row)
                new_output_rows.append(retained_output_row)
                continue

            # Otherwise recompute only this row
            zarr_file = row[file_col]
            rolling_c = row[rc_col]

            print(f"reading {zarr_file} at {rolling_c} accumulation...")

            try:
                rolling_c = int(str(rolling_c).split(" ")[0])
            except Exception as e:
                print(f"Could not parse Accumulation value '{rolling_c}': {e}")
                output_row = row_copy + [None]
                output_table.append(output_row)
                new_output_rows.append(output_row)
                continue

            ds = zarr_to_ds(zarr_file, rolling_c, reuse=True)

            if ds is not None:
                try:
                    # Downselect to chosen model if ds contains multiple models
                    if "model" in ds.dims:
                        ds = ds.sel(model=row[mn_col])
                except Exception as e:
                    print(f"Model selection failed for row {i}: {e}")
                    ds = None

            output_row = row_copy + [ds]
            output_table.append(output_row)
            new_output_rows.append(output_row)

        # Retain current input/output state for next update
        self._prev_header = list(header)
        self._prev_input_rows = [list(r) for r in input_rows]
        self._prev_output_rows = list(new_output_rows)

        self.outputs.table.set(output_table)

    def _clear_cache(self):
        self._prev_header = None
        self._prev_input_rows = []
        self._prev_output_rows = []


def zarr_to_ds(zarr_path, rolling_c=1, reuse=True):
    """
    Returns: xarray dataset by reading in zarr_path
    Caches base datasets by zarr_path.
    """
    global ds_cache

    base_ds = None

    if reuse and zarr_path in ds_cache:
        base_ds = ds_cache[zarr_path]
    else:
        try:
            base_ds = xr.open_zarr(zarr_path, decode_times=True)

            # Remove history var if it exists
            base_ds = base_ds.drop_vars("history", errors="ignore")

            # Select scenario if it exists
            if "scenario" in base_ds.dims:
                base_ds = base_ds.isel(scenario=0)

            # Normalize T12:00:0000 to T00:00:0000 so selection works better
            if "time" in base_ds.coords:
                base_ds = base_ds.assign_coords(time=base_ds.time.dt.floor("D"))

            ds_cache[zarr_path] = base_ds

        except Exception as e:
            print(e)
            ds_cache.pop(zarr_path, None)
            return None

    if rolling_c > 1:
        try:
            ds_rolled = base_ds.assign(
                pr=base_ds["pr"].rolling(time=rolling_c, center=False).sum(skipna=True)
            )
            return ds_rolled
        except Exception as e:
            print(e)
            return None

    return base_ds
