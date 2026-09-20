from faker import Faker
import bcrypt
from app.database.conexion import obtener_conexion

# Configuramos Faker para que genere nombres en español
fake = Faker('es_ES')

def encriptar_password(password: str) -> str:
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password.encode('utf-8'), salt)
    return hashed.decode('utf-8')

def poblar_usuarios(cantidad_choferes=40, cantidad_administrativos=10):
    conexion = obtener_conexion()
    if not conexion:
        print("Error: No hay conexión a SQL Server.")
        return

    cursor = conexion.cursor()
    password_global = encriptar_password("Flecha2026*") # Contraseña por defecto para todos
    
    print("Generando datos. Por favor espera...")

    try:
        # 1. Asegurar que los roles existan (Requerimiento de Negocio)
        cursor.execute("IF NOT EXISTS (SELECT 1 FROM Roles WHERE ID_Rol = 1) INSERT INTO Roles (ID_Rol, Nombre_Rol) VALUES (1, 'Gerente')")
        cursor.execute("IF NOT EXISTS (SELECT 1 FROM Roles WHERE ID_Rol = 2) INSERT INTO Roles (ID_Rol, Nombre_Rol) VALUES (2, 'Administrativo')")
        cursor.execute("IF NOT EXISTS (SELECT 1 FROM Roles WHERE ID_Rol = 3) INSERT INTO Roles (ID_Rol, Nombre_Rol) VALUES (3, 'Chofer')")

        # 2. Generar Administrativos (Call Center / Recepción)
        for _ in range(cantidad_administrativos):
            dni = str(fake.random_number(digits=8, fix_len=True))
            nombre = fake.name()
            email = fake.email()
            cursor.execute("""
                INSERT INTO Usuarios (DNI, Nombre_Completo, Correo, PasswordHash, ID_Rol, Estado)
                VALUES (?, ?, ?, ?, 2, 1)
            """, (dni, nombre, email, password_global))

        # 3. Generar Choferes (Flota)
        for _ in range(cantidad_choferes):
            dni = str(fake.random_number(digits=8, fix_len=True))
            nombre = fake.name()
            email = fake.email()
            cursor.execute("""
                INSERT INTO Usuarios (DNI, Nombre_Completo, Correo, PasswordHash, ID_Rol, Estado)
                VALUES (?, ?, ?, ?, 3, 1)
            """, (dni, nombre, email, password_global))

        conexion.commit()
        print(f"¡Éxito! Se crearon {cantidad_administrativos} administrativos y {cantidad_choferes} choferes.")
        print("Todos tienen la contraseña temporal: Flecha2026*")

    except Exception as e:
        print(f"Error en la inserción: {e}")
        conexion.rollback()
    finally:
        conexion.close()

if __name__ == "__main__":
    poblar_usuarios()