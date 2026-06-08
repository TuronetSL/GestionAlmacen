"""Flask application factory and main route registration."""
from __future__ import annotations

import json
import os
from datetime import datetime
from functools import wraps

from flask import Flask, g, redirect, render_template, request, session, url_for, jsonify, flash

from . import db as database


def _fmt_date(value, fmt="%d/%m/%Y"):
    """Jinja2 filter: format a string or datetime as a readable date."""
    if not value:
        return "—"
    if isinstance(value, str):
        for pattern in ("%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M:%S", "%Y-%m-%d"):
            try:
                value = datetime.strptime(value[:19], pattern)
                break
            except ValueError:
                continue
        else:
            return value
    try:
        return value.strftime(fmt)
    except Exception:
        return str(value)


def create_app() -> Flask:
    app = Flask(__name__, template_folder="templates", static_folder="static")
    app.secret_key = os.environ.get("SECRET_KEY", "gestor-almacen-quimicasur-2024-secret")
    app.config["SESSION_COOKIE_HTTPONLY"] = True

    # Custom Jinja2 filters
    app.jinja_env.filters["fecha"] = lambda v: _fmt_date(v, "%d/%m/%Y")
    app.jinja_env.filters["fechahora"] = lambda v: _fmt_date(v, "%d/%m/%Y %H:%M")
    app.jinja_env.filters["hora"] = lambda v: _fmt_date(v, "%H:%M")

    def _days_until(value):
        from datetime import datetime, date
        if not value:
            return 999
        if isinstance(value, str):
            try:
                value = datetime.strptime(value[:10], "%Y-%m-%d").date()
            except ValueError:
                return 999
        if isinstance(value, datetime):
            value = value.date()
        return (value - date.today()).days

    app.jinja_env.filters["days_until"] = _days_until

    # Initialise DB
    database.init_db()

    # ── Auth helpers ──────────────────────────────────────────────────────────

    def login_required(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            if "user_id" not in session:
                return redirect(url_for("auth_login"))
            return f(*args, **kwargs)
        return wrapper

    def get_current_user():
        if "user_id" not in session:
            return None
        return database.fetchone(
            "SELECT u.*, r.nombre AS rol_nombre, r.permisos FROM usuarios u "
            "LEFT JOIN roles r ON r.id = u.rol_id WHERE u.id = ?",
            (session["user_id"],),
        )

    # ── Context processor ────────────────────────────────────────────────────

    @app.context_processor
    def inject_globals():
        user = get_current_user()
        alerts = []
        if user:
            # Stock bajo mínimo
            low = database.scalar(
                "SELECT COUNT(*) FROM productos WHERE stock_actual <= stock_minimo AND activo=1"
            )
            # Caducidades próximas 30 días
            exp = database.scalar(
                "SELECT COUNT(*) FROM lotes WHERE fecha_caducidad IS NOT NULL "
                "AND date(fecha_caducidad) <= date('now','+30 days') "
                "AND date(fecha_caducidad) >= date('now') AND estado='activo'"
            )
            # NC abiertas
            nc = database.scalar(
                "SELECT COUNT(*) FROM no_conformidades WHERE estado IN ('abierta','en_investigacion')"
            )
            # OC pendientes
            oc = database.scalar(
                "SELECT COUNT(*) FROM ordenes_compra WHERE estado IN ('borrador','enviada','confirmada')"
            )
            alerts = {"stock_bajo": low, "caducidades": exp, "nc": nc, "oc_pendientes": oc}
        return {"current_user": user, "alerts": alerts, "now": datetime.now()}

    # ── Auth routes ──────────────────────────────────────────────────────────

    @app.route("/")
    def index():
        if "user_id" in session:
            return redirect(url_for("dashboard"))
        return redirect(url_for("auth_login"))

    @app.route("/login", methods=["GET", "POST"])
    def auth_login():
        if "user_id" in session:
            return redirect(url_for("dashboard"))
        error = None
        if request.method == "POST":
            username = request.form.get("username", "").strip()
            password = request.form.get("password", "")
            user = database.fetchone(
                "SELECT * FROM usuarios WHERE (username=? OR email=?) AND activo=1",
                (username, username),
            )
            if user and user["password_hash"] == database._hash(password):
                session["user_id"] = user["id"]
                session["username"] = user["username"]
                session.permanent = True
                database.execute(
                    "UPDATE usuarios SET ultimo_acceso=datetime('now') WHERE id=?", (user["id"],)
                )
                database.execute(
                    "INSERT INTO logs_actividad(usuario_id,username,accion,modulo,descripcion,ip,nivel) VALUES(?,?,?,?,?,?,?)",
                    (user["id"], user["username"], "Login", "Acceso", f"Sesión iniciada desde {request.remote_addr}", request.remote_addr, "INFO"),
                )
                return redirect(url_for("dashboard"))
            error = "Usuario o contraseña incorrectos"
        return render_template("login.html", error=error)

    @app.route("/logout")
    def auth_logout():
        if "user_id" in session:
            database.execute(
                "INSERT INTO logs_actividad(usuario_id,username,accion,modulo,descripcion,ip,nivel) VALUES(?,?,?,?,?,?,?)",
                (session.get("user_id"), session.get("username"), "Logout", "Acceso", "Sesión cerrada", request.remote_addr, "INFO"),
            )
        session.clear()
        return redirect(url_for("auth_login"))

    # ── Dashboard ─────────────────────────────────────────────────────────────

    @app.route("/dashboard")
    @login_required
    def dashboard():
        today = datetime.now().strftime("%Y-%m-%d")
        kpis = {
            "total_referencias": database.scalar("SELECT COUNT(*) FROM productos WHERE activo=1"),
            "entradas_hoy": database.scalar("SELECT COUNT(*) FROM movimientos WHERE tipo='entrada' AND date(fecha)=date('now')") or 0,
            "salidas_hoy": database.scalar("SELECT COUNT(*) FROM movimientos WHERE tipo='salida' AND date(fecha)=date('now')") or 0,
            "lotes_fabricacion": database.scalar("SELECT COUNT(*) FROM ordenes_fabricacion WHERE estado='en_proceso'") or 0,
            "caducidades_30": database.scalar("SELECT COUNT(*) FROM lotes WHERE fecha_caducidad IS NOT NULL AND date(fecha_caducidad) <= date('now','+30 days') AND date(fecha_caducidad) >= date('now') AND estado='activo'") or 0,
            "stock_bajo": database.scalar("SELECT COUNT(*) FROM productos WHERE stock_actual <= stock_minimo AND activo=1") or 0,
            "nc_abiertas": database.scalar("SELECT COUNT(*) FROM no_conformidades WHERE estado IN ('abierta','en_investigacion')") or 0,
            "oc_pendientes": database.scalar("SELECT COUNT(*) FROM ordenes_compra WHERE estado IN ('enviada','confirmada')") or 0,
        }
        movimientos = database.fetchall(
            "SELECT m.*, p.referencia, p.nombre AS prod_nombre, u.nombre||' '||u.apellidos AS usuario_nombre "
            "FROM movimientos m "
            "JOIN productos p ON p.id=m.producto_id "
            "LEFT JOIN usuarios u ON u.id=m.usuario_id "
            "ORDER BY m.fecha DESC LIMIT 8"
        )
        logs = database.fetchall(
            "SELECT * FROM logs_actividad ORDER BY fecha DESC LIMIT 6"
        )
        zonas = database.fetchall(
            "SELECT zona, SUM(capacidad_kg) AS cap, SUM(ocupado_kg) AS ocu FROM ubicaciones GROUP BY zona ORDER BY zona"
        )
        productos_bajo_stock = database.fetchall(
            "SELECT p.*, c.nombre AS cat_nombre FROM productos p "
            "LEFT JOIN categorias c ON c.id=p.categoria_id "
            "WHERE p.stock_actual <= p.stock_minimo AND p.activo=1 LIMIT 5"
        )
        return render_template(
            "dashboard.html",
            kpis=kpis,
            movimientos=movimientos,
            logs=logs,
            zonas=zonas,
            productos_bajo_stock=productos_bajo_stock,
        )

    # ── Register blueprints ──────────────────────────────────────────────────
    from .routes.almacen import bp as almacen_bp
    from .routes.produccion import bp as prod_bp
    from .routes.compras import bp as compras_bp
    from .routes.ventas import bp as ventas_bp
    from .routes.calidad import bp as calidad_bp
    from .routes.rrhh import bp as rrhh_bp
    from .routes.mantenimiento import bp as mant_bp
    from .routes.informes import bp as inf_bp
    from .routes.sistemas import bp as sis_bp

    for bp in [almacen_bp, prod_bp, compras_bp, ventas_bp, calidad_bp, rrhh_bp, mant_bp, inf_bp, sis_bp]:
        app.register_blueprint(bp)

    # Attach login_required decorator to blueprints
    @app.before_request
    def require_login():
        open_routes = {"auth_login", "auth_logout", "static"}
        if request.endpoint and request.endpoint not in open_routes and "user_id" not in session:
            return redirect(url_for("auth_login"))

    return app
