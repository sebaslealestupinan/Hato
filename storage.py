import os
import uuid
from dotenv import load_dotenv
from supabase import create_client

load_dotenv()

_client = create_client(os.environ["SUPABASE_URL"], os.environ["SUPABASE_SERVICE_KEY"])
BUCKET = os.getenv("SUPABASE_BUCKET", "fotos-animales")

ALLOWED = {"image/jpeg": "jpg", "image/png": "png", "image/webp": "webp"}
MAX_BYTES = 5 * 1024 * 1024  # 5 MB


async def subir_foto(finca_id: int, animal_id: int, archivo) -> str:
    """Sube la foto al bucket y devuelve la RUTA (se guarda en animales.foto_path)."""
    if archivo.content_type not in ALLOWED:
        raise ValueError("Formato no permitido (usa JPG, PNG o WEBP).")
    contenido = await archivo.read()
    if len(contenido) > MAX_BYTES:
        raise ValueError("La foto supera los 5 MB.")

    ruta = f"{finca_id}/{animal_id}/{uuid.uuid4().hex}.{ALLOWED[archivo.content_type]}"
    _client.storage.from_(BUCKET).upload(
        ruta, contenido, {"content-type": archivo.content_type}
    )
    return ruta


def url_foto(ruta: str | None, segundos: int = 3600) -> str | None:
    """URL temporal firmada para mostrar la foto en el HTML."""
    if not ruta:
        return None
    try:
        res = _client.storage.from_(BUCKET).create_signed_url(ruta, segundos)
        return res.get("signedURL") or res.get("signedUrl") or res.get("signed_url")
    except Exception:
        return None


def borrar_foto(ruta: str | None):
    if not ruta:
        return
    try:
        _client.storage.from_(BUCKET).remove([ruta])
    except Exception:
        pass