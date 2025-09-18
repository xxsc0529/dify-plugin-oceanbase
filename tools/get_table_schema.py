import json
from collections.abc import Generator
from typing import Any

from dify_plugin import Tool
from dify_plugin.entities.tool import ToolInvokeMessage

from tools.common import OceanBaseConfig, get_table_info


class GetTableSchemaTool(Tool):
    def _invoke(self, tool_parameters: dict[str, Any]) -> Generator[ToolInvokeMessage]:
        tables = tool_parameters.get("tables")
        config_options = tool_parameters.get("config_options") or "{}"

        try:
            config_options = json.loads(config_options)
        except json.JSONDecodeError:
            raise ValueError("Invalid JSON format for Connect Config")

        ob_config = OceanBaseConfig(self.runtime.credentials)
        assert ob_config.is_valid(), f"Invalid OceanBaseConfig: {ob_config}"
        db_uri = ob_config.get_uri()
        tables = tables.split(",") if tables else None
        table_info = get_table_info(db_uri, config_options, tables, include_constraint=True)

        yield self.create_json_message(table_info)
