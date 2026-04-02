from pycinema import Filter, getTableExtent

from copy import deepcopy
import cftime
from datetime import datetime, timedelta
import glob, re
import numpy as np
import pandas as pd
import xarray as xr

from PySide6 import QtCore, QtWidgets
from superqt import QRangeSlider

try:
  class Emitter(QtCore.QObject):
    s_update = QtCore.Signal()
    def __init__(self): super().__init__()
except NameError:
  class Emitter:
    def __init__(self): pass


class ZarrTimeSpan(Filter):
  def __init__(self):
    self.emitter = Emitter()
    self.ignore = False

    Filter.__init__(
      self,
      inputs={'table': [[]], 'ignore': ['^id'], 'state': {}},
      outputs={'table': [[]]}
    )

  # -------- date/int helpers --------
  @staticmethod
  def _i2d(i, start_date):  # int days -> date
    return start_date + timedelta(days=int(i))

  @staticmethod
  def _d2i(d, start_date):  # date -> int days
    return (d - start_date).days

  @staticmethod
  def _parse_date(s):
    # accept YYYY-MM-DD
    return datetime.strptime(s.strip(), "%Y-%m-%d").date()

  @staticmethod
  def _start_of_decade(d):
    year = (d.year // 10) * 10
    return datetime(year, 1, 1).date()

  @staticmethod
  def _snap_to_decade(d):
    year = round(d.year / 10) * 10
    return datetime(year, 1, 1).date()

  def _decade_index_to_date(self, i, start_decade_date):
    year = start_decade_date.year + int(i) * 10
    return datetime(year, 1, 1).date()

  def _date_to_decade_index(self, d, start_decade_date):
    return max(0, (d.year - start_decade_date.year) // 10)

  def get_selected_dates(self):
    ds = (self.inputs.state.get() or {}).get('date')
    if not ds:
      return None, None

    base = ds['start_date']
    v = ds.get('V') or [0]

    v0 = int(v[0]) if len(v) >= 1 else 0
    v1 = int(v[1]) if len(v) >= 2 else v0

    if ds.get('M', 'S') == 'S':
      d = base + timedelta(days=v0)
      return d, d

    start_decade = ds['start_decade_date']
    d0 = self._decade_index_to_date(v0, start_decade)
    d1 = self._decade_index_to_date(v1, start_decade)
    return d0, d1

    # threshold mode
    return (base + timedelta(days=v0),
            base + timedelta(days=v1))

  def to_cftime(self, t):
    # unwrap numpy arrays / xarray scalar containers
    if isinstance(t, np.ndarray):
      if t.ndim == 0:
        t = t.item()
      elif t.size == 1:
        t = t.reshape(-1)[0]
      else:
        raise ValueError("Expected a scalar time value, got an array")

    # Already cftime
    if isinstance(t, cftime.datetime):
      return t

    # Convert numpy/pandas datetime
    ts = pd.Timestamp(t)
    return cftime.DatetimeNoLeap(
      ts.year, ts.month, ts.day,
      ts.hour, ts.minute, ts.second
    )

  def _ensure_date_state(self, start_date, end_date, reset_on_change=True):
    span = max(0, (end_date - start_date).days)

    start_decade_date = datetime((start_date.year // 10) * 10, 1, 1).date()
    end_decade_date = datetime((end_date.year // 10) * 10, 1, 1).date()
    decade_span = max(0, (end_decade_date.year - start_decade_date.year) // 10)

    st = self.inputs.state.get() or {}
    prev = st.get('date')

    bounds_changed = (
      prev is None or
      prev.get('start_date') != start_date or
      prev.get('end_date') != end_date
    )

    if reset_on_change and bounds_changed:
      ds = {'M': 'O', 'V': [0]}
    else:
      ds = prev or {'M': 'O', 'V': [0]}

    ds['start_date'] = start_date
    ds['end_date'] = end_date
    ds['span_days'] = span
    ds['start_decade_date'] = start_decade_date
    ds['end_decade_date'] = end_decade_date
    ds['span_decades'] = decade_span

    mode = ds.get('M', 'S')
    v = ds.get('V') or [0]

    if mode == 'O':
      v0 = int(v[0]) if len(v) >= 1 else 0
      v1 = int(v[1]) if len(v) >= 2 else v0
      v = [min(max(v0, 0), decade_span), min(max(v1, 0), decade_span)]
    else:
      v = [min(max(int(v[0]) if len(v) else 0, 0), span)]

    ds['V'] = v

    st['date'] = ds
    self.inputs.state.set(st)

  # -------- widgets --------
  def generateWidgets(self):
    w = QtWidgets.QFrame()
    main = QtWidgets.QVBoxLayout(w)
    main.setContentsMargins(0,0,0,0)

    # ---------- DATE ROW ----------
    date_row = QtWidgets.QHBoxLayout()

    w.toggle = QtWidgets.QCheckBox("Threshold")

    w.single = QtWidgets.QSlider(QtCore.Qt.Horizontal)
    w.range = QRangeSlider(QtCore.Qt.Horizontal)

    w.edit_single = QtWidgets.QLineEdit()
    w.edit_single.setPlaceholderText("YYYY-MM-DD")
    w.edit_single.setMaximumWidth(110)

    w.edit_start = QtWidgets.QLineEdit()
    w.edit_start.setPlaceholderText("start YYYY-MM-DD")
    w.edit_start.setMaximumWidth(140)

    w.edit_end = QtWidgets.QLineEdit()
    w.edit_end.setPlaceholderText("end YYYY-MM-DD")
    w.edit_end.setMaximumWidth(140)

    #date_row.addWidget(w.toggle)
    date_row.addWidget(w.single, 1)
    date_row.addWidget(w.range, 1)
    date_row.addWidget(w.edit_single)
    date_row.addWidget(w.edit_start)
    date_row.addWidget(w.edit_end)

    main.addLayout(date_row)

    # ---------- LAT ROW ----------
    lat_row = QtWidgets.QHBoxLayout()

    w.lat = QRangeSlider(QtCore.Qt.Horizontal)

    w.edit_lat_min = QtWidgets.QLineEdit()
    w.edit_lat_min.setPlaceholderText("-90")
    w.edit_lat_min.setMaximumWidth(60)

    w.edit_lat_max = QtWidgets.QLineEdit()
    w.edit_lat_max.setPlaceholderText("90")
    w.edit_lat_max.setMaximumWidth(60)

    w.lat_label = QtWidgets.QLabel()

    lat_row.addWidget(QtWidgets.QLabel("Lat"))
    lat_row.addWidget(w.lat, 1)
    lat_row.addWidget(w.edit_lat_min)
    lat_row.addWidget(w.edit_lat_max)
    lat_row.addWidget(w.lat_label)

    main.addLayout(lat_row)

    # ---------- LON ROW ----------
    lon_row = QtWidgets.QHBoxLayout()

    w.lon = QRangeSlider(QtCore.Qt.Horizontal)

    w.edit_lon_min = QtWidgets.QLineEdit()
    w.edit_lon_min.setPlaceholderText("-180")
    w.edit_lon_min.setMaximumWidth(60)

    w.edit_lon_max = QtWidgets.QLineEdit()
    w.edit_lon_max.setPlaceholderText("180")
    w.edit_lon_max.setMaximumWidth(60)

    w.lon_label = QtWidgets.QLabel()

    lon_row.addWidget(QtWidgets.QLabel("Lon"))
    lon_row.addWidget(w.lon, 1)
    lon_row.addWidget(w.edit_lon_min)
    lon_row.addWidget(w.edit_lon_max)
    lon_row.addWidget(w.lon_label)

    main.addLayout(lon_row)

    # ---- callbacks that only touch state ----
    # FIXME: when switching to threshold at min value,
    #  can't move sliders. Guessing due to min value
    #  slider being on top
    def set_mode(checked):
      if self.ignore: return
      st = deepcopy(self.inputs.state.get()) or {}
      ds = st.get('date', {})
      ds['M'] = 'O' if checked else 'S'
      vv = ds.get('V', [0])
      ds['V'] = [vv[0], vv[-1] if len(vv) > 1 else vv[0]] if checked else [vv[0]]
      st['date'] = ds
      self.inputs.state.set(st)

    def set_single_slider(v):
      if self.ignore: return
      st = deepcopy(self.inputs.state.get()) or {}
      ds = st.get('date', {})
      ds['V'] = [int(v)]
      st['date'] = ds
      self.inputs.state.set(st)

    def set_range_slider(v):
      if self.ignore: return
      lo, hi = map(int, v)
      st = deepcopy(self.inputs.state.get()) or {}
      ds = st.get('date', {})
      ds['V'] = [lo, hi]
      st['date'] = ds
      self.inputs.state.set(st)

    def set_single_text():
      if self.ignore: return
      st = deepcopy(self.inputs.state.get()) or {}
      ds = st.get('date')
      if not ds: return
      try:
        d = self._parse_date(w.edit_single.text())
        i = self._d2i(d, ds['start_date'])
      except Exception:
        return
      i = min(max(i, 0), ds['span_days'])
      ds['V'] = [i]
      st['date'] = ds
      self.inputs.state.set(st)

    def set_range_texts():
      if self.ignore: return
      st = deepcopy(self.inputs.state.get()) or {}
      ds = st.get('date')
      if not ds: return
      try:
        d0 = self._parse_date(w.edit_start.text())
        d1 = self._parse_date(w.edit_end.text())
        i0 = self._date_to_decade_index(d0, ds['start_decade_date'])
        i1 = self._date_to_decade_index(d1, ds['start_decade_date'])
      except Exception:
        return
      lo = min(max(min(i0, i1), 0), ds['span_decades'])
      hi = min(max(max(i0, i1), 0), ds['span_decades'])
      ds['V'] = [lo, hi]
      st['date'] = ds
      self.inputs.state.set(st)

    def set_lat(v):
        if self.ignore: return
        lo, hi = map(float, v)
        st = deepcopy(self.inputs.state.get()) or {}
        st['lat']['V'] = [lo, hi]
        self.inputs.state.set(st)
    
    def set_lon(v):
        if self.ignore: return
        lo, hi = map(float, v)
        st = deepcopy(self.inputs.state.get()) or {}
        st['lon']['V'] = [lo, hi]
        self.inputs.state.set(st)

    def set_lat_text():
        if self.ignore: return
        st = deepcopy(self.inputs.state.get()) or {}
        try:
            lo = int(w.edit_lat_min.text())
            hi = int(w.edit_lat_max.text())
        except:
            return
        lo, hi = sorted([lo, hi])
        st['lat']['V'] = [lo, hi]
        self.inputs.state.set(st)
    
    def set_lon_text():
        if self.ignore: return
        st = deepcopy(self.inputs.state.get()) or {}
        try:
            lo = int(w.edit_lon_min.text())
            hi = int(w.edit_lon_max.text())
        except:
            return
        lo, hi = sorted([lo, hi])
        st['lon']['V'] = [lo, hi]
        self.inputs.state.set(st)
    
    w.edit_lat_min.editingFinished.connect(set_lat_text)
    w.edit_lat_max.editingFinished.connect(set_lat_text)
    w.edit_lon_min.editingFinished.connect(set_lon_text)
    w.edit_lon_max.editingFinished.connect(set_lon_text)

    w.lat.valueChanged.connect(lambda v: w.lat_label.setText(f"{v[0]} → {v[1]}"))
    w.lon.valueChanged.connect(lambda v: w.lon_label.setText(f"{v[0]} → {v[1]}"))

    w.lat.sliderReleased.connect(
      lambda: set_lat(w.lat.value())
    )

    w.lon.sliderReleased.connect(
      lambda: set_lon(w.lon.value())
    )

    w.toggle.toggled.connect(set_mode)
    w.single.sliderReleased.connect(
      lambda: set_single_slider(w.single.value())
    )
    w.range.sliderReleased.connect(
      lambda: set_range_slider(w.range.value())
    )
    w.edit_single.editingFinished.connect(set_single_text)
    w.edit_start.editingFinished.connect(set_range_texts)
    w.edit_end.editingFinished.connect(set_range_texts)

    self.emitter.s_update.connect(lambda: self.updateWidgets(w))
    self.updateWidgets(w)
    return w

  def updateWidgets(self, w):
    st = self.inputs.state.get() or {}
    ds = st.get('date')
    if not ds:
      return

    start_date = ds['start_date']
    span = ds['span_days']
    mode = ds.get('M', 'S')
    vv = ds.get('V', [0])

    self.ignore = True

    w.single.setRange(0, span)
    w.single.setSingleStep(1)
    w.single.setPageStep(30)

    if mode == 'O':
      w.range.setRange(0, ds['span_decades'])
      w.range.setSingleStep(1)
      w.range.setPageStep(1)
    else:
      w.range.setRange(0, span)
      w.range.setSingleStep(1)
      w.range.setPageStep(30)

    w.lat.setRange(-90, 90)
    w.lon.setRange(-180, 180)

    w.toggle.setChecked(mode == 'O')

    w.single.setVisible(mode == 'S')
    w.edit_single.setVisible(mode == 'S')

    w.range.setVisible(mode == 'O')
    w.edit_start.setVisible(mode == 'O')
    w.edit_end.setVisible(mode == 'O')

    if mode == 'S':
      i = int(vv[0])
      w.single.setValue(i)
      w.edit_single.setText(self._i2d(i, start_date).isoformat())
    else:
      lo = int(vv[0])
      # vv[0] + 1 to make sure the range is shown when first activated
      hi = int(vv[0] + 1 if vv[1] == vv[0] else vv[1] if len(vv) > 1 else vv[0])
      w.range.setValue((lo, hi))
      decade_base = ds['start_decade_date']
      w.edit_start.setText(self._decade_index_to_date(lo, decade_base).isoformat())
      w.edit_end.setText(self._decade_index_to_date(hi, decade_base).isoformat())

    lat = st['lat']['V']
    lon = st['lon']['V']
    
    self.ignore = True
    
    w.lat.setValue(tuple(lat))
    w.lon.setValue(tuple(lon))
    
    w.edit_lat_min.setText(str(lat[0]))
    w.edit_lat_max.setText(str(lat[1]))
    
    w.edit_lon_min.setText(str(lon[0]))
    w.edit_lon_max.setText(str(lon[1]))
    
    w.lat_label.setText(f"{lat[0]} → {lat[1]}")
    w.lon_label.setText(f"{lon[0]} → {lon[1]}")
    
    self.ignore = False

  # -------- update --------
  def _update(self):
    table = self.inputs.table.get()
    tableExtent = getTableExtent(table)
    if tableExtent[0] < 1 or tableExtent[1] < 1:
      self.outputs.table.set([])
      return 0

    # find "file" column
    file_col = next((i for i, h in enumerate(table[0]) if h == "file"), None)
    if file_col is None:
      self.outputs.table.set([])
      self.emitter.s_update.emit()
      return 1

    st = self.inputs.state.get() or {}
    lat_min = -90
    lat_max = 90
    lon_min = -180
    lon_max = 180

    if 'lat' not in st:
        st['lat'] = {'V': [lat_min, lat_max], 'B': [lat_min, lat_max]}
    else:
        st['lat']['B'] = [lat_min, lat_max]
    
    if 'lon' not in st:
        st['lon'] = {'V': [lon_min, lon_max], 'B': [lon_min, lon_max]}
    else:
        st['lon']['B'] = [lon_min, lon_max]
    
    self.inputs.state.set(st)

    # compute start/end from filenames
    zarr_globs = [row[file_col] for row in table[1:]]
    start_date = end_date = None
    year_to_year_pattern = re.compile(r'[0-9]+-[0-9]+\.zarr$')
    just_year_pattern = re.compile(r'[0-9]+\.zarr$')

    for g in zarr_globs:
        try:
            ds = xr.open_zarr(g, consolidated=None)[["time"]]
        except:
            print(f"Error loading {g} to inspect time range. Skipping.")
            continue
        s = self.to_cftime(ds.time.isel(time=0).values)
        s = datetime(s.year, s.month, s.day).date()
        e = self.to_cftime(ds.time.isel(time=-1).values)
        e = datetime(e.year, e.month, e.day).date()
        start_date = s if start_date is None else max(start_date, s)
        end_date = e if end_date is None else min(end_date, e)

    if start_date is None or end_date is None:
      self.outputs.table.set(table)
      self.emitter.s_update.emit()
      return 1

    # init/clamp slider state
    self._ensure_date_state(start_date, end_date, reset_on_change=True)

    st = self.inputs.state.get()
    output_s, output_e = self.get_selected_dates()
    dates = [output_s, output_e]
    lats = st['lat']['V']
    lons = st['lon']['V']
    headers = table[0] + ["Time Span", 'Latitude', 'Longitude']
    output_table = [input_row + [dates, lats, lons] for input_row in table[1:]]
    output_table.insert(0, headers)
    self.outputs.table.set(output_table)

    self.emitter.s_update.emit()
    return 1
