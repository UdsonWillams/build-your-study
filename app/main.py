"""Aplicação FastAPI: serve o site (Jinja2) e a API de progresso.

Roda com:  uvicorn app.main:app --reload
"""

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from .database import get_db
from .models import DeletedRoadmap, Module, Progress, Roadmap, Topic
from .schemas import ProgressIn, ProgressOut
from .seed import seed

BASE_DIR = Path(__file__).resolve().parent.parent
WEB_DIR = BASE_DIR / "web"


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Cria as tabelas e carrega o conteúdo dos JSONs na inicialização.
    seed()
    yield


app = FastAPI(title="BuildYourStudy", lifespan=lifespan)
app.mount("/static", StaticFiles(directory=WEB_DIR / "static"), name="static")
templates = Jinja2Templates(directory=str(WEB_DIR / "templates"))


def _completed_topic_ids(db: Session) -> set[int]:
    return set(db.scalars(select(Progress.topic_id)).all())


@app.get("/", response_class=HTMLResponse)
def index(request: Request, db: Session = Depends(get_db)):
    roadmaps = db.scalars(
        select(Roadmap)
        .where(Roadmap.active.is_(True))
        .options(selectinload(Roadmap.modules).selectinload(Module.topics))
        .order_by(Roadmap.position)
    ).all()
    completed = _completed_topic_ids(db)

    # Lista de categorias únicas
    categories = list(dict.fromkeys([rm.category for rm in roadmaps if rm.category]))

    # Progresso individual e global
    stats = {}
    total_all_topics = 0
    total_done_topics = 0

    for rm in roadmaps:
        topics = [t for m in rm.modules for t in m.topics]
        done = sum(1 for t in topics if t.id in completed)
        total_all_topics += len(topics)
        total_done_topics += done
        stats[rm.id] = {
            "total": len(topics),
            "done": done,
            "pct": round(100 * done / len(topics)) if topics else 0,
        }

    global_pct = (
        round(100 * total_done_topics / total_all_topics)
        if total_all_topics > 0
        else 0
    )

    return templates.TemplateResponse(
        "index.html",
        {
            "request": request,
            "roadmaps": roadmaps,
            "completed": completed,
            "stats": stats,
            "categories": categories,
            "total_all_topics": total_all_topics,
            "total_done_topics": total_done_topics,
            "global_pct": global_pct,
        },
    )


@app.get("/roadmap/{slug}", response_class=HTMLResponse)
def roadmap_page(slug: str, request: Request, db: Session = Depends(get_db)):
    roadmap = db.scalar(
        select(Roadmap)
        .where(Roadmap.slug == slug)
        .options(selectinload(Roadmap.modules).selectinload(Module.topics))
    )
    if roadmap is None:
        raise HTTPException(status_code=404, detail="Curso não encontrado")

    completed = _completed_topic_ids(db)
    topics = [t for m in roadmap.modules for t in m.topics]
    done = sum(1 for t in topics if t.id in completed)
    pct = round(100 * done / len(topics)) if topics else 0

    return templates.TemplateResponse(
        "roadmap.html",
        {
            "request": request,
            "roadmap": roadmap,
            "completed": completed,
            "done": done,
            "total": len(topics),
            "pct": pct,
        },
    )


@app.get("/lixeira", response_class=HTMLResponse)
def lixeira_page(request: Request, db: Session = Depends(get_db)):
    roadmaps = db.scalars(
        select(Roadmap)
        .where(Roadmap.active.is_(False))
        .options(selectinload(Roadmap.modules).selectinload(Module.topics))
        .order_by(Roadmap.position)
    ).all()

    stats = {
        rm.id: {"total": sum(len(m.topics) for m in rm.modules)}
        for rm in roadmaps
    }

    return templates.TemplateResponse(
        "lixeira.html",
        {"request": request, "roadmaps": roadmaps, "stats": stats},
    )


@app.post("/roadmap/{slug}/disable")
def disable_roadmap(slug: str, db: Session = Depends(get_db)):
    roadmap = db.scalar(select(Roadmap).where(Roadmap.slug == slug))
    if roadmap is None:
        raise HTTPException(status_code=404, detail="Curso não encontrado")
    roadmap.active = False
    db.commit()
    return RedirectResponse(url="/", status_code=303)


@app.post("/roadmap/{slug}/enable")
def enable_roadmap(slug: str, db: Session = Depends(get_db)):
    roadmap = db.scalar(select(Roadmap).where(Roadmap.slug == slug))
    if roadmap is None:
        raise HTTPException(status_code=404, detail="Curso não encontrado")
    roadmap.active = True
    db.commit()
    return RedirectResponse(url="/", status_code=303)


@app.post("/roadmap/{slug}/delete")
def delete_roadmap(slug: str, db: Session = Depends(get_db)):
    roadmap = db.scalar(select(Roadmap).where(Roadmap.slug == slug))
    if roadmap is None:
        raise HTTPException(status_code=404, detail="Curso não encontrado")
    if roadmap.active:
        raise HTTPException(
            status_code=400,
            detail="Desative o curso antes de excluí-lo definitivamente.",
        )
    db.delete(roadmap)
    if db.scalar(select(DeletedRoadmap).where(DeletedRoadmap.slug == slug)) is None:
        db.add(DeletedRoadmap(slug=slug))
    db.commit()
    return RedirectResponse(url="/lixeira", status_code=303)


@app.get("/topic/{slug}", response_class=HTMLResponse)
def topic_page(slug: str, request: Request, db: Session = Depends(get_db)):
    topic = db.scalar(
        select(Topic)
        .where(Topic.slug == slug)
        .options(selectinload(Topic.exercises))
    )
    if topic is None:
        raise HTTPException(status_code=404, detail="Tópico não encontrado")

    # Navegação: tópicos do mesmo roadmap em ordem (módulo, depois posição).
    roadmap = topic.module.roadmap
    ordered = [t for m in roadmap.modules for t in m.topics]
    idx = next(i for i, t in enumerate(ordered) if t.id == topic.id)
    prev_topic = ordered[idx - 1] if idx > 0 else None
    next_topic = ordered[idx + 1] if idx < len(ordered) - 1 else None

    completed = _completed_topic_ids(db)

    return templates.TemplateResponse(
        "topic.html",
        {
            "request": request,
            "topic": topic,
            "module": topic.module,
            "roadmap": roadmap,
            "prev_topic": prev_topic,
            "next_topic": next_topic,
            "is_done": topic.id in completed,
        },
    )


@app.get("/api/progress", response_model=ProgressOut)
def get_progress(db: Session = Depends(get_db)):
    return ProgressOut(completed_topic_ids=sorted(_completed_topic_ids(db)))


@app.post("/api/progress", response_model=ProgressOut)
def mark_progress(payload: ProgressIn, db: Session = Depends(get_db)):
    topic = db.get(Topic, payload.topic_id)
    if topic is None:
        raise HTTPException(status_code=404, detail="Tópico não encontrado")

    existing = db.scalar(select(Progress).where(Progress.topic_id == topic.id))
    if existing is None:
        db.add(Progress(topic_id=topic.id))
        db.commit()

    return ProgressOut(completed_topic_ids=sorted(_completed_topic_ids(db)))


@app.delete("/api/progress/{topic_id}", response_model=ProgressOut)
def unmark_progress(topic_id: int, db: Session = Depends(get_db)):
    existing = db.scalar(select(Progress).where(Progress.topic_id == topic_id))
    if existing is not None:
        db.delete(existing)
        db.commit()
    return ProgressOut(completed_topic_ids=sorted(_completed_topic_ids(db)))
