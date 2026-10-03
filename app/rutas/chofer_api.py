from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from app.database.conexion import obtener_conexion

# APIRouter dedicado al subsistema operativo, financiero y de reportes
router_chofer = APIRouter()

# ==============================================================================
# MEMORIA DE CONFIGURACIÓN COMERCIAL (HU-08: TARIFAS, PROMOS Y COMISIÓN APP)
# ==============================================================================
CONFIG_COMERCIAL = {
    "tarifa_base": 5.00,
    "costo_km": 2.50,
    "promo_pct": 0.0,
    "comision_pct": 20.0  # Por defecto 20% pertenece a Flecha Veloz y 80% al Chofer
}

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

class LiquidarChoferRequest(BaseModel):
    id_chofer: int
    comision_pct: float = 20.0

class ConfigComercialRequest(BaseModel):
    tarifa_base: float
    costo_km: float
    promo_pct: float
    comision_pct: float


# ==============================================================================
# ENDPOINTS DE CONFIGURACIÓN COMERCIAL (HU-08 CA-01)
# ==============================================================================
@router_chofer.get("/api/configuracion/comercial")
def obtener_configuracion_comercial():
    return CONFIG_COMERCIAL

@router_chofer.put("/api/configuracion/comercial")
def actualizar_configuracion_comercial(datos: ConfigComercialRequest):
    CONFIG_COMERCIAL["tarifa_base"] = max(1.0, float(datos.tarifa_base))
    CONFIG_COMERCIAL["costo_km"] = max(0.5, float(datos.costo_km))
    CONFIG_COMERCIAL["promo_pct"] = min(80.0, max(0.0, float(datos.promo_pct)))
    CONFIG_COMERCIAL["comision_pct"] = min(50.0, max(1.0, float(datos.comision_pct)))
    return {
        "mensaje": "Configuración comercial actualizada correctamente",
        "config": CONFIG_COMERCIAL
    }


# ==============================================================================
# ENDPOINTS DE VEHÍCULOS Y ESTADO (HU-04)
# ==============================================================================
@router_chofer.get("/api/vehiculo/{id_chofer}")
def obtener_vehiculo(id_chofer: int):
    conexion = obtener_conexion()
    try:
        cursor = conexion.cursor()
        cursor.execute("SELECT Placa, Operativo FROM Vehiculos WHERE ID_Chofer = %s", (id_chofer,))
        vehiculo = cursor.fetchone()
        if not vehiculo:
            raise HTTPException(status_code=404, detail="Vehículo no encontrado")
        return {"placa": vehiculo[0], "operativo": vehiculo[1]}
    finally:
        if conexion:
            conexion.close()

@router_chofer.put("/api/vehiculo/estado")
def actualizar_estado(datos: EstadoVehiculoRequest):
    conexion = obtener_conexion()
    try:
        cursor = conexion.cursor()
        cursor.execute("UPDATE Vehiculos SET Operativo = %s WHERE ID_Chofer = %s", (datos.operativo, datos.id_chofer))
        conexion.commit()
        return {"mensaje": "Estado actualizado"}
    finally:
        if conexion:
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
            WHERE u.ID_Rol = 3 AND u.Estado = 1
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
        if conexion:
            conexion.close()


# ==============================================================================
# ENDPOINTS DE VIAJES Y OPERACIONES (HU-02 y HU-06)
# ==============================================================================
@router_chofer.post("/api/viajes/asignar")
def asignar_viaje(datos: ViajeRequest):
    conexion = obtener_conexion()
    try:
        cursor = conexion.cursor()
        cursor.execute("""
            INSERT INTO Viajes (ID_Chofer, Nombre_Pasajero, Origen, Destino, Tarifa, 
                                Origen_Lat, Origen_Lng, Destino_Lat, Destino_Lng, Estado)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, 'En Curso')
        """, (datos.id_chofer, datos.nombre_pasajero, datos.origen, datos.destino, datos.tarifa, 
              datos.origen_lat, datos.origen_lng, datos.destino_lat, datos.destino_lng))
        
        cursor.execute("UPDATE Vehiculos SET Operativo = 0 WHERE ID_Chofer = %s", (datos.id_chofer,))
        conexion.commit()
        return {"mensaje": "Viaje asignado correctamente."}
    except Exception as e:
        conexion.rollback()
        raise HTTPException(status_code=400, detail="Error al procesar el viaje")
    finally:
        if conexion:
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
            WHERE ID_Chofer = %s AND Estado = 'En Curso'
        """, (id_chofer,))
        viaje = cursor.fetchone()
        
        if viaje:
            return {
                "id_viaje": viaje[0],
                "pasajero": viaje[1],
                "origen": viaje[2],
                "destino": viaje[3],
                "tarifa": float(viaje[4]),
                "origen_lat": float(viaje[5]) if viaje[5] is not None else 0.0,
                "origen_lng": float(viaje[6]) if viaje[6] is not None else 0.0,
                "destino_lat": float(viaje[7]) if viaje[7] is not None else 0.0,
                "destino_lng": float(viaje[8]) if viaje[8] is not None else 0.0
            }
        return {"mensaje": "Sin viajes"}
    finally:
        if conexion:
            conexion.close()

@router_chofer.post("/api/viajes/completar")
def completar_viaje(datos: CompletarViajeRequest):
    conexion = obtener_conexion()
    try:
        cursor = conexion.cursor()
        
        cursor.execute("SELECT Destino_Lat, Destino_Lng FROM Viajes WHERE ID_Viaje = %s", (datos.id_viaje,))
        destino = cursor.fetchone()
        if not destino:
            raise HTTPException(status_code=404, detail="Viaje no encontrado")
            
        lat, lng = destino[0], destino[1]
        
        # Marcamos el viaje como Completado (Atendida)
        cursor.execute("UPDATE Viajes SET Estado = 'Completado' WHERE ID_Viaje = %s", (datos.id_viaje,))
        
        cursor.execute("""
            UPDATE Vehiculos 
            SET Operativo = 1, Latitud = %s, Longitud = %s 
            WHERE ID_Chofer = %s
        """, (lat, lng, datos.id_chofer))
        
        conexion.commit()
        return {"mensaje": "Viaje completado y marcado como atendido"}
    except Exception as e:
        conexion.rollback()
        raise HTTPException(status_code=400, detail="Error al completar")
    finally:
        if conexion:
            conexion.close()

@router_chofer.post("/api/viajes/rechazar")
def rechazar_viaje(datos: RechazarViajeRequest):
    conexion = obtener_conexion()
    try:
        cursor = conexion.cursor()
        cursor.execute("UPDATE Viajes SET Estado = 'Cancelado' WHERE ID_Viaje = %s", (datos.id_viaje,))
        cursor.execute("UPDATE Vehiculos SET Operativo = 1 WHERE ID_Chofer = %s", (datos.id_chofer,))
        conexion.commit()
        return {"mensaje": "Viaje rechazado"}
    except Exception as e:
        conexion.rollback()
        raise HTTPException(status_code=400, detail="Error al rechazar")
    finally:
        if conexion:
            conexion.close()


# ==============================================================================
# ENDPOINTS FINANCIEROS CON RETENCIÓN DE COMISIÓN DE FLECHA VELOZ
# ==============================================================================
@router_chofer.get("/api/chofer/ganancias/{id_chofer}")
def obtener_ganancias_chofer(id_chofer: int):
    """
    Calcula el Saldo Disponible Real del Chofer:
    1. Suma el Bruto de viajes completados.
    2. Retiene el % de comisión que pertenece a la app Flecha Veloz (ej. 20%).
    3. Al Neto del Chofer (80%) le resta los retiros/liquidaciones ya efectuados.
    """
    conexion = obtener_conexion()
    try:
        cursor = conexion.cursor()
        comision_pct = float(CONFIG_COMERCIAL.get("comision_pct", 20.0))
        
        # 1. Total Bruto recaudado en viajes completados
        cursor.execute("SELECT COALESCE(SUM(Tarifa), 0) FROM Viajes WHERE ID_Chofer = %s AND Estado = 'Completado'", (id_chofer,))
        resultado_ganado = cursor.fetchone()
        total_bruto = float(resultado_ganado[0]) if resultado_ganado and resultado_ganado[0] is not None else 0.0
        
        # 2. Separación de Comisión de Flecha Veloz vs Neto del Chofer
        comision_app = round(total_bruto * (comision_pct / 100.0), 2)
        neto_chofer  = round(total_bruto - comision_app, 2)
        
        # 3. Total ya retirado o liquidado al chofer
        cursor.execute("SELECT COALESCE(SUM(Monto), 0) FROM Retiros WHERE ID_Chofer = %s", (id_chofer,))
        resultado_retirado = cursor.fetchone()
        total_retirado = float(resultado_retirado[0]) if resultado_retirado and resultado_retirado[0] is not None else 0.0
        
        # 4. Saldo Neto Disponible para transferir (nunca incluye la parte de Flecha Veloz)
        saldo_disponible = max(0.0, round(neto_chofer - total_retirado, 2))
        
        return {
            "ganancias_hoy": saldo_disponible,      # Lo que el chofer puede retirar
            "ganancias_totales": total_bruto,       # Total bruto histórico
            "comision_pct": comision_pct,           # % de Flecha Veloz
            "comision_app": comision_app,           # Soles que pertenecen a Flecha Veloz
            "neto_chofer": neto_chofer,             # Soles totales que pertenecen al chofer
            "total_retirado": total_retirado        # Soles ya transferidos/liquidados
        }
    except Exception as e:
        print(f"Error en financiero: {e}")
        return {
            "ganancias_hoy": 0.0,
            "ganancias_totales": 0.0,
            "comision_pct": 20.0,
            "comision_app": 0.0,
            "neto_chofer": 0.0,
            "total_retirado": 0.0
        }
    finally:
        if conexion:
            conexion.close()

@router_chofer.post("/api/chofer/retirar")
def retirar_fondos(datos: RetiroRequest):
    """
    Permite al chofer transferir únicamente su saldo NETO disponible
    (después de descontar la comisión de Flecha Veloz).
    """
    conexion = obtener_conexion()
    try:
        cursor = conexion.cursor()
        comision_pct = float(CONFIG_COMERCIAL.get("comision_pct", 20.0))
        
        cursor.execute("SELECT COALESCE(SUM(Tarifa), 0) FROM Viajes WHERE ID_Chofer = %s AND Estado = 'Completado'", (datos.id_chofer,))
        resultado_ganado = cursor.fetchone()
        total_bruto = float(resultado_ganado[0]) if resultado_ganado and resultado_ganado[0] is not None else 0.0
        
        # Calculamos el neto real del chofer (descontando la parte de Flecha Veloz)
        comision_app = round(total_bruto * (comision_pct / 100.0), 2)
        neto_chofer  = round(total_bruto - comision_app, 2)
        
        cursor.execute("SELECT COALESCE(SUM(Monto), 0) FROM Retiros WHERE ID_Chofer = %s", (datos.id_chofer,))
        resultado_retirado = cursor.fetchone()
        total_retirado = float(resultado_retirado[0]) if resultado_retirado and resultado_retirado[0] is not None else 0.0
        
        saldo_neto_disponible = max(0.0, round(neto_chofer - total_retirado, 2))
        monto_solicitado = round(float(datos.monto), 2)
        
        if monto_solicitado <= 0 or monto_solicitado > (saldo_neto_disponible + 0.01):
            raise HTTPException(
                status_code=400, 
                detail=f"Monto inválido. Tu saldo neto disponible (descontando {comision_pct}% de comisión Flecha Veloz) es S/ {saldo_neto_disponible:.2f}"
            )

        cursor.execute("INSERT INTO Retiros (ID_Chofer, Monto) VALUES (%s, %s)", (datos.id_chofer, monto_solicitado))
        conexion.commit()
        
        return {
            "mensaje": f"Retiro neto de S/ {monto_solicitado:.2f} procesado con éxito",
            "saldo_restante": max(0.0, round(saldo_neto_disponible - monto_solicitado, 2))
        }
    except HTTPException as he:
        conexion.rollback()
        raise he
    except Exception as e:
        conexion.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        if conexion:
            conexion.close()


# ==============================================================================
# ENDPOINT DE LIQUIDACIÓN GERENCIAL DE COMISIONES (HU-08 CA-02)
# ==============================================================================
@router_chofer.post("/api/reportes/liquidar")
def liquidar_comisiones_chofer(datos: LiquidarChoferRequest):
    """
    Ejecuta la liquidación mensual desde Gerencia:
    Calcula el saldo neto pendiente del chofer, retiene la comisión de Flecha Veloz
    y registra el desembolso en la tabla Retiros para saldar la cuenta a S/ 0.00.
    """
    conexion = obtener_conexion()
    try:
        cursor = conexion.cursor()
        comision_pct = float(datos.comision_pct or CONFIG_COMERCIAL.get("comision_pct", 20.0))
        CONFIG_COMERCIAL["comision_pct"] = comision_pct

        cursor.execute("SELECT COALESCE(SUM(Tarifa), 0) FROM Viajes WHERE ID_Chofer = %s AND Estado = 'Completado'", (datos.id_chofer,))
        res_bruto = cursor.fetchone()
        total_bruto = float(res_bruto[0]) if res_bruto and res_bruto[0] is not None else 0.0

        comision_empresa = round(total_bruto * (comision_pct / 100.0), 2)
        neto_chofer      = round(total_bruto - comision_empresa, 2)

        cursor.execute("SELECT COALESCE(SUM(Monto), 0) FROM Retiros WHERE ID_Chofer = %s", (datos.id_chofer,))
        res_retirado = cursor.fetchone()
        total_retirado = float(res_retirado[0]) if res_retirado and res_retirado[0] is not None else 0.0

        saldo_pendiente_chofer = max(0.0, round(neto_chofer - total_retirado, 2))

        if saldo_pendiente_chofer <= 0.0:
            return {
                "mensaje": "Este conductor ya se encuentra completamente liquidado.",
                "comision_empresa": comision_empresa,
                "monto_liquidado": 0.0,
                "pendiente_liquidar": 0.0,
                "liquidado": True
            }

        # Insertamos el desembolso final en Retiros para dejar el saldo pendiente en 0.00 en la BD
        cursor.execute("INSERT INTO Retiros (ID_Chofer, Monto) VALUES (%s, %s)", (datos.id_chofer, saldo_pendiente_chofer))
        conexion.commit()

        return {
            "mensaje": "Liquidación mensual registrada en base de datos.",
            "comision_empresa": comision_empresa,
            "monto_liquidado": saldo_pendiente_chofer,
            "pendiente_liquidar": 0.0,
            "liquidado": True
        }
    except Exception as e:
        conexion.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        if conexion:
            conexion.close()


# ==============================================================================
# ENDPOINTS DE REPORTES Y KPIs (HU-09 CA-01)
# ==============================================================================
@router_chofer.get("/api/reportes/resumen")
def obtener_resumen_reportes(rango: str = "hoy"):
    filtro_fecha = "DATE(Fecha_Registro) = CURRENT_DATE"
    if rango == "ayer":
        filtro_fecha = "DATE(Fecha_Registro) = CURRENT_DATE - INTERVAL '1 day'"
    elif rango == "semana":
        filtro_fecha = "DATE(Fecha_Registro) >= CURRENT_DATE - INTERVAL '7 days'"
    elif rango == "mes":
        filtro_fecha = "EXTRACT(MONTH FROM Fecha_Registro) = EXTRACT(MONTH FROM CURRENT_DATE) AND EXTRACT(YEAR FROM Fecha_Registro) = EXTRACT(YEAR FROM CURRENT_DATE)"
    elif rango == "total":
        filtro_fecha = "1=1"

    conexion = obtener_conexion()
    try:
        cursor = conexion.cursor()
        comision_pct = float(CONFIG_COMERCIAL.get("comision_pct", 20.0))
        
        cursor.execute(f"SELECT COALESCE(SUM(Tarifa), 0) FROM Viajes WHERE Estado = 'Completado' AND {filtro_fecha}")
        ganancias = float(cursor.fetchone()[0] or 0.0)
        
        cursor.execute(f"SELECT COUNT(*) FROM Viajes WHERE Estado = 'Completado' AND {filtro_fecha}")
        completados = int(cursor.fetchone()[0] or 0)
        
        cursor.execute(f"SELECT COUNT(*) FROM Viajes WHERE Estado = 'Cancelado' AND {filtro_fecha}")
        cancelados = int(cursor.fetchone()[0] or 0)

        # Conteo de clientes registrados para HU-09 CA-01
        try:
            cursor.execute("SELECT COUNT(*) FROM Clientes")
            nuevos_clientes = int(cursor.fetchone()[0] or 0)
        except Exception:
            nuevos_clientes = completados
        
        return {
            "ganancias_hoy": ganancias,
            "comision_empresa": round(ganancias * (comision_pct / 100.0), 2),
            "viajes_completados": completados,
            "viajes_cancelados": cancelados,
            "nuevos_clientes": nuevos_clientes
        }
    finally:
        if conexion:
            conexion.close()

@router_chofer.get("/api/reportes/ranking")
def obtener_ranking_choferes(rango: str = "hoy"):
    filtro_fecha = "DATE(v.Fecha_Registro) = CURRENT_DATE"
    if rango == "ayer": 
        filtro_fecha = "DATE(v.Fecha_Registro) = CURRENT_DATE - INTERVAL '1 day'"
    elif rango == "semana": 
        filtro_fecha = "DATE(v.Fecha_Registro) >= CURRENT_DATE - INTERVAL '7 days'"
    elif rango == "mes": 
        filtro_fecha = "EXTRACT(MONTH FROM v.Fecha_Registro) = EXTRACT(MONTH FROM CURRENT_DATE) AND EXTRACT(YEAR FROM v.Fecha_Registro) = EXTRACT(YEAR FROM CURRENT_DATE)"
    elif rango == "total": 
        filtro_fecha = "1=1"

    conexion = obtener_conexion()
    try:
        cursor = conexion.cursor()
        comision_pct = float(CONFIG_COMERCIAL.get("comision_pct", 20.0))

        cursor.execute(f"""
            SELECT u.ID_Usuario, u.Nombre_Completo, u.DNI, u.Correo,
                   COALESCE(COUNT(v.ID_Viaje), 0) as Total_Viajes,
                   COALESCE(SUM(v.Tarifa), 0) as Recaudado,
                   veh.Placa, veh.Operativo,
                   COALESCE((SELECT SUM(r.Monto) FROM Retiros r WHERE r.ID_Chofer = u.ID_Usuario), 0) as Total_Retirado,
                   COALESCE((SELECT SUM(v2.Tarifa) FROM Viajes v2 WHERE v2.ID_Chofer = u.ID_Usuario AND v2.Estado = 'Completado'), 0) as Recaudado_Historico
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
        resultado = []

        for r in ranking:
            recaudado_rango = float(r[5] or 0.0)
            total_retirado  = float(r[8] or 0.0)
            recaudado_hist  = float(r[9] or 0.0)

            comision_rango = round(recaudado_rango * (comision_pct / 100.0), 2)
            neto_rango     = round(recaudado_rango - comision_rango, 2)

            # Cálculo exacto del saldo pendiente de liquidar en la cuenta del chofer
            neto_historico = round(recaudado_hist * (1.0 - (comision_pct / 100.0)), 2)
            pendiente_liquidar = max(0.0, round(neto_historico - total_retirado, 2))
            esta_liquidado = (recaudado_hist > 0 and pendiente_liquidar <= 0.01)

            resultado.append({
                "id": r[0],
                "nombre": r[1],
                "dni": r[2],
                "correo": r[3],
                "viajes": r[4],
                "recaudado": recaudado_rango,
                "comision": comision_rango,
                "neto_chofer": neto_rango,
                "retirado": total_retirado,
                "pendiente_liquidar": pendiente_liquidar,
                "liquidado": esta_liquidado,
                "placa": r[6] if r[6] else "Sin Vehículo",
                "operativo": r[7] if r[7] is not None else 0
            })

        return resultado
    finally:
        if conexion:
            conexion.close()

@router_chofer.get("/api/reportes/historial_chofer/{id_chofer}")
def obtener_historial_viajes_chofer(id_chofer: int, rango: str = "hoy"):
    """Extrae la lista detallada de viajes realizados por un chofer en un rango de tiempo."""
    filtro_fecha = "DATE(Fecha_Registro) = CURRENT_DATE"
    if rango == "ayer": 
        filtro_fecha = "DATE(Fecha_Registro) = CURRENT_DATE - INTERVAL '1 day'"
    elif rango == "semana": 
        filtro_fecha = "DATE(Fecha_Registro) >= CURRENT_DATE - INTERVAL '7 days'"
    elif rango == "mes": 
        filtro_fecha = "EXTRACT(MONTH FROM Fecha_Registro) = EXTRACT(MONTH FROM CURRENT_DATE) AND EXTRACT(YEAR FROM Fecha_Registro) = EXTRACT(YEAR FROM CURRENT_DATE)"
    elif rango == "total": 
        filtro_fecha = "1=1" 

    conexion = obtener_conexion()
    try:
        cursor = conexion.cursor()
        cursor.execute(f"""
            SELECT ID_Viaje, Nombre_Pasajero, Origen, Destino, Tarifa, Estado, 
                   TO_CHAR(Fecha_Registro, 'HH24:MI:SS') as Hora,
                   TO_CHAR(Fecha_Registro, 'YYYY-MM-DD') as Fecha
            FROM Viajes 
            WHERE ID_Chofer = %s AND {filtro_fecha}
            ORDER BY Fecha_Registro DESC
        """, (id_chofer,))
        
        viajes = cursor.fetchall()
        
        return [
            {
                "id_viaje": v[0],
                "pasajero": v[1],
                "origen": v[2],
                "destino": v[3],
                "tarifa": float(v[4]) if v[4] else 0.0,
                "estado": v[5],
                "hora": v[6],
                "fecha": v[7]
            } for v in viajes
        ]
    except Exception as e:
        print(f"Error en historial de viajes: {e}")
        return []
    finally:
        if conexion:
            conexion.close()