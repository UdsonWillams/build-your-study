"""Carga de conteúdo: lê os JSONs de `content/` e popula o banco via ORM.

Idempotente: a cada execução, o conteúdo (roadmaps/módulos/tópicos/exercícios) é
recriado a partir dos arquivos, mas a tabela `Progress` é **preservada** (o progresso
do aluno não se perde ao atualizar/adicionar aulas), assim como o campo `active` do
roadmap (desativar um curso pela interface não é desfeito por um reseed).

Remover o arquivo .json de um curso NÃO apaga o roadmap do banco — ele só deixa de
ser atualizado. Para removê-lo de fato, desative o curso pela interface e exclua-o
definitivamente na Lixeira.

Para adicionar novos roadmaps, basta criar outro arquivo .json em `app/content/`
seguindo o mesmo formato e reiniciar o app.
"""

import contextlib
import io
import json
import sqlite3
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from .database import Base, SessionLocal, engine
from .models import Exercise, Module, Roadmap, Topic

CONTENT_DIR = Path(__file__).resolve().parent / "content"


def _validate_sql_exercise(
    setup_sql: str, solution: str, topic_slug: str, position: int, verify_query: str | None = None
) -> None:
    """Roda setup_sql + a solution de referência num SQLite em memória.

    Pega erro de autoria (setup_sql ou solution quebrados) na carga do conteúdo,
    em vez de deixar o aluno esbarrar num exercício com bug.

    Exercícios de INSERT/UPDATE/DELETE não retornam linhas — por isso, quando
    `verify_query` está presente, validamos rodando o comando (`solution`) e depois
    uma consulta de verificação (que precisa retornar linhas) em vez de exigir que
    a própria `solution` seja um SELECT.
    """
    conn = sqlite3.connect(":memory:")
    try:
        if setup_sql:
            conn.executescript(setup_sql)
        conn.execute(solution)
        if verify_query:
            conn.execute(verify_query)
    except sqlite3.Error as e:
        raise ValueError(
            f"Exercício sql inválido no tópico '{topic_slug}' (posição {position}): {e}"
        ) from e
    finally:
        conn.close()


def _validate_code_exercise(solution: str, test_code: str, topic_slug: str, position: int) -> None:
    """Roda a solution de referência + test_code de um exercício `code` de verdade.

    Mesma ideia da validação de sql: pega bug de autoria (solution errada, assert
    com typo, etc.) na carga do conteúdo, replicando o mesmo runtime usado pelo
    Pyodide no navegador (namespace com `_student_code` disponível).
    """
    if not test_code:
        return
    ns = {"_student_code": solution}
    try:
        with contextlib.redirect_stdout(io.StringIO()):
            exec(solution, ns)
            exec(test_code, ns)
    except Exception as e:
        raise ValueError(
            f"Exercício code inválido no tópico '{topic_slug}' (posição {position}): {type(e).__name__}: {e}"
        ) from e


def _load_roadmap(db: Session, data: dict, active: bool = True) -> None:
    """Cria (ou recria) um roadmap completo a partir do dict do JSON."""
    # Remove a versão anterior deste roadmap (cascade apaga módulos/tópicos/exercícios).
    # O Progress aponta para tópicos por id; ao recriar, os ids mudam, então
    # religamos o progresso por slug logo abaixo.
    existing = db.scalar(select(Roadmap).where(Roadmap.slug == data["slug"]))
    if existing is not None:
        db.delete(existing)
        db.flush()

    roadmap = Roadmap(
        slug=data["slug"],
        title=data["title"],
        description=data.get("description", ""),
        category=data.get("category", "Geral"),
        icon=data.get("icon", "📚"),
        level=data.get("level", "Iniciante"),
        position=data.get("position", 0),
        active=active,
    )
    for m in data.get("modules", []):
        module = Module(
            slug=m["slug"],
            title=m["title"],
            summary=m.get("summary", ""),
            position=m.get("position", 0),
        )
        for t in m.get("topics", []):
            topic = Topic(
                slug=t["slug"],
                title=t["title"],
                lesson_md=t.get("lesson_md", ""),
                position=t.get("position", 0),
                setup_sql=t.get("setup_sql", ""),
            )
            for ex in t.get("exercises", []):
                raw_options = ex.get("options", "")
                options = json.dumps(raw_options) if isinstance(raw_options, (list, dict)) else raw_options

                if ex.get("type") == "sql":
                    resolved_setup_sql = (
                        raw_options.get("setup_sql") if isinstance(raw_options, dict) else None
                    ) or t.get("setup_sql", "")
                    verify_query = raw_options.get("verify_query") if isinstance(raw_options, dict) else None
                    _validate_sql_exercise(
                        resolved_setup_sql, ex.get("solution", ""), t["slug"], ex.get("position", 0), verify_query
                    )
                elif ex.get("type", "code") == "code":
                    _validate_code_exercise(
                        ex.get("solution", ""), ex.get("test_code", ""), t["slug"], ex.get("position", 0)
                    )

                topic.exercises.append(
                    Exercise(
                        position=ex.get("position", 0),
                        type=ex.get("type", "code"),
                        prompt=ex["prompt"],
                        starter_code=ex.get("starter_code", ""),
                        test_code=ex.get("test_code", ""),
                        solution=ex.get("solution", ""),
                        audio_text=ex.get("audio_text", ""),
                        audio_lang=ex.get("audio_lang", "en-US"),
                        options=options,
                    )
                )
            module.topics.append(topic)
        roadmap.modules.append(module)

    db.add(roadmap)


def _ensure_schema() -> None:
    """Garante que as novas colunas existam no SQLite caso o banco seja antigo."""
    from sqlalchemy import text
    with engine.connect() as conn:
        try:
            res_roadmaps = conn.execute(text("PRAGMA table_info(roadmaps);")).fetchall()
            cols_roadmaps = {row[1] for row in res_roadmaps}
            if cols_roadmaps and "category" not in cols_roadmaps:
                conn.execute(text("ALTER TABLE roadmaps ADD COLUMN category VARCHAR(80) DEFAULT 'Geral'"))
                conn.execute(text("ALTER TABLE roadmaps ADD COLUMN icon VARCHAR(10) DEFAULT '📚'"))
                conn.execute(text("ALTER TABLE roadmaps ADD COLUMN level VARCHAR(50) DEFAULT 'Iniciante'"))
                conn.commit()

            if cols_roadmaps and "active" not in cols_roadmaps:
                conn.execute(text("ALTER TABLE roadmaps ADD COLUMN active BOOLEAN DEFAULT 1"))
                conn.commit()

            res_exercises = conn.execute(text("PRAGMA table_info(exercises);")).fetchall()
            cols_exercises = {row[1] for row in res_exercises}
            if cols_exercises and "type" not in cols_exercises:
                conn.execute(text("ALTER TABLE exercises ADD COLUMN type VARCHAR(20) DEFAULT 'code'"))
                conn.execute(text("ALTER TABLE exercises ADD COLUMN audio_text TEXT DEFAULT ''"))
                conn.execute(text("ALTER TABLE exercises ADD COLUMN audio_lang VARCHAR(20) DEFAULT 'en-US'"))
                conn.execute(text("ALTER TABLE exercises ADD COLUMN options TEXT DEFAULT ''"))
                conn.commit()

            res_topics = conn.execute(text("PRAGMA table_info(topics);")).fetchall()
            cols_topics = {row[1] for row in res_topics}
            if cols_topics and "setup_sql" not in cols_topics:
                conn.execute(text("ALTER TABLE topics ADD COLUMN setup_sql TEXT DEFAULT ''"))
                conn.commit()
        except Exception:
            pass


def seed() -> None:
    """Cria as tabelas (se necessário) e carrega todos os JSONs de content/."""
    Base.metadata.create_all(engine)
    _ensure_schema()

    files = sorted(CONTENT_DIR.glob("*.json"))
    if not files:
        return

    with SessionLocal() as db:
        # Guarda os slugs de tópicos já concluídos para religar o progresso
        # depois que os tópicos forem recriados (os ids mudam).
        from .models import DeletedRoadmap, Progress

        completed_slugs = {
            slug
            for (slug,) in db.execute(
                select(Topic.slug).join(Progress, Progress.topic_id == Topic.id)
            ).all()
        }

        # Guarda quais roadmaps estão desativados para preservar isso no reload
        # (desativar um curso não pode ser desfeito por um simples restart).
        active_by_slug = dict(db.execute(select(Roadmap.slug, Roadmap.active)).all())

        # Cursos excluídos definitivamente na Lixeira nunca voltam, mesmo que o
        # arquivo .json ainda exista em content/ (exclusão é para valer).
        deleted_slugs = set(db.scalars(select(DeletedRoadmap.slug)).all())

        parsed = [json.loads(path.read_text(encoding="utf-8")) for path in files]

        for data in parsed:
            if data["slug"] in deleted_slugs:
                continue
            _load_roadmap(db, data, active=active_by_slug.get(data["slug"], True))
        db.flush()

        # Religa o progresso pelos slugs preservados.
        db.query(Progress).delete()
        if completed_slugs:
            topics = db.scalars(
                select(Topic).where(Topic.slug.in_(completed_slugs))
            ).all()
            for topic in topics:
                db.add(Progress(topic_id=topic.id))

        db.commit()


if __name__ == "__main__":
    seed()
    print("Conteúdo carregado com sucesso.")
