from PyQt5.QtWidgets import *
from pathlib import Path
from pipelineeditor.node_node import Node
from pipelineeditor.node_content_widget import QDMNodeContentWidget
from pipelineeditor.graphics.node_graphics_node import QDMGraphicsNode
from examples.mantis.nodes.colap import CollapseGB
from pipelineeditor.node_socket import *
from pipelineeditor.utils import dump_exception


class MVGraphicsNode(QDMGraphicsNode):
    def initSizes(self):
        super().initSizes()
        self.width = 160
        self.height = 74
        self.edge_roundness = 8
        self.edge_padding = 0
        self._title_horizontal_padding = 8
        self._title_vertical_padding = 10

    def initAssets(self):
        super().initAssets()
        current_file_path = Path(__file__).parent
        self.icons = QImage(str(current_file_path.joinpath(r"icons/status_icons.png")))

    def paint(self, painter, QStyleOptionGraphicsItem, widget=None):
        super().paint(painter, QStyleOptionGraphicsItem, widget)

        offset = 24
        if self.node.isDirty():
            offset = 0
        if self.node.isInvalid():
            offset = 48

        painter.drawImage(
            QRectF(-10, -10, 24, 24),
            self.icons,
            QRectF(offset, 0, 24, 24)
        )


class MVContentWidget(QDMNodeContentWidget):
    def initUI(self):
        lbl = QLabel(self.node.content_label, self)
        lbl.setObjectName(self.node.content_label_obj_name)


class MVNode(Node):
    icon = ""
    op_code = 0
    op_title = "Undefined"
    content_label = ""
    content_label_obj_name = "mv_node_bg"
    _uuid = ""
    uuid_line_edit = None

    def __init__(self, scene, inputs=[2, 2], outputs=[1]) -> None:
        super().__init__(scene, self.__class__.op_title, inputs, outputs)

        self.value = None

        # mark all nodes by default to dirty
        self.markDirty()

    def initInnerClasses(self):
        self.content = MVContentWidget(self)
        self.gr_node = MVGraphicsNode(self)

    def initSettings(self):
        super().initSettings()
        self.input_socket_position = LEFT_CENTER
        self.output_socket_position = RIGHT_CENTER

    def eval_operation(self, input1, input2):
        return 123

    def eval_impl(self):
        i1 = self.getInput(0)
        i2 = self.getInput(1)

        if not i1 or not i2:
            self.markInvalid()
            self.markDescendantsDirty()
            self.gr_node.setToolTip("Connecet all inputs")
            return None
        else:
            val = self.eval_operation(i1.eval(), i2.eval())
            self.value = val
            self.markDirty(False)
            self.markInvalid(False)
            self.gr_node.setToolTip("")
            self.markDescendantsDirty()
            self.evalChildren()

            return val

    def eval(self):
        # Eval only when node is either dirty or invalid
        # if not self._is_dirty and not self._is_invalid:
        #     return self.value

        try:
            val = self.eval_impl()
            return val
        except ValueError as e:
            self.markInvalid()
            self.gr_node.setToolTip(str(e))
            self.markDescendantsDirty()
        except Exception as e:
            self.markInvalid()
            self.gr_node.setToolTip(str(e))
            dump_exception(e)

    def onInputChanged(self, socket=None):
        self.markDirty()
        self.eval()

    def getUUID(self):
        return self._uuid if self._uuid else ""

    def createCollapsWidget(self):
        colaps_widget = QWidget()
        colaps_widget.setMinimumWidth(270)
        colaps_widget.setStyleSheet("")
        colaps_widget.setObjectName(str(self.id))
        layout = QVBoxLayout()
        layout.setSpacing(0)
        layout.setAlignment(Qt.AlignTop)
        colaps_widget.setLayout(layout)

        return colaps_widget

    def createUUIDCollapsGB(self, callback, set_readonly=True):
        self.uuid_line_edit = QLineEdit("")
        self.uuid_line_edit.setReadOnly(set_readonly)
        self.uuid_line_edit.textChanged.connect(callback)

        UuidGB = CollapseGB()
        UuidGB.setTitle("UUID")
        UuidGB.setLayout(QGridLayout())
        UuidGB.layout().addWidget(QLabel("UUID:"), 0, 0)
        UuidGB.layout().addWidget(self.uuid_line_edit, 0, 1)
        UuidGB.setFixedHeight(UuidGB.sizeHint().height())

        return UuidGB

    def serialize(self):
        res = super().serialize()
        res['op_code'] = self.__class__.op_code
        return res

    def deserialize(self, data, hashmap={}, restore_id=True):
        res = super().deserialize(data, hashmap, restore_id)
        return res


class MVOperationsNode(MVNode):
    pass


class MVInputNode(MVNode):
    pass


class MVOutputNode(MVNode):
    pass