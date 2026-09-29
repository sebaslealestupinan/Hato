from typing import Optional
from datetime import date
from uuid import UUID
from pydantic import BaseModel, ConfigDict


# ------ Finca ------
class FincaBase(BaseModel):
    nombre: str
    tamaño: float  # hectáreas
    ubicacion: str

class FincaCreate(FincaBase):
    pass

class Finca(FincaBase):
    id: int
    model_config = ConfigDict(from_attributes=True)


# ------ Evento Animal ------
class EventoAnimalBase(BaseModel):
    tipo: str  # 'vacunacion', 'desparasitacion', 'tratamiento', 'parto', 'inseminacion', 'novedad'
    descripcion: str
    fecha_evento: date
    proximo_control: Optional[date] = None

class EventoAnimalCreate(EventoAnimalBase):
    pass

class EventoAnimal(EventoAnimalBase):
    id: int
    animal_id: int
    model_config = ConfigDict(from_attributes=True)


# ------ Ganado ------
class GanadoBase(BaseModel):
    identificacion: str
    nombre: Optional[str] = None
    fecha_nacimiento: date
    sexo: str
    raza: Optional[str] = None
    estado: str = "Activo"
    finca_id: int
    tipo_animal_id: int
    madre_id: Optional[int] = None
    padre_id: Optional[int] = None

class GanadoCreate(GanadoBase):
    aplico_droga_nacimiento: Optional[str] = None

class Ganado(GanadoBase):
    id: int
    codigo_publico: UUID
    edad: Optional[int] = None       # meses, calculada
    foto: Optional[str] = None
    eventos: list[EventoAnimal] = []
    model_config = ConfigDict(from_attributes=True)

class GanadoUpdateData(BaseModel):
    identificacion: str
    nombre: Optional[str] = None
    fecha_nacimiento: date
    sexo: str
    raza: Optional[str] = None
    estado: str = "Activo"
    finca_id: int
    tipo_animal_id: int
    madre_id: Optional[int] = None
    padre_id: Optional[int] = None


# ------ Tipo de animal ------
class TipoAnimalBase(BaseModel):
    nombre: str

class TipoAnimalCreate(TipoAnimalBase):
    pass

class TipoAnimal(TipoAnimalBase):
    id: int
    model_config = ConfigDict(from_attributes=True)