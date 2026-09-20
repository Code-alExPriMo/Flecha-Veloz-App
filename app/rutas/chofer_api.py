from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from app.database.conexion import obtener_conexion

# APIRouter es como un mini-FastAPI dedicado solo a este subsistema
router_chofer = APIRouter()

# ==============================================================================
# MODELOS DE DATOS PYDANTIC
# ==============================================================================
class EstadoVehiculoRequest(BaseModel):
    id_chofer: int
    operativo: int

class ViajeRequest(BaseModel):
    id_chofer: int
    nombre_pasajero: str
    origen: str
    destino: str
    tarifa: float
    origen_lat: float = 0.0  
    origen_lng: float = 0.0  
    destino_lat: float = 0.0
    destino_lng: float = 0.0

class CompletarViajeRequest(BaseModel):
    id_viaje: int
    id_chofer: int

class RechazarViajeRequest(BaseModel):
    id_viaje: int
    id_chofer: int

class RetiroRequest(BaseModel):
    id_chofer: int
    monto: float   


# ==============================================================================
# ENDPOINTS DE VEHÍCULOS Y ESTADO
# ==============================================================================
@router_chofer.get("/api/vehiculo/{id_chofer}")
def obtener_vehiculo(id_chofer: int):
    conexion = obtener_conexion()
    try:
        cursor = conexion.cursor()
        cursor.execute("SELECT Placa, Operativo FROM Vehiculos WHERE ID_Chofer = ?", (id_chofer,))
        vehiculo = cursor.fetchone()
        if not vehiculo:
            raise HTTPException(status_code=404, detail="Vehículo no encontrado")
        return {"placa": vehiculo[0], "operativo": vehiculo[1]}
    finally:
        conexion.close()

@router_chofer.put("/api/vehiculo/estado")
def actualizar_estado(datos: EstadoVehiculoRequest):
    conexion = obtener_conexion()
    try:
        cursor = conexion.cursor()
        cursor.execute("UPDATE Vehiculos SET Operativo = ? WHERE ID_Chofer = ?", (datos.operativo, datos.id_chofer))
        conexion.commit()
        return {"mensaje": "Estado actualizado"}
    finally:
        conexion.close()

@router_chofer.get("/api/vehiculos/todos")
def obtener_toda_la_flota():
    conexion = obtener_conexion()
    try:
        cursor = conexion.cursor()
        cursor.execute("""
            SELECT v.ID_Vehiculo, v.Placa, u.Nombre_Completo, v.Operativo, 
                   v.Latitud, v.Longitud, u.ID_Usuario, u.ID_Rol
            FROM Vehiculos v
            INNER JOIN Usuarios u ON v.ID_Chofer = u.ID_Usuario
            WHERE u.ID_Rol = 3
        """)
        vehiculos = cursor.fetchall()
        return [
            {
                "id_vehiculo": v[0],
                "placa": v[1],
                "nombre": v[2],
                "operativo": v[3],
                "lat": float(v[4]) if v[4] is not None else None,
                "lng": float(v[5]) if v[5] is not None else None,
                "id_chofer": v[6]
            } for v in vehiculos
        ]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        conexion.close()


# ==============================================================================
# ENDPOINTS DE VIAJES Y OPERACIONES
# ==============================================================================
@router_chofer.post("/api/viajes/asignar")
def asignar_viaje(datos: ViajeRequest):
    conexion = obtener_conexion()
    try:
        cursor = conexion.cursor()
        cursor.execute("""
            INSERT INTO Viajes (ID_Chofer, Nombre_Pasajero, Origen, Destino, Tarifa, 
                                Origen_Lat, Origen_Lng, Destino_Lat, Destino_Lng, Estado)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'En Curso')
        """, (datos.id_chofer, datos.nombre_pasajero, datos.origen, datos.destino, datos.tarifa, 
              datos.origen_lat, datos.origen_lng, datos.destino_lat, datos.destino_lng))
        
        cursor.execute("UPDATE Vehiculos SET Operativo = 0 WHERE ID_Chofer = ?", (datos.id_chofer,))
        conexion.commit()
        return {"mensaje": "Viaje asignado correctamente."}
    except Exception as e:
        conexion.rollback()
        raise HTTPException(status_code=400, detail="Error al procesar el viaje")
    finally:
        conexion.close()

@router_chofer.get("/api/viajes/actual/{id_chofer}")
def obtener_viaje_actual(id_chofer: int):
    conexion = obtener_conexion()
    try:
        cursor = conexion.cursor()
        cursor.execute("""
            SELECT ID_Viaje, Nombre_Pasajero, Origen, Destino, Tarifa, 
                   Origen_Lat, Origen_Lng, Destino_Lat, Destino_Lng 
            FROM Viajes 
            WHERE ID_Chofer = ? AND Estado = 'En Curso'
        """, (id_chofer,))
        viaje = cursor.fetchone()
        
        if viaje:
            return {
                "id_viaje": viaje[0],
                "pasajero": viaje[1],
                "origen": viaje[2],
                "destino": viaje[3],
                "tarifa": viaje[4],
                "origen_lat": viaje[5],
                "origen_lng": viaje[6],
                "destino_lat": viaje[7],
                "destino_lng": viaje[8]
            }
        return {"mensaje": "Sin viajes"}
    finally:
        conexion.close()

@router_chofer.post("/api/viajes/completar")
def completar_viaje(datos: CompletarViajeRequest):
    conexion = obtener_conexion()
    try:
        cursor = conexion.cursor()
        
        cursor.execute("SELECT Destino_Lat, Destino_Lng FROM Viajes WHERE ID_Viaje = ?", (datos.id_viaje,))
        destino = cursor.fetchone()
        if not destino:
            raise HTTPException(status_code=404, detail="Viaje no encontrado")
            
        lat, lng = destino[0], destino[1]
        
        # Marcamos el viaje como completado (AQUÍ ES DONDE EL DINERO SE HACE REALIDAD)
        cursor.execute("UPDATE Viajes SET Estado = 'Completado' WHERE ID_Viaje = ?", (datos.id_viaje,))
        
        cursor.execute("""
            UPDATE Vehiculos 
            SET Operativo = 1, Latitud = ?, Longitud = ? 
            WHERE ID_Chofer = ?
        """, (lat, lng, datos.id_chofer))
        
        conexion.commit()
        return {"mensaje": "Viaje completado"}
    except Exception as e:
        conexion.rollback()
        raise HTTPException(status_code=400, detail="Error al completar")
    finally:
        conexion.close()

@router_chofer.post("/api/viajes/rechazar")
def rechazar_viaje(datos: RechazarViajeRequest):
    conexion = obtener_conexion()
    try:
        cursor = conexion.cursor()
        cursor.execute("UPDATE Viajes SET Estado = 'Cancelado' WHERE ID_Viaje = ?", (datos.id_viaje,))
        cursor.execute("UPDATE Vehiculos SET Operativo = 1 WHERE ID_Chofer = ?", (datos.id_chofer,))
        conexion.commit()
        return {"mensaje": "Viaje rechazado"}
    except Exception as e:
        conexion.rollback()
        raise HTTPException(status_code=400, detail="Error al rechazar")
    finally:
        conexion.close()


# ==============================================================================
# ENDPOINTS FINANCIEROS (SISTEMA DE LIBRO MAYOR SEGURO)
# ==============================================================================
@router_chofer.get("/api/chofer/ganancias/{id_chofer}")
def obtener_ganancias_chofer(id_chofer: int):
    """Calcula el Saldo Disponible: (Total Ganado) - (Total Retirado) con doble blindaje"""
    conexion = obtener_conexion()
    try:
        cursor = conexion.cursor()
        
        # 1. Total ganado
        cursor.execute("SELECT ISNULL(SUM(Tarifa), 0) FROM Viajes WHERE ID_Chofer = ? AND Estado = 'Completado'", (id_chofer,))
        resultado_ganado = cursor.fetchone()
        total_ganado = float(resultado_ganado[0]) if resultado_ganado and resultado_ganado[0] is not None else 0.0
        
        # 2. Total retirado
        cursor.execute("SELECT ISNULL(SUM(Monto), 0) FROM Retiros WHERE ID_Chofer = ?", (id_chofer,))
        resultado_retirado = cursor.fetchone()
        total_retirado = float(resultado_retirado[0]) if resultado_retirado and resultado_retirado[0] is not None else 0.0
        
        # 3. Saldo real
        saldo_disponible = total_ganado - total_retirado
        
        return {
            "ganancias_hoy": float(saldo_disponible), 
            "ganancias_totales": float(total_ganado)
        }
    except Exception as e:
        print(f"Error en financiero: {e}")
        return {"ganancias_hoy": 0.0, "ganancias_totales": 0.0}
    finally:
        conexion.close()


@router_chofer.post("/api/chofer/retirar")
def retirar_fondos(datos: RetiroRequest):
    """Registra el retiro parcial o total en la base de datos"""
    conexion = obtener_conexion()
    try:
        cursor = conexion.cursor()
        
        cursor.execute("SELECT ISNULL(SUM(Tarifa), 0) FROM Viajes WHERE ID_Chofer = ? AND Estado = 'Completado'", (datos.id_chofer,))
        resultado_ganado = cursor.fetchone()
        total_ganado = float(resultado_ganado[0]) if resultado_ganado else 0.0
        
        cursor.execute("SELECT ISNULL(SUM(Monto), 0) FROM Retiros WHERE ID_Chofer = ?", (datos.id_chofer,))
        resultado_retirado = cursor.fetchone()
        total_retirado = float(resultado_retirado[0]) if resultado_retirado else 0.0
        
        saldo_actual = total_ganado - total_retirado
        
        if datos.monto <= 0 or datos.monto > saldo_actual:
            raise HTTPException(status_code=400, detail="Monto inválido o saldo insuficiente")

        cursor.execute("INSERT INTO Retiros (ID_Chofer, Monto) VALUES (?, ?)", (datos.id_chofer, datos.monto))
        conexion.commit()
        
        return {"mensaje": f"Retiro de S/ {datos.monto} procesado"}
    except HTTPException as he:
        conexion.rollback()
        raise he
    except Exception as e:
        conexion.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        conexion.close()


# ==============================================================================
# ENDPOINTS DE REPORTES Y KPIs
# ==============================================================================
@router_chofer.get("/api/reportes/resumen")
def obtener_resumen_reportes(rango: str = "hoy"):
    filtro_fecha = "CAST(Fecha_Registro AS DATE) = CAST(GETDATE() AS DATE)"
    if rango == "ayer":
        filtro_fecha = "CAST(Fecha_Registro AS DATE) = CAST(DATEADD(day, -1, GETDATE()) AS DATE)"
    elif rango == "semana":
        filtro_fecha = "CAST(Fecha_Registro AS DATE) >= CAST(DATEADD(day, -7, GETDATE()) AS DATE)"
    elif rango == "mes":
        filtro_fecha = "MONTH(Fecha_Registro) = MONTH(GETDATE()) AND YEAR(Fecha_Registro) = YEAR(GETDATE())"
    elif rango == "total":
        filtro_fecha = "1=1"

    conexion = obtener_conexion()
    try:
        cursor = conexion.cursor()
        
        cursor.execute(f"SELECT ISNULL(SUM(Tarifa), 0) FROM Viajes WHERE Estado = 'Completado' AND {filtro_fecha}")
        ganancias = cursor.fetchone()[0]
        
        cursor.execute(f"SELECT COUNT(*) FROM Viajes WHERE Estado = 'Completado' AND {filtro_fecha}")
        completados = cursor.fetchone()[0]
        
        cursor.execute(f"SELECT COUNT(*) FROM Viajes WHERE Estado = 'Cancelado' AND {filtro_fecha}")
        cancelados = cursor.fetchone()[0]
        
        return {
            "ganancias_hoy": float(ganancias),
            "viajes_completados": completados,
            "viajes_cancelados": cancelados
        }
    finally:
        conexion.close()

@router_chofer.get("/api/reportes/ranking")
def obtener_ranking_choferes(rango: str = "hoy"):
    filtro_fecha = "CAST(v.Fecha_Registro AS DATE) = CAST(GETDATE() AS DATE)"
    if rango == "ayer": 
        filtro_fecha = "CAST(v.Fecha_Registro AS DATE) = CAST(DATEADD(day, -1, GETDATE()) AS DATE)"
    elif rango == "semana": 
        filtro_fecha = "CAST(v.Fecha_Registro AS DATE) >= CAST(DATEADD(day, -7, GETDATE()) AS DATE)"
    elif rango == "mes": 
        filtro_fecha = "MONTH(v.Fecha_Registro) = MONTH(GETDATE()) AND YEAR(v.Fecha_Registro) = YEAR(GETDATE())"
    elif rango == "total": 
        filtro_fecha = "1=1"

    conexion = obtener_conexion()
    try:
        cursor = conexion.cursor()
        cursor.execute(f"""
            SELECT u.ID_Usuario, u.Nombre_Completo, u.DNI, u.Correo,
                   ISNULL(COUNT(v.ID_Viaje), 0) as Total_Viajes,
                   ISNULL(SUM(v.Tarifa), 0) as Recaudado,
                   veh.Placa, veh.Operativo
            FROM Usuarios u
            LEFT JOIN Vehiculos veh ON u.ID_Usuario = veh.ID_Chofer
            LEFT JOIN Viajes v ON u.ID_Usuario = v.ID_Chofer 
                               AND v.Estado = 'Completado' 
                               AND {filtro_fecha}
            WHERE u.ID_Rol = 3
            GROUP BY u.ID_Usuario, u.Nombre_Completo, u.DNI, u.Correo, veh.Placa, veh.Operativo
            ORDER BY Recaudado DESC, Total_Viajes DESC, u.Nombre_Completo ASC
        """)
        ranking = cursor.fetchall()
        return [{
            "id": r[0], "nombre": r[1], "dni": r[2], "correo": r[3],
            "viajes": r[4], "recaudado": float(r[5]),
            "placa": r[6] if r[6] else "Sin Vehículo", "operativo": r[7] if r[7] is not None else 0
        } for r in ranking]
    finally:
        conexion.close()