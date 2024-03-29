from PyQt5.QtWidgets import *
from PyQt5.QtGui import *
from PyQt5.QtCore import *

SOCKET_COLORS = [
    QColor("#FF7700"),
    QColor("#52e220"),
    QColor("#0056a6"),
    QColor("#a86db1"),
    QColor("#b54747"),
    QColor("#dbe220"),
    QColor("#888888"),
    QColor("#B4E220"),
    QColor("#B9B9B9")
]


class QDMGraphicsSocket(QGraphicsItem):

    def __init__(self, socket):
        super().__init__(socket.node.gr_node)

        self.socket = socket
        self.is_highlight = False
        self.radius = 6.0
        self.outline_width = 1.0
        self.highlight_width = 2.0
        self.initAssets()

    @property
    def socket_type(self):
        return self.socket._socket_type

    def getSocketColor(self, key):
        if type(key) == int:
            return SOCKET_COLORS[key]
        elif type(key) == str:
            return QColor(key)
        return Qt.transparent

    def changeSocketType(self):
        """Change the Socket Type"""
        self._color_background = self.getSocketColor(self.socket_type)
        self._brush = QBrush(self._color_background)
        # print("Socket changed to:", self._color_background.getRgbF())
        self.update()

    def initAssets(self):

        # determine socket color
        self._color_background = self.getSocketColor(self.socket_type)
        self._color_outline = QColor("#FF000000")
        self._color_highlight = QColor("#FF37A6FF")

        self._pen = QPen(self._color_outline)
        self._pen.setWidthF(self.outline_width)

        self._pen_highlight = QPen(self._color_highlight)
        self._pen_highlight.setWidthF(self.highlight_width)

        self._brush = QBrush(self._color_background)

    def paint(self, painter, QStyleOptionGraphicsItem, widget=None):
        """Painting a circle"""
        painter.setBrush(self._brush)
        painter.setPen(self._pen if not self.is_highlight else self._pen_highlight)
        painter.drawEllipse(int(-self.radius), int(-self.radius), int(2 * self.radius), int(2 * self.radius))

    def boundingRect(self) -> QRectF:
        """Defining Qt' bounding rectangle"""
        return QRectF(
            - self.radius - self.outline_width,
            - self.radius - self.outline_width,
            2 * (self.radius + self.outline_width),
            2 * (self.radius + self.outline_width),
        )