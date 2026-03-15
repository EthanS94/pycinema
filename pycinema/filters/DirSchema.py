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

            parts = re.split(r'[_]', p.name)[0:2]
            zarr_string = str(p)

            # Include 1 day, 3 day, 5 day as a column
            for day in ['1 day','3 day','5 day']:
                rows.append(parts + [day] + [f"{zarr_string}"] + [idx])
                idx += 1

    max_parts = max((len(r) - 1 for r in rows), default=0)
    headers = ["Model", "Scenario", "1/3/5 Day Accumulation", "file", "id"]

    # pad rows so all match header length
    table = [r[:-1] + [""] * (max_parts - (len(r) - 1)) + [r[-1]] for r in rows]

    return headers, table
