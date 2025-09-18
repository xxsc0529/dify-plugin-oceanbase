import json
import re
from collections.abc import Generator
from typing import Any

import records
from dify_plugin import Tool
from dify_plugin.entities.tool import ToolInvokeMessage

from tools.common import OceanBaseConfig


class ExecuteSqlTool(Tool):
    def _invoke(self, tool_parameters: dict[str, Any]) -> Generator[ToolInvokeMessage]:
        sql = tool_parameters.get("sql").strip()
        return_format = tool_parameters.get("format", "json")
        config_options = tool_parameters.get("config_options") or "{}"

        try:
            config_options = json.loads(config_options)
        except json.JSONDecodeError:
            raise ValueError("Invalid JSON format for Connect Config")

        ob_config = OceanBaseConfig(self.runtime.credentials)
        assert ob_config.is_valid(), f"Invalid OceanBaseConfig: {ob_config}"
        db_uri = ob_config.get_uri()
        db = records.Database(db_uri, **config_options)

        try:
            if re.match(r'^\s*(SELECT|SHOW|WITH)\s+', sql, re.IGNORECASE):
                rows = db.query(sql)
                if return_format == "json":
                    result = rows.as_dict()
                    yield self.create_json_message({"result": result})
                elif return_format == "md":
                    result = str(rows.dataset)
                    yield self.create_text_message(result)
                elif return_format == "csv":
                    result = rows.export("csv").encode()
                    yield self.create_blob_message(
                        result, meta={"mime_type": "text/csv", "filename": "result.csv"}
                    )
                elif return_format == "yaml":
                    result = rows.export("yaml").encode()
                    yield self.create_blob_message(
                        result,
                        meta={"mime_type": "text/yaml", "filename": "result.yaml"},
                    )
                elif return_format == "xlsx":
                    result = rows.export("xlsx")
                    yield self.create_blob_message(
                        result,
                        meta={
                            "mime_type": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                            "filename": "result.xlsx",
                        },
                    )
                elif return_format == "html":
                    result = rows.export("html").encode()
                    yield self.create_blob_message(
                        result,
                        meta={"mime_type": "text/html", "filename": "result.html"},
                    )
                else:
                    raise ValueError(f"Unsupported format: {return_format}")
            else:
                raise ValueError("'sql' should start with 'SELECT|SHOW|WITH'")
        finally:
            db.close()
