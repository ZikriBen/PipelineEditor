from PyQt5.QtCore import *
from PyQt5.QtGui import *
from pathlib import Path
from examples.calculator.calc_config import *
from pipelineeditor.node_editor_widget import NodeEditorWidget
from pipelineeditor.utils import dump_exception 
# from pipelineeditor.node_node import Node
from examples.calculator.calc_node_base import *


class CalculatorSubWindow(NodeEditorWidget):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setAttribute(Qt.WA_DeleteOnClose)
        self.scene.add_has_been_modified_listener(self.setTitle)
        self.scene.add_drag_enter_listener(self.onDragEnter)
        self.scene.add_drop_listener(self.onDrop)
        self.scene.set_node_class_selector(self.getNodeClassFromData)
        self._close_event_listeners = []
        self.setTitle()

    def getNodeClassFromData(self, data):
        if 'op_code' not in data:
            return Node

        return get_class_from_op_code(data['op_code'])

    def setTitle(self):
        self.setWindowTitle(self.getUserFriendltFilename())

    def closeEvent(self, event) -> None:
        for callback in self._close_event_listeners:
            callback(self, event)

    def addCloseEventListener(self, callback):
        self._close_event_listeners.append(callback)

    def onDragEnter(self, event):
        print("Calc subwindow: onDragEnter")
        print(f"mimeData: {event.mimeData()}|")

        if event.mimeData().hasFormat(LISTBOX_MIMETYPE) or event.mimeData().hasUrls():
            event.acceptProposedAction()
        else:
            print("... denided drag event")
            event.setAccepted(False)

    def onDrop(self, event):
        print("Calc subwindow: onDrop")
        print(f"mimeData: {event.mimeData().text()}|")
        # Drop File from Nodes ListBox
        if event.mimeData().hasFormat(LISTBOX_MIMETYPE):
            eventData = event.mimeData().data(LISTBOX_MIMETYPE)
            dataStream = QDataStream(eventData, QIODevice.ReadOnly)
            pixmap = QPixmap()
            dataStream >> pixmap
            op_code = dataStream.readInt()
            text = dataStream.readQString()

            mouse_pos = event.pos()
            scene_pos = self.scene.gr_scene.views()[0].mapToScene(mouse_pos)

            print(f"DROP: {op_code} - {text} mouse at: {mouse_pos} scene at: {scene_pos}")

            try:
                node = get_class_from_op_code(op_code)(self.scene)
                node.setPos(scene_pos.x(), scene_pos.y())
                self.scene.history.store_history(f"Created Node {node.__class__.__name__}")
            except Exception as e:
                dump_exception(e)

            event.setDropAction(Qt.MoveAction)
            event.accept()
        # Drop File from Windows Explorer
        elif event.mimeData().hasUrls():
            op_code = OP_NODE_INPUT
            mouse_pos = event.pos()
            scene_pos = self.scene.gr_scene.views()[0].mapToScene(mouse_pos)

            # TODO: Fix dragging files in input files
            for i, url in enumerate(event.mimeData().urls()):
                print(f"DROP: {op_code} - {str(url)} mouse at: {mouse_pos} scene at: {scene_pos}")

                try:
                    offset = i * 20
                    node = get_class_from_op_code(OP_NODE_INPUT)(self.scene)
                    node.setPos(scene_pos.x() + offset, scene_pos.y() + offset)
                    # node.setContentTitle(Path((url.toString())).name) # Need to fix node content
                    self.scene.history.store_history(f"Created Node {node.__class__.__name__}")
                except Exception as e:
                    dump_exception(e)

            event.setDropAction(Qt.MoveAction)
            event.accept()
        else:
            print("... ignore drop event, not in requested format")
            event.ignore()
