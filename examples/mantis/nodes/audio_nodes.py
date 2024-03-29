from PyQt5.QtCore import *
from pathlib import Path
from examples.mantis.mv_config import *
from examples.mantis.mv_node_base import *
from examples.mantis.nodes.colap import CollapseGB
from pipelineeditor.utils import dump_exception
current_file_path = Path(__file__).parent.parent


@register_nodes(OP_NODE_O_AUDIO)
class MVNode_O_Audio(MVOperationsNode):
    icon = str(current_file_path.joinpath(r"icons\ops.png"))
    op_code = OP_NODE_O_AUDIO
    op_title = "Audio"
    content_label = "AUDIO"
    content_label_obj_name = "wav_o_audio_node_bg"
    colaps_widget = None
    _uuid = ""
    uuid_line_edit = None

    def __init__(self, scene) -> None:
        super().__init__(scene, inputs=[2], outputs=[2])
        self.createParamWidget()

    def createParamWidget(self):
        if not self.colaps_widget:
            self.colaps_widget = self.createCollapsWidget()
            UuidGB = self.createUUIDCollapsGB(self.onTextChange)
            self.colaps_widget.layout().addWidget(UuidGB)

        return self.colaps_widget

    def eval_impl(self):
        input_node = self.getInput(0)
        output_node = self.getOutput(0)

        if not input_node:
            self.gr_node.setToolTip("Not connected")
            self.markInvalid()
            return

        if input_node.__class__.__name__ != "MVNode_S_UUID":
            self.gr_node.setToolTip("Input should be UUID node")
            if self.uuid_line_edit:
                self.uuid_line_edit.setText("")
            self.markInvalid()
            return

        if not output_node:
            self.gr_node.setToolTip("Output node not connected")
            self.markInvalid()
            return

        if output_node.__class__.__name__ != "MVNode_T_WAV_File":
            self.gr_node.setToolTip("Output should be WAV file")
            self.markInvalid()
            return

        val = input_node.getVal()

        if val is None:
            self.gr_node.setToolTip("Not a valid UUID")
            if self.uuid_line_edit:
                self.uuid_line_edit.setText("")
            self.markInvalid()
            return

        if self.uuid_line_edit:
            self.uuid_line_edit.setText(val)

        val = output_node.eval()

        if val is None:
            self.gr_node.setToolTip("File output path is missing")
            self.markInvalid()
            return

        self.output_path = val

        self.markDirty(False)
        self.markInvalid(False)
        self.gr_node.setToolTip("")

        return self._uuid

    def getVal(self):
        return self._uuid

    def onTextChange(self):
        self._uuid = self.uuid_line_edit.text()
        self.eval()

    def serialize(self):
        res = super().serialize()
        res['uuid'] = self.uuid_line_edit.text()
        res['params'] = {}
        res['params']['uuid'] = self.uuid_line_edit.text()
        return res

    def deserialize(self, data, hashmap={}, restore_id=True):
        res = super().deserialize(data, hashmap, restore_id)
        try:
            value = data['uuid']
            self.uuid_line_edit.setText(value)
            return True & res
        except Exception as e:
            dump_exception(e)
        return res
