from pycinema import Filter

import os
from pathlib import Path
import re

class DirSchema(Filter):
    def __init__(self):
        super().__init__(
            inputs={
                'directory': ''
            },
            outputs={
                'table': [[]]
            }
        )

    def _update(self):

        top_dir = self.inputs.directory.get()
        headers, table = subdir_table(top_dir)
        table.insert(0, headers)

        self.outputs.table.set(table)

def has_nc_file(directory: Path):
    return any(f.suffix == ".nc" for f in directory.glob("*.nc"))

def is_zarr_file(f: Path):
    return f.suffix == ".zarr"

def get_nc_glob(directory: Path):
    files = [f.name for f in directory.rglob("*.nc")]
    common_prefix = os.path.commonprefix(files)

    # return early if common_prefix is the full file name
    if common_prefix == files[0]:
        return files[0]

    # Reverse strings to compute common suffix
    reversed_files = [f[::-1] for f in files]
    common_suffix = os.path.commonprefix(reversed_files)[::-1]

    return f"{common_prefix}*{common_suffix}"


def subdir_table(root):
    root = Path(root)
    rows = []

    idx = 0

    # FIXME: probably better to just hard code this to exactly what we want rather then trying to figure it out
    pattern = re.compile(r'^[^_]+([_][^_]+){1,}$')  # at least 2 segments separated by _ or -
    for p in root.rglob("*"):

        if (p.is_dir()
            and pattern.match(p.name)
            and has_nc_file(p)):

            parts = re.split(r'[_]', p.name)
            nc_glob_string = get_nc_glob(p)

            # Include 1 day, 3 day, 5 day as a column
            for day in ['1 day','3 day','5 day']:
                rows.append(parts + [day] + [f"{p}/{nc_glob_string}"] + [idx])
                idx += 1

        elif (p.is_dir() and has_nc_file(p)):
            parts = [p.name, 'N/A']
            nc_glob_string = get_nc_glob(p)

            # Include 1 day, 3 day, 5 day as a column
            for day in ['1 day','3 day','5 day']:
                rows.append(parts + [day] + [f"{p}/{nc_glob_string}"] + [idx])
                idx += 1

        elif (p.is_dir()
            and pattern.match(p.name)
            and is_zarr_file(p)):

            # Historical Observations
            if "obs_" in str(p):
                model_name = re.split(r'_[0-9]', p.name)[0]
                hist_type = 'observational'
                future_type = 'N/A'

            # Historical Models
            elif "historical" in str(p):
                model_name = re.split(r'_historical', p.name)[0]
                hist_type = 'model'
                future_type = 'N/A'

            # Future Models
            else:
                if 'ssp245' in p.name:
                    model_name = re.split(r'_ssp245', p.name)[0]
                    hist_type = 'N/A'
                    future_type = 'ssp245'
                elif 'ssp370' in p.name:
                    model_name = re.split(r'_ssp370', p.name)[0]
                    hist_type = 'N/A'
                    future_type = 'ssp370'
                elif 'ssp585' in p.name:
                    model_name = re.split(r'_ssp585', p.name)[0]
                    hist_type = 'N/A'
                    future_type = 'ssp585'
                elif 'future-scenario' in p.name:
                    model_name = re.split(r'_future-scenario', p.name)[0]
                    hist_type = 'N/A'
                    future_type = 'future-scenario'

            parts = [model_name, hist_type, future_type]
            zarr_string = str(p)

            # Include 1 day, 3 day, 5 day as a column
            for day in ['1 day','3 day','5 day']:
                rows.append(parts + [day] + [zarr_string] + [idx])
                idx += 1

    headers = ["Model Name", "Historical", "Future", "Accumulation", "file", "id"]

    return headers, rows
