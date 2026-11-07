"""Baseline: empty schema to prove migration tooling and database connectivity.

Revision ID: 5f3a1c2b9d01
Revises:
Create Date: 2026-11-05 00:00:00

"""

from collections.abc import Sequence

revision: str = "5f3a1c2b9d01"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
