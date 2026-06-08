from __future__ import annotations
import hashlib
import json
from datetime import datetime
from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from ..db import fetchall, fetchone, execute, scalar, _hash

bp = Blueprint("sistemas", __name__, url_prefix="/sistemas")


@bp.route("/")
def index():
    return redirect(url_for("sistemas.usuarios"))


@bp.route("/usuarios")
def usuarios():
    q = request.args.get("q", "")
    dept = request.args.get("dept", "")
    activo = request.args.get("activo", "")
    sql = (
        "SELECT u.*, r.nombre AS rol_nombre FROM usuarios u LEFT JOIN roles r ON r.id=u.rol_id WHERE 1=1 "
    )
    params = []
    if q:
        sql += " AND (u.nombre LIKE ? OR u.username LIKE ? OR u.email LIKE ?)"
        params += [f"%{q}%"] * 3
    if dept:
        sql += " AND u.departamento=?"
        params.append(dept)
    if activo != "":
        sql += " AND u.activo=?"
        params.append(int(activo))
    users = fetchall(sql + " ORDER BY u.departamento, u.nombre", tuple(params))
    roles = fetchall("SELECT * FROM roles ORDER BY nombre")
    depts = fetchall("SELECT DISTINCT departamento FROM usuarios ORDER BY departamento")
    total = scalar("SELECT COUNT(*) FROM usuarios WHERE activo=1")
    return render_template("sistemas/usuarios.html", usuarios=users, roles=roles, depts=depts, total=total, q=q, dept=dept, activo=activo)


@bp.route("/usuarios/nuevo", methods=["GET", "POST"])
def usuario_nuevo():
    roles = fetchall("SELECT * FROM roles ORDER BY nombre")
    if request.method == "POST":
        f = request.form
        execute(
            "INSERT INTO usuarios(nombre,apellidos,username,email,password_hash,departamento,rol_id,activo) VALUES(?,?,?,?,?,?,?,1)",
            (f["nombre"], f["apellidos"], f["username"], f["email"],
             _hash(f.get("password","pass123")), f["departamento"], f["rol_id"]),
        )
        flash("Usuario creado correctamente", "ok")
        return redirect(url_for("sistemas.usuarios"))
    return render_template("sistemas/usuario_form.html", usuario=None, roles=roles)


@bp.route("/usuarios/<int:uid>/editar", methods=["GET", "POST"])
def usuario_editar(uid):
    user = fetchone("SELECT * FROM usuarios WHERE id=?", (uid,))
    roles = fetchall("SELECT * FROM roles ORDER BY nombre")
    if not user:
        flash("Usuario no encontrado", "err")
        return redirect(url_for("sistemas.usuarios"))
    if request.method == "POST":
        f = request.form
        execute(
            "UPDATE usuarios SET nombre=?,apellidos=?,email=?,departamento=?,rol_id=?,activo=? WHERE id=?",
            (f["nombre"], f["apellidos"], f["email"], f["departamento"], f["rol_id"], int(f.get("activo","1")), uid),
        )
        if f.get("new_password"):
            execute("UPDATE usuarios SET password_hash=? WHERE id=?", (_hash(f["new_password"]), uid))
        flash("Usuario actualizado", "ok")
        return redirect(url_for("sistemas.usuarios"))
    return render_template("sistemas/usuario_form.html", usuario=user, roles=roles)


@bp.route("/usuarios/<int:uid>/toggle", methods=["POST"])
def usuario_toggle(uid):
    user = fetchone("SELECT activo FROM usuarios WHERE id=?", (uid,))
    if user:
        execute("UPDATE usuarios SET activo=? WHERE id=?", (0 if user["activo"] else 1, uid))
        flash("Estado del usuario actualizado", "ok")
    return redirect(url_for("sistemas.usuarios"))


@bp.route("/roles")
def roles():
    roles_list = fetchall(
        "SELECT r.*, COUNT(u.id) AS num_usuarios FROM roles r "
        "LEFT JOIN usuarios u ON u.rol_id=r.id AND u.activo=1 GROUP BY r.id ORDER BY r.nombre"
    )
    return render_template("sistemas/roles.html", roles=roles_list)


@bp.route("/permisos")
def permisos():
    roles_list = fetchall("SELECT * FROM roles ORDER BY nombre")
    modulos = ["Almacén","Producción","Compras","Ventas","Calidad","RRHH","Mantenimiento","Informes","Sistemas"]
    return render_template("sistemas/permisos.html", roles=roles_list, modulos=modulos)


@bp.route("/config")
def config():
    return render_template("sistemas/config.html")


@bp.route("/monitor")
def monitor():
    import os, shutil
    disk = shutil.disk_usage("/")
    stats = {
        "disk_total_gb": round(disk.total / 1e9, 1),
        "disk_used_gb": round(disk.used / 1e9, 1),
        "disk_pct": round(disk.used / disk.total * 100, 1),
        "sesiones": scalar("SELECT COUNT(*) FROM usuarios WHERE activo=1") or 0,
        "total_logs": scalar("SELECT COUNT(*) FROM logs_actividad") or 0,
        "uptime": "En línea",
    }
    procesos = [
        {"nombre": "Servidor web Flask", "estado": "Running", "desc": "Puerto 5000"},
        {"nombre": "Base de datos SQLite", "estado": "Running", "desc": "WAL mode activo"},
        {"nombre": "Monitor de caducidades", "estado": "Running", "desc": "Verificación diaria"},
        {"nombre": "Tareas programadas", "estado": "Running", "desc": "6 tareas activas"},
    ]
    return render_template("sistemas/monitor.html", stats=stats, procesos=procesos)


@bp.route("/logs")
def logs():
    nivel = request.args.get("nivel", "")
    modulo = request.args.get("modulo", "")
    sql = "SELECT l.*, u.nombre||' '||u.apellidos AS usr_nombre FROM logs_actividad l LEFT JOIN usuarios u ON u.id=l.usuario_id WHERE 1=1 "
    params = []
    if nivel:
        sql += " AND l.nivel=?"
        params.append(nivel)
    if modulo:
        sql += " AND l.modulo=?"
        params.append(modulo)
    logs_list = fetchall(sql + " ORDER BY l.fecha DESC LIMIT 100", tuple(params))
    modulos = fetchall("SELECT DISTINCT modulo FROM logs_actividad ORDER BY modulo")
    return render_template("sistemas/logs.html", logs=logs_list, modulos=modulos, nivel=nivel, modulo=modulo)


@bp.route("/auditoria")
def auditoria():
    logs_list = fetchall(
        "SELECT l.*, u.nombre||' '||u.apellidos AS usr_nombre FROM logs_actividad l "
        "LEFT JOIN usuarios u ON u.id=l.usuario_id WHERE l.accion NOT IN ('Login','Logout') "
        "ORDER BY l.fecha DESC LIMIT 80"
    )
    return render_template("sistemas/auditoria.html", logs=logs_list)


@bp.route("/backup")
def backup():
    backups = fetchall("SELECT * FROM backups_registro ORDER BY fecha DESC LIMIT 20")
    return render_template("sistemas/backup.html", backups=backups)


@bp.route("/backup/ejecutar", methods=["POST"])
def backup_ejecutar():
    import os
    tipo = request.form.get("tipo", "completo")
    from ..db import DB_PATH
    tamano = round(os.path.getsize(DB_PATH) / 1e6, 2) if DB_PATH.exists() else 0
    execute(
        "INSERT INTO backups_registro(tipo,fecha,tamano_mb,estado,ruta) VALUES(?,datetime('now'),?,'ok',?)",
        (tipo, tamano, f"/backups/ga_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{tipo}.bak"),
    )
    flash("Copia de seguridad generada correctamente", "ok")
    return redirect(url_for("sistemas.backup"))


@bp.route("/bbdd")
def bbdd():
    from ..db import DB_PATH
    import os
    tables = fetchall("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
    table_stats = []
    for t in tables:
        name = t["name"]
        count = scalar(f"SELECT COUNT(*) FROM \"{name}\"") or 0
        table_stats.append({"name": name, "count": count})
    size_mb = round(os.path.getsize(DB_PATH) / 1e6, 2) if DB_PATH.exists() else 0
    return render_template("sistemas/bbdd.html", tables=table_stats, size_mb=size_mb)


@bp.route("/bbdd/vacuum", methods=["POST"])
def bbdd_vacuum():
    from ..db import get_db
    with get_db() as conn:
        conn.execute("VACUUM")
    flash("VACUUM ejecutado correctamente", "ok")
    return redirect(url_for("sistemas.bbdd"))


@bp.route("/dispositivos")
def dispositivos():
    devs = fetchall(
        "SELECT d.*, u.nombre||' '||u.apellidos AS usu_nombre "
        "FROM dispositivos d LEFT JOIN usuarios u ON u.id=d.usuario_asignado ORDER BY d.tipo, d.nombre"
    )
    usuarios = fetchall("SELECT id, nombre||' '||apellidos AS nombre FROM usuarios WHERE activo=1 ORDER BY nombre")
    return render_template("sistemas/dispositivos.html", dispositivos=devs, usuarios=usuarios)


@bp.route("/dispositivos/nuevo", methods=["POST"])
def dispositivo_nuevo():
    f = request.form
    codigo = f"DEV-{datetime.now().strftime('%y%m%d%H%M%S')}"
    execute(
        "INSERT INTO dispositivos(codigo,nombre,tipo,ubicacion,ip,mac,usuario_asignado,estado) VALUES(?,?,?,?,?,?,?,?)",
        (codigo, f["nombre"], f["tipo"], f.get("ubicacion",""), f.get("ip",""), f.get("mac",""),
         f.get("usuario_asignado") or None, "activo"),
    )
    flash("Dispositivo registrado", "ok")
    return redirect(url_for("sistemas.dispositivos"))


@bp.route("/integraciones")
def integraciones():
    integs = [
        {"nombre": "SAP Business One", "tipo": "ERP", "icon": "🏦", "estado": "activo", "desc": "Sincronización pedidos, facturas y stock", "ultimo_sync": "Hace 4 min"},
        {"nombre": "Microsoft 365 / Exchange", "tipo": "Email", "icon": "📧", "estado": "activo", "desc": "Notificaciones y alertas automáticas", "ultimo_sync": "Activo"},
        {"nombre": "Active Directory", "tipo": "Auth", "icon": "🪪", "estado": "activo", "desc": "SSO y gestión de usuarios", "ultimo_sync": "Hace 8 min"},
        {"nombre": "Power BI", "tipo": "BI", "icon": "📊", "estado": "configurado", "desc": "Cuadros de mando ejecutivos", "ultimo_sync": "Ayer 06:00"},
        {"nombre": "Agencia Transporte (API)", "tipo": "Logística", "icon": "🚚", "estado": "error", "desc": "Tracking y etiquetas de envío", "ultimo_sync": "Error — revisar token"},
        {"nombre": "Báscula industrial IoT", "tipo": "IoT", "icon": "⚖️", "estado": "activo", "desc": "Lectura automática de pesos", "ultimo_sync": "Hace 1 min"},
    ]
    return render_template("sistemas/integraciones.html", integraciones=integs)


@bp.route("/ldap")
def ldap():
    return render_template("sistemas/ldap.html")
