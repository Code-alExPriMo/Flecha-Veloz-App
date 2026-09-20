import bcrypt

def encriptar_password(password_plana: str) -> str:
    """Convierte una contraseña de texto plano en un hash irreversible."""
    sal = bcrypt.gensalt()
    hash_password = bcrypt.hashpw(password_plana.encode('utf-8'), sal)
    return hash_password.decode('utf-8')

def verificar_password(password_plana: str, hash_guardado: str) -> bool:
    """Compara el intento de login con el hash guardado en la base de datos."""
    return bcrypt.checkpw(
        password_plana.encode('utf-8'), 
        hash_guardado.encode('utf-8')
    )