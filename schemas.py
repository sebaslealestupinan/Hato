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


# ------ Ganado ------
class GanadoBase(BaseModel):
    identificacion: str
    nombre: Optional[str] = None
    fecha_nacimiento: date
    sexo: str
    finca_id: int
    tipo_animal_id: int

class GanadoCreate(GanadoBase):
    pass

class Ganado(GanadoBase):
    id: int
    codigo_publico: UUID
    edad: Optional[int] = None       # meses, calculada
    foto: Optional[str] = None
    model_config = ConfigDict(from_attributes=True)

class GanadoUpdateData(BaseModel):
    identificacion: str
    nombre: Optional[str] = None
    fecha_nacimiento: date
    sexo: str
    finca_id: int
    tipo_animal_id: int


# ------ Tipo de animal ------
class TipoAnimalBase(BaseModel):
    nombre: str

class TipoAnimalCreate(TipoAnimalBase):
    pass

class TipoAnimal(TipoAnimalBase):
    id: int
    model_config = ConfigDict(from_attributes=True)