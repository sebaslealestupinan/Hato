import os
import uuid

import cloudinary
import cloudinary.uploader
from dotenv import load_dotenv

load_dotenv()


cloudinary.config(
    cloud_name=os.getenv("CLOUDINARY_CLOUD_NAME"),
    api_key=os.getenv("CLOUDINARY_API_KEY"),
    api_secret=os.getenv("CLOUDINARY_API_SECRET"),
    secure=True,
)


ALLOWED = {
    "image/jpeg": "jpg",
    "image/png": "png",
    "image/webp": "webp",
}

MAX_BYTES = 5 * 1024 * 1024


async def subir_foto(finca_id: int, animal_id: int, archivo) -> str:
    if archivo.content_type not in ALLOWED:
        raise ValueError("Formato no permitido (usa JPG, PNG o WEBP).")

    contenido = await archivo.read()

    if len(contenido) > MAX_BYTES:
        raise ValueError("La foto supera los 5 MB.")

    public_id = f"ganado/{finca_id}/{animal_id}/{uuid.uuid4().hex}"

    resultado = cloudinary.uploader.upload(
        contenido,
        public_id=public_id,
        resource_type="image",
    )

    return resultado["public_id"]


def url_foto(public_id: str | None) -> str | None:
    if not public_id:
        return None

    return cloudinary.CloudinaryImage(public_id).build_url(
        secure=True
    )


def borrar_foto(public_id: str | None):
    if not public_id:
        return

    cloudinary.uploader.destroy(
        public_id,
        resource_type="image",
    )