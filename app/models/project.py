from datetime import datetime

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class Project(Base):
    __tablename__ = "projects"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    owner_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    total_size_bytes: Mapped[int] = mapped_column(
        BigInteger,
        nullable=False,
        server_default="0",
    )
    documents_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        server_default="0",
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    members: Mapped[list["ProjectMember"]] = relationship(
        back_populates="project",
        cascade="all, delete-orphan",
    )
    invites: Mapped[list["ProjectInvite"]] = relationship(
        back_populates="project",
        cascade="all, delete-orphan",
    )

    __table_args__ = (
        CheckConstraint("total_size_bytes >= 0", name="projects_total_size_check"),
        CheckConstraint("documents_count >= 0", name="projects_documents_count_check"),
    )


class ProjectMember(Base):
    __tablename__ = "project_members"

    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
    )
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    role: Mapped[str] = mapped_column(String(20), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    project: Mapped[Project] = relationship(back_populates="members")

    __table_args__ = (
        UniqueConstraint(
            "project_id",
            "user_id",
            name="project_members_project_user_key",
        ),
        CheckConstraint(
            "role IN ('owner', 'participant')",
            name="project_members_role_check",
        ),
    )


class ProjectInvite(Base):
    __tablename__ = "project_invites"

    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
    )
    invited_login: Mapped[str | None] = mapped_column(String(50))
    invited_email: Mapped[str | None] = mapped_column(String(255))
    token_hash: Mapped[str] = mapped_column(Text, unique=True, nullable=False)
    role: Mapped[str] = mapped_column(String(20), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )
    accepted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    project: Mapped[Project] = relationship(back_populates="invites")

    __table_args__ = (
        CheckConstraint(
            "role IN ('owner', 'participant')",
            name="project_invites_role_check",
        ),
        CheckConstraint(
            "invited_login IS NOT NULL OR invited_email IS NOT NULL",
            name="project_invites_target_check",
        ),
    )
