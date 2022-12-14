import json
from pathlib import Path

from PyQt5.QtWidgets import *
from PyQt5.QtGui import *
from PyQt5.QtCore import *

from pipelineeditor.node_editor_widget import NodeEditorWidget
# from node_editor_widget import NodeEditorWidget


class NodeEditorWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()

        self.author_name = "ZikriBen"
        self.module_name = "Pipeline Editor"
        self.initUI()

        # QApplication.instance().clipboard().dataChanged.connect(self.onClipboardChanged)

    def initUI(self):
        self.createActions()
        self.createMenus()

        self.node_editor = NodeEditorWidget(self)
        self.setCentralWidget(self.node_editor)
        self.node_editor.scene.add_has_been_modified_listener(self.setTitle)
        self.createStatusBar()

        widget = QWidget(self)
        widget.setLayout(QHBoxLayout())
        widget.layout().addWidget(self.status_bar_text)
        spacerItem = QSpacerItem(800, 0, QSizePolicy.Preferred, QSizePolicy.Preferred)
        widget.layout().addItem(spacerItem)
        widget.layout().addWidget(self.status_mouse_pos)

        self.statusBar().addPermanentWidget(widget)
        self.node_editor.view.scenePosChanged.connect(self.onSceneChanged)

        self.setGeometry(200, 200, 800, 600)
        self.setTitle()
        self.show()

    def createStatusBar(self):
        self.statusBar().showMessage("")
        self.statusBar().setStyleSheet('QStatusBar::item {border: None;}')
        self.status_mouse_pos = QLabel("")
        self.status_bar_text = QLabel("")

    def createActions(self):
        self.actNew    = QAction("&New",     self, triggered=self.onFileNew,    shortcut="Ctrl+N",       statusTip="Create new pipeline")
        self.actOpen   = QAction("&Open",    self, triggered=self.onFileOpen,   shortcut="Ctrl+O",       statusTip="Open file")
        self.actSave   = QAction("&Save",    self, triggered=self.onFileSave,   shortcut="Ctrl+S",       statusTip="Save file")
        self.actSaveAs = QAction("Save &As", self, triggered=self.onFileSaveAs, shortcut="Ctrl+Shift+S", statusTip="Save file as...")
        self.actExit   = QAction("E&xit",    self, triggered=self.closeEvent,   shortcut="ESC",          statusTip="Exit application")

        self.actUndo   = QAction("&Undo",    self, triggered=self.onEditUndo,   shortcut="Ctrl+Z",       statusTip="Undo last operation")
        self.actRedo   = QAction("&Redo",    self, triggered=self.onEditRedo,   shortcut="Ctrl+Y",       statusTip="Redo last operation")
        self.actCopy   = QAction("&Copy",    self, triggered=self.onEditCopy,   shortcut="Ctrl+C",       statusTip="Copy Selected")
        self.actPaste  = QAction("&Paste",   self, triggered=self.onEditPaste,  shortcut="Ctrl+V",       statusTip="Paste Selected")
        self.actCut    = QAction("Cu&t",     self, triggered=self.onEditCut,    shortcut="Ctrl+X",       statusTip="Cut Selected")
        self.actDelete = QAction("&Delete",  self, triggered=self.onEditDelete, shortcut="Del",          statusTip="Delete selected items")

    def createMenus(self):
        self.menubar = self.menuBar()
        self.filemenu = self.menubar.addMenu('&File')

        self.filemenu.addAction(self.actNew)
        self.filemenu.addSeparator()
        self.filemenu.addAction(self.actOpen)
        self.filemenu.addAction(self.actSave)
        self.filemenu.addAction(self.actSaveAs)
        self.filemenu.addSeparator()
        self.filemenu.addAction(self.actExit)

        self.editmenu = self.menubar.addMenu('&Edit')
        self.editmenu.addAction(self.actUndo)
        self.editmenu.addAction(self.actRedo)
        self.editmenu.addAction(self.actCopy)
        self.editmenu.addAction(self.actPaste)
        self.editmenu.addAction(self.actCut)
        self.editmenu.addSeparator()
        self.editmenu.addAction(self.actDelete)

    def setTitle(self):
        title = "Pipeline Editor - "
        title += self.getcurrentPipelineEditorWidget().getUserFriendltFilename()

        self.setWindowTitle(title)

    def onFileNew(self):
        if self.save_dlg:
            self.getcurrentPipelineEditorWidget().scene.clear()
            self.getcurrentPipelineEditorWidget().filename = None
            self.setTitle()

    def onFileOpen(self):
        if self.save_dlg:
            fname, ffilter = QFileDialog.getOpenFileName(self, "Open pipeline from file")

            if not fname:
                return

            self.getcurrentPipelineEditorWidget().fileLoad(fname)

    def onFileSave(self):
        if not self.getcurrentPipelineEditorWidget().isFilenameSet():
            return self.onFileSaveAs()

        # self.getcurrentPipelineEditorWidget().scene.save_to_file(self.getcurrentPipelineEditorWidget().filename)
        self.getcurrentPipelineEditorWidget().fileSave()
        self.print_msg(f"Successfully saved to {self.getcurrentPipelineEditorWidget().filename}")

        if hasattr("selfTitle", self.getcurrentPipelineEditorWidget()):
            self.getcurrentPipelineEditorWidget().setTitle()

        return True

    def onFileSaveAs(self):
        fname, ffilter = QFileDialog.getSaveFileName(self, "Save pipeline to file")

        if not fname:
            return False

        self.getcurrentPipelineEditorWidget().fileSave(fname)
        self.print_msg(f"Successfully saved to {self.getcurrentPipelineEditorWidget().filename}")

        return True

    def onEditUndo(self):
        self.getcurrentPipelineEditorWidget().scene.history.undo()

    def onEditRedo(self):
        self.getcurrentPipelineEditorWidget().scene.history.redo()

    def onEditDelete(self):
        self.getcurrentPipelineEditorWidget().scene.gr_scene.views()[0].deleteSelected()

    def onEditCut(self):
        data = self.getcurrentPipelineEditorWidget().scene.clipboard.serializedSelected(delete=True)
        str_data = json.dumps(data, indent=4)
        QApplication.instance().clipboard().setText(str_data)

    def onEditCopy(self):
        data = self.getcurrentPipelineEditorWidget().scene.clipboard.serializedSelected(delete=False)
        str_data = json.dumps(data, indent=4)
        QApplication.instance().clipboard().setText(str_data)

    def onEditPaste(self):
        raw_data = QApplication.instance().clipboard().text()
        try:
            data = json.loads(raw_data)
        except Exception as e:
            print(e)
            return

        if 'nodes' not in data:
            print("Json is not contain any node")
            return

        self.getcurrentPipelineEditorWidget().scene.clipboard.deserializeFromClipboard(data)

    def print_msg(self, msg, color='black', msecs=3000):
        QTimer.singleShot(msecs, lambda: self.status_bar_text.setText(""))
        self.status_bar_text.setStyleSheet(f"color : {color}")
        self.status_bar_text.setText(msg)

    def onSceneChanged(self, x, y):
        self.status_mouse_pos.setText(f"Scene Pos [{x}, {y}]")

    def getcurrentPipelineEditorWidget(self):
        return self.centralWidget()

    def isModified(self):
        return self.getcurrentPipelineEditorWidget().scene.has_been_modified

    def closeEvent(self, event) -> None:
        if self.save_dlg():
            event.accept()
        else:
            event.ignore()

    def save_dlg(self):
        if not self.isModified():
            return True

        res = QMessageBox.warning(self, "Pipeline Editor Alert", "The document has been modified.\nDo you want to save your changes?", QMessageBox.Save | QMessageBox.Discard | QMessageBox.Cancel)

        if res == QMessageBox.Save:
            return self.onFileSave()
        elif res == QMessageBox.Cancel:
            return False

        return True

    def readSettings(self):
        settings = QSettings(self.author_name, self.module_name)
        pos = settings.value('pos', QPoint(200, 200))
        size = settings.value('size', QSize(400, 400))
        self.move(pos)
        self.resize(size)

    def writeSettings(self):
        settings = QSettings(self.author_name, self.module_name)
        settings.setValue('pos', self.pos())
        settings.setValue('size', self.size())
