import cloudinary
import cloudinary.uploader
from dotenv import load_dotenv
import os

load_dotenv()

cloudinary.config(
    cloud_name=os.getenv("CLOUDINARY_CLOUD_NAME"),
    api_key=os.getenv("CLOUDINARY_API_KEY"),
    api_secret=os.getenv("CLOUDINARY_API_SECRET"),
    secure=True,
)

resultado = cloudinary.uploader.upload(
    "static/img/fondo.png",
    public_id="pruebas/hato/fondo",
    resource_type="image",
)

print("Subida exitosa")
print("Public ID:", resultado["public_id"])
print("URL:", resultado["secure_url"])