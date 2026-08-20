"""
ComfortNet backend — FastAPI application entrypoint.

STATUS: IMPLEMENTED (software foundation). No physical hardware, MQTT
broker, or AI model is connected. See /health for a live status summary
and README.md for how to run this.
"""
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import CORS_ALLOW_ORIGINS
from app.database import Base, engine, SessionLocal
from app.models import Campus, Node
from app.routers import health, auth, campuses, nodes, telemetry, alerts, analytics, demo, ml as ml_router

DEMO_CAMPUS_ID = "demo-campus"
DEMO_NODE_IDS = ["tree-01", "tree-02", "tree-03"]


def seed_demo_data():
    """
    DEVELOPMENT CHOICE: seeds one demo campus and three demo nodes
    (tree-01..tree-03, matching the prototype's tree naming) if the
    database is empty, so the API and simulator have something to work
    with immediately on first run. This is demo convenience, not a claim
    that any of these nodes are real or installed (install_status stays
    "proposed").
    """
    db = SessionLocal()
    try:
        if not db.query(Campus).filter(Campus.id == DEMO_CAMPUS_ID).first():
            db.add(Campus(id=DEMO_CAMPUS_ID, name="Demo Campus", contact_org="Hackathon Demo"))
            db.commit()

        for node_id in DEMO_NODE_IDS:
            if not db.query(Node).filter(Node.id == node_id).first():
                db.add(Node(
                    id=node_id,
                    campus_id=DEMO_CAMPUS_ID,
                    tree_reference=node_id.replace("-", " ").title(),
                    install_status="proposed",
                ))
        db.commit()
    finally:
        db.close()


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    seed_demo_data()
    yield


app = FastAPI(
    title="ComfortNet Backend (Phase 2 Software Foundation)",
    description=(
        "Software foundation for ComfortNet. No physical hardware or MQTT broker is "
        "implemented. All telemetry is simulated. A predictive-maintenance ML prototype "
        "exists (RandomForestClassifier, trained on synthetic telemetry only — see /ml/status) "
        "and is NOT field-validated or production-ready. "
        "See /health for live status and the project README for full disclosure."
    ),
    version="0.2.0-hackathon",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ALLOW_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router)
app.include_router(auth.router)
app.include_router(campuses.router)
app.include_router(nodes.router)
app.include_router(telemetry.router)
app.include_router(alerts.router)
app.include_router(analytics.router)
app.include_router(demo.router)
app.include_router(ml_router.router)


@app.get("/")
def root():
    return {
        "project": "ComfortNet",
        "status": "Phase 2 software foundation — no hardware, no MQTT broker; ML prototype exists but is synthetic-data-only, not field-validated",
        "docs": "/docs",
        "health": "/health",
        "demo_campus_id": DEMO_CAMPUS_ID,
        "demo_node_ids": DEMO_NODE_IDS,
    }
