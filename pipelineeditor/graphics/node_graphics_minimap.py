from PyQt5.QtWidgets import QWidget, QVBoxLayout
from PyQt5.QtCore import Qt, QRectF, QPointF, QTimer, pyqtSignal
from PyQt5.QtGui import QPainter, QColor, QPen, QBrush, QPainterPath, QFont


class QDMGraphicsMinimap(QWidget):
    """Lightweight minimap that draws simplified node representations."""

    def __init__(self, scene, main_view, parent=None):
        super().__init__(parent)
        self.scene = scene  # The data scene (not gr_scene)
        self.main_view = main_view
        self._dragging = False

        # Track node count to know when to recalculate bounds
        self._last_node_count = 0
        self._last_edge_count = 0

        # Colors
        self.bg_color = QColor(35, 35, 35, 230)
        self.border_color = QColor(80, 80, 80)
        self.node_body_color = QColor(63, 63, 63)
        self.node_title_color = QColor(90, 90, 90)
        self.node_border_color = QColor(50, 50, 50)
        self.node_selected_border = QColor(255, 165, 0)
        self.edge_color = QColor(130, 130, 130, 180)
        self.viewport_fill = QColor(255, 255, 255, 20)
        self.viewport_border = QColor(255, 100, 100)

        # Cached bounds - stable, only updates on node add/remove
        self._scene_bounds = QRectF()
        self._transform_scale = 1.0
        self._transform_offset = QPointF()

        self.initUI()
        self.connectSignals()
        QTimer.singleShot(100, self._forceUpdateBounds)

    def initUI(self):
        self.setFixedSize(200, 150)
        self.setMouseTracking(True)

    def connectSignals(self):
        """Connect signals to keep minimap in sync."""
        gr_scene = self.main_view.gr_scene

        # Update when scene changes (for repainting node positions)
        gr_scene.changed.connect(self._onSceneChanged)

        # Update viewport rect when main view scrolls
        h_scroll = self.main_view.horizontalScrollBar()
        v_scroll = self.main_view.verticalScrollBar()
        if h_scroll:
            h_scroll.valueChanged.connect(self.update)
        if v_scroll:
            v_scroll.valueChanged.connect(self.update)

        # Update when zoom changes
        if hasattr(self.main_view, 'viewportTransformChanged'):
            self.main_view.viewportTransformChanged.connect(self.update)

    def _onSceneChanged(self, regions=None):
        """Handle scene changes - only recalc bounds if node/edge count changed."""
        current_node_count = len(self.scene.nodes)
        current_edge_count = len(self.scene.edges)

        # Only recalculate bounds when nodes/edges are added or removed
        if current_node_count != self._last_node_count or current_edge_count != self._last_edge_count:
            self._last_node_count = current_node_count
            self._last_edge_count = current_edge_count
            self._updateBounds()

        # Always repaint (to show moved nodes)
        self.update()

    def _forceUpdateBounds(self):
        """Force recalculation of bounds."""
        self._last_node_count = len(self.scene.nodes)
        self._last_edge_count = len(self.scene.edges)
        self._updateBounds()
        self.update()

    def _updateBounds(self):
        """Calculate the bounding rect of all nodes."""
        if not self.scene.nodes:
            self._scene_bounds = QRectF(-500, -500, 1000, 1000)
        else:
            min_x = min_y = float('inf')
            max_x = max_y = float('-inf')

            for node in self.scene.nodes:
                gr_node = node.gr_node
                pos = gr_node.pos()
                rect = gr_node.boundingRect()

                node_left = pos.x()
                node_top = pos.y()
                node_right = pos.x() + rect.width()
                node_bottom = pos.y() + rect.height()

                min_x = min(min_x, node_left)
                min_y = min(min_y, node_top)
                max_x = max(max_x, node_right)
                max_y = max(max_y, node_bottom)

            # Add padding
            padding = 200
            self._scene_bounds = QRectF(
                min_x - padding,
                min_y - padding,
                (max_x - min_x) + padding * 2,
                (max_y - min_y) + padding * 2
            )

        self._updateTransform()

    def _updateTransform(self):
        """Calculate transform to map scene coords to widget coords."""
        if self._scene_bounds.isEmpty():
            return

        # Available drawing area (with margin for border)
        margin = 4
        available_w = self.width() - margin * 2
        available_h = self.height() - margin * 2

        # Scale to fit
        scale_x = available_w / self._scene_bounds.width() if self._scene_bounds.width() > 0 else 1
        scale_y = available_h / self._scene_bounds.height() if self._scene_bounds.height() > 0 else 1
        self._transform_scale = min(scale_x, scale_y)

        # Center offset
        scaled_w = self._scene_bounds.width() * self._transform_scale
        scaled_h = self._scene_bounds.height() * self._transform_scale
        self._transform_offset = QPointF(
            margin + (available_w - scaled_w) / 2,
            margin + (available_h - scaled_h) / 2
        )

    def _sceneToWidget(self, scene_point):
        """Convert scene coordinates to widget coordinates."""
        return QPointF(
            (scene_point.x() - self._scene_bounds.x()) * self._transform_scale + self._transform_offset.x(),
            (scene_point.y() - self._scene_bounds.y()) * self._transform_scale + self._transform_offset.y()
        )

    def _widgetToScene(self, widget_point):
        """Convert widget coordinates to scene coordinates."""
        return QPointF(
            (widget_point.x() - self._transform_offset.x()) / self._transform_scale + self._scene_bounds.x(),
            (widget_point.y() - self._transform_offset.y()) / self._transform_scale + self._scene_bounds.y()
        )

    def _sceneRectToWidget(self, scene_rect):
        """Convert a scene rect to widget coordinates."""
        top_left = self._sceneToWidget(scene_rect.topLeft())
        w = scene_rect.width() * self._transform_scale
        h = scene_rect.height() * self._transform_scale
        return QRectF(top_left.x(), top_left.y(), w, h)

    def paintEvent(self, event):
        """Draw the minimap with simplified but styled graphics."""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        # Background with rounded corners
        painter.setBrush(QBrush(self.bg_color))
        painter.setPen(QPen(self.border_color, 1))
        painter.drawRoundedRect(self.rect().adjusted(1, 1, -1, -1), 4, 4)

        if self._transform_scale <= 0:
            return

        # Draw edges (curved lines)
        painter.setPen(QPen(self.edge_color, 1))
        for edge in self.scene.edges:
            if edge.start_socket and edge.end_socket:
                start_node_pos = edge.start_socket.node.gr_node.pos()
                end_node_pos = edge.end_socket.node.gr_node.pos()
                start_socket_pos = edge.start_socket.gr_socket.pos()
                end_socket_pos = edge.end_socket.gr_socket.pos()

                start_pos = start_node_pos + start_socket_pos
                end_pos = end_node_pos + end_socket_pos

                start_widget = self._sceneToWidget(start_pos)
                end_widget = self._sceneToWidget(end_pos)

                # Draw simple bezier curve
                path = QPainterPath()
                path.moveTo(start_widget)
                ctrl_offset = abs(end_widget.x() - start_widget.x()) * 0.5
                path.cubicTo(
                    start_widget.x() + ctrl_offset, start_widget.y(),
                    end_widget.x() - ctrl_offset, end_widget.y(),
                    end_widget.x(), end_widget.y()
                )
                painter.drawPath(path)

        # Draw nodes (mini node style with title bar)
        for node in self.scene.nodes:
            gr_node = node.gr_node
            pos = gr_node.pos()
            rect = gr_node.boundingRect()

            scene_rect = QRectF(pos.x(), pos.y(), rect.width(), rect.height())
            widget_rect = self._sceneRectToWidget(scene_rect)

            # Skip if too small to see
            if widget_rect.width() < 2 or widget_rect.height() < 2:
                continue

            # Node body
            is_selected = gr_node.isSelected()
            border_color = self.node_selected_border if is_selected else self.node_border_color
            border_width = 2 if is_selected else 1

            painter.setPen(QPen(border_color, border_width))
            painter.setBrush(QBrush(self.node_body_color))

            # Draw rounded rect for node body
            radius = min(3, widget_rect.width() * 0.1, widget_rect.height() * 0.1)
            painter.drawRoundedRect(widget_rect, radius, radius)

            # Draw title bar (top portion)
            title_height = max(2, widget_rect.height() * 0.2)
            title_rect = QRectF(
                widget_rect.x(),
                widget_rect.y(),
                widget_rect.width(),
                title_height
            )

            # Title bar color based on node state
            if hasattr(node, 'is_invalid') and node.is_invalid:
                title_color = QColor(180, 70, 70)  # Red for invalid
            elif hasattr(node, 'is_dirty') and node.is_dirty:
                title_color = QColor(180, 180, 70)  # Yellow for dirty
            else:
                title_color = self.node_title_color

            painter.setBrush(QBrush(title_color))
            painter.setPen(Qt.NoPen)

            # Draw title with top rounded corners only
            title_path = QPainterPath()
            title_path.addRoundedRect(title_rect, radius, radius)
            # Clip bottom corners
            clip_rect = QRectF(
                title_rect.x(),
                title_rect.y() + title_rect.height() / 2,
                title_rect.width(),
                title_rect.height() / 2
            )
            title_path.addRect(clip_rect)
            painter.drawPath(title_path)

        # Draw viewport rectangle (ROI)
        visible_scene_rect = self.main_view.mapToScene(
            self.main_view.viewport().rect()
        ).boundingRect()
        viewport_widget_rect = self._sceneRectToWidget(visible_scene_rect)

        painter.setBrush(QBrush(self.viewport_fill))
        painter.setPen(QPen(self.viewport_border, 2))
        painter.drawRect(viewport_widget_rect)

    def mousePressEvent(self, event):
        """Start dragging the viewport."""
        if event.button() == Qt.LeftButton:
            self._dragging = True
            self._moveViewportTo(event.pos())
            event.accept()

    def mouseMoveEvent(self, event):
        """Drag the viewport."""
        if self._dragging:
            self._moveViewportTo(event.pos())
            event.accept()

    def mouseReleaseEvent(self, event):
        """Stop dragging."""
        if event.button() == Qt.LeftButton:
            self._dragging = False
            event.accept()

    def _moveViewportTo(self, pos):
        """Center the main view on the clicked minimap position."""
        scene_pos = self._widgetToScene(QPointF(pos))
        self.main_view.centerOn(scene_pos)
        self.update()

    def resizeEvent(self, event):
        """Handle resize."""
        super().resizeEvent(event)
        self._updateTransform()

    def updateBounds(self):
        """Public method to force bounds update (e.g., after loading a file)."""
        self._forceUpdateBounds()


class QDMGraphicsLegend(QWidget):
    """Semi-transparent legend showing keyboard shortcuts."""

    panelResized = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)

        # Colors
        self.bg_color = QColor(30, 30, 30, 200)
        self.border_color = QColor(70, 70, 70)
        self.text_color = QColor(180, 180, 180)
        self.key_color = QColor(100, 160, 220)
        self.separator_color = QColor(60, 60, 60)

        # Legend items: (key, description)
        self.items = [
            ("MMB Drag", "Pan view"),
            ("Scroll", "Zoom"),
            ("Ctrl+LMB Drag", "Cut edges"),
            ("Ctrl+Socket", "Reroute edge"),
            ("Shift+Click", "Multi-select"),
            ("Delete", "Remove selected"),
            ("Ctrl+A", "Select all"),
        ]

        self._collapsed = False
        self.initUI()

    def initUI(self):
        self.setFixedWidth(200)
        self._updateHeight()
        self.setCursor(Qt.PointingHandCursor)

    def _updateHeight(self):
        if self._collapsed:
            self.setFixedHeight(24)
        else:
            row_height = 18
            padding = 10
            header_height = 24
            self.setFixedHeight(header_height + len(self.items) * row_height + padding)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        # Background
        painter.setBrush(QBrush(self.bg_color))
        painter.setPen(QPen(self.border_color, 1))
        painter.drawRoundedRect(self.rect().adjusted(1, 1, -1, -1), 4, 4)

        # Header
        header_font = QFont()
        header_font.setPointSize(10)
        header_font.setBold(True)
        painter.setFont(header_font)
        painter.setPen(self.text_color)

        collapse_indicator = "▼" if not self._collapsed else "▶"
        painter.drawText(8, 17, f"{collapse_indicator} Shortcuts")

        if self._collapsed:
            return

        # Separator line
        painter.setPen(QPen(self.separator_color, 1))
        painter.drawLine(8, 23, self.width() - 8, 23)

        # Items
        item_font = QFont()
        item_font.setPointSize(9)
        painter.setFont(item_font)

        y = 40
        row_height = 18

        for key, desc in self.items:
            # Key (highlighted)
            painter.setPen(self.key_color)
            painter.drawText(10, y, key)

            # Description
            painter.setPen(self.text_color)
            key_width = painter.fontMetrics().horizontalAdvance(key)
            painter.drawText(10 + key_width + 8, y, desc)

            y += row_height

    def mousePressEvent(self, event):
        """Toggle collapsed state."""
        if event.button() == Qt.LeftButton:
            self._collapsed = not self._collapsed
            self._updateHeight()
            self.update()
            self.panelResized.emit()
            event.accept()


class QDMMinimapPanel(QWidget):
    """Combined panel with minimap and legend."""

    def __init__(self, scene, main_view, parent=None):
        super().__init__(parent)
        self.scene = scene
        self.main_view = main_view

        self.initUI()

    def initUI(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)

        # Minimap
        self.minimap = QDMGraphicsMinimap(self.scene, self.main_view, self)
        layout.addWidget(self.minimap)

        # Legend
        self.legend = QDMGraphicsLegend(self)
        self.legend.panelResized.connect(self._updateSize)
        layout.addWidget(self.legend)

        # Make background transparent
        self.setAttribute(Qt.WA_TranslucentBackground)

        # Set initial size
        self._updateSize()

    def _updateSize(self):
        """Update panel size based on children."""
        total_height = self.minimap.height() + 4 + self.legend.height()
        self.setFixedSize(200, total_height)

    def updateBounds(self):
        """Forward to minimap."""
        self.minimap.updateBounds()
