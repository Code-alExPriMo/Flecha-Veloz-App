from fastapi import FastAPI, HTTPException, status, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
from app.database.conexion import obtener_conexion
from app.security.auth import verificar_password, encriptar_password
from app.rutas.chofer_api import router_chofer

app = FastAPI(title="API Flecha Veloz")
app.include_router(router_chofer)

# 1. Montamos la carpeta estática para que la web pueda leer el CSS y las imágenes
app.mount("/static", StaticFiles(directory="app/static"), name="static")

# 2. Configuramos el motor de plantillas apuntando a nuestra carpeta HTML
templates = Jinja2Templates(directory="app/templates")

# ==============================================================================
# MODELOS DE DATOS (PYDANTIC)
# ==============================================================================
class LoginRequest(BaseModel):
    dni: str
    password: str

class RegistroChoferRequest(BaseModel):
    dni: str
    nombre: str
    correo: str
    placa: str
    password: str

class EstadoVehiculoRequest(BaseModel):
    id_chofer: int
    operativo: int

class PerfilUpdateRequest(BaseModel):
    id_usuario: int
    nombre: str
    correo: str
    telefono: str

class CerrarCuentaRequest(BaseModel):
    id_usuario: int

# NUEVO: Modelo para que el Admin cambie el estado de un chofer
class CambiarEstadoRequest(BaseModel):
    id_usuario: int
    estado: int


# ==============================================================================
# RUTAS DE INTERFAZ GRÁFICA (PÁGINAS HTML)
# ==============================================================================
@app.get("/")
def cargar_interfaz_principal(request: Request):
    """Renderiza la pantalla gráfica de Login."""
    return templates.TemplateResponse(request=request, name="login.html")

@app.get("/dashboard")
def cargar_dashboard(request: Request):
    """Renderiza el panel de control principal post-login."""
    return templates.TemplateResponse(request=request, name="dashboard.html")

@app.get("/registro_chofer", response_class=HTMLResponse)
async def pagina_registro_chofer(request: Request):
    """Renderiza el formulario de alta de nuevos choferes."""
    return templates.TemplateResponse(request=request, name="registro_chofer.html")

@app.get("/panel_chofer", response_class=HTMLResponse)
async def pagina_panel_chofer(request: Request):
    """Renderiza el panel de control exclusivo para el conductor con su mapa."""
    return templates.TemplateResponse(request=request, name="panel_chofer.html")

@app.get("/central", response_class=HTMLResponse)
async def pagina_central(request: Request):
    """Renderiza la pantalla de monitoreo y despacho para Gerencia/Administración."""
    return templates.TemplateResponse(request=request, name="central.html")

@app.get("/reportes", response_class=HTMLResponse)
async def pagina_reportes(request: Request):
    """Renderiza la pantalla de Inteligencia de Negocios para Gerencia"""
    return templates.TemplateResponse(request=request, name="reportes.html")

@app.get("/ajustes", response_class=HTMLResponse)
async def pagina_ajustes(request: Request):
    """Renderiza la pantalla de configuración de perfil y seguridad."""
    return templates.TemplateResponse(request=request, name="ajustes.html")


# ==============================================================================
# ENDPOINTS DE API (LÓGICA DE NEGOCIO Y BASE DE DATOS)
# ==============================================================================
@app.post("/api/login")
def iniciar_sesion(credenciales: LoginRequest):
    """Endpoint para validar las credenciales del usuario."""
    conexion = obtener_conexion()
    if not conexion:
        raise HTTPException(status_code=500, detail="Error interno del servidor.")

    try:
        cursor = conexion.cursor()
        cursor.execute("""
            SELECT ID_Usuario, ID_Rol, PasswordHash, Estado, Nombre_Completo, Correo 
            FROM Usuarios WHERE DNI = ?
        """, (credenciales.dni,))
        usuario = cursor.fetchone()

        if not usuario:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Credenciales incorrectas")

        id_usuario, id_rol, hash_guardado, estado, nombre_completo, correo = usuario

        if not estado:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Usuario inactivo")

        if not verificar_password(credenciales.password, hash_guardado):
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Credenciales incorrectas")

        return {
            "mensaje": "Acceso concedido",
            "id_usuario": id_usuario,
            "id_rol": id_rol,
            "nombre": nombre_completo,
            "correo": correo
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        conexion.close()

@app.post("/api/registrar_chofer")
def api_registrar_chofer(datos: RegistroChoferRequest):
    """Endpoint para registrar un nuevo chofer y su vehículo."""
    conexion = obtener_conexion()
    if not conexion:
        raise HTTPException(status_code=500, detail="Error de conexión a la BD.")

    try:
        cursor = conexion.cursor()
        
        cursor.execute("SELECT ID_Usuario FROM Usuarios WHERE DNI = ?", (datos.dni,))
        if cursor.fetchone():
            raise HTTPException(status_code=400, detail="Este DNI ya está registrado.")

        hash_pass = encriptar_password(datos.password)
        
        cursor.execute("""
            INSERT INTO Usuarios (ID_Rol, DNI, Nombre_Completo, Correo, PasswordHash, Estado)
            OUTPUT INSERTED.ID_Usuario
            VALUES (3, ?, ?, ?, ?, 1)
        """, (datos.dni, datos.nombre, datos.correo, hash_pass))
        
        nuevo_id_usuario = cursor.fetchone()[0]

        cursor.execute("""
            INSERT INTO Vehiculos (ID_Chofer, Placa, Operativo)
            VALUES (?, ?, 0)
        """, (nuevo_id_usuario, datos.placa.upper()))

        conexion.commit()
        return {"mensaje": "Chofer y vehículo registrados con éxito", "id": nuevo_id_usuario}

    except Exception as e:
        conexion.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        conexion.close()

@app.get("/api/usuarios/perfil/{id_usuario}")
def obtener_perfil(id_usuario: int):
    """Obtiene los datos actuales del usuario para llenar el formulario."""
    conexion = obtener_conexion()
    try:
        cursor = conexion.cursor()
        cursor.execute("SELECT Nombre_Completo, Correo, DNI, Telefono FROM Usuarios WHERE ID_Usuario = ?", (id_usuario,))
        user = cursor.fetchone()
        if not user:
            raise HTTPException(status_code=404, detail="Usuario no encontrado")
        
        return {
            "nombre": user[0], 
            "correo": user[1], 
            "dni": user[2], 
            "telefono": user[3] if user[3] else "" 
        }
    finally:
        conexion.close()

@app.put("/api/usuarios/perfil")
def actualizar_perfil(datos: PerfilUpdateRequest):
    """Actualiza la información básica y el teléfono."""
    conexion = obtener_conexion()
    try:
        cursor = conexion.cursor()
        cursor.execute("""
            UPDATE Usuarios 
            SET Nombre_Completo = ?, Correo = ?, Telefono = ? 
            WHERE ID_Usuario = ?
        """, (datos.nombre, datos.correo, datos.telefono, datos.id_usuario))
        conexion.commit()
        return {"mensaje": "Perfil actualizado correctamente"}
    except Exception as e:
        conexion.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        conexion.close()

@app.put("/api/usuarios/cerrar_cuenta")
def cerrar_cuenta(datos: CerrarCuentaRequest):
    """Baja Lógica: Cambia el Estado a 0 (Inactivo)."""
    conexion = obtener_conexion()
    try:
        cursor = conexion.cursor()
        cursor.execute("UPDATE Usuarios SET Estado = 0 WHERE ID_Usuario = ?", (datos.id_usuario,))
        
        # Si es chofer, apagamos su taxi para que desaparezca del mapa
        cursor.execute("UPDATE Vehiculos SET Operativo = 0 WHERE ID_Chofer = ?", (datos.id_usuario,))
        conexion.commit()
        
        return {"mensaje": "Cuenta suspendida permanentemente"}
    except Exception as e:
        conexion.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        conexion.close()

# ==============================================================================
# NUEVOS ENDPOINTS DE GESTIÓN DE PERSONAL (GERENCIA)
# ==============================================================================
@app.get("/api/admin/choferes")
def listar_choferes_admin():
    """Obtiene la lista de todos los choferes para el panel gerencial."""
    conexion = obtener_conexion()
    try:
        cursor = conexion.cursor()
        cursor.execute("""
            SELECT u.ID_Usuario, u.Nombre_Completo, u.DNI, u.Correo, u.Telefono, u.Estado, v.Placa
            FROM Usuarios u
            LEFT JOIN Vehiculos v ON u.ID_Usuario = v.ID_Chofer
            WHERE u.ID_Rol = 3
            ORDER BY u.Estado DESC, u.Nombre_Completo ASC
        """)
        choferes = cursor.fetchall()
        return [
            {
                "id": c[0],
                "nombre": c[1],
                "dni": c[2],
                "correo": c[3],
                "telefono": c[4] if c[4] else "Sin registrar",
                "estado": c[5],
                "placa": c[6] if c[6] else "Sin vehículo"
            } for c in choferes
        ]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        conexion.close()

@app.put("/api/admin/choferes/estado")
def cambiar_estado_usuario(datos: CambiarEstadoRequest):
    """El Administrador suspende (0) o reactiva (1) a un chofer."""
    conexion = obtener_conexion()
    try:
        cursor = conexion.cursor()
        cursor.execute("UPDATE Usuarios SET Estado = ? WHERE ID_Usuario = ?", (datos.estado, datos.id_usuario))
        
        # Si lo suspendemos, también apagamos su vehículo por seguridad en el mapa
        if datos.estado == 0:
            cursor.execute("UPDATE Vehiculos SET Operativo = 0 WHERE ID_Chofer = ?", (datos.id_usuario,))
            
        conexion.commit()
        return {"mensaje": "Estado de la cuenta actualizado exitosamente."}
    except Exception as e:
        conexion.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        conexion.close()