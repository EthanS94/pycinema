from pycinema import Filter
from pycinema import getTableExtent

import datetime as dt
import cftime
import json
import os
import re


def format_time_value(t):
    """
    Convert datetime-like values to YYYY-MM-DD strings.
    """
    if t is None:
        return None

    if isinstance(t, (dt.datetime, dt.date)):
        return t.strftime("%Y-%m-%d")

    if isinstance(t, cftime.datetime):
        return f"{t.year:04d}-{t.month:02d}-{t.day:02d}"

    if hasattr(t, "strftime"):
        return t.strftime("%Y-%m-%d")

    return str(t)


def parse_rolling_accumulation(metric_value):
    """
    Example:
        '1 Day' -> {'label': '1 Day', 'days': 1}
        '3 Day' -> {'label': '3 Day', 'days': 3}
    """
    label = str(metric_value)
    match = re.match(r"(\d+)", label)
    days = int(match.group(1)) if match else None

    return {
        "label": label,
        "days": days,
    }


def safe_list(value):
    """
    Convert tuples/lists to plain Python lists for JSON serialization.
    """
    if isinstance(value, (list, tuple)):
        return list(value)
    return value


class TableMetadataJSON(Filter):
    def __init__(self):
        super().__init__(
            inputs={
                "table": [[]],
                "output_path": "~/table_metadata.json",
                "deduplicate": [False],
            },
            outputs={
                "json_data": {},
                "json_text": "",
                "output_path": "",
            }
        )

    def _update(self):

        table = self.inputs.table.get()
        output_path = self.inputs.output_path.get()
        output_path = os.path.expanduser(output_path)
        deduplicate = self.inputs.deduplicate.get()

        tableExtent = getTableExtent(table)
        if tableExtent[0] < 1 or tableExtent[1] < 1:
            self.outputs.json_data.set({"entries": []})
            self.outputs.json_text.set('{\n  "entries": []\n}')
            self.outputs.output_path.set("")
            return 1

        headers = table[0]
        col_idx = {h: i for i, h in enumerate(headers)}

        dataset_col = col_idx.get("Dataset")
        collection_col = col_idx.get("Collection")
        time_col = col_idx.get("Time Span")
        lat_col = col_idx.get("Latitude")
        lon_col = col_idx.get("Longitude")
        metric_col = col_idx.get("Metric")
        scenario_col = col_idx.get("Scenario")

        required = {
            "Dataset": dataset_col,
            "Collection": collection_col,
            "Time Span": time_col,
            "Latitude": lat_col,
            "Longitude": lon_col,
            "Metric": metric_col,
            "Scenario": scenario_col,
        }

        missing = [name for name, idx in required.items() if idx is None]
        if missing:
            print(f"Missing required table columns: {missing}")
            self.outputs.json_data.set({"entries": []})
            self.outputs.json_text.set('{\n  "entries": []\n}')
            self.outputs.output_path.set("")
            return 1

        entries = []
        seen = set()

        for row in table[1:]:
            time_span = row[time_col]
            start_time = None
            end_time = None

            if isinstance(time_span, (list, tuple)) and len(time_span) >= 2:
                start_time = format_time_value(time_span[0])
                end_time = format_time_value(time_span[1])
            elif time_span is not None:
                start_time = format_time_value(time_span)
                end_time = format_time_value(time_span)

            metric_info = parse_rolling_accumulation(row[metric_col])

            entry = {
                "dataset_name": row[dataset_col],
                "collection": row[collection_col],
                "time_start": start_time,
                "time_end": end_time,
                "lat_range": safe_list(row[lat_col]),
                "lon_range": safe_list(row[lon_col]),
                "accumulation_days": metric_info["days"],
                "accumulation_label": metric_info["label"],
                "scenario": row[scenario_col],
            }

            if deduplicate:
                dedupe_key = (
                    entry["dataset_name"],
                    entry["collection"],
                    entry["time_start"],
                    entry["time_end"],
                    tuple(entry["lat_range"]) if isinstance(entry["lat_range"], list) else entry["lat_range"],
                    tuple(entry["lon_range"]) if isinstance(entry["lon_range"], list) else entry["lon_range"],
                    entry["accumulation_days"],
                    entry["accumulation_label"],
                    entry["scenario"],
                )
                if dedupe_key in seen:
                    continue
                seen.add(dedupe_key)

            entries.append(entry)

        json_data = {
            "entries": entries
        }

        json_text = json.dumps(json_data, indent=2)

        try:
            with open(output_path, "w+", encoding="utf-8") as f:
                f.write(json_text)

            print(f"Wrote metadata JSON: {output_path}")

        except Exception as e:
            print(f"Failed to write metadata JSON: {e}")
            self.outputs.json_data.set(json_data)
            self.outputs.json_text.set(json_text)
            self.outputs.output_path.set("")
            return 1

        self.outputs.json_data.set(json_data)
        self.outputs.json_text.set(json_text)
        self.outputs.output_path.set(output_path)

        return 1
