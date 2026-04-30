from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from tax_compliance_radar.api.audit_router import router as audit_router
from tax_compliance_radar.api.qa_router import router as qa_router
from tax_compliance_radar.config import settings
from tax_compliance_radar.services.db import initialize_database

app = FastAPI(title=settings.app_name)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def on_startup() -> None:
    initialize_database()


@app.get("/api/v1/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


app.include_router(qa_router)
app.include_router(audit_router)
