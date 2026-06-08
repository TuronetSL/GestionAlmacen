from __future__ import annotations
from datetime import datetime, date
from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from ..db import fetchall, fetchone, execute

bp = Blueprint("rrhh", __name__, url_prefix="/rrhh")


@bp.route("/")
def index():
    return redirect(url_for("rrhh.empleados"))


@bp.route("/empleados")
def empleados():
    q = request.args.get("q", "")
    dept = request.args.get("dept", "")
    estado = request.args.get("estado", "")
    sql = "SELECT * FROM empleados WHERE 1=1 "
    params = []
    if q:
        sql += " AND (nombre LIKE ? OR apellidos LIKE ? OR codigo LIKE ?)"
        params += [f"%{q}%"] * 3
    if dept:
        sql += " AND departamento=?"
        params.append(dept)
    if estado:
        sql += " AND estado=?"
        params.append(estado)
    emps = fetchall(sql + " ORDER BY departamento, nombre", tuple(params))
    depts = fetchall("SELECT DISTINCT departamento FROM empleados ORDER BY departamento")
    return render_template("rrhh/empleados.html", empleados=emps, depts=depts, q=q, dept=dept, estado=estado)


@bp.route("/empleados/nuevo", methods=["GET", "POST"])
def empleado_nuevo():
    if request.method == "POST":
        f = request.form
        codigo = f"EMP-{datetime.now().strftime('%y%m%d%H%M')}"
        execute(
            "INSERT INTO empleados(codigo,nombre,apellidos,dni,email,telefono,departamento,cargo,fecha_alta,tipo_contrato,jornada,estado) VALUES(?,?,?,?,?,?,?,?,?,?,?,?)",
            (codigo, f["nombre"], f["apellidos"], f.get("dni",""), f.get("email",""), f.get("telefono",""),
             f["departamento"], f.get("cargo",""), f.get("fecha_alta", date.today().isoformat()),
             f.get("tipo_contrato","indefinido"), f.get("jornada","completa"), "activo"),
        )
        flash("Empleado registrado", "ok")
        return redirect(url_for("rrhh.empleados"))
    return render_template("rrhh/empleado_form.html", empleado=None)


@bp.route("/empleados/<int:eid>/editar", methods=["GET", "POST"])
def empleado_editar(eid):
    emp = fetchone("SELECT * FROM empleados WHERE id=?", (eid,))
    if request.method == "POST":
        f = request.form
        execute(
            "UPDATE empleados SET nombre=?,apellidos=?,dni=?,email=?,telefono=?,departamento=?,cargo=?,tipo_contrato=?,jornada=?,estado=? WHERE id=?",
            (f["nombre"], f["apellidos"], f.get("dni",""), f.get("email",""), f.get("telefono",""),
             f["departamento"], f.get("cargo",""), f.get("tipo_contrato",""), f.get("jornada",""), f.get("estado","activo"), eid),
        )
        flash("Empleado actualizado", "ok")
        return redirect(url_for("rrhh.empleados"))
    return render_template("rrhh/empleado_form.html", empleado=emp)


@bp.route("/horario")
def horario():
    fecha = request.args.get("fecha", date.today().isoformat())
    fichajes = fetchall(
        "SELECT fi.*, e.nombre||' '||e.apellidos AS emp_nombre, e.departamento "
        "FROM fichajes fi JOIN empleados e ON e.id=fi.empleado_id WHERE fi.fecha=? ORDER BY e.departamento, e.nombre",
        (fecha,),
    )
    empleados = fetchall("SELECT id, nombre||' '||apellidos AS nombre, departamento FROM empleados WHERE estado='activo' ORDER BY nombre")
    return render_template("rrhh/horario.html", fichajes=fichajes, empleados=empleados, fecha=fecha)


@bp.route("/horario/fichar", methods=["POST"])
def fichar():
    f = request.form
    eid = int(f["empleado_id"])
    hoy = date.today().isoformat()
    existing = fetchone("SELECT * FROM fichajes WHERE empleado_id=? AND fecha=?", (eid, hoy))
    if existing:
        if not existing["hora_salida"]:
            execute("UPDATE fichajes SET hora_salida=time('now') WHERE id=?", (existing["id"],))
            flash("Salida registrada", "ok")
        else:
            flash("Ya hay fichaje completo para hoy", "warn")
    else:
        execute("INSERT INTO fichajes(empleado_id,fecha,hora_entrada) VALUES(?,?,time('now'))", (eid, hoy))
        flash("Entrada registrada", "ok")
    return redirect(url_for("rrhh.horario"))


@bp.route("/turnos")
def turnos():
    empleados = fetchall(
        "SELECT e.*, COUNT(f.id) AS fichajes_mes "
        "FROM empleados e LEFT JOIN fichajes f ON f.empleado_id=e.id AND strftime('%Y-%m',f.fecha)=strftime('%Y-%m','now') "
        "WHERE e.estado='activo' GROUP BY e.id ORDER BY e.departamento"
    )
    return render_template("rrhh/turnos.html", empleados=empleados)


@bp.route("/vacaciones")
def vacaciones():
    estado = request.args.get("estado", "")
    sql = (
        "SELECT vs.*, e.nombre||' '||e.apellidos AS emp_nombre, e.departamento "
        "FROM vacaciones_solicitudes vs JOIN empleados e ON e.id=vs.empleado_id WHERE 1=1 "
    )
    params = []
    if estado:
        sql += " AND vs.estado=?"
        params.append(estado)
    sols = fetchall(sql + " ORDER BY vs.creado_en DESC", tuple(params))
    empleados = fetchall("SELECT id, nombre||' '||apellidos AS nombre FROM empleados WHERE estado='activo' ORDER BY nombre")
    return render_template("rrhh/vacaciones.html", solicitudes=sols, empleados=empleados, estado=estado)


@bp.route("/vacaciones/nueva", methods=["POST"])
def vacacion_nueva():
    f = request.form
    fi = datetime.strptime(f["fecha_inicio"], "%Y-%m-%d").date()
    ff = datetime.strptime(f["fecha_fin"], "%Y-%m-%d").date()
    dias = (ff - fi).days + 1
    execute(
        "INSERT INTO vacaciones_solicitudes(empleado_id,fecha_inicio,fecha_fin,dias,estado,motivo) VALUES(?,?,?,?,'pendiente',?)",
        (f["empleado_id"], f["fecha_inicio"], f["fecha_fin"], dias, f.get("motivo","")),
    )
    flash("Solicitud de vacaciones enviada", "ok")
    return redirect(url_for("rrhh.vacaciones"))


@bp.route("/vacaciones/<int:vid>/aprobar", methods=["POST"])
def vacacion_aprobar(vid):
    accion = request.form.get("accion", "aprobada")
    execute("UPDATE vacaciones_solicitudes SET estado=? WHERE id=?", (accion, vid))
    flash(f"Solicitud {accion}", "ok")
    return redirect(url_for("rrhh.vacaciones"))


@bp.route("/formacion")
def formacion():
    empleados = fetchall("SELECT * FROM empleados WHERE estado='activo' ORDER BY departamento, nombre")
    return render_template("rrhh/formacion.html", empleados=empleados)


@bp.route("/epis")
def epis():
    epis_list = fetchall(
        "SELECT ea.*, e.nombre||' '||e.apellidos AS emp_nombre, e.departamento "
        "FROM epis_asignados ea JOIN empleados e ON e.id=ea.empleado_id ORDER BY ea.proxima_revision"
    )
    empleados = fetchall("SELECT id, nombre||' '||apellidos AS nombre FROM empleados WHERE estado='activo' ORDER BY nombre")
    vencidos = [e for e in epis_list if e["proxima_revision"] and e["proxima_revision"] < date.today().isoformat()]
    return render_template("rrhh/epis.html", epis=epis_list, empleados=empleados, vencidos=vencidos)
