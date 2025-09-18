import json
from collections.abc import Generator
from typing import Any

from dify_plugin import Tool
from dify_plugin.entities.model.message import SystemPromptMessage, UserPromptMessage
from dify_plugin.entities.tool import ToolInvokeMessage

from tools.common import OceanBaseConfig, get_table_info

SYSTEM_PROMPT = """
You are a MySQL expert. Your task is to generate an executable query for MySQL based on a user's question.

Requirements:
1. Generate a complete, executable query that can be run directly
2. Query only necessary columns
3. Don't wrap column names in double quotes (") as delimited identifiers
4. Unless specified, limit results to 5 rows
5. Use date('now') for current date references
6. The response format should not include special characters like ```, \n, \", etc.

Query Guidelines:
- Ensure the query matches MySQL syntax
- Only use columns that exist in the provided tables
- Add appropriate table joins with correct join conditions
- Include WHERE clauses to filter data as needed
- Add ORDER BY when sorting is beneficial
- Use appropriate data type casting

Common Pitfalls to Avoid:
- NULL handling in NOT IN clauses
- UNION vs UNION ALL usage
- Exclusive range conditions
- Data type mismatches
- Missing or incorrect quotes around identifiers
- Wrong function arguments
- Incorrect join conditions
"""

USER_PROMPT_TEMPLATE = """
Context and Tables:
{table_info}

Examples:
User input: How many employees are there
Your response: SELECT COUNT(*) FROM "Employee"

User input: How many tracks are there in the album with ID 5?
Your response: SELECT COUNT(*) FROM Track WHERE AlbumId = 5;

User input: Which albums are from the year 2000?
Your response: SELECT * FROM Album WHERE strftime('%Y', ReleaseDate) = '2000';

User input: List all tracks in the 'Rock' genre.
Your response: SELECT * FROM Track WHERE GenreId = (SELECT GenreId FROM Genre WHERE Name = 'Rock');


Now, the user input is : {query}
"""


class Text2SqlTool(Tool):
    def _invoke(self, tool_parameters: dict[str, Any]) -> Generator[ToolInvokeMessage]:
        query = tool_parameters.get("query").strip()
        tables = tool_parameters.get("tables")
        model_config = tool_parameters.get("model")
        config_options = tool_parameters.get("config_options") or "{}"

        try:
            config_options = json.loads(config_options)
        except json.JSONDecodeError:
            raise ValueError("Invalid JSON format for Connect Config")

        ob_config = OceanBaseConfig(self.runtime.credentials)
        assert ob_config.is_valid(), f"Invalid OceanBaseConfig: {ob_config}"
        db_uri = ob_config.get_uri()
        tables = tables.split(",") if tables else None
        table_info = get_table_info(db_uri, config_options, tables)

        prompt_messages = [
            SystemPromptMessage(content=SYSTEM_PROMPT),
            UserPromptMessage(
                content=USER_PROMPT_TEMPLATE.format(table_info=list(table_info.values()), query=query)
            ),
        ]

        response = self.session.model.llm.invoke(
            model_config=model_config,
            prompt_messages=prompt_messages,
            stream=False,
        )
        yield self.create_text_message(response.message.content)
