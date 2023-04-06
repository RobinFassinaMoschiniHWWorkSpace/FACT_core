from __future__ import annotations

from helperFunctions.tag import TagColor
from plugins.mime_blacklists import MIME_BLACKLIST_COMPRESSED
from analysis.plugin.compat import AnalysisBasePluginAdapterMixin
from analysis.plugin import AnalysisPluginV0, Tag
from typing import Optional, Dict, TYPE_CHECKING

from ..internal.schema import Schema
from ..internal.schema import DeviceTree, IllegalDeviceTreeError

if TYPE_CHECKING:
    import io


class AnalysisPlugin(AnalysisPluginV0, AnalysisBasePluginAdapterMixin):
    def __init__(self):
        metadata = AnalysisPluginV0.MetaData(
            name='device_tree',
            description='get the device tree in text from the device tree blob',
            version='1.1.0',
            system_version=None,
            mime_blacklist=[*MIME_BLACKLIST_COMPRESSED, 'audio', 'image', 'video'],
            timeout=10,
            Schema=Schema,
        )
        super().__init__(metadata=metadata)

    def summarize(self, result: Schema) -> list[str]:
        models = [device_tree.model for device_tree in result.device_trees if device_tree.model]

        if not models:
            return ['unknown-model']

        return models

    def analyze(
        self,
        file_handle: io.FileIO,
        virtual_file_path: dict,
        analyses: Dict[str, dict],
    ) -> Optional[Schema]:
        del virtual_file_path, analyses

        binary = file_handle.readall()

        device_trees = []
        offset = 0
        while (offset := binary.find(DeviceTree.Header.MAGIC, offset)) >= 0:
            try:
                device_tree = DeviceTree.from_binary(binary, offset=offset)
                # We found a valid device tree.
                # Skip only the header because device trees may contain device trees themselves.
                offset += DeviceTree.Header.SIZE
                device_trees.append(device_tree)
            except IllegalDeviceTreeError:
                offset += 1

        if len(device_trees) == 0:
            return None

        return Schema(device_trees=device_trees)

    def get_tags(self, result: Schema, summary: list[str]) -> list[Tag]:
        del result, summary
        return [
            Tag(
                name=self.metadata.name,
                value='device tree',
                color=TagColor.ORANGE,
            ),
        ]
