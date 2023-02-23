from PyQt5.QtGui import *
from PyQt5.QtCore import *
from PyQt5.QtWidgets import *

import json
from pipelineeditor.graphics.node_graphics_edge import QDMGraphicsEdge
from pipelineeditor.graphics.node_graphics_socket import QDMGraphicsSocket
from pipelineeditor.node_edge_dragging import EdgeDragging
from pipelineeditor.graphics.node_graphics_cutline import QDMGraphicsCutline
from pipelineeditor.utils import dump_exception

MODE_NOOP = 1
MODE_EDGE_DRAG = 2
MODE_EDGE_CUT = 3
EDGE_DRAG_THRESHOLD = 50


class QDMGraphicsView(QGraphicsView):

    scenePosChanged = pyqtSignal(int, int)

    def __init__(self, gr_scene, parent=None):
        super().__init__(parent)
        self.gr_scene = gr_scene
        self.initUI()
        self.setScene(self.gr_scene)
        self.mode = MODE_NOOP
        self.editingFlag = False
        self.rubberBandDragRect = False
        self.zoom_in_factor = 1.25
        self.zoom = 10
        self.zoom_step = 1
        self.zoom_range = [2, 15]
        self.zoom_clamp = True
        self.last_scene_mouse_pos = QPoint(0, 0)
        self.last_mb_pos = None
        self.release_mb_pos = None

        self.dragging = EdgeDragging(self)

        self.cutline = QDMGraphicsCutline()
        self.gr_scene.addItem(self.cutline)

    def initUI(self):
        self.setRenderHints(QPainter.Antialiasing | QPainter.HighQualityAntialiasing | QPainter.TextAntialiasing | QPainter.SmoothPixmapTransform)

        self.setViewportUpdateMode(QGraphicsView.FullViewportUpdate)

        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        self.setTransformationAnchor(QGraphicsView.AnchorUnderMouse)
        self.setDragMode(QGraphicsView.RubberBandDrag)

        # enable drop event
        self.setAcceptDrops(True)

        # init listeneres
        self._drag_enter_listeneres = []
        self._drop_listeneres = []
        self._doubleclick_listeneres = []

    def reset_mode(self):
        self.mode = MODE_NOOP

    def dragEnterEvent(self, event) -> None:
        for callback in self._drag_enter_listeneres:
            callback(event)

    def dropEvent(self, event) -> None:
        for callback in self._drop_listeneres:
            callback(event)

    def mouseDoubleClickEvent(self, event) -> None:
        for callback in self._doubleclick_listeneres:
            callback(event)

    def addDragEnterListener(self, callback):
        self._drag_enter_listeneres.append(callback)

    def addDropListener(self, callback):
        self._drop_listeneres.append(callback)

    def addDoubleClickListener(self, callback):
        self._doubleclick_listeneres.append(callback)

    def keyPressEvent(self, event: QKeyEvent) -> None:
        super().keyPressEvent(event)

        if event.key() == 80:
            self.take_screenshot()

        if event.key() == 65 and event.modifiers() & Qt.ControlModifier:
            self.selectAll()

    def selectAll(self):
        for item in self.gr_scene.items():
            item.setSelected(True)
        current_selection = self.gr_scene.scene.getSelectedItems()

        if current_selection != self.gr_scene.scene._last_selected_items:
            if current_selection == []:
                self.gr_scene.itemsDeselected.emit()
            else:
                self.gr_scene.itemSelected.emit()

            self.gr_scene.scene._last_selected_items = current_selection

    def deleteSelected(self):
        for item in self.gr_scene.selectedItems():
            if isinstance(item, QDMGraphicsEdge):
                item.edge.remove()
            if hasattr(item, 'node'):
                item.node.remove()
        self.gr_scene.scene.history.store_history("Delete Selected", True)

    def mousePressEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.MiddleButton:
            self.middleButtonEventPress(event)
        elif event.button() == Qt.LeftButton:
            self.leftMouseButtonPress(event)
        elif event.button() == Qt.RightButton:
            self.rightMouseButtonPress(event)
        else:
            super().mousePressEvent(event)

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.MiddleButton:
            self.middleButtonEventRelease(event)
        elif event.button() == Qt.LeftButton:
            self.leftMouseButtonRelease(event)
        elif event.button() == Qt.RightButton:
            self.rightMouseButtonRelease(event)
        else:
            super().mouseReleaseEvent(event)

    def middleButtonEventPress(self, event):
        # Faking event for enable MMB dragging the scene (pan)
        release_event = QMouseEvent(QEvent.MouseButtonRelease, event.localPos(), event.screenPos(), Qt.LeftButton, Qt.NoButton, event.modifiers())
        super().mouseReleaseEvent(release_event)

        self.setDragMode(QGraphicsView.ScrollHandDrag)

        fake_event = QMouseEvent(event.type(), event.localPos(), event.screenPos(), Qt.LeftButton, event.buttons() | Qt.LeftButton, event.modifiers())
        super().mousePressEvent(fake_event)

    def middleButtonEventRelease(self, event):
        # Faking event for enable MMB dragging the scene (pan)
        fake_event = QMouseEvent(event.type(), event.localPos(), event.screenPos(), Qt.LeftButton, event.buttons() | Qt.LeftButton, event.modifiers())
        super().mouseReleaseEvent(fake_event)
        self.setDragMode(QGraphicsView.RubberBandDrag)

    def leftMouseButtonPress(self, event):
        item = self.getItemAtClick(event)
        self.last_mb_pos = self.mapToScene(event.pos())

        # Shift clicking items
        if hasattr(item, "node") or isinstance(item, QDMGraphicsEdge) or not item:
            # TODO: Fix first node moving...
            if item and hasattr(item, "node"):
                if event.modifiers() & Qt.ShiftModifier and event.modifiers() & Qt.ControlModifier:
                    print("Shift Control pressed")
                    data = self.gr_scene.scene.clipboard.serializedSelected(delete=False)
                    self.gr_scene.scene.clipboard.deserializeFromClipboard(data, adjust_pos=False)

            if event.modifiers() & Qt.ShiftModifier:
                event.ignore()
                fakeEvent = QMouseEvent(QEvent.MouseButtonPress, event.localPos(), event.screenPos(), Qt.LeftButton, event.buttons() | Qt.LeftButton, event.modifiers() | Qt.ControlModifier)
                super().mousePressEvent(fakeEvent)
                return

        if isinstance(item, QDMGraphicsSocket) and self.mode == MODE_NOOP:
            self.mode = MODE_EDGE_DRAG
            self.dragging.edgeDragStart(item)
            return

        if self.mode == MODE_EDGE_DRAG and self.dragging.edgeDragEnd(item):
            return

        # Cutline event
        if not item:
            if event.modifiers() & Qt.ControlModifier:
                self.mode = MODE_EDGE_CUT
                fakeEvent = QMouseEvent(QEvent.MouseButtonRelease, event.localPos(), event.screenPos(), Qt.LeftButton, Qt.NoButton, event.modifiers())
                super().mouseReleaseEvent(fakeEvent)
                QApplication.setOverrideCursor(Qt.CrossCursor)
                return
            else:
                self.rubberBandDragRect = True

        super().mousePressEvent(event)

    def leftMouseButtonRelease(self, event):
        item = self.getItemAtClick(event)

        try:
            if hasattr(item, "node") or isinstance(item, QDMGraphicsEdge) or not item:
                if event.modifiers() & Qt.ShiftModifier:
                    event.ignore()
                    fakeEvent = QMouseEvent(event.type(), event.localPos(), event.screenPos(), Qt.LeftButton, Qt.NoButton, event.modifiers() | Qt.ControlModifier)
                    super().mouseReleaseEvent(fakeEvent)
                    return

            if self.mode == MODE_EDGE_DRAG:
                if self.distanceBetweenClickAndReleaseIsOff(event):
                    if self.dragging.edgeDragEnd(item):
                        return

            if self.mode == MODE_EDGE_CUT:
                self.cut_intersecting_edges()
                self.cutline._line_points = []
                self.cutline.update()
                QApplication.setOverrideCursor(Qt.ArrowCursor)
                self.mode = MODE_NOOP
                return

            # Store selection in history_stamps
            if self.rubberBandDragRect:
                self.rubberBandDragRect = False
                current_selection = self.gr_scene.selectedItems()

                if current_selection != self.gr_scene.scene._last_selected_items:
                    if current_selection == []:
                        self.gr_scene.itemsDeselected.emit()
                    else:
                        self.gr_scene.itemSelected.emit()

                    self.gr_scene.scene._last_selected_items = current_selection
                return

            if not item:
                self.gr_scene.itemsDeselected.emit()
        except Exception as e:
            dump_exception(e)

        super().mouseReleaseEvent(event)

    def mouseMoveEvent(self, event):
        scenepos = self.mapToScene(event.pos())

        if self.mode == MODE_EDGE_DRAG:
            self.dragging.update_destination(scenepos.x(), scenepos.y())

        if self.mode == MODE_EDGE_CUT and self.cutline:
            self.cutline._line_points.append(scenepos)
            self.cutline.update()

        self.last_scene_mouse_position = scenepos

        self.scenePosChanged.emit(int(scenepos.x()), int(scenepos.y()))

        super().mouseMoveEvent(event)

    def distanceBetweenClickAndReleaseIsOff(self, event):
        new_lmb_release_scene_pos = self.mapToScene(event.pos())
        dist_scene = new_lmb_release_scene_pos - self.last_mb_pos
        edge_drag_threshold_sq = EDGE_DRAG_THRESHOLD * EDGE_DRAG_THRESHOLD
        return (dist_scene.x() * dist_scene.x() + dist_scene.y() * dist_scene.y()) > edge_drag_threshold_sq

    def rightMouseButtonPress(self, event):
        super().mousePressEvent(event)

    def rightMouseButtonRelease(self, event):
        super().mouseReleaseEvent(event)

    def wheelEvent(self, event):
        zoom_out_factor = 1 / self.zoom_in_factor

        if event.angleDelta().y() > 0:
            zoom_factor = self.zoom_in_factor
            self.zoom += self.zoom_step
        else:
            zoom_factor = zoom_out_factor
            self.zoom -= self.zoom_step

        clamped = False

        if self.zoom < self.zoom_range[0]:
            self.zoom = self.zoom_range[0]
            clamped = True
        if self.zoom > self.zoom_range[1]:
            self.zoom = self.zoom_range[1]
            clamped = True

        if not clamped or not self.zoom_clamp:
            self.scale(zoom_factor, zoom_factor)

    def getItemAtClick(self, event):
        return self.itemAt(event.pos())

    def cut_intersecting_edges(self):
        for ix in range(len(self.cutline._line_points) - 1):
            p1 = self.cutline._line_points[ix]
            p2 = self.cutline._line_points[ix + 1]

            for edge in self.gr_scene.scene.edges.copy():
                if edge.gr_edge.intersects_with(p1, p2):
                    edge.remove()
        self.gr_scene.scene.history.store_history("Cutting Edge", True)

    def take_screenshot(self):
        image = QImage(self.viewport().size(), QImage.Format_ARGB32)
        painter = QPainter(image)
        self.render(painter)
        painter.end()

        # Save the screenshot to a file
        image.save("test.png")
