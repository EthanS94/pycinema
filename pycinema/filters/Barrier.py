from copy import deepcopy
from pycinema import Filter, getTableExtent

try:
  from PySide6 import QtWidgets
except Exception:
  pass

class Barrier(Filter):
  def __init__(self):
    self._buffer = [[]]  # latest input table
    self._pending_pass = False

    Filter.__init__(
      self,
      inputs={'table': [[]]},
      outputs={'table': [[]]}
    )

  def generateWidgets(self):
    w = QtWidgets.QFrame()
    w.setLayout(QtWidgets.QHBoxLayout())
    w.layout().setContentsMargins(0,0,0,0)

    btn = QtWidgets.QPushButton("Apply")
    w.layout().addWidget(btn)

    def do_pass():
      self._pending_pass = True
      self.update()

    btn.clicked.connect(do_pass)
    return w

  def _update(self):
    table = self.inputs.table.get()
    self._buffer = table if getTableExtent(table)[0] > 0 else [[]]

    if self._pending_pass:
      self.outputs.table.set(deepcopy(self._buffer))
      self._pending_pass = False

    return 1
