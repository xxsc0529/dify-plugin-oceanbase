from typing import Any
from urllib.parse import quote_plus

from sqlalchemy import create_engine, inspect
from sqlalchemy.dialects import registry

registry.register("mysql.oceanbase", "pyobvector.schema.dialect", "OceanBaseDialect")


class OceanBaseConfig:
    def __init__(self, config: dict[str, Any]) -> None:
        self.hostname = config.get("hostname")
        self.port = config.get("port")
        self.db_name = config.get("db_name", "")
        self.username = config.get("username")
        self.password = config.get("password", "")

    def is_valid(self) -> bool:
        return self.hostname and self.port and self.username

    def get_uri(self):
        encoded_username = quote_plus(self.username)
        encoded_password = quote_plus(self.password)
        return f"mysql+oceanbase://{encoded_username}:{encoded_password}@{self.hostname}:{self.port}/{self.db_name}?charset=utf8mb4"


def get_table_info(
    uri: str,
    conn_options: dict[str, Any],
    tables: list[str],
    include_constraint: bool = False,
) -> dict[str, dict[str, Any]]:
    """
    Get table information.

    :param uri: database URI used to create sqlalchemy engine
    :param conn_options: options of sqlalchemy engine
    :param tables: table names separated by comma
    :param include_constraint: flag of whether to include table constraints
    :return: table information in format: {table_name -> table_info}
    """
    engine = create_engine(uri, **conn_options)
    inspector = inspect(engine)
    tables = tables if tables else inspector.get_table_names()

    table_infos = {}
    with engine.connect() as _:
        for table_name in tables:
            try:
                table_info: dict[str, Any] = {
                    "table_name": table_name,
                    "columns": [
                        {
                            "name": col["name"],
                            "type": str(col["type"]),
                            "nullable": col.get("nullable", True),
                            "default": col.get("default"),
                            "comment": col.get("comment", ""),
                        }
                        for col in inspector.get_columns(table_name)
                    ],
                    "comment": inspector.get_table_comment(table_name).get("text"),
                }

                if include_constraint:
                    table_info["primary_keys"] = inspector.get_pk_constraint(table_name).get("constrained_columns")
                    table_info["foreign_keys"] = [
                        {
                            "referred_table": fk['referred_table'],
                            "referred_columns": fk['referred_columns'],
                            "constrained_columns": fk['constrained_columns']
                        }
                        for fk in inspector.get_foreign_keys(table_name)
                    ]
                    table_info["indexes"] = [
                        {
                            "name": idx['name'],
                            "columns": idx['column_names'],
                            "unique": idx['unique']
                        }
                        for idx in inspector.get_indexes(table_name)
                    ]

                table_infos[table_name] = table_info
            except Exception as e:
                table_info[table_name] = f"Error getting table info: {str(e)}"

    return table_infos
