import io
import os
from datetime import date
from uuid import UUID

import qrcode
from fastapi import APIRouter, Request, Depends, HTTPException, UploadFile, File, Form
from fastapi.responses import StreamingResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

import models, schemas, storage
from database import get_db

templates = Jinja2Templates(directory="templates")
templates.env.globals["foto_url"] = storage.url_foto  # se usa en los HTML

router = APIRouter(prefix="/ganado", tags=["Ganado"])


def _error_integridad(e: IntegrityError, identificacion: str | None = None) -> HTTPException:
    codigo = getattr(e.orig, "pgcode", None)
    if codigo == "23505":
        return HTTPException(400, f"La identificación '{identificacion}' ya existe en esa finca.")
    if codigo == "23503":
        return HTTPException(400, "La finca o el tipo de animal no existe.")
    if codigo == "23514":
        return HTTPException(400, "Datos inválidos: revisa el sexo y que la fecha de nacimiento no sea futura.")
    return HTTPException(400, "Error de integridad de datos.")


def _base_url(request: Request) -> str:
    """URL pública que va dentro del QR. En Render se define BASE_URL en las variables de entorno."""
    return (os.getenv("BASE_URL") or str(request.base_url)).rstrip("/")


# ============================================================
#                    VISTAS (HTML)
# ============================================================

@router.get("/registrar")
async def registrar_ganado_view(request: Request, db: Session = Depends(get_db)):
    fincas = db.query(models.Finca).all()
    tipos_animales = db.query(models.TipoAnimal).all()
    hembras = db.query(models.Ganado).filter(models.Ganado.sexo == "Hembra").order_by(models.Ganado.identificacion).all()
    machos = db.query(models.Ganado).filter(models.Ganado.sexo == "Macho").order_by(models.Ganado.identificacion).all()
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
async def listar_ganado_view(request: Request, db: Session = Depends(get_db)):
    ganados = db.query(models.Ganado).order_by(models.Ganado.id).all()
    fincas = db.query(models.Finca).all()
    tipos_animales = db.query(models.TipoAnimal).all()
    return templates.TemplateResponse(
        "ganado/lista_ganado.html",
        {"request": request, "ganados": ganados, "fincas": fincas, "tipos_animales": tipos_animales}
    )


@router.get("/editar/{ganado_id}")
async def editar_ganado_view(ganado_id: int, request: Request, db: Session = Depends(get_db)):
    ganado = db.query(models.Ganado).filter(models.Ganado.id == ganado_id).first()
    if not ganado:
        raise HTTPException(status_code=404, detail="Ganado no encontrado")
    fincas = db.query(models.Finca).all()
    tipos_animales = db.query(models.TipoAnimal).all()
    hembras = db.query(models.Ganado).filter(models.Ganado.sexo == "Hembra", models.Ganado.id != ganado_id).order_by(models.Ganado.identificacion).all()
    machos = db.query(models.Ganado).filter(models.Ganado.sexo == "Macho", models.Ganado.id != ganado_id).order_by(models.Ganado.identificacion).all()
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
async def detalle_ganado_view(ganado_id: int, request: Request, db: Session = Depends(get_db)):
    ganado = db.query(models.Ganado).filter(models.Ganado.id == ganado_id).first()
    if not ganado:
        raise HTTPException(status_code=404, detail="Ganado no encontrado")
    return templates.TemplateResponse(
        "ganado/detalle_ganado.html", {"request": request, "ganado": ganado}
    )


@router.get("/ficha/{codigo}")
async def ficha_publica_view(codigo: UUID, request: Request, db: Session = Depends(get_db)):
    """Ficha que se abre al escanear el QR. Se busca por codigo_publico, no por id."""
    ganado = db.query(models.Ganado).filter(models.Ganado.codigo_publico == codigo).first()
    if not ganado:
        raise HTTPException(status_code=404, detail="Ficha no encontrada")
    return templates.TemplateResponse(
        "ganado/ficha_publica.html", {"request": request, "ganado": ganado}
    )


@router.get("/qr/{codigo}")
def qr_animal(codigo: UUID, request: Request, db: Session = Depends(get_db)):
    """Imagen PNG del QR de un animal."""
    existe = db.query(models.Ganado.id).filter(models.Ganado.codigo_publico == codigo).first()
    if not existe:
        raise HTTPException(status_code=404, detail="Animal no encontrado")

    url = f"{_base_url(request)}/ganado/ficha/{codigo}"
    img = qrcode.make(url, box_size=10, border=2)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    return StreamingResponse(buf, media_type="image/png")


# ============================================================
#                    API (JSON / FormData)
# ============================================================

@router.post("/api/", response_model=schemas.Ganado)
async def crear_ganado(
    identificacion: str = Form(...),
    nombre: str | None = Form(None),
    fecha_nacimiento: date = Form(...),
    sexo: str = Form(...),
    raza: str | None = Form(None),
    estado: str = Form("Activo"),
    finca_id: int = Form(...),
    tipo_animal_id: int = Form(...),
    madre_id: int | None = Form(None),
    padre_id: int | None = Form(None),
    aplico_droga_nacimiento: str | None = Form(None),
    foto: UploadFile | None = File(None),
    db: Session = Depends(get_db),
):
    identificacion = identificacion.strip()
    animal = models.Ganado(
        identificacion=identificacion,
        nombre=(nombre or "").strip() or None,
        fecha_nacimiento=fecha_nacimiento,
        sexo=sexo,
        raza=(raza or "").strip() or None,
        estado=estado or "Activo",
        finca_id=finca_id,
        tipo_animal_id=tipo_animal_id,
        madre_id=madre_id if madre_id and madre_id > 0 else None,
        padre_id=padre_id if padre_id and padre_id > 0 else None,
    )
    db.add(animal)
    try:
        db.flush()  # obtiene animal.id sin confirmar todavía
    except IntegrityError as e:
        db.rollback()
        raise _error_integridad(e, identificacion)

    # Si se especificó droga o medicamento al nacer, se crea un evento automático
    if aplico_droga_nacimiento and aplico_droga_nacimiento.strip():
        evento_nacimiento = models.EventoAnimal(
            animal_id=animal.id,
            tipo="tratamiento",
            descripcion=f"Tratamiento / Droga al nacer: {aplico_droga_nacimiento.strip()}",
            fecha_evento=fecha_nacimiento,
        )
        db.add(evento_nacimiento)

    ruta = None
    if foto and foto.filename:
        try:
            ruta = await storage.subir_foto(finca_id, animal.id, foto)
        except ValueError as e:
            db.rollback()
            raise HTTPException(400, str(e))
        except Exception:
            db.rollback()
            raise HTTPException(502, "No se pudo subir la foto. Intenta de nuevo.")
        animal.foto = ruta

    try:
        db.commit()
    except Exception:
        db.rollback()
        storage.borrar_foto(ruta)
        raise HTTPException(500, "No se pudo guardar el animal.")

    db.refresh(animal)
    return animal


@router.get("/api/", response_model=list[schemas.Ganado])
def listar_ganado_api(db: Session = Depends(get_db)):
    return db.query(models.Ganado).order_by(models.Ganado.id).all()


@router.delete("/api/{ganado_id}")
def eliminar_ganado(ganado_id: int, db: Session = Depends(get_db)):
    ganado = db.query(models.Ganado).filter(models.Ganado.id == ganado_id).first()
    if not ganado:
        raise HTTPException(status_code=404, detail="Ganado no encontrado")

    ruta = ganado.foto
    db.delete(ganado)
    db.commit()
    storage.borrar_foto(ruta)  # borra también la foto del bucket
    return {"mensaje": "Ganado eliminado correctamente"}

@router.put("/api/{ganado_id}/foto", response_model=schemas.Ganado)
async def cambiar_foto(
    ganado_id: int,
    foto: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    """Sube una foto nueva y reemplaza la anterior (también en el bucket)."""
    ganado = db.query(models.Ganado).filter(models.Ganado.id == ganado_id).first()
    if not ganado:
        raise HTTPException(status_code=404, detail="Ganado no encontrado")

    try:
        nueva_ruta = await storage.subir_foto(ganado.finca_id, ganado.id, foto)
    except ValueError as e:
        raise HTTPException(400, str(e))
    except Exception:
        raise HTTPException(502, "No se pudo subir la foto. Intenta de nuevo.")

    ruta_anterior = ganado.foto
    ganado.foto = nueva_ruta
    try:
        db.commit()
    except Exception:
        db.rollback()
        storage.borrar_foto(nueva_ruta)
        raise HTTPException(500, "No se pudo guardar la foto.")

    storage.borrar_foto(ruta_anterior)
    db.refresh(ganado)
    return ganado


@router.delete("/api/{ganado_id}/foto")
def quitar_foto(ganado_id: int, db: Session = Depends(get_db)):
    """Quita la foto del animal y la borra del bucket."""
    ganado = db.query(models.Ganado).filter(models.Ganado.id == ganado_id).first()
    if not ganado:
        raise HTTPException(status_code=404, detail="Ganado no encontrado")

    ruta = ganado.foto
    ganado.foto = None
    db.commit()
    storage.borrar_foto(ruta)
    return {"mensaje": "Foto eliminada correctamente"}

    
@router.put("/{ganado_id}", response_model=schemas.Ganado)
def actualizar_ganado(ganado_id: int, datos: schemas.GanadoUpdateData, db: Session = Depends(get_db)):
    ganado = db.query(models.Ganado).filter(models.Ganado.id == ganado_id).first()
    if not ganado:
        raise HTTPException(status_code=404, detail="Registro de ganado no encontrado")

    for key, value in datos.dict().items():
        setattr(ganado, key, value)

    try:
        db.commit()
    except IntegrityError as e:
        db.rollback()
        raise _error_integridad(e, datos.identificacion)

    db.refresh(ganado)
    return ganado