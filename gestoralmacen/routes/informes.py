from __future__ import annotations
from flask import Blueprint, render_template
from ..db import fetchall, scalar

bp = Blueprint("informes", __name__, url_prefix="/informes")


@bp.route("/")
def index():
    return dashboard()


@bp.route("/dashboard")
def dashboard():
    kpi = {
        "entradas": scalar("SELECT COUNT(*) FROM movimientos WHERE tipo='entrada' AND date(fecha) >= date('now','-30 days')") or 0,
        "salidas": scalar("SELECT COUNT(*) FROM movimientos WHERE tipo='salida' AND date(fecha) >= date('now','-30 days')") or 0,
        "of_completadas": scalar("SELECT COUNT(*) FROM ordenes_fabricacion WHERE estado='completada'") or 0,
        "pedidos_enviados": scalar("SELECT COUNT(*) FROM pedidos_venta WHERE estado='enviado'") or 0,
        "nc_abiertas": scalar("SELECT COUNT(*) FROM no_conformidades WHERE estado IN ('abierta','en_investigacion')") or 0,
        "ot_abiertas": scalar("SELECT COUNT(*) FROM ordenes_mantenimiento WHERE estado IN ('pendiente','en_curso')") or 0,
    }
    top_productos = fetchall(
        "SELECT p.nombre, p.unidad, SUM(m.cantidad) AS total_mov "
        "FROM movimientos m JOIN productos p ON p.id=m.producto_id "
        "GROUP BY p.id ORDER BY total_mov DESC LIMIT 5"
    )
    mov_por_tipo = fetchall(
        "SELECT tipo, COUNT(*) AS cnt, COALESCE(SUM(cantidad),0) AS total "
        "FROM movimientos WHERE date(fecha) >= date('now','-30 days') GROUP BY tipo"
    )
    nc_por_severidad = fetchall(
        "SELECT severidad, COUNT(*) AS cnt FROM no_conformidades GROUP BY severidad"
    )
    stock_por_zona = fetchall(
        "SELECT zona, ROUND(AVG(CASE WHEN capacidad_kg>0 THEN ocupado_kg*100.0/capacidad_kg ELSE 0 END),1) AS pct "
        "FROM ubicaciones GROUP BY zona ORDER BY zona"
    )
    return render_template(
        "informes/dashboard.html",
        kpi=kpi,
        top_productos=top_productos,
        mov_por_tipo=mov_por_tipo,
        nc_por_severidad=nc_por_severidad,
        stock_por_zona=stock_por_zona,
    )


@bp.route("/personalizados")
def personalizados():
    return render_template("informes/personalizados.html")


@bp.route("/exportar")
def exportar():
    return render_template("informes/exportar.html")
