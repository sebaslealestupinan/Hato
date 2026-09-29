import uuid
from datetime import date
from sqlalchemy import (Column, BigInteger, String, Text, Numeric, Date, DateTime,
                        ForeignKey, UniqueConstraint, Uuid, func)
from sqlalchemy.orm import relationship
from database import Base


class Finca(Base):
    __tablename__ = "fincas"

    id = Column(BigInteger, primary_key=True)
    nombre = Column(String(100), nullable=False)
    tamaño = Column("tamano_hectareas", Numeric(10, 2), nullable=False)
    ubicacion = Column(String(200), nullable=False)
    fecha_creacion = Column("created_at", DateTime(timezone=True), server_default=func.now())

    ganados = relationship("Ganado", back_populates="finca", cascade="all, delete-orphan")


class TipoAnimal(Base):
    __tablename__ = "tipos_animales"

    id = Column(BigInteger, primary_key=True)
    nombre = Column(String(60), unique=True, nullable=False)

    ganados = relationship("Ganado", back_populates="tipo_animal")


class Ganado(Base):
    __tablename__ = "animales"
    __table_args__ = (UniqueConstraint("finca_id", "identificacion"),)

    id = Column(BigInteger, primary_key=True)
    codigo_publico = Column(Uuid, default=uuid.uuid4, unique=True, nullable=False)
    identificacion = Column(String(50), nullable=False)
    nombre = Column(String(100), nullable=True)
    sexo = Column(String(10), nullable=False)
    raza = Column(String(80), nullable=True)
    fecha_nacimiento = Column(Date, nullable=False)
    finca_id = Column(BigInteger, ForeignKey("fincas.id"), nullable=False)
    tipo_animal_id = Column(BigInteger, ForeignKey("tipos_animales.id"), nullable=False)
    foto = Column("foto_path", Text, nullable=True)
    fecha_registro = Column("created_at", DateTime(timezone=True), server_default=func.now())

    finca = relationship("Finca", back_populates="ganados")
    tipo_animal = relationship("TipoAnimal", back_populates="ganados")
    eventos = relationship("EventoAnimal", back_populates="animal", cascade="all, delete-orphan")

    @property
    def edad(self):
        """Edad en meses, calculada desde la fecha de nacimiento."""
        n = self.fecha_nacimiento
        if not n:
            return None
        hoy = date.today()
        return (hoy.year - n.year) * 12 + (hoy.month - n.month) - (1 if hoy.day < n.day else 0)


class EventoAnimal(Base):
    __tablename__ = "eventos_animal"

    id = Column(BigInteger, primary_key=True)
    animal_id = Column(BigInteger, ForeignKey("animales.id"), nullable=False)
    tipo = Column(String, nullable=False)
    descripcion = Column(Text, nullable=False)
    fecha_evento = Column(Date, nullable=False, server_default=func.current_date())
    proximo_control = Column(Date, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    animal = relationship("Ganado", back_populates="eventos")