from sqlalchemy import text
from database import engine

with engine.connect() as conn:
    print(conn.execute(text("select nombre from tipos_animales order by id")).fetchall())