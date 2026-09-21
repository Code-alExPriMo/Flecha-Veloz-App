import psycopg2
from psycopg2.extras import NamedTupleCursor
import re

def obtener_conexion():
    # URL de Supabase
    DATABASE_URL = "postgresql://postgres.fgqyfihrmukrjrbjznhj:UCDwcXNUovr0u30V@aws-0-sa-east-1.pooler.supabase.com:6543/postgres"
    
    try:
        conexion = psycopg2.connect(DATABASE_URL, cursor_factory=NamedTupleCursor)
        return ConexionWrapper(conexion)
    except Exception as e:
        print(f"Error conectando a Supabase: {e}")
        return None

class CursorWrapper:
    def __init__(self, cursor, conexion):
        self.cursor = cursor
        self.conexion = conexion

    def execute(self, query, vars=None):
        # 1. Quitar sintaxis de SQL Server (corchetes y dbo)
        query_pg = query.replace('?', '%s')
        query_pg = query_pg.replace('[dbo].', '').replace('[dbo]', '')
        query_pg = query_pg.replace('[', '').replace(']', '')
        
        # 2. TRADUCCIÓN INTELIGENTE DEL RETURNING (Lo mueve al final)
        match = re.search(r'OUTPUT\s+INSERTED\.([a-zA-Z0-9_]+)', query_pg, flags=re.IGNORECASE)
        if match:
            columna_id = match.group(1) # Extrae ID_Usuario, ID_Viaje, etc.
            # Borra la frase original de donde esté
            query_pg = re.sub(r'OUTPUT\s+INSERTED\.[a-zA-Z0-9_]+', '', query_pg, flags=re.IGNORECASE)
            # La pega al final de la consulta
            query_pg = f"{query_pg.strip()} RETURNING {columna_id}"
        
        # 3. Funciones y fechas
        query_pg = query_pg.replace('ISNULL(', 'COALESCE(')
        query_pg = query_pg.replace('GETDATE()', 'CURRENT_TIMESTAMP')
        query_pg = query_pg.replace('CAST(Fecha_Registro AS DATE) = CAST(CURRENT_TIMESTAMP AS DATE)', 'DATE(Fecha_Registro) = CURRENT_DATE')
        query_pg = query_pg.replace('CAST(Fecha_Registro AS DATE) = CAST(DATEADD(day, -1, CURRENT_TIMESTAMP) AS DATE)', "DATE(Fecha_Registro) = CURRENT_DATE - INTERVAL '1 day'")
        query_pg = query_pg.replace('CAST(Fecha_Registro AS DATE) >= CAST(DATEADD(day, -7, CURRENT_TIMESTAMP) AS DATE)', "DATE(Fecha_Registro) >= CURRENT_DATE - INTERVAL '7 days'")
        
        query_pg = query_pg.replace('MONTH(Fecha_Registro)', 'EXTRACT(MONTH FROM Fecha_Registro)')
        query_pg = query_pg.replace('YEAR(Fecha_Registro)', 'EXTRACT(YEAR FROM Fecha_Registro)')
        query_pg = query_pg.replace('MONTH(CURRENT_TIMESTAMP)', 'EXTRACT(MONTH FROM CURRENT_DATE)')
        query_pg = query_pg.replace('YEAR(CURRENT_TIMESTAMP)', 'EXTRACT(YEAR FROM CURRENT_DATE)')
        query_pg = query_pg.replace('MONTH(v.Fecha_Registro)', 'EXTRACT(MONTH FROM v.Fecha_Registro)')
        query_pg = query_pg.replace('YEAR(v.Fecha_Registro)', 'EXTRACT(YEAR FROM v.Fecha_Registro)')

        # Formatear parámetros
        if vars is not None:
            if not isinstance(vars, (tuple, list)):
                vars = (vars,)
            self.cursor.execute(query_pg, vars)
        else:
            self.cursor.execute(query_pg)
            
        return self

    def fetchone(self): return self.cursor.fetchone()
    def fetchall(self): return self.cursor.fetchall()
    def commit(self): self.conexion.commit()
    def close(self): self.cursor.close()

class ConexionWrapper:
    def __init__(self, conexion):
        self.conexion = conexion

    def cursor(self): return CursorWrapper(self.conexion.cursor(), self.conexion)
    def commit(self): self.conexion.commit()
    def rollback(self): self.conexion.rollback()
    def close(self): self.conexion.close()