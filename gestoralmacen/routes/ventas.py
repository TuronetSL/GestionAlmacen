from __future__ import annotations
import json
from datetime import datetime
from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from ..db import fetchall, fetchone, execute

bp = Blueprint("ventas", __name__, url_prefix="/ventas")


@bp.route("/")
def index():
    return redirect(url_for("ventas.pedidos"))


@bp.route("/clientes")
def clientes():
    q = request.args.get("q", "")
    sql = "SELECT * FROM clientes WHERE activo=1 "
    params = []
    if q:
        sql += "AND (nombre LIKE ? OR codigo LIKE ? OR ciudad LIKE ?)"
        params = [f"%{q}%"] * 3
    clts = fetchall(sql + " ORDER BY nombre", tuple(params))
    return render_template("ventas/clientes.html", clientes=clts, q=q)


@bp.route("/clientes/nuevo", methods=["GET", "POST"])
def cliente_nuevo():
    if request.method == "POST":
        f = request.form
        codigo = f"CLI-{datetime.now().strftime('%y%m%d%H%M')}"
        execute(
            "INSERT INTO clientes(codigo,nombre,nif,email,telefono,direccion,ciudad,contacto,condiciones_pago,descuento_pct) VALUES(?,?,?,?,?,?,?,?,?,?)",
            (codigo, f["nombre"], f.get("nif",""), f.get("email",""), f.get("telefono",""),
             f.get("direccion",""), f.get("ciudad",""), f.get("contacto",""),
             f.get("condiciones_pago","30 días"), float(f.get("descuento_pct") or 0)),
        )
        flash("Cliente creado", "ok")
        return redirect(url_for("ventas.clientes"))
    return render_template("ventas/cliente_form.html", cliente=None)


@bp.route("/clientes/<int:cid>/editar", methods=["GET", "POST"])
def cliente_editar(cid):
    cli = fetchone("SELECT * FROM clientes WHERE id=?", (cid,))
    if request.method == "POST":
        f = request.form
        execute(
            "UPDATE clientes SET nombre=?,nif=?,email=?,telefono=?,direccion=?,ciudad=?,contacto=?,condiciones_pago=?,descuento_pct=? WHERE id=?",
            (f["nombre"], f.get("nif",""), f.get("email",""), f.get("telefono",""),
             f.get("direccion",""), f.get("ciudad",""), f.get("contacto",""),
             f.get("condiciones_pago",""), float(f.get("descuento_pct") or 0), cid),
        )
        flash("Cliente actualizado", "ok")
        return redirect(url_for("ventas.clientes"))
    return render_template("ventas/cliente_form.html", cliente=cli)


@bp.route("/pedidos")
def pedidos():
    estado = request.args.get("estado", "")
    sql = (
        "SELECT pv.*, c.nombre AS cli_nombre "
        "FROM pedidos_venta pv JOIN clientes c ON c.id=pv.cliente_id WHERE 1=1 "
    )
    params = []
    if estado:
        sql += " AND pv.estado=?"
        params.append(estado)
    pvs = fetchall(sql + " ORDER BY pv.creado_en DESC", tuple(params))
    clientes = fetchall("SELECT id, nombre FROM clientes WHERE activo=1 ORDER BY nombre")
    productos = fetchall("SELECT p.id, p.referencia, p.nombre, p.unidad FROM productos p JOIN categorias c ON c.id=p.categoria_id WHERE c.tipo='PT' AND p.activo=1 ORDER BY p.referencia")
    return render_template("ventas/pedidos.html", pedidos=pvs, clientes=clientes, productos=productos, estado=estado)


@bp.route("/pedidos/nuevo", methods=["POST"])
def pedido_nuevo():
    f = request.form
    num = f"PV-{datetime.now().strftime('%Y-%m%d%H%M%S')}"
    lineas = json.dumps([{"producto": f.get("prod_nombre",""), "cantidad": float(f.get("cantidad",0)), "precio": float(f.get("precio",0))}])
    total = float(f.get("cantidad",0)) * float(f.get("precio",0))
    execute(
        "INSERT INTO pedidos_venta(numero,cliente_id,fecha,fecha_entrega,estado,lineas,total,usuario_id) VALUES(?,?,date('now'),?,'pendiente',?,?,?)",
        (num, f["cliente_id"], f.get("fecha_entrega",""), lineas, total, session.get("user_id")),
    )
    flash("Pedido de venta creado", "ok")
    return redirect(url_for("ventas.pedidos"))


@bp.route("/pedidos/<int:pid>/estado", methods=["POST"])
def pedido_estado(pid):
    execute("UPDATE pedidos_venta SET estado=? WHERE id=?", (request.form["estado"], pid))
    flash("Estado actualizado", "ok")
    return redirect(url_for("ventas.pedidos"))


@bp.route("/albaranes")
def albaranes():
    albs = fetchall(
        "SELECT a.*, pv.numero AS pv_num, c.nombre AS cli_nombre "
        "FROM albaranes a LEFT JOIN pedidos_venta pv ON pv.id=a.pedido_id "
        "LEFT JOIN clientes c ON c.id=pv.cliente_id ORDER BY a.creado_en DESC"
    )
    pedidos = fetchall("SELECT id, numero FROM pedidos_venta WHERE estado IN ('confirmado','en_preparacion') ORDER BY numero")
    return render_template("ventas/albaranes.html", albaranes=albs, pedidos=pedidos)


@bp.route("/devoluciones")
def devoluciones():
    devs = fetchall(
        "SELECT m.*, p.referencia, p.nombre AS prod_nombre FROM movimientos m "
        "JOIN productos p ON p.id=m.producto_id WHERE m.tipo='devolucion' ORDER BY m.fecha DESC"
    )
    return render_template("ventas/devoluciones.html", devoluciones=devs)
