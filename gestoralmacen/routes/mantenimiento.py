from __future__ import annotations
from datetime import datetime
from flask import Blueprint, render_template, request, redirect, url_for, flash
from ..db import fetchall, fetchone, execute

bp = Blueprint("mantenimiento", __name__, url_prefix="/mantenimiento")


@bp.route("/")
def index():
    return redirect(url_for("mantenimiento.equipos"))


@bp.route("/equipos")
def equipos():
    estado = request.args.get("estado", "")
    sql = "SELECT * FROM equipos WHERE 1=1 "
    params = []
    if estado:
        sql += " AND estado=?"
        params.append(estado)
    eqs = fetchall(sql + " ORDER BY nombre", tuple(params))
    return render_template("mantenimiento/equipos.html", equipos=eqs, estado=estado)


@bp.route("/equipos/nuevo", methods=["GET", "POST"])
def equipo_nuevo():
    if request.method == "POST":
        f = request.form
        codigo = f"EQ-{datetime.now().strftime('%y%m%d%H%M')}"
        execute(
            "INSERT INTO equipos(codigo,nombre,tipo,marca,modelo,numero_serie,ubicacion,fecha_compra,fecha_proxima_revision,estado) VALUES(?,?,?,?,?,?,?,?,?,'operativo')",
            (codigo, f["nombre"], f.get("tipo",""), f.get("marca",""), f.get("modelo",""),
             f.get("numero_serie",""), f.get("ubicacion",""), f.get("fecha_compra",""),
             f.get("fecha_proxima_revision","")),
        )
        flash("Equipo registrado", "ok")
        return redirect(url_for("mantenimiento.equipos"))
    return render_template("mantenimiento/equipo_form.html", equipo=None)


@bp.route("/ordenes")
def ordenes():
    estado = request.args.get("estado", "")
    sql = (
        "SELECT om.*, e.nombre AS eq_nombre, e.ubicacion AS eq_ubicacion, "
        "emp.nombre||' '||emp.apellidos AS tec_nombre "
        "FROM ordenes_mantenimiento om LEFT JOIN equipos e ON e.id=om.equipo_id "
        "LEFT JOIN empleados emp ON emp.id=om.tecnico_id WHERE 1=1 "
    )
    params = []
    if estado:
        sql += " AND om.estado=?"
        params.append(estado)
    oms = fetchall(sql + " ORDER BY om.fecha_apertura DESC", tuple(params))
    equipos = fetchall("SELECT id, nombre FROM equipos ORDER BY nombre")
    tecnicos = fetchall("SELECT id, nombre||' '||apellidos AS nombre FROM empleados WHERE departamento='Mantenimiento' ORDER BY nombre")
    return render_template("mantenimiento/ordenes.html", ordenes=oms, equipos=equipos, tecnicos=tecnicos, estado=estado)


@bp.route("/ordenes/nueva", methods=["POST"])
def orden_nueva():
    f = request.form
    num = f"OM-{datetime.now().strftime('%Y%m%d%H%M%S')}"
    execute(
        "INSERT INTO ordenes_mantenimiento(numero,equipo_id,tipo,descripcion,prioridad,estado,tecnico_id) VALUES(?,?,?,?,?,'pendiente',?)",
        (num, f.get("equipo_id") or None, f["tipo"], f["descripcion"], f.get("prioridad","normal"),
         f.get("tecnico_id") or None),
    )
    # Update equipment status if urgent/corrective
    if f.get("tipo") == "correctivo" and f.get("equipo_id"):
        execute("UPDATE equipos SET estado='en_mantenimiento' WHERE id=?", (f["equipo_id"],))
    flash("Orden de mantenimiento creada", "ok")
    return redirect(url_for("mantenimiento.ordenes"))


@bp.route("/ordenes/<int:oid>/cerrar", methods=["POST"])
def orden_cerrar(oid):
    f = request.form
    om = fetchone("SELECT * FROM ordenes_mantenimiento WHERE id=?", (oid,))
    execute(
        "UPDATE ordenes_mantenimiento SET estado='completada', fecha_cierre=datetime('now'), coste=?, tiempo_horas=?, notas=? WHERE id=?",
        (float(f.get("coste") or 0), float(f.get("tiempo_horas") or 0), f.get("notas",""), oid),
    )
    if om and om["equipo_id"]:
        execute("UPDATE equipos SET estado='operativo', fecha_ultima_revision=date('now') WHERE id=?", (om["equipo_id"],))
    flash("Orden cerrada", "ok")
    return redirect(url_for("mantenimiento.ordenes"))


@bp.route("/preventivo")
def preventivo():
    proximos = fetchall(
        "SELECT * FROM equipos WHERE fecha_proxima_revision IS NOT NULL "
        "AND date(fecha_proxima_revision) <= date('now','+30 days') ORDER BY fecha_proxima_revision"
    )
    todos = fetchall("SELECT * FROM equipos ORDER BY fecha_proxima_revision NULLS LAST")
    return render_template("mantenimiento/preventivo.html", proximos=proximos, todos=todos)


@bp.route("/historial")
def historial():
    oms = fetchall(
        "SELECT om.*, e.nombre AS eq_nombre FROM ordenes_mantenimiento om "
        "LEFT JOIN equipos e ON e.id=om.equipo_id WHERE om.estado='completada' ORDER BY om.fecha_cierre DESC LIMIT 50"
    )
    return render_template("mantenimiento/historial.html", historial=oms)
