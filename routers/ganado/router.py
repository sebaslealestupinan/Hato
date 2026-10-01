from datetime import date

from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    UploadFile,
)
from sqlalchemy.orm import Session

import schemas

from database import get_db
from . import crud
from .templates import router as templates_router


router = APIRouter()

router.include_router(templates_router)


# ============================================================
#                    API GANADO
# ============================================================

@router.post(
    "/ganado/api/",
    response_model=schemas.Ganado,
)
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
    return await crud.crear_ganado_async(
        db=db,
        identificacion=identificacion,
        nombre=nombre,
        fecha_nacimiento=fecha_nacimiento,
        sexo=sexo,
        raza=raza,
        estado=estado,
        finca_id=finca_id,
        tipo_animal_id=tipo_animal_id,
        madre_id=madre_id,
        padre_id=padre_id,
        aplico_droga_nacimiento=aplico_droga_nacimiento,
        foto=foto,
    )


@router.get(
    "/ganado/api/",
    response_model=list[schemas.Ganado],
)
def listar_ganado_api(
    db: Session = Depends(get_db),
):
    return crud.listar_ganado(db)


@router.delete("/ganado/api/{ganado_id}")
def eliminar_ganado(
    ganado_id: int,
    db: Session = Depends(get_db),
):
    return crud.eliminar_ganado(
        db,
        ganado_id,
    )


@router.put(
    "/ganado/api/{ganado_id}/foto",
    response_model=schemas.Ganado,
)
async def cambiar_foto(
    ganado_id: int,
    foto: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    return await crud.cambiar_foto(
        db,
        ganado_id,
        foto,
    )


@router.delete("/ganado/api/{ganado_id}/foto")
def quitar_foto(
    ganado_id: int,
    db: Session = Depends(get_db),
):
    return crud.quitar_foto(
        db,
        ganado_id,
    )


@router.put(
    "/ganado/{ganado_id}",
    response_model=schemas.Ganado,
)
def actualizar_ganado(
    ganado_id: int,
    datos: schemas.GanadoUpdateData,
    db: Session = Depends(get_db),
):
    return crud.actualizar_ganado(
        db,
        ganado_id,
        datos,
    )


# ============================================================
#              EVENTOS / HISTORIAL SANITARIO
# ============================================================

@router.post(
    "/ganado/api/{ganado_id}/eventos",
    response_model=schemas.EventoAnimal,
)
def crear_evento_animal(
    ganado_id: int,
    evento_in: schemas.EventoAnimalCreate,
    db: Session = Depends(get_db),
):
    return crud.crear_evento_animal(
        db,
        ganado_id,
        evento_in,
    )


@router.delete("/ganado/api/eventos/{evento_id}")
def eliminar_evento_animal(
    evento_id: int,
    db: Session = Depends(get_db),
):
    return crud.eliminar_evento_animal(
        db,
        evento_id,
    )


# ============================================================
#              GENEALOGÍA / CONSANGUINIDAD
# ============================================================

@router.get(
    "/ganado/api/{ganado_id}/verificar-cruce/{pareja_id}"
)
def verificar_cruce_api(
    ganado_id: int,
    pareja_id: int,
    db: Session = Depends(get_db),
):
    return crud.verificar_cruce(
        db,
        ganado_id,
        pareja_id,
    )