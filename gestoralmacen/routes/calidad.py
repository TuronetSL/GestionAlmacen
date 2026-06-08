from __future__ import annotations
from datetime import datetime
from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from ..db import fetchall, fetchone, execute

bp = Blueprint("calidad", __name__, url_prefix="/calidad")


@bp.route("/")
def index():
    return redirect(url_for("calidad.control"))


@bp.route("/control")
def control():
    ccs = fetchall(
        "SELECT cc.*, p.referencia, p.nombre AS prod_nombre, l.numero AS lote_num, u.nombre||' '||u.apellidos AS tec_nombre "
        "FROM controles_calidad cc LEFT JOIN productos p ON p.id=cc.producto_id "
        "LEFT JOIN lotes l ON l.id=cc.lote_id LEFT JOIN usuarios u ON u.id=cc.tecnico_id ORDER BY cc.creado_en DESC LIMIT 40"
    )
    productos = fetchall("SELECT id, referencia, nombre FROM productos WHERE activo=1 ORDER BY referencia")
    lotes = fetchall("SELECT id, numero FROM lotes WHERE estado='activo' ORDER BY numero")
    tecnicos = fetchall("SELECT id, nombre||' '||apellidos AS nombre FROM usuarios WHERE activo=1 ORDER BY nombre")
    return render_template("calidad/control.html", controles=ccs, productos=productos, lotes=lotes, tecnicos=tecnicos)


@bp.route("/control/nuevo", methods=["POST"])
def control_nuevo():
    f = request.form
    num = f"QC-{datetime.now().strftime('%Y%m%d%H%M%S')}"
    execute(
        "INSERT INTO controles_calidad(numero,tipo,producto_id,lote_id,fecha,resultado,tecnico_id,observaciones) VALUES(?,?,?,?,date('now'),?,?,?)",
        (num, f["tipo"], f.get("producto_id") or None, f.get("lote_id") or None,
         f.get("resultado","pendiente"), f.get("tecnico_id") or None, f.get("observaciones","")),
    )
    if f.get("resultado") == "no_conforme" and f.get("lote_id"):
        execute("UPDATE lotes SET estado='bloqueado' WHERE id=?", (f["lote_id"],))
    flash("Control de calidad registrado", "ok")
    return redirect(url_for("calidad.control"))


@bp.route("/no-conformidades")
def no_conformidades():
    estado = request.args.get("estado", "")
    sev = request.args.get("sev", "")
    sql = (
        "SELECT nc.*, u.nombre||' '||u.apellidos AS resp_nombre, p.referencia "
        "FROM no_conformidades nc LEFT JOIN usuarios u ON u.id=nc.responsable_id "
        "LEFT JOIN productos p ON p.id=nc.producto_id WHERE 1=1 "
    )
    params = []
    if estado:
        sql += " AND nc.estado=?"
        params.append(estado)
    if sev:
        sql += " AND nc.severidad=?"
        params.append(sev)
    ncs = fetchall(sql + " ORDER BY nc.fecha_apertura DESC", tuple(params))
    usuarios = fetchall("SELECT id, nombre||' '||apellidos AS nombre FROM usuarios WHERE activo=1 ORDER BY nombre")
    return render_template("calidad/no_conformidades.html", ncs=ncs, usuarios=usuarios, estado=estado, sev=sev)


@bp.route("/no-conformidades/nueva", methods=["POST"])
def nc_nueva():
    f = request.form
    num = f"NC-{datetime.now().strftime('%Y%m%d%H%M%S')}"
    execute(
        "INSERT INTO no_conformidades(numero,descripcion,modulo,severidad,estado,accion_correctiva,responsable_id,creado_por) VALUES(?,?,?,?,?,?,?,?)",
        (num, f["descripcion"], f["modulo"], f["severidad"], "abierta",
         f.get("accion_correctiva",""), f.get("responsable_id") or None, session.get("user_id")),
    )
    flash("No conformidad registrada", "ok")
    return redirect(url_for("calidad.no_conformidades"))


@bp.route("/no-conformidades/<int:nid>/estado", methods=["POST"])
def nc_estado(nid):
    nuevo = request.form["estado"]
    if nuevo == "cerrada":
        execute("UPDATE no_conformidades SET estado=?, fecha_cierre=datetime('now') WHERE id=?", (nuevo, nid))
    else:
        execute("UPDATE no_conformidades SET estado=? WHERE id=?", (nuevo, nid))
    flash("Estado actualizado", "ok")
    return redirect(url_for("calidad.no_conformidades"))


@bp.route("/analisis")
def analisis():
    ccs = fetchall(
        "SELECT cc.*, p.nombre AS prod_nombre, l.numero AS lote_num "
        "FROM controles_calidad cc LEFT JOIN productos p ON p.id=cc.producto_id "
        "LEFT JOIN lotes l ON l.id=cc.lote_id ORDER BY cc.creado_en DESC LIMIT 30"
    )
    return render_template("calidad/analisis.html", analisis=ccs)


@bp.route("/fds")
def fds():
    fichas = fetchall(
        "SELECT fs.*, p.referencia FROM fichas_seguridad fs LEFT JOIN productos p ON p.id=fs.producto_id WHERE fs.activo=1 ORDER BY fs.nombre_producto"
    )
    return render_template("calidad/fds.html", fichas=fichas)


@bp.route("/certificaciones")
def certificaciones():
    return render_template("calidad/certificaciones.html")


@bp.route("/auditorias")
def auditorias():
    return render_template("calidad/auditorias.html")
