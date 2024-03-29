from PyQt5.QtWidgets import *
from PyQt5.QtGui import *
from PyQt5.QtCore import *


class QDMGraphicsNode(QGraphicsItem):
    def __init__(self, node, parent=None) -> None:
        super().__init__(parent)
        self.node = node

        # init flags
        self._was_moved = False
        self._last_selected_state = False
        self.hovered = False
        self.initSizes()
        self.initAssets()

        self.initUI()

    def initUI(self):
        self.setFlags(QGraphicsItem.ItemIsSelectable | QGraphicsItem.ItemIsMovable)

        self.initTitle()
        self.title = self.node.title
        self.initContent()
        self.setAcceptHoverEvents(True)

    def initSizes(self):
        self.width = 180
        self.height = 240
        self.edge_roundness = 10
        self.edge_padding = 10
        self.title_height = 24
        self._title_horizontal_padding = 4
        self._title_vertical_padding = 4

    def initAssets(self):
        self._color = QColor("#7F000000")
        self._color_selected = QColor("#FFFFA637")
        self._color_hovered  = QColor("#FF37A6FF")

        self._title_color = Qt.white
        self._pen_default = QPen(self._color)
        self._pen_selected = QPen(self._color_selected)
        self._pen_hovered = QPen(self._color_hovered)
        self._brush_title = QBrush(QColor("#FF313131"))
        self._brush_background = QBrush(QColor("#E3212121"))
        self._pen_default.setWidthF(1)
        self._pen_selected.setWidthF(1)
        self._pen_hovered.setWidthF(2)

    @property
    def content(self):
        return self.node.content if self.node else None

    @property
    def title(self):
        return self._title

    @title.setter
    def title(self, value):
        self._title = value
        self.title_item.setPlainText(self._title)

    def onSelected(self):
        self.node.scene.gr_scene.itemSelected.emit()

    def doSelect(self, new_state):
        self.setSelected(new_state)
        self._last_selected_state = new_state
        if new_state:
            self.onSelected()

    def hoverEnterEvent(self, event) -> None:
        self.hovered = True
        self.update()

    def hoverLeaveEvent(self, event) -> None:
        self.hovered = False
        self.update()

    def mouseMoveEvent(self, event: 'QGraphicsSceneMouseEvent') -> None:
        super().mouseMoveEvent(event)

        # optmize this, just update selected nodes
        for node in self.scene().scene.nodes:
            if self.node.gr_node.isSelected():
                node.updateConnectedEdges()
        self._was_moved = True

    def mouseReleaseEvent(self, event: 'QGraphicsSceneMouseEvent') -> None:
        super().mouseReleaseEvent(event)
        # handle when gr_node was moved
        if self._was_moved:
            self._was_moved = False
            self.node.scene.history.store_history("Node Moved", True)

            self.node.scene.resetLastSelectedStates()
            self._last_selected_state = True
            # we need to store the last selected state, because moving is also means selecting the object
            self.node.scene._last_selected_items = self.node.scene.getSelectedItems()

            # we want to skip storing selection in history
            return

        # handle when gr_node was clicked on
        if self._last_selected_state != self.isSelected() or self.node.scene._last_selected_items != self.node.scene.getSelectedItems():
            self.node.scene.resetLastSelectedStates()
            self._last_selected_state = self.isSelected()
            self.onSelected()

    def mouseDoubleClickEvent(self, event):
        """Overriden event for doubleclick. Resend to `Node::onDoubleClicked`"""
        self.node.onDoubleClicked(event)

    def boundingRect(self) -> QRectF:
        return QRectF(
            0,
            0,
            self.width,
            self.height
        ).normalized()

    def initTitle(self):
        self.title_item = QGraphicsTextItem(self)
        self.title_item.node = self.node
        self.title_item.setDefaultTextColor(self._title_color)
        # self.title_item.setFont(self._title_font)
        self.title_item.setPos(self._title_horizontal_padding, 0)
        self.title_item.setTextWidth(self.width - 2 * self._title_horizontal_padding)

    def initContent(self):
        if self.content is not None:
            self.content.setGeometry(
                self.edge_padding,
                self.title_height + self.edge_padding,
                self.width - 2 * self.edge_padding,
                self.height - 2 * self.edge_padding - self.title_height
            )

        # get the QGraphicsProxyWidget when inserted into the grScene
        self.gr_content = self.node.scene.gr_scene.addWidget(self.content)
        self.gr_content.setParentItem(self)

    def paint(self, painter, QStyleOptionGraphicsItem, widget=None):
        # title
        path_title = QPainterPath()
        path_title.setFillRule(Qt.WindingFill)
        path_title.addRoundedRect(0, 0, self.width, self.title_height, self.edge_roundness, self.edge_roundness)
        path_title.addRect(0, self.title_height - self.edge_roundness, self.edge_roundness, self.edge_roundness)
        path_title.addRect(self.width - self.edge_roundness, self.title_height - self.edge_roundness, self.edge_roundness, self.edge_roundness)
        painter.setPen(Qt.NoPen)
        painter.setBrush(self._brush_title)
        painter.drawPath(path_title.simplified())

        # contnet
        path_content = QPainterPath()
        path_content.setFillRule(Qt.WindingFill)
        path_content.addRoundedRect(0, self.title_height, self.width, self.height - self.title_height, self.edge_roundness, self.edge_roundness)
        path_content.addRect(0, self.title_height, self.edge_roundness, self.edge_roundness)
        path_content.addRect(self.width - self.edge_roundness, self.title_height, self.edge_roundness, self.edge_roundness)
        painter.setPen(Qt.NoPen)
        painter.setBrush(self._brush_background)
        painter.drawPath(path_content.simplified())

        # outline
        path_outline = QPainterPath()
        path_outline.addRoundedRect(-1, -1, self.width, self.height, self.edge_roundness, self.edge_roundness)
        painter.setBrush(Qt.NoBrush)
        if self.hovered:
            painter.setPen(self._pen_hovered)
            painter.drawPath(path_outline.simplified())
            painter.setPen(self._pen_default)
            painter.drawPath(path_outline.simplified())
        else:
            painter.setPen(self._pen_default if not self.isSelected() else self._pen_selected)
            painter.drawPath(path_outline.simplified())