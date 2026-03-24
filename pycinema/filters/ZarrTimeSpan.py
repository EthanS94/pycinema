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

  def get_selected_dates(self):
    ds = (self.inputs.state.get() or {}).get('date')
    if not ds:
      return None, None

    base = ds['start_date']
    v = ds.get('V') or [0]

    # Always ensure 2 values exist for range logic
    v0 = int(v[0]) if len(v) >= 1 else 0
    v1 = int(v[1]) if len(v) >= 2 else v0

    if ds.get('M', 'S') == 'S':
      d = base + timedelta(days=v0)
      return d, d

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

    st = self.inputs.state.get() or {}
    prev = st.get('date')

    bounds_changed = (
      prev is None or
      prev.get('start_date') != start_date or
      prev.get('end_date') != end_date
    )

    if reset_on_change and bounds_changed:
      ds = {'M': 'S', 'V': [0]}
    else:
      ds = prev or {'M': 'S', 'V': [0]}

    ds['start_date'] = start_date
    ds['end_date'] = end_date
    ds['span_days'] = span

    mode = ds.get('M', 'S')
    v = ds.get('V') or [0]

    # normalize length BEFORE clamping
    if mode == 'O':  # range needs 2
      v0 = int(v[0]) if len(v) >= 1 else 0
      v1 = int(v[1]) if len(v) >= 2 else v0
      v = [v0, v1]
    else:            # single needs 1
      v = [int(v[0]) if len(v) else 0]

    # clamp into new bounds
    v = [min(max(int(x), 0), span) for x in v]
    ds['V'] = v

    st['date'] = ds
    self.inputs.state.set(st)

  # -------- widgets --------
  def generateWidgets(self):
    w = QtWidgets.QFrame()
    lay = QtWidgets.QHBoxLayout(w)
    lay.setContentsMargins(0,0,0,0)

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

    lay.addWidget(w.toggle)
    lay.addWidget(w.single, 1)
    lay.addWidget(w.range, 1)
    lay.addWidget(w.edit_single)
    lay.addWidget(w.edit_start)
    lay.addWidget(w.edit_end)

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
        i0 = self._d2i(d0, ds['start_date'])
        i1 = self._d2i(d1, ds['start_date'])
      except Exception:
        return
      lo = min(max(min(i0, i1), 0), ds['span_days'])
      hi = min(max(max(i0, i1), 0), ds['span_days'])
      ds['V'] = [lo, hi]
      st['date'] = ds
      self.inputs.state.set(st)

    w.toggle.toggled.connect(set_mode)
    w.single.valueChanged.connect(set_single_slider)
    w.range.valueChanged.connect(set_range_slider)
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
    w.range.setRange(0, span)

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
      hi = int(vv[1] if len(vv) > 1 else vv[0])
      w.range.setValue((lo, hi))
      w.edit_start.setText(self._i2d(lo, start_date).isoformat())
      w.edit_end.setText(self._i2d(hi, start_date).isoformat())

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

    output_s, output_e = self.get_selected_dates()
    dates = [output_s, output_e]
    headers = table[0] + ["Time Span"]
    output_table = [input_row + [dates] for input_row in table[1:]]
    output_table.insert(0, headers)
    self.outputs.table.set(output_table)

    self.emitter.s_update.emit()
    return 1
