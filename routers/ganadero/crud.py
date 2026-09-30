import os

import models
import storage
from fastapi import HTTPException, Request
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session


def error_integridad(
    e: IntegrityError,
    identificacion: str | None = None,
) -> HTTPException:
    codigo = getattr(e.orig, "pgcode", None)

    if codigo == "23505":
        return HTTPException(
            status_code=400,
            detail=f"La identificación '{identificacion}' ya existe en esa finca.",
        )

    if codigo == "23503":
        return HTTPException(
            status_code=400,
            detail="La finca o el tipo de animal no existe.",
        )

    if codigo == "23514":
        return HTTPException(
            status_code=400,
            detail="Datos inválidos: revisa el sexo y que la fecha de nacimiento no sea futura.",
        )

    return HTTPException(
        status_code=400,
        detail="Error de integridad de datos.",
    )


def obtener_ganado(db: Session, ganado_id: int):
    ganado = (
        db.query(models.Ganado)
        .filter(models.Ganado.id == ganado_id)
        .first()
    )

    if not ganado:
        raise HTTPException(
            status_code=404,
            detail="Ganado no encontrado",
        )

    return ganado


def listar_ganado(db: Session):
    return (
        db.query(models.Ganado)
        .order_by(models.Ganado.id)
        .all()
    )


def obtener_datos_registro(db: Session):
    fincas = db.query(models.Finca).all()

    tipos_animales = (
        db.query(models.TipoAnimal)
        .all()
    )

    hembras = (
        db.query(models.Ganado)
        .filter(models.Ganado.sexo == "Hembra")
        .order_by(models.Ganado.identificacion)
        .all()
    )

    machos = (
        db.query(models.Ganado)
        .filter(models.Ganado.sexo == "Macho")
        .order_by(models.Ganado.identificacion)
        .all()
    )

    return fincas, tipos_animales, hembras, machos


def obtener_datos_edicion(db: Session, ganado_id: int):
    ganado = obtener_ganado(db, ganado_id)

    fincas = db.query(models.Finca).all()

    tipos_animales = (
        db.query(models.TipoAnimal)
        .all()
    )

    hembras = (
        db.query(models.Ganado)
        .filter(
            models.Ganado.sexo == "Hembra",
            models.Ganado.id != ganado_id,
        )
        .order_by(models.Ganado.identificacion)
        .all()
    )

    machos = (
        db.query(models.Ganado)
        .filter(
            models.Ganado.sexo == "Macho",
            models.Ganado.id != ganado_id,
        )
        .order_by(models.Ganado.identificacion)
        .all()
    )

    return ganado, fincas, tipos_animales, hembras, machos


def crear_ganado(
    db: Session,
    identificacion: str,
    nombre: str | None,
    fecha_nacimiento,
    sexo: str,
    raza: str | None,
    estado: str,
    finca_id: int,
    tipo_animal_id: int,
    madre_id: int | None,
    padre_id: int | None,
    aplico_droga_nacimiento: str | None,
    foto,
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
        db.flush()
    except IntegrityError as e:
        db.rollback()
        raise error_integridad(e, identificacion)

    if aplico_droga_nacimiento and aplico_droga_nacimiento.strip():
        evento_nacimiento = models.EventoAnimal(
            animal_id=animal.id,
            tipo="tratamiento",
            descripcion=(
                "Tratamiento / Droga al nacer: "
                f"{aplico_droga_nacimiento.strip()}"
            ),
            fecha_evento=fecha_nacimiento,
        )

        db.add(evento_nacimiento)

    ruta_foto = None

    if foto and foto.filename:
        try:
            ruta_foto = storage.subir_foto(
                finca_id,
                animal.id,
                foto,
            )
        except ValueError as e:
            db.rollback()
            raise HTTPException(
                status_code=400,
                detail=str(e),
            )
        except Exception:
            db.rollback()
            raise HTTPException(
                status_code=502,
                detail="No se pudo subir la foto. Intenta de nuevo.",
            )

        animal.foto = await_storage_result(ruta_foto)

    try:
        db.commit()
    except Exception:
        db.rollback()
        storage.borrar_foto(ruta_foto)

        raise HTTPException(
            status_code=500,
            detail="No se pudo guardar el animal.",
        )

    db.refresh(animal)

    return animal


def await_storage_result(ruta):
    """
    Placeholder interno para mantener la asignación explícita.

    La función real de subida es async, por lo que crear_ganado()
    se ejecuta desde el router mediante crear_ganado_async().
    """
    return ruta


async def crear_ganado_async(
    db: Session,
    identificacion: str,
    nombre: str | None,
    fecha_nacimiento,
    sexo: str,
    raza: str | None,
    estado: str,
    finca_id: int,
    tipo_animal_id: int,
    madre_id: int | None,
    padre_id: int | None,
    aplico_droga_nacimiento: str | None,
    foto,
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
        db.flush()
    except IntegrityError as e:
        db.rollback()
        raise error_integridad(e, identificacion)

    if aplico_droga_nacimiento and aplico_droga_nacimiento.strip():
        evento_nacimiento = models.EventoAnimal(
            animal_id=animal.id,
            tipo="tratamiento",
            descripcion=(
                "Tratamiento / Droga al nacer: "
                f"{aplico_droga_nacimiento.strip()}"
            ),
            fecha_evento=fecha_nacimiento,
        )
        db.add(evento_nacimiento)

    ruta_foto = None

    if foto and foto.filename:
        try:
            ruta_foto = await storage.subir_foto(
                finca_id,
                animal.id,
                foto,
            )
        except ValueError as e:
            db.rollback()
            raise HTTPException(
                status_code=400,
                detail=str(e),
            )
        except Exception:
            db.rollback()
            raise HTTPException(
                status_code=502,
                detail="No se pudo subir la foto. Intenta de nuevo.",
            )

        animal.foto = ruta_foto

    try:
        db.commit()
    except Exception:
        db.rollback()

        if ruta_foto:
            storage.borrar_foto(ruta_foto)

        raise HTTPException(
            status_code=500,
            detail="No se pudo guardar el animal.",
        )

    db.refresh(animal)

    return animal


def eliminar_ganado(db: Session, ganado_id: int):
    ganado = obtener_ganado(db, ganado_id)

    ruta_foto = ganado.foto

    db.delete(ganado)
    db.commit()

    if ruta_foto:
        storage.borrar_foto(ruta_foto)

    return {"mensaje": "Ganado eliminado correctamente"}


async def cambiar_foto(
    db: Session,
    ganado_id: int,
    foto,
):
    ganado = obtener_ganado(db, ganado_id)

    try:
        nueva_ruta = await storage.subir_foto(
            ganado.finca_id,
            ganado.id,
            foto,
        )
    except ValueError as e:
        raise HTTPException(
            status_code=400,
            detail=str(e),
        )
    except Exception:
        raise HTTPException(
            status_code=502,
            detail="No se pudo subir la foto. Intenta de nuevo.",
        )

    ruta_anterior = ganado.foto
    ganado.foto = nueva_ruta

    try:
        db.commit()
    except Exception:
        db.rollback()
        storage.borrar_foto(nueva_ruta)

        raise HTTPException(
            status_code=500,
            detail="No se pudo guardar la foto.",
        )

    if ruta_anterior:
        storage.borrar_foto(ruta_anterior)

    db.refresh(ganado)

    return ganado


def quitar_foto(db: Session, ganado_id: int):
    ganado = obtener_ganado(db, ganado_id)

    ruta_foto = ganado.foto
    ganado.foto = None

    db.commit()

    if ruta_foto:
        storage.borrar_foto(ruta_foto)

    return {"mensaje": "Foto eliminada correctamente"}


def actualizar_ganado(
    db: Session,
    ganado_id: int,
    datos,
):
    ganado = obtener_ganado(db, ganado_id)

    for key, value in datos.model_dump().items():
        setattr(ganado, key, value)

    try:
        db.commit()
    except IntegrityError as e:
        db.rollback()
        raise error_integridad(
            e,
            datos.identificacion,
        )

    db.refresh(ganado)

    return ganado


def crear_evento_animal(
    db: Session,
    ganado_id: int,
    evento_in,
):
    animal = obtener_ganado(db, ganado_id)

    nuevo_evento = models.EventoAnimal(
        animal_id=animal.id,
        tipo=evento_in.tipo,
        descripcion=evento_in.descripcion,
        fecha_evento=evento_in.fecha_evento,
        proximo_control=evento_in.proximo_control,
    )

    db.add(nuevo_evento)
    db.commit()
    db.refresh(nuevo_evento)

    return nuevo_evento


def eliminar_evento_animal(
    db: Session,
    evento_id: int,
):
    evento = (
        db.query(models.EventoAnimal)
        .filter(models.EventoAnimal.id == evento_id)
        .first()
    )

    if not evento:
        raise HTTPException(
            status_code=404,
            detail="Evento no encontrado",
        )

    db.delete(evento)
    db.commit()

    return {"mensaje": "Evento eliminado correctamente"}


def obtener_ganado_por_codigo(db: Session, codigo):
    ganado = (
        db.query(models.Ganado)
        .filter(models.Ganado.codigo_publico == codigo)
        .first()
    )

    if not ganado:
        raise HTTPException(
            status_code=404,
            detail="Ficha no encontrada",
        )

    return ganado


def obtener_ancestros_set(animal, visitados=None):
    if visitados is None:
        visitados = set()

    if not animal:
        return visitados

    if animal.madre_id and animal.madre_id not in visitados:
        visitados.add(animal.madre_id)

        if animal.madre:
            obtener_ancestros_set(
                animal.madre,
                visitados,
            )

    if animal.padre_id and animal.padre_id not in visitados:
        visitados.add(animal.padre_id)

        if animal.padre:
            obtener_ancestros_set(
                animal.padre,
                visitados,
            )

    return visitados


def obtener_datos_genealogia(
    db: Session,
    ganado_id: int,
):
    ganado = obtener_ganado(db, ganado_id)

    sexo_opuesto = (
        "Macho"
        if ganado.sexo == "Hembra"
        else "Hembra"
    )

    candidatos = (
        db.query(models.Ganado)
        .filter(
            models.Ganado.sexo == sexo_opuesto,
            models.Ganado.id != ganado_id,
        )
        .order_by(models.Ganado.identificacion)
        .all()
    )

    return ganado, candidatos


def verificar_cruce(
    db: Session,
    ganado_id: int,
    pareja_id: int,
):
    a1 = obtener_ganado(db, ganado_id)
    a2 = obtener_ganado(db, pareja_id)

    if a1.id == a2.id:
        return {
            "compatible": False,
            "motivo": "Es el mismo animal.",
        }

    if a1.sexo == a2.sexo:
        return {
            "compatible": False,
            "motivo": (
                f"Ambos animales son del mismo sexo "
                f"({a1.sexo})."
            ),
        }

    if a1.madre_id == a2.id or a1.padre_id == a2.id:
        return {
            "compatible": False,
            "motivo": (
                "🔴 CONSANGUINIDAD DIRECTA: "
                f"El animal {a2.identificacion} es progenitor "
                f"directo de {a1.identificacion}."
            ),
        }

    if a2.madre_id == a1.id or a2.padre_id == a1.id:
        return {
            "compatible": False,
            "motivo": (
                "🔴 CONSANGUINIDAD DIRECTA: "
                f"El animal {a1.identificacion} es progenitor "
                f"directo de {a2.identificacion}."
            ),
        }

    if a1.madre_id and a1.madre_id == a2.madre_id:
        madre_name = (
            a1.madre.identificacion
            if a1.madre
            else f"ID {a1.madre_id}"
        )

        return {
            "compatible": False,
            "motivo": (
                "🔴 HERMANOS DE MADRE: "
                f"Comparten la misma madre ({madre_name})."
            ),
        }

    if a1.padre_id and a1.padre_id == a2.padre_id:
        padre_name = (
            a1.padre.identificacion
            if a1.padre
            else f"ID {a1.padre_id}"
        )

        return {
            "compatible": False,
            "motivo": (
                "🔴 HERMANOS DE PADRE: "
                f"Comparten el mismo padre ({padre_name})."
            ),
        }

    ancestros_a1 = obtener_ancestros_set(a1)
    ancestros_a2 = obtener_ancestros_set(a2)

    if a1.id in ancestros_a2:
        return {
            "compatible": False,
            "motivo": (
                "🔴 ANCESTRO DIRECTO: "
                f"El animal {a1.identificacion} es ancestro "
                f"de {a2.identificacion}."
            ),
        }

    if a2.id in ancestros_a1:
        return {
            "compatible": False,
            "motivo": (
                "🔴 ANCESTRO DIRECTO: "
                f"El animal {a2.identificacion} es ancestro "
                f"de {a1.identificacion}."
            ),
        }

    comunes = ancestros_a1.intersection(ancestros_a2)

    if comunes:
        animales_comunes = (
            db.query(models.Ganado)
            .filter(models.Ganado.id.in_(comunes))
            .all()
        )

        nombres_comunes = ", ".join(
            f"{animal.identificacion} "
            f"({animal.nombre or 'sin nombre'})"
            for animal in animales_comunes
        )

        return {
            "compatible": False,
            "motivo": (
                "⚠️ CONSANGUINIDAD DETECTADA: "
                "Comparten ancestros en común "
                f"({nombres_comunes}). "
                "Riesgo de endogamia."
            ),
        }

    return {
        "compatible": True,
        "motivo": (
            "✅ CRUCE COMPATIBLE: "
            "No se detectaron ancestros en común "
            "(madres, padres o abuelos)."
        ),
    }


def existe_animal_por_codigo(db: Session, codigo):
    existe = (
        db.query(models.Ganado.id)
        .filter(models.Ganado.codigo_publico == codigo)
        .first()
    )

    if not existe:
        raise HTTPException(
            status_code=404,
            detail="Animal no encontrado",
        )


def obtener_ganado_para_qr(db: Session, ganado_id: int):
    return obtener_ganado(db, ganado_id)


def listar_para_qr(db: Session):
    return (
        db.query(models.Ganado)
        .order_by(models.Ganado.identificacion)
        .all()
    )


def base_url(request: Request) -> str:
    return (
        os.getenv("BASE_URL")
        or str(request.base_url)
    ).rstrip("/")