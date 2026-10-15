"""calls: multi-proveedor (provider + provider_call_id)

Revision ID: b1f0c5a7d2e4
Revises: 806a912c0919
"""

import sqlalchemy as sa
from alembic import op

revision = "b1f0c5a7d2e4"
down_revision = "806a912c0919"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.alter_column("calls", "vapi_call_id", new_column_name="provider_call_id")
    op.drop_constraint("calls_vapi_call_id_key", "calls", type_="unique")
    op.add_column(
        "calls", sa.Column("provider", sa.String(length=16), nullable=False, server_default="vapi")
    )
    op.alter_column("calls", "provider", server_default=None)
    op.create_unique_constraint("uq_calls_provider_call", "calls", ["provider", "provider_call_id"])


def downgrade() -> None:
    op.drop_constraint("uq_calls_provider_call", "calls", type_="unique")
    op.drop_column("calls", "provider")
    op.alter_column("calls", "provider_call_id", new_column_name="vapi_call_id")
    op.create_unique_constraint("calls_vapi_call_id_key", "calls", ["vapi_call_id"])
