from datetime import date

from fastapi import APIRouter, Request, Depends, HTTPException, UploadFile, File, Form
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


# ============================================================
#                    VISTAS (HTML)
# ============================================================

@router.get("/registrar")
async def registrar_ganado_view(request: Request, db: Session = Depends(get_db)):
    fincas = db.query(models.Finca).all()
    tipos_animales = db.query(models.TipoAnimal).all()
    return templates.TemplateResponse(
        "ganado/registrar_ganado.html",
        {"request": request, "fincas": fincas, "tipos_animales": tipos_animales},
    )


@router.get("/lista")
async def listar_ganado_view(request: Request, db: Session = Depends(get_db)):
    ganados = db.query(models.Ganado).order_by(models.Ganado.id).all()
    return templates.TemplateResponse(
        "ganado/lista_ganado.html", {"request": request, "ganados": ganados}
    )


@router.get("/editar/{ganado_id}")
async def editar_ganado_view(ganado_id: int, request: Request, db: Session = Depends(get_db)):
    ganado = db.query(models.Ganado).filter(models.Ganado.id == ganado_id).first()
    if not ganado:
        raise HTTPException(status_code=404, detail="Ganado no encontrado")
    fincas = db.query(models.Finca).all()
    tipos_animales = db.query(models.TipoAnimal).all()
    return templates.TemplateResponse(
        "ganado/editar_ganado.html",
        {"request": request, "ganado": ganado, "fincas": fincas, "tipos_animales": tipos_animales},
    )


@router.get("/detalle/{ganado_id}")
async def detalle_ganado_view(ganado_id: int, request: Request, db: Session = Depends(get_db)):
    ganado = db.query(models.Ganado).filter(models.Ganado.id == ganado_id).first()
    if not ganado:
        raise HTTPException(status_code=404, detail="Ganado no encontrado")
    return templates.TemplateResponse(
        "ganado/detalle_ganado.html", {"request": request, "ganado": ganado}
    )


# ============================================================
#                    API (JSON / FormData)
# ============================================================

@router.post("/api/", response_model=schemas.Ganado)
async def crear_ganado(
    identificacion: str = Form(...),
    nombre: str | None = Form(None),
    fecha_nacimiento: date = Form(...),
    sexo: str = Form(...),
    finca_id: int = Form(...),
    tipo_animal_id: int = Form(...),
    edad: int | None = Form(None),  # ya no se guarda: se calcula desde la fecha de nacimiento
    foto: UploadFile | None = File(None),
    db: Session = Depends(get_db),
):
    identificacion = identificacion.strip()
    animal = models.Ganado(
        identificacion=identificacion,
        nombre=(nombre or "").strip() or None,
        fecha_nacimiento=fecha_nacimiento,
        sexo=sexo,
        finca_id=finca_id,
        tipo_animal_id=tipo_animal_id,
    )
    db.add(animal)
    try:
        db.flush()  # obtiene animal.id sin confirmar todavía
    except IntegrityError as e:
        db.rollback()
        raise _error_integridad(e, identificacion)

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