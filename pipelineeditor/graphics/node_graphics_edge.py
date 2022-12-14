import math
from PyQt5.QtWidgets import *
from PyQt5.QtGui import *
from PyQt5.QtCore import *

from pipelineeditor.node_socket import *

EDGE_CP_ROUNDNESS = 100


class QDMGraphicsEdge(QGraphicsPathItem):
    def __init__(self, edge, parent=None):
        super().__init__(parent)
        self.edge = edge
        self._color = QColor("#001000")
        self._color_selected = QColor("#00ff00")
        self._width = 2

        self._pen = QPen(self._color)
        self._pen.setWidth(self._width)

        self._pen_dragging = QPen(self._color)
        self._pen_selected = QPen(self._color_selected)
        self._pen_selected.setWidth(self._width)
        self._pen_dragging.setWidth(self._width)
        self._pen_dragging.setStyle(Qt.DashLine)

        self.setFlag(QGraphicsItem.ItemIsSelectable)
        self.setZValue(-1)

        self.posSource = [0, 0]
        self.posDestination = [200, 100]

    def setSource(self, x, y):
        self.posSource = x, y

    def boundingRect(self) -> QRectF:
        return self.shape().boundingRect()

    def shape(self) -> QPainterPath:
        return self.calcPath()

    def setDestination(self, x, y):
        self.posDestination = x, y

    def paint(self, painter, QStyleOptionGraphicsItem, widget=None) -> None:
        self.setPath(self.calcPath())
        if not self.edge.end_socket:
            painter.setPen(self._pen_dragging)
        else:
            painter.setPen(self._pen if not self.isSelected() else self._pen_selected)
        painter.setBrush(Qt.NoBrush)
        painter.drawPath(self.path())

    def calcPath(self):
        raise NotImplementedError("This method must be overriden by the child class")

    def intersects_with(self, p1, p2):
        cut_path = QPainterPath(p1)
        cut_path.lineTo(p2)
        return cut_path.intersects(self.calcPath())


class QDMGraphicsEdgeDirect(QDMGraphicsEdge):
    def calcPath(self):
        path = QPainterPath(QPointF(self.posSource[0], self.posSource[1]))
        path.lineTo(QPointF(self.posDestination[0], self.posDestination[1]))
        return path


class QDMGraphicsEdgeBezier(QDMGraphicsEdge):
    def calcPath(self):
        s = self.posSource
        d = self.posDestination

        dist = (d[0] - s[0]) * 0.5

        cpx_s = +dist
        cpx_d = -dist
        cpy_s = 0
        cpy_d = 0

        if self.edge.start_socket:
            sspos = self.edge.start_socket._position

            if (s[0] > d[0] and sspos in (RIGHT_TOP, RIGHT_BOTTOM)) or (s[0] < d[0] and sspos in (LEFT_TOP, LEFT_BOTTOM)):
                cpx_s = -cpx_s
                cpx_d = -cpx_d
                cpy_d = ((s[1] - d[1]) / math.fabs((s[1] - d[1]) if s[1] - d[1] != 0 else 0.001)) * EDGE_CP_ROUNDNESS
                cpy_s = ((d[1] - s[1]) / math.fabs((d[1] - s[1]) if d[1] - s[1] != 0 else 0.001)) * EDGE_CP_ROUNDNESS

        path = QPainterPath(QPointF(s[0], s[1]))
        path.cubicTo(
            s[0] + cpx_s,
            s[1] + cpy_s,
            d[0] + cpx_d,
            d[1] + cpy_d,
            d[0],
            d[1]
        )

        return path