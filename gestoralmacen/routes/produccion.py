from __future__ import annotations
import json
from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from ..db import fetchall, fetchone, execute, scalar

bp = Blueprint("produccion", __name__, url_prefix="/produccion")


@bp.route("/")
def index():
    return redirect(url_for("produccion.ordenes"))


@bp.route("/ordenes")
def ordenes():
    estado = request.args.get("estado", "")
    sql = (
        "SELECT of.*, f.nombre AS formula_nombre, p.nombre AS prod_nombre, p.unidad, "
        "u.nombre||' '||u.apellidos AS operario_nombre "
        "FROM ordenes_fabricacion of "
        "LEFT JOIN formulas f ON f.id=of.formula_id "
        "LEFT JOIN productos p ON p.id=of.producto_id "
        "LEFT JOIN usuarios u ON u.id=of.operario_id "
        "WHERE 1=1 "
    )
    params = []
    if estado:
        sql += " AND of.estado=?"
        params.append(estado)
    sql += " ORDER BY of.creado_en DESC"
    ofs = fetchall(sql, tuple(params))
    return render_template("produccion/ordenes.html", ordenes=ofs, estado=estado)


@bp.route("/ordenes/nueva", methods=["GET", "POST"])
def orden_nueva():
    formulas = fetchall("SELECT f.*, p.nombre AS prod_nombre FROM formulas f LEFT JOIN productos p ON p.id=f.producto_id WHERE f.activo=1")
    operarios = fetchall("SELECT id, nombre||' '||apellidos AS nombre FROM usuarios WHERE activo=1 ORDER BY nombre")
    if request.method == "POST":
        f = request.form
        num = f"OF-{__import__('datetime').datetime.now().strftime('%Y-%m%d%H%M%S')}"
        execute(
            "INSERT INTO ordenes_fabricacion(numero,formula_id,producto_id,cantidad_planificada,fecha_planificada,estado,operario_id,notas) VALUES(?,?,?,?,?,?,?,?)",
            (num, f["formula_id"], f["producto_id"], float(f["cantidad"]), f.get("fecha_planificada",""),
             "pendiente", f.get("operario_id") or None, f.get("notas","")),
        )
        flash("Orden de fabricación creada", "ok")
        return redirect(url_for("produccion.ordenes"))
    return render_template("produccion/orden_form.html", formulas=formulas, operarios=operarios)


@bp.route("/ordenes/<int:oid>/estado", methods=["POST"])
def orden_estado(oid):
    nuevo_estado = request.form["estado"]
    of = fetchone("SELECT * FROM ordenes_fabricacion WHERE id=?", (oid,))
    if not of:
        flash("OF no encontrada", "err")
        return redirect(url_for("produccion.ordenes"))
    updates = {"estado": nuevo_estado}
    if nuevo_estado == "en_proceso" and not of["fecha_inicio"]:
        execute("UPDATE ordenes_fabricacion SET estado=?, fecha_inicio=datetime('now') WHERE id=?", (nuevo_estado, oid))
    elif nuevo_estado == "completada":
        cantidad_prod = float(request.form.get("cantidad_producida") or of["cantidad_planificada"])
        merma = float(request.form.get("merma_kg") or 0)
        lote_num = request.form.get("lote_producido", "").strip() or f"LT-PT-{oid:04d}"
        execute(
            "UPDATE ordenes_fabricacion SET estado='completada', fecha_fin=datetime('now'), cantidad_producida=?, merma_kg=?, lote_producido=? WHERE id=?",
            (cantidad_prod, merma, lote_num, oid),
        )
        # Create PT lot and update stock
        if of["producto_id"]:
            execute(
                "INSERT OR IGNORE INTO lotes(numero,producto_id,cantidad,cantidad_disponible,fecha_entrada) VALUES(?,?,?,?,date('now'))",
                (lote_num, of["producto_id"], cantidad_prod, cantidad_prod),
            )
            execute("UPDATE productos SET stock_actual=stock_actual+? WHERE id=?", (cantidad_prod, of["producto_id"]))
    else:
        execute("UPDATE ordenes_fabricacion SET estado=? WHERE id=?", (nuevo_estado, oid))
    flash(f"Estado actualizado a '{nuevo_estado}'", "ok")
    return redirect(url_for("produccion.ordenes"))


@bp.route("/formulas")
def formulas():
    fms = fetchall(
        "SELECT f.*, p.nombre AS prod_nombre, p.unidad FROM formulas f "
        "LEFT JOIN productos p ON p.id=f.producto_id WHERE f.activo=1 ORDER BY f.codigo"
    )
    return render_template("produccion/formulas.html", formulas=fms)


@bp.route("/formulas/<int:fid>")
def formula_detalle(fid):
    formula = fetchone(
        "SELECT f.*, p.nombre AS prod_nombre FROM formulas f LEFT JOIN productos p ON p.id=f.producto_id WHERE f.id=?", (fid,)
    )
    ingredientes = json.loads(formula["ingredientes"] or "[]")
    return render_template("produccion/formula_detalle.html", formula=formula, ingredientes=ingredientes)


@bp.route("/planificacion")
def planificacion():
    pendientes = fetchall(
        "SELECT of.*, f.nombre AS f_nombre, p.nombre AS p_nombre "
        "FROM ordenes_fabricacion of LEFT JOIN formulas f ON f.id=of.formula_id LEFT JOIN productos p ON p.id=of.producto_id "
        "WHERE of.estado IN ('pendiente','en_proceso') ORDER BY of.fecha_planificada NULLS LAST"
    )
    return render_template("produccion/planificacion.html", pendientes=pendientes)


@bp.route("/trazabilidad")
def trazabilidad():
    lotes_pt = fetchall(
        "SELECT l.*, p.referencia, p.nombre AS p_nombre, of.numero AS of_numero "
        "FROM lotes l JOIN productos p ON p.id=l.producto_id "
        "LEFT JOIN ordenes_fabricacion of ON of.lote_producido=l.numero "
        "JOIN categorias c ON c.id=p.categoria_id WHERE c.tipo='PT' ORDER BY l.creado_en DESC LIMIT 30"
    )
    return render_template("produccion/trazabilidad.html", lotes=lotes_pt)
