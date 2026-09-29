from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

import models  # noqa: F401  (registra los modelos)
from routers import finca, ganado, tipo_animal

app = FastAPI(
    title="Sistema de Gestión de Ganado",
    description="API para administrar fincas, ganado y tipos de ganado",
    version="1.0.0",
)

app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # En producción, poner el dominio real
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(finca.router)
app.include_router(ganado.router)
app.include_router(tipo_animal.router)


@app.get("/")
def home(request: Request):
    return templates.TemplateResponse(
        "index.html",
        {"request": request, "mensaje": "Sistema funcionando"},
    )