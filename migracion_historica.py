import pandas as pd
from app.database.conexion import obtener_conexion

def migrar_datos():
    conexion = obtener_conexion()
    if not conexion:
        print("❌ No se pudo conectar a Supabase.")
        return

    cursor = conexion.cursor()
    print("🚀 Iniciando migración de datos históricos a Supabase...")

    try:
        print("Leyendo usuarios_historicos.csv...")
        df_usuarios = pd.read_csv('usuarios_historicos.csv')
        
        # EL TRUCO: Mapear el ID antiguo de SQL Server con el DNI (que nunca cambia)
        mapa_dni = df_usuarios.set_index('ID_Usuario')['DNI'].to_dict()
        
        for index, fila in df_usuarios.iterrows():
            cursor.execute("SELECT ID_Usuario FROM Usuarios WHERE DNI = %s", (str(fila['DNI']),))
            existe = cursor.fetchone()
            
            if not existe:
                cursor.execute("""
                    INSERT INTO Usuarios (ID_Rol, DNI, Nombre_Completo, Correo, PasswordHash, Estado, Telefono) 
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                """, (
                    fila['ID_Rol'], str(fila['DNI']), fila['Nombre_Completo'], 
                    fila['Correo'], fila['PasswordHash'], fila['Estado'], str(fila['Telefono'])
                ))
        print("✅ Usuarios verificados en la nube.")

        print("Leyendo vehiculos_historicos.csv...")
        df_vehiculos = pd.read_csv('vehiculos_historicos.csv')
        
        for index, fila in df_vehiculos.iterrows():
            # 1. Buscamos el DNI exacto que tenía este chofer en tu laptop
            dni_chofer = mapa_dni.get(fila['ID_Chofer'])
            
            if dni_chofer:
                # 2. Le consultamos a Supabase qué ID NUEVO le asignó a este DNI
                cursor.execute("SELECT ID_Usuario FROM Usuarios WHERE DNI = %s", (str(dni_chofer),))
                usuario_nube = cursor.fetchone()
                
                if usuario_nube:
                    # Extraemos el ID real generado en la nube (posición 0)
                    nuevo_id = usuario_nube[0] 
                    
                    cursor.execute("SELECT ID_Vehiculo FROM Vehiculos WHERE Placa = %s", (str(fila['Placa']),))
                    if not cursor.fetchone():
                        cursor.execute("""
                            INSERT INTO Vehiculos (ID_Chofer, Placa, Operativo, Latitud, Longitud) 
                            VALUES (%s, %s, %s, %s, %s)
                        """, (
                            nuevo_id, str(fila['Placa']), fila['Operativo'], 
                            fila['Latitud'], fila['Longitud']
                        ))
        print("✅ Vehículos migrados y enlazados con éxito.")

        conexion.commit()
        print("🎉 ¡MIGRACIÓN COMPLETADA! Todos tus datos están enlazados en la nube.")

    except Exception as e:
        conexion.rollback()
        print(f"❌ Error durante la migración: {e}")
    finally:
        conexion.close()

if __name__ == "__main__":
    migrar_datos()