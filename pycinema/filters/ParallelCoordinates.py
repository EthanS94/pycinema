import sqlite3
import re
from copy import deepcopy

from pycinema.filters.ParametersView import computeValues

from pycinema import Filter, getTableExtent, getColumnIndexFromTable, isNumber
from pycinema.filters.TableQuery import executeSQL, createTable, insertData, queryData

try:
    from PySide6 import QtGui, QtCore, QtWidgets
except ImportError:
    pass

try:
    def createLabel(parent, text):
        item = QtWidgets.QGraphicsSimpleTextItem(str(text), parent)
        font = QtGui.QFont()
        font.setPointSize(10)
        item.setFont(font)

        palette = QtCore.QCoreApplication.instance().palette()
        item.setBrush(palette.text().color())
        item.setCursor(QtCore.Qt.PointingHandCursor)
        return item


    class Lines(QtWidgets.QGraphicsItem):
        def __init__(self):
            super().__init__()
            self.br = QtCore.QRectF(0, 0, 0, 0)

            dark_theme = (
                QtCore.QCoreApplication.instance().palette().base().color().red() < 100
            )
            if dark_theme:
                self.pen_line_normal = QtGui.QPen(QtGui.QColor("#555"))
                self.pen_line_highlight = QtGui.QPen(QtGui.QColor("#fff"))
            else:
                self.pen_line_normal = QtGui.QPen(QtGui.QColor("#eee"))
                self.pen_line_highlight = QtGui.QPen(QtGui.QColor("#333"))

            self.pen_line_highlight.setWidth(2)

            self.lines_normal = []
            self.lines_highlight = []

            self.path_normal = QtGui.QPainterPath()
            self.path_highlight = QtGui.QPainterPath()

        def setBoundingRect(self, br):
            self.prepareGeometryChange()
            self.br = br

            self.path_normal = QtGui.QPainterPath()
            self.path_highlight = QtGui.QPainterPath()

            if len(self.lines_normal) < 1 and len(self.lines_highlight) < 1:
                return

            x0 = self.br.x()
            y0 = self.br.y()
            w = self.br.width()
            h = self.br.height()

            interpolate = lambda l, q, q0: q0 + l * q

            for lines, path in (
                (self.lines_normal, self.path_normal),
                (self.lines_highlight, self.path_highlight),
            ):
                for line in lines:
                    path.moveTo(
                        interpolate(line[0], w, x0),
                        interpolate(line[1], h, y0),
                    )
                    path.lineTo(
                        interpolate(line[2], w, x0),
                        interpolate(line[3], h, y0),
                    )

        def boundingRect(self):
            return self.br

        def paint(self, painter, option, widget):
            painter.setPen(self.pen_line_normal)
            painter.drawPath(self.path_normal)
            painter.setPen(self.pen_line_highlight)
            painter.drawPath(self.path_highlight)


    class Axis(QtWidgets.QGraphicsItem):
        def __init__(self, parameter, filter):
            super().__init__()

            self.br = QtCore.QRectF(0, 0, 0, 0)

            self.parameter = parameter
            self.filter = filter
            self.values = deepcopy(filter.model[parameter])
            self.n_values = len(self.values)
            self.compose = False
            self.selection_idx0 = 0
            self.selection_idx1 = 0
            self.mouse_state = -1

            self.label = createLabel(self, parameter)
            lb = self.label.boundingRect()
            self.label.setPos(-lb.width() / 2, 0)

            palette = QtCore.QCoreApplication.instance().palette()
            self.pen_grid = QtGui.QPen(palette.light().color())

            self.line = QtWidgets.QGraphicsLineItem(0, -100, 0, 100, self)
            self.line.setPen(self.pen_grid)

            self.ticks = []
            n = len(self.values)
            if n == 1:
                self.addTick(0.5, self.values[0])
            else:
                d = 1 / (n - 1)
                skip_d = 1 if n < 20 else round(n / 20)
                self.addTick(0, self.values[0])
                self.addTick(1, self.values[-1])

                i = d
                for t in range(1, n):
                    if t % skip_d == 0:
                        self.addTick(i, self.values[t])
                    i += d

            self.bar = QtWidgets.QGraphicsRectItem(0, 0, 0, 0, self)

            dark_theme = (
                QtCore.QCoreApplication.instance().palette().base().color().red() < 100
            )
            bar_c = QtGui.QColor("#fff" if dark_theme else "#333")

            self.bar.setBrush(bar_c)
            bar_pen = QtGui.QPen(bar_c)
            bar_pen.setWidth(3)
            self.bar.setPen(bar_pen)
            self.bar.setCursor(QtCore.Qt.PointingHandCursor)
            self.bar.hide()

            self.y0 = 0
            self.y1 = 0

        def snapToValueIdx(self, y):
            if self.y1 == self.y0 or self.n_values <= 1:
                return 0
            l = (y - self.y0) / (self.y1 - self.y0)
            l = max(min(l, 1), 0)
            return round(l * (self.n_values - 1))

        def mousePressEvent(self, event):
            y = event.pos().y()
            if y < self.y0:
                self.mouse_state = 0
            else:
                self.mouse_state = 1
                idx = self.snapToValueIdx(y)
                self.selection_idx0 = idx
                self.selection_idx1 = idx
                self.bar.show()
                self.updateBar()

        def mouseMoveEvent(self, event):
            if self.mouse_state != 1:
                return
            idx = self.snapToValueIdx(event.pos().y())
            if idx != self.selection_idx1:
                self.selection_idx1 = idx
                self.updateBar()

        def mouseReleaseEvent(self, event):
            if self.mouse_state == 0:
                self.compose = not self.compose
                if self.compose:
                    self.filter.inputs.compose.set(self.parameter)
                else:
                    self.filter.inputs.compose.set(None)
            else:
                self.bar.hide()
                mods = QtWidgets.QApplication.keyboardModifiers()
                grow = bool(mods & (QtCore.Qt.ShiftModifier | QtCore.Qt.ControlModifier))
                self.updateSelection(grow)
            self.mouse_state = -1

        def updateSelection(self, grow=False):
            indices = sorted([self.selection_idx0, self.selection_idx1])
            new_values = {self.values[s] for s in range(indices[0], indices[1] + 1)}

            if not grow:
                parameters = {self.parameter: set(new_values)}
            else:
                parameters = self.filter.computeParameterValues()

                if self.parameter in parameters:
                    parameters[self.parameter] |= new_values
                else:
                    parameters[self.parameter] = set(new_values)

            self.filter.axis_selections = {
                p: set(vs) for p, vs in parameters.items() if len(vs) > 0
            }

            sql = "SELECT `id` " + self.filter.computeSQL(self.filter.axis_selections)
            table = queryData(self.filter.db, sql)
            self.filter.inputs.selection.set(
                [table[i][0] for i in range(1, len(table))],
                True,
                True,
            )

        def addTick(self, l, text):
            tick_line = QtWidgets.QGraphicsLineItem(0, 0, 0, 0, self)
            tick_line.l = l
            tick_line.setPen(self.pen_grid)
            tick_label = createLabel(self, text)
            self.ticks.append((tick_line, tick_label))

        def updateBar(self):
            if self.selection_idx0 < self.selection_idx1:
                idx0, idx1 = self.selection_idx0, self.selection_idx1
            else:
                idx1, idx0 = self.selection_idx0, self.selection_idx1

            barMargin = 0.25 / self.n_values if self.n_values > 0 else 0
            if self.n_values > 1:
                l0 = max(0, idx0 / (self.n_values - 1) - barMargin)
                l1 = min(1, idx1 / (self.n_values - 1) + barMargin)
            else:
                l0 = 0.45
                l1 = 0.55

            hy0 = (1 - l0) * self.y0 + l0 * self.y1
            hy1 = (1 - l1) * self.y0 + l1 * self.y1
            self.bar.setRect(-1, hy0, 2, hy1 - hy0)

        def titleRect(self):
            return self.label.boundingRect()

        def maxTickLabelWidth(self):
            w = 0
            for _, tick_label in self.ticks:
                w = max(w, tick_label.boundingRect().width())
            return w

        def maxTickLabelHeight(self):
            h = 0
            for _, tick_label in self.ticks:
                h = max(h, tick_label.boundingRect().height())
            return h

        def _resize(self, x, y, height, axis_width):
            self.prepareGeometryChange()

            self.br = QtCore.QRectF(-axis_width / 2, y, axis_width, height)
            self.setPos(x, 0)

            title_rect = self.label.boundingRect()
            self.label.setPos(-title_rect.width() / 2, y + 5)

            self.y0 = y + title_rect.height() + 15
            self.y1 = y + height - 10

            if self.y1 < self.y0:
                self.y1 = self.y0

            self.line.setLine(0, self.y0, 0, self.y1)

            for tick_line, tick_label in self.ticks:
                ty = (1 - tick_line.l) * self.y0 + tick_line.l * self.y1
                tick_line.setLine(-5, ty, 5, ty)
                tb = tick_label.boundingRect()
                tick_label.setPos(-10 - tb.width(), ty - tb.height() / 2)

            self.updateBar()

        def boundingRect(self):
            return self.br

        def paint(self, painter, option, widget):
            return


    class _ParallelCoordinates(QtWidgets.QGraphicsView):
        def __init__(self, filter):
            super().__init__()
            self.filter = filter

            self.setRenderHints(QtGui.QPainter.Antialiasing)
            self.setDragMode(QtWidgets.QGraphicsView.DragMode.NoDrag)
            self.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
            self.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)

            self.axes = {}
            self.lines = Lines()

            scene = QtWidgets.QGraphicsScene(self)
            scene.addItem(self.lines)
            self.setScene(scene)

        def removeAxes(self):
            for a in self.axes:
                axis = self.axes[a]
                self.scene().removeItem(axis)
            self.axes = {}

        def addAxes(self):
            model = self.filter.model
            for p in model:
                axis = Axis(p, self.filter)
                self.axes[p] = axis
                self.scene().addItem(axis)

        def updatePlot(self):
            self.removeAxes()
            self.removeLines()

            self.addAxes()
            self.addBackgroundLines()
            self._resize()

        def addHighlightedLines(self):
            table = self.filter.inputs.table.get()
            model = self.filter.model
            parameters = [p for p in model]
            n = len(parameters) - 1
            if n < 1:
                return

            dx = 1 / n

            lines = []
            edges = set()

            id_column_idx = table[0].index("id")
            selection = self.filter.inputs.selection.get()
            selected_rows = [
                i for i in range(1, len(table)) if table[i][id_column_idx] in selection
            ]

            for i in range(0, len(parameters) - 1):
                p0 = parameters[i]
                p1 = parameters[i + 1]
                c0 = table[0].index(p0)
                c1 = table[0].index(p1)
                s0 = self.axes[p0].values
                s1 = self.axes[p1].values
                n0 = len(s0) - 1
                n1 = len(s1) - 1

                for r in selected_rows:
                    edge = (str(table[r][c0]), str(table[r][c1]))
                    if edge not in edges:
                        lines.append(
                            [
                                i * dx,
                                s0.index(edge[0]) / n0 if n0 > 0 else 0.5,
                                (i + 1) * dx,
                                s1.index(edge[1]) / n1 if n1 > 0 else 0.5,
                            ]
                        )
                        edges.add(edge)

            self.lines.lines_highlight = lines
            self._resize()

        def removeLines(self):
            self.lines.lines_highlight = []
            self.lines.path_highlight = QtGui.QPainterPath()
            self.lines.lines_normal = []
            self.lines.path_normal = QtGui.QPainterPath()

        def addBackgroundLines(self):
            lines = self.lines.lines_normal
            model = self.filter.model
            table = self.filter.inputs.table.get()

            parameters = [p for p in model]
            n = len(parameters) - 1
            if n < 1:
                return

            dx = 1 / n
            n_rows = len(table)

            for i in range(0, len(parameters) - 1):
                p0 = parameters[i]
                p1 = parameters[i + 1]
                c0 = table[0].index(p0)
                c1 = table[0].index(p1)
                s0 = self.axes[p0].values
                s1 = self.axes[p1].values
                n0 = len(s0) - 1
                n1 = len(s1) - 1

                edges = set()
                for r in range(1, n_rows):
                    edge = (str(table[r][c0]), str(table[r][c1]))
                    if edge not in edges:
                        lines.append(
                            [
                                i * dx,
                                s0.index(edge[0]) / n0 if n0 > 0 else 0.5,
                                (i + 1) * dx,
                                s1.index(edge[1]) / n1 if n1 > 0 else 0.5,
                            ]
                        )
                        edges.add(edge)

        def _computeMargins(self):
            left = 20
            right = 20
            top = 20
            bottom = 20

            for axis in self.axes.values():
                title_rect = axis.titleRect()
                top = max(top, title_rect.height() + 15)

                tick_w = axis.maxTickLabelWidth()
                tick_h = axis.maxTickLabelHeight()

                left = max(left, tick_w + 20)
                top = max(top, title_rect.height() + 10)
                bottom = max(bottom, tick_h / 2 + 10)

            return left, top, right, bottom

        def scrollContentsBy(self, a, b):
            return

        def wheelEvent(self, event):
            return

        def fitInView(self):
            return

        def keyPressEvent(self, event):
            return

        def _resize(self):
            model = self.filter.model
            parameters = [p for p in model]
            n = len(parameters)
            if n < 1:
                return

            vr = self.viewport().rect()
            self.scene().setSceneRect(0, 0, vr.width(), vr.height())
            view_rect = self.mapToScene(vr).boundingRect()

            left_margin, top_margin, right_margin, bottom_margin = self._computeMargins()

            w = max(1.0, view_rect.width() - left_margin - right_margin)
            h = max(1.0, view_rect.height() - top_margin - bottom_margin)

            if n > 1:
                x = view_rect.x() + left_margin
                aw = w / (n - 1)
            else:
                x = view_rect.x() + left_margin + w / 2.0
                aw = w

            y = view_rect.y() + top_margin

            for p in parameters:
                axis = self.axes[p]
                axis._resize(x, y, h, aw)
                x += aw

            a0 = self.axes[parameters[0]]
            a1 = self.axes[parameters[-1]]
            x0 = a0.pos().x()
            x1 = a1.pos().x()
            y0 = a0.y0
            y1 = a0.y1
            self.lines.setBoundingRect(QtCore.QRectF(x0, y0, x1 - x0, y1 - y0))

        def resizeEvent(self, event):
            super().resizeEvent(event)
            self._resize()


except NameError:
    pass


class ParallelCoordinates(Filter):
    def __init__(self):
        self.model = {}
        self.widgets = []

        self.db = None
        self.axis_selections = {}

        self.inputTimes = [-1, -1]
        Filter.__init__(
            self,
            inputs={
                "table": [[]],
                "ignore": ["^file", "^id"],
                "selection": [],
                "compose": "",
            },
            outputs={
                "table": [[]],
                "sql": "",
                "compose": (None, {}),
            },
        )

    def computeParameterValues(self):
        return {
            p: set(vs) for p, vs in self.axis_selections.items() if len(vs) > 0
        }

    def computeSQL(self, parameters):
        if not parameters:
            return "FROM `input`"

        clauses = []
        for p, vals in parameters.items():
            clauses.append(
                "`"
                + p
                + '` IN ("'
                + '","'.join([str(v) for v in vals])
                + '")'
            )
        return "FROM `input` WHERE " + " AND ".join(clauses)

    def generateWidgets(self):
        widget = _ParallelCoordinates(self)
        widget.updatePlot()
        self.widgets.append(widget)
        return widget

    def _update(self):
        table = self.inputs.table.get()
        tableExtent = getTableExtent(table)
        if tableExtent[0] < 1 or tableExtent[1] < 1:
            self.outputs.table.set([[]])
            self.outputs.sql.set("")
            return 0

        inputTimes = [self.inputs.table.getTime(), self.inputs.ignore.get()]
        if self.inputTimes != inputTimes:
            self.inputTimes = inputTimes
            ignore = self.inputs.ignore.get()
            parameterIndices = [
                idx
                for idx in range(0, tableExtent[1])
                if not any(
                    [re.search(i, table[0][idx], re.IGNORECASE) for i in ignore]
                )
            ]

            new_model = {}
            for i in parameterIndices:
                parameter = table[0][i]
                new_model[parameter] = computeValues(table, i)

            self.model = new_model
            self.axis_selections = {}
            for w in self.widgets:
                w.updatePlot()

            self.db = sqlite3.connect(":memory:")
            createTable(self.db, table)
            insertData(self.db, table)

        for w in self.widgets:
            w.addHighlightedLines()

        parameters = self.computeParameterValues()
        if len(parameters) < 1:
            sql = "SELECT * FROM `input` LIMIT 0"
        else:
            sql = "SELECT * " + self.computeSQL(parameters)
        self.outputs.sql.set(sql)

        output_table = queryData(self.db, sql)
        output_table = [list(row) for row in output_table]
        self.outputs.table.set(output_table)

        compose = self.inputs.compose.get()
        for w in self.widgets:
            for a in w.axes:
                axis = w.axes[a]
                axis.compose = a == compose

                font = axis.label.font()
                font.setBold(axis.compose)
                axis.label.setFont(font)

                lb = axis.label.boundingRect()
                axis.label.setPos(-lb.width() / 2, axis.label.pos().y())

        if compose != "":
            idx = getColumnIndexFromTable(output_table, compose)
            values = set()
            for i in range(1, len(output_table)):
                values.add(output_table[i][idx])
            compose = (compose, {v: i for i, v in enumerate(values)})
        else:
            compose = (None, {})
        self.outputs.compose.set(compose)

        return 1
