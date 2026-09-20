import pyodbc
def obtener_conexion():
    try:
        #cadena dde conexión
        conexion=pyodbc.connect(
            "DRIVER={ODBC Driver 17 for SQL Server};"
            "SERVER=.;"
            "DATABASE=FlechaVeloz;"
            "Trusted_Connection=yes;"
        )
        return conexion
    except Exception as e:
        #En producción esto iría a un archivo log , por ahora lo imprimimos
        print(f"Error crítico al conectar a la base de datos:{e}")
        return None