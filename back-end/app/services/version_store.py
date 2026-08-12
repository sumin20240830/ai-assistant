import sqlite3
from datetime import datetime, timezone
from pathlib import Path

from app.models.validate_schema import EntitySchema
from app.models.version_schema import (
    CreateSchemaVersionRequest,
    SchemaVersionRecord,
)


DATABASE_PATH = Path(__file__).resolve().parents[2] / "data" / "schema_versions.db"


def get_connection() -> sqlite3.Connection:
    DATABASE_PATH.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(DATABASE_PATH)
    connection.row_factory = sqlite3.Row
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS schema_versions (
            session_id TEXT NOT NULL,
            version INTEGER NOT NULL,
            source TEXT NOT NULL,
            reason TEXT,
            created_at TEXT NOT NULL,
            schema_json TEXT NOT NULL,
            PRIMARY KEY (session_id, version)
        )
        """
    )
    return connection


def row_to_record(row: sqlite3.Row) -> SchemaVersionRecord:
    return SchemaVersionRecord(
        sessionId=row["session_id"],
        version=row["version"],
        source=row["source"],
        reason=row["reason"],
        createdAt=row["created_at"],
        schemaData=EntitySchema.model_validate_json(row["schema_json"]),
    )


def list_schema_versions(session_id: str) -> list[SchemaVersionRecord]:
    with get_connection() as connection:
        rows = connection.execute(
            """
            SELECT session_id, version, source, reason, created_at, schema_json
            FROM schema_versions
            WHERE session_id = ?
            ORDER BY version DESC
            """,
            (session_id,),
        ).fetchall()

    return [row_to_record(row) for row in rows]


def create_schema_version(
    request: CreateSchemaVersionRequest,
) -> SchemaVersionRecord:
    with get_connection() as connection:
        latest_version = connection.execute(
            """
            SELECT COALESCE(MAX(version), 0)
            FROM schema_versions
            WHERE session_id = ?
            """,
            (request.sessionId,),
        ).fetchone()[0]

        # 历史版本不覆盖；若版本号已存在，自动生成下一版本。
        next_version = max(request.schemaData.version, latest_version + 1)
        versioned_schema = request.schemaData.model_copy(
            update={"version": next_version}
        )
        created_at = datetime.now(timezone.utc).isoformat()

        connection.execute(
            """
            INSERT INTO schema_versions (
                session_id,
                version,
                source,
                reason,
                created_at,
                schema_json
            ) VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                request.sessionId,
                next_version,
                request.source,
                request.reason,
                created_at,
                versioned_schema.model_dump_json(),
            ),
        )
        connection.commit()

    return SchemaVersionRecord(
        sessionId=request.sessionId,
        version=next_version,
        source=request.source,
        reason=request.reason,
        createdAt=created_at,
        schemaData=versioned_schema,
    )
