"""Models ORM (SQLAlchemy 2.0).

Hierarquia do conteúdo:

    Roadmap → Module (etapa) → Topic (lição) → Exercise

E o progresso do aluno (uso local single-user): a presença de uma linha em
`Progress` para um `topic_id` significa que aquele tópico foi concluído.
"""

from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .database import Base


def _now() -> datetime:
    return datetime.now(timezone.utc)


class Roadmap(Base):
    __tablename__ = "roadmaps"

    id: Mapped[int] = mapped_column(primary_key=True)
    slug: Mapped[str] = mapped_column(String(80), unique=True, index=True)
    title: Mapped[str] = mapped_column(String(160))
    description: Mapped[str] = mapped_column(Text, default="")
    category: Mapped[str] = mapped_column(String(80), default="Geral")
    icon: Mapped[str] = mapped_column(String(10), default="📚")
    level: Mapped[str] = mapped_column(String(50), default="Iniciante")
    position: Mapped[int] = mapped_column(Integer, default=0)
    active: Mapped[bool] = mapped_column(Boolean, default=True)

    modules: Mapped[list["Module"]] = relationship(
        back_populates="roadmap",
        cascade="all, delete-orphan",
        order_by="Module.position",
    )


class Module(Base):
    __tablename__ = "modules"

    id: Mapped[int] = mapped_column(primary_key=True)
    roadmap_id: Mapped[int] = mapped_column(ForeignKey("roadmaps.id"))
    slug: Mapped[str] = mapped_column(String(80), unique=True, index=True)
    title: Mapped[str] = mapped_column(String(160))
    summary: Mapped[str] = mapped_column(Text, default="")
    position: Mapped[int] = mapped_column(Integer, default=0)

    roadmap: Mapped["Roadmap"] = relationship(back_populates="modules")
    topics: Mapped[list["Topic"]] = relationship(
        back_populates="module",
        cascade="all, delete-orphan",
        order_by="Topic.position",
    )


class Topic(Base):
    __tablename__ = "topics"

    id: Mapped[int] = mapped_column(primary_key=True)
    module_id: Mapped[int] = mapped_column(ForeignKey("modules.id"))
    slug: Mapped[str] = mapped_column(String(80), unique=True, index=True)
    title: Mapped[str] = mapped_column(String(160))
    lesson_md: Mapped[str] = mapped_column(Text, default="")
    position: Mapped[int] = mapped_column(Integer, default=0)
    setup_sql: Mapped[str] = mapped_column(Text, default="")

    module: Mapped["Module"] = relationship(back_populates="topics")
    exercises: Mapped[list["Exercise"]] = relationship(
        back_populates="topic",
        cascade="all, delete-orphan",
        order_by="Exercise.position",
    )
    progress: Mapped["Progress | None"] = relationship(
        back_populates="topic",
        cascade="all, delete-orphan",
        uselist=False,
    )


class Exercise(Base):
    __tablename__ = "exercises"

    id: Mapped[int] = mapped_column(primary_key=True)
    topic_id: Mapped[int] = mapped_column(ForeignKey("topics.id"))
    position: Mapped[int] = mapped_column(Integer, default=0)
    type: Mapped[str] = mapped_column(String(20), default="code")
    prompt: Mapped[str] = mapped_column(Text)
    starter_code: Mapped[str] = mapped_column(Text, default="")
    test_code: Mapped[str] = mapped_column(Text, default="")
    solution: Mapped[str] = mapped_column(Text, default="")
    audio_text: Mapped[str] = mapped_column(Text, default="")
    audio_lang: Mapped[str] = mapped_column(String(20), default="en-US")
    options: Mapped[str] = mapped_column(Text, default="")

    topic: Mapped["Topic"] = relationship(back_populates="exercises")


class Progress(Base):
    """Uma linha por tópico concluído (single-user local)."""

    __tablename__ = "progress"
    __table_args__ = (UniqueConstraint("topic_id", name="uq_progress_topic"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    topic_id: Mapped[int] = mapped_column(ForeignKey("topics.id"), index=True)
    completed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_now
    )
    # Nota de 0 a 10 do tópico, guardando a melhor já obtida. Fica nula em
    # tópicos sem exercícios (só leitura), que não têm o que avaliar.
    score: Mapped[float | None] = mapped_column(Float, nullable=True, default=None)

    topic: Mapped["Topic"] = relationship(back_populates="progress")


class DeletedRoadmap(Base):
    """Lápide de um curso excluído definitivamente pela Lixeira.

    Existe para que a exclusão seja definitiva de verdade: sem isso, o `seed()`
    recriaria o roadmap no próximo restart sempre que o arquivo .json dele ainda
    existir em `app/content/`. Enquanto o slug estiver aqui, o arquivo é ignorado.
    """

    __tablename__ = "deleted_roadmaps"

    id: Mapped[int] = mapped_column(primary_key=True)
    slug: Mapped[str] = mapped_column(String(80), unique=True, index=True)
    deleted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
