from __future__ import annotations
import json
from datetime import datetime
from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from ..db import fetchall, fetchone, execute

bp = Blueprint("compras", __name__, url_prefix="/compras")


@bp.route("/")
def index():
    return redirect(url_for("compras.ordenes"))


@bp.route("/proveedores")
def proveedores():
    q = request.args.get("q", "")
    sql = "SELECT * FROM proveedores WHERE activo=1 "
    params = []
    if q:
        sql += "AND (nombre LIKE ? OR codigo LIKE ? OR ciudad LIKE ?)"
        params = [f"%{q}%"] * 3
    sql += " ORDER BY nombre"
    provs = fetchall(sql, tuple(params))
    return render_template("compras/proveedores.html", proveedores=provs, q=q)


@bp.route("/proveedores/nuevo", methods=["GET", "POST"])
def proveedor_nuevo():
    if request.method == "POST":
        f = request.form
        codigo = f"PROV-{datetime.now().strftime('%y%m%d%H%M')}"
        execute(
            "INSERT INTO proveedores(codigo,nombre,nif,email,telefono,direccion,ciudad,contacto,plazo_entrega,condiciones_pago) VALUES(?,?,?,?,?,?,?,?,?,?)",
            (codigo, f["nombre"], f.get("nif",""), f.get("email",""), f.get("telefono",""),
             f.get("direccion",""), f.get("ciudad",""), f.get("contacto",""),
             int(f.get("plazo_entrega") or 7), f.get("condiciones_pago","")),
        )
        flash("Proveedor creado", "ok")
        return redirect(url_for("compras.proveedores"))
    return render_template("compras/proveedor_form.html", proveedor=None)


@bp.route("/proveedores/<int:pid>/editar", methods=["GET", "POST"])
def proveedor_editar(pid):
    prov = fetchone("SELECT * FROM proveedores WHERE id=?", (pid,))
    if request.method == "POST":
        f = request.form
        execute(
            "UPDATE proveedores SET nombre=?,nif=?,email=?,telefono=?,direccion=?,ciudad=?,contacto=?,plazo_entrega=?,condiciones_pago=? WHERE id=?",
            (f["nombre"], f.get("nif",""), f.get("email",""), f.get("telefono",""),
             f.get("direccion",""), f.get("ciudad",""), f.get("contacto",""),
             int(f.get("plazo_entrega") or 7), f.get("condiciones_pago",""), pid),
        )
        flash("Proveedor actualizado", "ok")
        return redirect(url_for("compras.proveedores"))
    return render_template("compras/proveedor_form.html", proveedor=prov)


@bp.route("/ordenes")
def ordenes():
    estado = request.args.get("estado", "")
    sql = (
        "SELECT oc.*, p.nombre AS prov_nombre "
        "FROM ordenes_compra oc JOIN proveedores p ON p.id=oc.proveedor_id WHERE 1=1 "
    )
    params = []
    if estado:
        sql += " AND oc.estado=?"
        params.append(estado)
    sql += " ORDER BY oc.creado_en DESC"
    ocs = fetchall(sql, tuple(params))
    proveedores = fetchall("SELECT id, nombre FROM proveedores WHERE activo=1 ORDER BY nombre")
    productos = fetchall("SELECT id, referencia, nombre, unidad, precio_compra FROM productos WHERE activo=1 ORDER BY referencia")
    return render_template("compras/ordenes.html", ordenes=ocs, proveedores=proveedores, productos=productos, estado=estado)


@bp.route("/ordenes/nueva", methods=["POST"])
def orden_nueva():
    f = request.form
    num = f"OC-{datetime.now().strftime('%Y-%m%d%H%M%S')}"
    lineas = json.dumps([{"producto": f.get("prod_nombre",""), "cantidad": float(f.get("cantidad",0)), "precio": float(f.get("precio",0))}])
    total = float(f.get("cantidad",0)) * float(f.get("precio",0))
    execute(
        "INSERT INTO ordenes_compra(numero,proveedor_id,fecha,fecha_entrega_prevista,estado,lineas,total,usuario_id) VALUES(?,?,date('now'),?,?,?,?,?)",
        (num, f["proveedor_id"], f.get("fecha_entrega",""), "borrador", lineas, total, session.get("user_id")),
    )
    flash("Orden de compra creada", "ok")
    return redirect(url_for("compras.ordenes"))


@bp.route("/ordenes/<int:oid>/estado", methods=["POST"])
def orden_estado(oid):
    execute("UPDATE ordenes_compra SET estado=? WHERE id=?", (request.form["estado"], oid))
    flash("Estado actualizado", "ok")
    return redirect(url_for("compras.ordenes"))


@bp.route("/facturas")
def facturas():
    # Show orders received as "invoices"
    ocs = fetchall(
        "SELECT oc.*, p.nombre AS prov_nombre FROM ordenes_compra oc "
        "JOIN proveedores p ON p.id=oc.proveedor_id WHERE oc.estado IN ('recibida','recibida_parcial') ORDER BY oc.creado_en DESC"
    )
    return render_template("compras/facturas.html", facturas=ocs)


@bp.route("/materias")
def materias():
    productos = fetchall(
        "SELECT p.*, c.nombre AS cat_nombre FROM productos p JOIN categorias c ON c.id=p.categoria_id WHERE c.tipo='MP' AND p.activo=1 ORDER BY p.referencia"
    )
    return render_template("compras/materias.html", productos=productos)
