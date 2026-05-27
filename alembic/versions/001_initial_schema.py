"""Initial schema.

Revision ID: 001_initial
Revises:
Create Date: 2026-05-26 18:50:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "001_initial"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.BigInteger(), primary_key=True),
        sa.Column("login", sa.String(length=50), nullable=False, unique=True),
        sa.Column("email", sa.String(length=255), nullable=False, unique=True),
        sa.Column("password_hash", sa.Text(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )

    op.create_table(
        "projects",
        sa.Column("id", sa.BigInteger(), primary_key=True),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("owner_id", sa.BigInteger(), nullable=False),
        sa.Column(
            "total_size_bytes",
            sa.BigInteger(),
            server_default="0",
            nullable=False,
        ),
        sa.Column(
            "documents_count",
            sa.Integer(),
            server_default="0",
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(
            "total_size_bytes >= 0",
            name="projects_total_size_check",
        ),
        sa.CheckConstraint(
            "documents_count >= 0",
            name="projects_documents_count_check",
        ),
        sa.ForeignKeyConstraint(["owner_id"], ["users.id"], ondelete="RESTRICT"),
    )

    op.create_table(
        "project_members",
        sa.Column("id", sa.BigInteger(), primary_key=True),
        sa.Column("project_id", sa.BigInteger(), nullable=False),
        sa.Column("user_id", sa.BigInteger(), nullable=False),
        sa.Column("role", sa.String(length=20), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.CheckConstraint(
            "role IN ('owner', 'participant')",
            name="project_members_role_check",
        ),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.UniqueConstraint(
            "project_id",
            "user_id",
            name="project_members_project_user_key",
        ),
    )

    op.create_table(
        "documents",
        sa.Column("id", sa.BigInteger(), primary_key=True),
        sa.Column("project_id", sa.BigInteger(), nullable=False),
        sa.Column("uploaded_by_id", sa.BigInteger(), nullable=False),
        sa.Column("filename", sa.Text(), nullable=False),
        sa.Column("content_type", sa.String(length=255), nullable=False),
        sa.Column("size_bytes", sa.BigInteger(), nullable=False),
        sa.Column("storage_key", sa.Text(), nullable=False, unique=True),
        sa.Column(
            "status",
            sa.String(length=40),
            server_default="uploaded",
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint("size_bytes >= 0", name="documents_size_bytes_check"),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["uploaded_by_id"],
            ["users.id"],
            ondelete="RESTRICT",
        ),
    )

    op.create_table(
        "project_invites",
        sa.Column("id", sa.BigInteger(), primary_key=True),
        sa.Column("project_id", sa.BigInteger(), nullable=False),
        sa.Column("invited_login", sa.String(length=50), nullable=True),
        sa.Column("invited_email", sa.String(length=255), nullable=True),
        sa.Column("token_hash", sa.Text(), nullable=False, unique=True),
        sa.Column("role", sa.String(length=20), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("accepted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.CheckConstraint(
            "role IN ('owner', 'participant')",
            name="project_invites_role_check",
        ),
        sa.CheckConstraint(
            "invited_login IS NOT NULL OR invited_email IS NOT NULL",
            name="project_invites_target_check",
        ),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="CASCADE"),
    )

    op.create_index("idx_projects_owner_id", "projects", ["owner_id"])
    op.create_index("idx_projects_deleted_at", "projects", ["deleted_at"])
    op.create_index(
        "idx_project_members_project_id",
        "project_members",
        ["project_id"],
    )
    op.create_index("idx_project_members_user_id", "project_members", ["user_id"])
    op.create_index("idx_documents_project_id", "documents", ["project_id"])
    op.create_index(
        "idx_documents_uploaded_by_id",
        "documents",
        ["uploaded_by_id"],
    )
    op.create_index("idx_documents_deleted_at", "documents", ["deleted_at"])
    op.create_index("idx_documents_status", "documents", ["status"])
    op.create_index(
        "idx_project_invites_project_id",
        "project_invites",
        ["project_id"],
    )
    op.create_index(
        "idx_project_invites_expires_at",
        "project_invites",
        ["expires_at"],
    )


def downgrade() -> None:
    op.drop_index("idx_project_invites_expires_at", table_name="project_invites")
    op.drop_index("idx_project_invites_project_id", table_name="project_invites")
    op.drop_index("idx_documents_status", table_name="documents")
    op.drop_index("idx_documents_deleted_at", table_name="documents")
    op.drop_index("idx_documents_uploaded_by_id", table_name="documents")
    op.drop_index("idx_documents_project_id", table_name="documents")
    op.drop_index("idx_project_members_user_id", table_name="project_members")
    op.drop_index("idx_project_members_project_id", table_name="project_members")
    op.drop_index("idx_projects_deleted_at", table_name="projects")
    op.drop_index("idx_projects_owner_id", table_name="projects")
    op.drop_table("project_invites")
    op.drop_table("documents")
    op.drop_table("project_members")
    op.drop_table("projects")
    op.drop_table("users")
