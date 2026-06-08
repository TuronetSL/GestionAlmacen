from __future__ import annotations
import json
from datetime import date, datetime
from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from ..db import fetchall, fetchone, execute, scalar

bp = Blueprint("almacen", __name__, url_prefix="/almacen")


@bp.route("/")
def index():
    return redirect(url_for("almacen.inventario"))


@bp.route("/inventario")
def inventario():
    search = request.args.get("q", "")
    tipo = request.args.get("tipo", "")
    sql = (
        "SELECT p.*, c.nombre AS cat_nombre, c.tipo AS cat_tipo "
        "FROM productos p LEFT JOIN categorias c ON c.id=p.categoria_id "
        "WHERE p.activo=1 "
    )
    params: list = []
    if search:
        sql += " AND (p.referencia LIKE ? OR p.nombre LIKE ?)"
        params += [f"%{search}%", f"%{search}%"]
    if tipo:
        sql += " AND c.tipo=?"
        params.append(tipo)
    sql += " ORDER BY p.referencia"
    productos = fetchall(sql, tuple(params))
    categorias = fetchall("SELECT * FROM categorias ORDER BY nombre")
    return render_template("almacen/inventario.html", productos=productos, categorias=categorias, search=search, tipo=tipo)


@bp.route("/inventario/nuevo", methods=["GET", "POST"])
def inventario_nuevo():
    categorias = fetchall("SELECT * FROM categorias ORDER BY nombre")
    if request.method == "POST":
        f = request.form
        execute(
            "INSERT INTO productos(referencia,nombre,descripcion,categoria_id,unidad,stock_actual,stock_minimo,stock_maximo,ubicacion,precio_compra) VALUES(?,?,?,?,?,?,?,?,?,?)",
            (f["referencia"], f["nombre"], f.get("descripcion",""), f["categoria_id"], f["unidad"],
             float(f.get("stock_actual") or 0), float(f.get("stock_minimo") or 0),
             float(f.get("stock_maximo") or 0), f.get("ubicacion",""), float(f.get("precio_compra") or 0)),
        )
        _log("Producto creado", "Almacén", f"Nuevo producto {f['referencia']} — {f['nombre']}")
        flash("Producto creado correctamente", "ok")
        return redirect(url_for("almacen.inventario"))
    return render_template("almacen/inventario_form.html", producto=None, categorias=categorias, accion="nuevo")


@bp.route("/inventario/<int:pid>/editar", methods=["GET", "POST"])
def inventario_editar(pid):
    producto = fetchone("SELECT * FROM productos WHERE id=?", (pid,))
    categorias = fetchall("SELECT * FROM categorias ORDER BY nombre")
    if not producto:
        flash("Producto no encontrado", "err")
        return redirect(url_for("almacen.inventario"))
    if request.method == "POST":
        f = request.form
        execute(
            "UPDATE productos SET nombre=?,descripcion=?,categoria_id=?,unidad=?,stock_minimo=?,stock_maximo=?,ubicacion=?,precio_compra=? WHERE id=?",
            (f["nombre"], f.get("descripcion",""), f["categoria_id"], f["unidad"],
             float(f.get("stock_minimo") or 0), float(f.get("stock_maximo") or 0),
             f.get("ubicacion",""), float(f.get("precio_compra") or 0), pid),
        )
        _log("Producto editado", "Almacén", f"Producto {producto['referencia']} actualizado")
        flash("Producto actualizado", "ok")
        return redirect(url_for("almacen.inventario"))
    return render_template("almacen/inventario_form.html", producto=producto, categorias=categorias, accion="editar")


@bp.route("/inventario/<int:pid>")
def inventario_detalle(pid):
    producto = fetchone(
        "SELECT p.*, c.nombre AS cat_nombre FROM productos p LEFT JOIN categorias c ON c.id=p.categoria_id WHERE p.id=?", (pid,)
    )
    lotes = fetchall("SELECT * FROM lotes WHERE producto_id=? ORDER BY fecha_caducidad", (pid,))
    movimientos = fetchall(
        "SELECT m.*, u.nombre||' '||u.apellidos AS usu FROM movimientos m "
        "LEFT JOIN usuarios u ON u.id=m.usuario_id WHERE m.producto_id=? ORDER BY m.fecha DESC LIMIT 20", (pid,)
    )
    return render_template("almacen/inventario_detalle.html", producto=producto, lotes=lotes, movimientos=movimientos)


@bp.route("/entradas", methods=["GET"])
def entradas():
    movimientos = fetchall(
        "SELECT m.*, p.referencia, p.nombre AS prod_nombre, p.unidad, u.nombre||' '||u.apellidos AS usu_nombre "
        "FROM movimientos m JOIN productos p ON p.id=m.producto_id "
        "LEFT JOIN usuarios u ON u.id=m.usuario_id "
        "WHERE m.tipo='entrada' ORDER BY m.fecha DESC LIMIT 50"
    )
    productos = fetchall("SELECT id,referencia,nombre,unidad FROM productos WHERE activo=1 ORDER BY referencia")
    return render_template("almacen/entradas.html", movimientos=movimientos, productos=productos)


@bp.route("/entradas/nueva", methods=["POST"])
def entrada_nueva():
    f = request.form
    pid = int(f["producto_id"])
    cantidad = float(f["cantidad"])
    lote_num = f.get("numero_lote", "").strip()
    caducidad = f.get("fecha_caducidad", "") or None

    lote_id = None
    if lote_num:
        existing = fetchone("SELECT id FROM lotes WHERE numero=?", (lote_num,))
        if not existing:
            lote_id = execute(
                "INSERT INTO lotes(numero,producto_id,cantidad,cantidad_disponible,fecha_entrada,fecha_caducidad) VALUES(?,?,?,?,date('now'),?)",
                (lote_num, pid, cantidad, cantidad, caducidad),
            )
        else:
            lote_id = existing["id"]
            execute("UPDATE lotes SET cantidad=cantidad+?, cantidad_disponible=cantidad_disponible+? WHERE id=?",
                    (cantidad, cantidad, lote_id))

    execute(
        "INSERT INTO movimientos(tipo,producto_id,lote_id,cantidad,ubicacion_destino,referencia_doc,usuario_id,departamento,notas,fecha) VALUES('entrada',?,?,?,?,?,?,?,?,datetime('now'))",
        (pid, lote_id, cantidad, f.get("ubicacion",""), f.get("referencia_doc",""), session.get("user_id"), "Almacén", f.get("notas","")),
    )
    execute("UPDATE productos SET stock_actual=stock_actual+? WHERE id=?", (cantidad, pid))
    _log("Entrada registrada", "Almacén", f"Entrada {cantidad} uds producto_id={pid}")
    flash("Entrada registrada correctamente", "ok")
    return redirect(url_for("almacen.entradas"))


@bp.route("/salidas", methods=["GET"])
def salidas():
    movimientos = fetchall(
        "SELECT m.*, p.referencia, p.nombre AS prod_nombre, p.unidad, u.nombre||' '||u.apellidos AS usu_nombre "
        "FROM movimientos m JOIN productos p ON p.id=m.producto_id "
        "LEFT JOIN usuarios u ON u.id=m.usuario_id "
        "WHERE m.tipo='salida' ORDER BY m.fecha DESC LIMIT 50"
    )
    productos = fetchall("SELECT id,referencia,nombre,unidad,stock_actual FROM productos WHERE activo=1 AND stock_actual>0 ORDER BY referencia")
    return render_template("almacen/salidas.html", movimientos=movimientos, productos=productos)


@bp.route("/salidas/nueva", methods=["POST"])
def salida_nueva():
    f = request.form
    pid = int(f["producto_id"])
    cantidad = float(f["cantidad"])
    prod = fetchone("SELECT stock_actual FROM productos WHERE id=?", (pid,))
    if not prod or prod["stock_actual"] < cantidad:
        flash("Stock insuficiente", "err")
        return redirect(url_for("almacen.salidas"))
    execute(
        "INSERT INTO movimientos(tipo,producto_id,cantidad,ubicacion_origen,referencia_doc,usuario_id,departamento,notas,fecha) VALUES('salida',?,?,?,?,?,?,?,datetime('now'))",
        (pid, cantidad, f.get("ubicacion",""), f.get("referencia_doc",""), session.get("user_id"), f.get("departamento","Almacén"), f.get("notas","")),
    )
    execute("UPDATE productos SET stock_actual=stock_actual-? WHERE id=?", (cantidad, pid))
    _log("Salida registrada", "Almacén", f"Salida {cantidad} uds producto_id={pid}")
    flash("Salida registrada correctamente", "ok")
    return redirect(url_for("almacen.salidas"))


@bp.route("/traspasos", methods=["GET"])
def traspasos():
    movimientos = fetchall(
        "SELECT m.*, p.referencia, p.nombre AS prod_nombre, p.unidad "
        "FROM movimientos m JOIN productos p ON p.id=m.producto_id "
        "WHERE m.tipo='traspaso' ORDER BY m.fecha DESC LIMIT 50"
    )
    productos = fetchall("SELECT id,referencia,nombre,unidad,stock_actual FROM productos WHERE activo=1 ORDER BY referencia")
    ubicaciones = fetchall("SELECT codigo,zona,pasillo,estante FROM ubicaciones ORDER BY codigo")
    return render_template("almacen/traspasos.html", movimientos=movimientos, productos=productos, ubicaciones=ubicaciones)


@bp.route("/traspasos/nuevo", methods=["POST"])
def traspaso_nuevo():
    f = request.form
    pid = int(f["producto_id"])
    cantidad = float(f["cantidad"])
    execute(
        "INSERT INTO movimientos(tipo,producto_id,cantidad,ubicacion_origen,ubicacion_destino,usuario_id,departamento,notas,fecha) VALUES('traspaso',?,?,?,?,?,?,?,datetime('now'))",
        (pid, cantidad, f.get("origen",""), f.get("destino",""), session.get("user_id"), "Almacén", f.get("notas","")),
    )
    _log("Traspaso registrado", "Almacén", f"Traspaso {cantidad} uds {f.get('origen')} → {f.get('destino')}")
    flash("Traspaso registrado", "ok")
    return redirect(url_for("almacen.traspasos"))


@bp.route("/lotes")
def lotes():
    search = request.args.get("q", "")
    estado = request.args.get("estado", "")
    sql = (
        "SELECT l.*, p.referencia, p.nombre AS prod_nombre, p.unidad "
        "FROM lotes l JOIN productos p ON p.id=l.producto_id WHERE 1=1 "
    )
    params = []
    if search:
        sql += " AND (l.numero LIKE ? OR p.nombre LIKE ?)"
        params += [f"%{search}%", f"%{search}%"]
    if estado:
        sql += " AND l.estado=?"
        params.append(estado)
    sql += " ORDER BY l.fecha_caducidad NULLS LAST, l.creado_en DESC"
    lotes_list = fetchall(sql, tuple(params))
    return render_template("almacen/lotes.html", lotes=lotes_list, search=search, estado=estado)


@bp.route("/caducidades")
def caducidades():
    caducados = fetchall(
        "SELECT l.*, p.referencia, p.nombre AS prod_nombre, p.unidad "
        "FROM lotes l JOIN productos p ON p.id=l.producto_id "
        "WHERE date(l.fecha_caducidad) < date('now') AND l.estado='activo' ORDER BY l.fecha_caducidad"
    )
    proximos_7 = fetchall(
        "SELECT l.*, p.referencia, p.nombre AS prod_nombre, p.unidad "
        "FROM lotes l JOIN productos p ON p.id=l.producto_id "
        "WHERE date(l.fecha_caducidad) BETWEEN date('now') AND date('now','+7 days') AND l.estado='activo' ORDER BY l.fecha_caducidad"
    )
    proximos_30 = fetchall(
        "SELECT l.*, p.referencia, p.nombre AS prod_nombre, p.unidad "
        "FROM lotes l JOIN productos p ON p.id=l.producto_id "
        "WHERE date(l.fecha_caducidad) BETWEEN date('now','+8 days') AND date('now','+30 days') AND l.estado='activo' ORDER BY l.fecha_caducidad"
    )
    return render_template("almacen/caducidades.html", caducados=caducados, proximos_7=proximos_7, proximos_30=proximos_30)


@bp.route("/ubicaciones")
def ubicaciones():
    zonas = fetchall(
        "SELECT zona, COUNT(*) AS total, SUM(capacidad_kg) AS cap, SUM(ocupado_kg) AS ocu "
        "FROM ubicaciones GROUP BY zona ORDER BY zona"
    )
    detalle = fetchall("SELECT * FROM ubicaciones ORDER BY zona, pasillo, estante")
    return render_template("almacen/ubicaciones.html", zonas=zonas, detalle=detalle)


def _log(accion, modulo, desc):
    execute(
        "INSERT INTO logs_actividad(usuario_id,username,accion,modulo,descripcion,ip,nivel) VALUES(?,?,?,?,?,?,?)",
        (session.get("user_id"), session.get("username"), accion, modulo, desc, "127.0.0.1", "INFO"),
    )
