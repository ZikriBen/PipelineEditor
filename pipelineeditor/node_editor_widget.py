from PyQt5.QtWidgets import *
from PyQt5.QtGui import *
from PyQt5.QtCore import *

from pathlib import Path
from pipelineeditor.node_node import Node
from pipelineeditor.node_scene import Scene, InvalidFile
from pipelineeditor.node_edge import Edge

from pipelineeditor.graphics.node_graphics_view import QDMGraphicsView
from pipelineeditor.graphics.node_graphics_minimap import QDMMinimapPanel


class NodeEditorWidget(QWidget):
    SceneClass = Scene

    def __init__(self, parent=None) -> None:
        super().__init__(parent)

        self.filename = None
        self._minimap_enabled = True
        self.initUI()

    def initUI(self):
        self.layout = QVBoxLayout()
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.setLayout(self.layout)
        self.scene = self.__class__.SceneClass()

        # Create graphics view
        self.view = QDMGraphicsView(self.scene.gr_scene, self)
        self.layout.addWidget(self.view)

        # Create minimap panel with legend (pass data scene, not graphics scene)
        self.minimap = QDMMinimapPanel(self.scene, self.view, self)
        self._positionMinimap()

        self.scene.gr_scene.scene.history.store_history("Init scene")

    def _positionMinimap(self):
        """Position the minimap in the top-right corner."""
        if hasattr(self, 'minimap'):
            margin = 10
            x = self.width() - self.minimap.width() - margin
            y = margin
            self.minimap.move(x, y)
            self.minimap.raise_()  # Keep on top

    def resizeEvent(self, event):
        """Handle resize to reposition minimap."""
        super().resizeEvent(event)
        self._positionMinimap()

    def setMinimapEnabled(self, enabled):
        """Show or hide the minimap."""
        self._minimap_enabled = enabled
        self.minimap.setVisible(enabled)

    def isMinimapEnabled(self):
        """Check if minimap is enabled."""
        return self._minimap_enabled

    def fileLoad(self, fname):
        QApplication.setOverrideCursor(Qt.WaitCursor)
        try:
            self.scene.load_from_file(fname)
            self.filename = fname
            self.scene.history.clear()
            self.scene.history.store_initial_history_stamp()
            return True
        except InvalidFile as e:
            QApplication.restoreOverrideCursor()
            QMessageBox.warning(self, f"Error loading {fname}", str(e))
            return False
        finally:
            QApplication.restoreOverrideCursor()

    def fileNew(self):
        self.scene.clear()
        self.filename = None
        self.scene.history.clear()
        self.scene.history.store_initial_history_stamp()

    def fileSave(self, filename=None):
        if filename:
            self.filename = filename

        self.scene.save_to_file(self.filename)
        QApplication.setOverrideCursor(Qt.WaitCursor)
        QApplication.restoreOverrideCursor()
        return True

    def isFilenameSet(self):
        return self.filename is not None

    def getSelectedItems(self):
        return self.scene.getSelectedItems()

    def hasSelectedItems(self):
        return self.getSelectedItems() != []

    def canUndo(self):
        return self.scene.history.can_undo()

    def canRedo(self):
        return self.scene.history.can_redo()

    def isModified(self):
        return self.scene.isModified()

    def getUserFriendltFilename(self):
        name = Path(self.filename).name if self.isFilenameSet() else "New Graph"
        return name + ("*" if self.isModified() else "")

    def add_nodes(self):
        node1 = Node(self.scene, "My Awesome Node1", inputs=[0, 2, 3], outputs=[1])
        node2 = Node(self.scene, "My Awesome Node2", inputs=[1, 2, 3], outputs=[1])
        node3 = Node(self.scene, "My Awesome Node3", inputs=[0, 2, 3], outputs=[1])
        node1.setPos(-350, -250)
        node2.setPos(-75, 0)
        node3.setPos(200, -250)

        edge1 = Edge(self.scene, node1.outputs[0], node2.inputs[0], edge_type=2)
        edge2 = Edge(self.scene, node2.outputs[0], node3.inputs[1], edge_type=2)

        self.scene.history.store_initial_history_stamp()
