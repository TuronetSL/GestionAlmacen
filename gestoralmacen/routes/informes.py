from __future__ import annotations
from flask import Blueprint, render_template
from ..db import fetchall, scalar

bp = Blueprint("informes", __name__, url_prefix="/informes")


@bp.route("/")
def index():
    return dashboard()


@bp.route("/dashboard")
def dashboard():
    kpis = {
        "ventas_mes": scalar("SELECT COALESCE(SUM(total),0) FROM pedidos_venta WHERE strftime('%Y-%m',fecha)=strftime('%Y-%m','now')") or 0,
        "compras_mes": scalar("SELECT COALESCE(SUM(total),0) FROM ordenes_compra WHERE strftime('%Y-%m',creado_en)=strftime('%Y-%m','now')") or 0,
        "ofs_mes": scalar("SELECT COUNT(*) FROM ordenes_fabricacion WHERE strftime('%Y-%m',creado_en)=strftime('%Y-%m','now')") or 0,
        "nc_mes": scalar("SELECT COUNT(*) FROM no_conformidades WHERE strftime('%Y-%m',fecha_apertura)=strftime('%Y-%m','now')") or 0,
        "empleados_activos": scalar("SELECT COUNT(*) FROM empleados WHERE estado='activo'") or 0,
        "stock_valor": scalar("SELECT COALESCE(SUM(stock_actual*precio_compra),0) FROM productos WHERE activo=1") or 0,
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
        kpis=kpis,
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
