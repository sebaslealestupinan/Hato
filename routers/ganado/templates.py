import io
import qrcode

from fastapi import APIRouter, Depends, Request, HTTPException
from fastapi.responses import StreamingResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

import storage

from database import get_db
from . import crud


router = APIRouter(prefix="/ganado", tags=["Ganado - Vistas"])

templates = Jinja2Templates(directory="templates")
templates.env.globals["foto_url"] = storage.url_foto


@router.get("/registrar")
async def registrar_ganado_view(
    request: Request,
    db: Session = Depends(get_db),
):
    (
        fincas,
        tipos_animales,
        hembras,
        machos,
    ) = crud.obtener_datos_registro(db)

    return templates.TemplateResponse(
        "ganado/registrar_ganado.html",
        {
            "request": request,
            "fincas": fincas,
            "tipos_animales": tipos_animales,
            "hembras": hembras,
            "machos": machos,
        },
    )


@router.get("/lista")
async def listar_ganado_view(
    request: Request,
    db: Session = Depends(get_db),
):
    ganados = crud.listar_ganado(db)

    fincas = db.query(crud.models.Finca).all()
    tipos_animales = db.query(crud.models.TipoAnimal).all()

    return templates.TemplateResponse(
        "ganado/lista_ganado.html",
        {
            "request": request,
            "ganados": ganados,
            "fincas": fincas,
            "tipos_animales": tipos_animales,
        },
    )


@router.get("/editar/{ganado_id}")
async def editar_ganado_view(
    ganado_id: int,
    request: Request,
    db: Session = Depends(get_db),
):
    (
        ganado,
        fincas,
        tipos_animales,
        hembras,
        machos,
    ) = crud.obtener_datos_edicion(
        db,
        ganado_id,
    )

    return templates.TemplateResponse(
        "ganado/editar_ganado.html",
        {
            "request": request,
            "ganado": ganado,
            "fincas": fincas,
            "tipos_animales": tipos_animales,
            "hembras": hembras,
            "machos": machos,
        },
    )


@router.get("/detalle/{ganado_id}")
async def detalle_ganado_view(
    ganado_id: int,
    request: Request,
    db: Session = Depends(get_db),
):
    ganado = crud.obtener_ganado(
        db,
        ganado_id,
    )

    return templates.TemplateResponse(
        "ganado/detalle_ganado.html",
        {
            "request": request,
            "ganado": ganado,
        },
    )


@router.get("/ficha/{codigo}")
async def ficha_publica_view(
    codigo,
    request: Request,
    db: Session = Depends(get_db),
):
    ganado = crud.obtener_ganado_por_codigo(
        db,
        codigo,
    )

    return templates.TemplateResponse(
        "ganado/ficha_publica.html",
        {
            "request": request,
            "ganado": ganado,
        },
    )


@router.get("/qr/{codigo}")
def qr_animal(
    codigo,
    request: Request,
    db: Session = Depends(get_db),
):
    crud.existe_animal_por_codigo(
        db,
        codigo,
    )

    url = (
        f"{crud.base_url(request)}"
        f"/ganado/ficha/{codigo}"
    )

    img = qrcode.make(
        url,
        box_size=10,
        border=2,
    )

    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)

    return StreamingResponse(
        buf,
        media_type="image/png",
    )


@router.get("/genealogia/{ganado_id}")
async def genealogia_view(
    ganado_id: int,
    request: Request,
    db: Session = Depends(get_db),
):
    ganado, candidatos = crud.obtener_datos_genealogia(
        db,
        ganado_id,
    )

    return templates.TemplateResponse(
        "ganado/genealogia.html",
        {
            "request": request,
            "ganado": ganado,
            "candidatos": candidatos,
        },
    )


@router.get("/imprimir-qr/{ganado_id}")
async def imprimir_qr_view(
    ganado_id: int,
    request: Request,
    db: Session = Depends(get_db),
):
    ganado = crud.obtener_ganado(
        db,
        ganado_id,
    )

    return templates.TemplateResponse(
        "ganado/imprimir_qr.html",
        {
            "request": request,
            "ganado": ganado,
        },
    )


@router.get("/imprimir-qr-lote")
async def imprimir_qr_lote_view(
    request: Request,
    db: Session = Depends(get_db),
):
    ganados = crud.listar_para_qr(db)

    return templates.TemplateResponse(
        "ganado/imprimir_qr_lote.html",
        {
            "request": request,
            "ganados": ganados,
        },
    )