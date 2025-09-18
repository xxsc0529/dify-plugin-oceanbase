from typing import Any

from dify_plugin import ToolProvider
from dify_plugin.errors.tool import ToolProviderCredentialValidationError

from tools.common import OceanBaseConfig
from tools.execute_sql import ExecuteSqlTool


class OceanBaseProvider(ToolProvider):

    def _validate_credentials(self, credentials: dict[str, Any]) -> None:
        ob_config = OceanBaseConfig(credentials)
        if not ob_config.is_valid():
            return

        try:
            for _ in ExecuteSqlTool.from_credentials(credentials).invoke(
                tool_parameters={"sql": "SELECT 1"}
            ):
                pass
        except Exception as e:
            raise ToolProviderCredentialValidationError(str(e))
