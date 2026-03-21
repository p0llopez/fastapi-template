"""rename api_key to key_hash and hash existing values

Revision ID: 2b0640c7d0ad
Revises: ee87a42a42a5
Create Date: 2026-03-19 17:40:06.399528

"""

import hashlib
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "2b0640c7d0ad"
down_revision: str | Sequence[str] | None = "ee87a42a42a5"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Rename api_key to key_hash and hash existing plain-text values."""
    op.alter_column("api_keys", "api_key", new_column_name="key_hash")
    op.drop_constraint(op.f("uq_api_keys_api_key"), "api_keys", type_="unique")
    op.create_unique_constraint(op.f("uq_api_keys_key_hash"), "api_keys", ["key_hash"])

    conn = op.get_bind()
    rows = conn.execute(sa.text("SELECT api_key_id, key_hash FROM api_keys"))
    for row in rows:
        hashed = hashlib.sha256(row.key_hash.encode()).hexdigest()
        conn.execute(
            sa.text("UPDATE api_keys SET key_hash = :hash WHERE api_key_id = :id"),
            {"hash": hashed, "id": row.api_key_id},
        )


def downgrade() -> None:
    """Rename key_hash back to api_key. Hashes cannot be reversed."""
    op.drop_constraint(op.f("uq_api_keys_key_hash"), "api_keys", type_="unique")
    op.alter_column("api_keys", "key_hash", new_column_name="api_key")
    op.create_unique_constraint(op.f("uq_api_keys_api_key"), "api_keys", ["api_key"])
