from __future__ import annotations

from datetime import date, timedelta
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from biblioteca.db import get_connection, init_db

DB_PATH = Path("data/biblioteca.sqlite")


def base_layout(content: str, notice: str = "") -> bytes:
    return f"""<!doctype html>
<html lang='es'>
<head>
  <meta charset='utf-8'>
  <meta name='viewport' content='width=device-width, initial-scale=1'>
  <title>Biblioteca del Pueblo</title>
  <link rel='stylesheet' href='/static/style.css'>
</head>
<body>
<header>
  <h1>📚 Biblioteca de Mi Pueblo</h1>
  <nav>
    <a href='/'>Inicio</a>
    <a href='/libros'>Libros</a>
    <a href='/socios'>Socios</a>
    <a href='/prestamos'>Préstamos</a>
  </nav>
</header>
<main>{f"<p class='notice'>{notice}</p>" if notice else ''}{content}</main>
</body>
</html>""".encode("utf-8")


class BibliotecaHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        parsed = urlparse(self.path)
        if parsed.path.startswith("/static/"):
            return self.serve_static(parsed.path)
        if parsed.path == "/":
            return self.send_html(self.render_home())
        if parsed.path == "/libros":
            return self.send_html(self.render_libros())
        if parsed.path == "/socios":
            return self.send_html(self.render_socios())
        if parsed.path == "/prestamos":
            return self.send_html(self.render_prestamos())
        return self.send_error(HTTPStatus.NOT_FOUND)

    def do_POST(self):
        parsed = urlparse(self.path)
        length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(length).decode("utf-8")
        data = {k: v[0] for k, v in parse_qs(body).items()}

        if parsed.path == "/libros":
            self.crear_libro(data)
            return self.redirect("/libros?msg=Libro+añadido")
        if parsed.path == "/socios":
            self.crear_socio(data)
            return self.redirect("/socios?msg=Socio+registrado")
        if parsed.path == "/prestamos":
            ok = self.crear_prestamo(data)
            return self.redirect("/prestamos?msg=" + ("Préstamo+creado" if ok else "Sin+copias+disponibles"))
        if parsed.path.startswith("/prestamos/") and parsed.path.endswith("/devolver"):
            prestamo_id = int(parsed.path.split("/")[2])
            self.devolver_prestamo(prestamo_id)
            return self.redirect("/prestamos?msg=Libro+devuelto")
        return self.send_error(HTTPStatus.NOT_FOUND)

    def serve_static(self, path: str):
        file_path = Path("biblioteca") / path.removeprefix("/static/")
        if not file_path.exists():
            return self.send_error(404)
        self.send_response(200)
        self.send_header("Content-type", "text/css")
        self.end_headers()
        self.wfile.write(file_path.read_bytes())

    def send_html(self, body: bytes, status=200):
        self.send_response(status)
        self.send_header("Content-type", "text/html; charset=utf-8")
        self.end_headers()
        self.wfile.write(body)

    def redirect(self, location: str):
        self.send_response(303)
        self.send_header("Location", location)
        self.end_headers()

    def db(self):
        return get_connection(DB_PATH)

    def query_msg(self):
        query = parse_qs(urlparse(self.path).query)
        return query.get("msg", [""])[0].replace("+", " ")

    def render_home(self) -> bytes:
        with self.db() as conn:
            stats = {
                "libros": conn.execute("SELECT COUNT(*) c FROM libros").fetchone()["c"],
                "socios": conn.execute("SELECT COUNT(*) c FROM socios").fetchone()["c"],
                "prestamos": conn.execute("SELECT COUNT(*) c FROM prestamos WHERE estado != 'devuelto'").fetchone()["c"],
            }
            atrasados = conn.execute(
                """SELECT p.id, l.titulo, s.nombre, p.fecha_limite
                FROM prestamos p JOIN libros l ON l.id=p.libro_id JOIN socios s ON s.id=p.socio_id
                WHERE p.estado='atrasado' ORDER BY p.fecha_limite ASC"""
            ).fetchall()
        rows = "".join(
            f"<tr><td>{r['id']}</td><td>{r['titulo']}</td><td>{r['nombre']}</td><td>{r['fecha_limite']}</td></tr>"
            for r in atrasados
        )
        content = f"""
<section class='cards'>
 <article><h2>{stats['libros']}</h2><p>Libros</p></article>
 <article><h2>{stats['socios']}</h2><p>Socios</p></article>
 <article><h2>{stats['prestamos']}</h2><p>Préstamos activos</p></article>
</section>
<h3>Préstamos atrasados</h3>
<table><tr><th>ID</th><th>Libro</th><th>Socio</th><th>Límite</th></tr>{rows or "<tr><td colspan='4'>Sin atrasos</td></tr>"}</table>
"""
        return base_layout(content, self.query_msg())

    def render_libros(self) -> bytes:
        with self.db() as conn:
            libros = conn.execute("SELECT * FROM libros ORDER BY creado_en DESC").fetchall()
        rows = "".join(
            f"<tr><td>{l['titulo']}</td><td>{l['autor']}</td><td>{l['categoria']}</td><td>{l['isbn']}</td><td>{l['copias_disponibles']}/{l['total_copias']}</td></tr>"
            for l in libros
        )
        content = f"""
<h2>Libros</h2>
<form method='post' class='grid-form'>
<input name='titulo' placeholder='Título' required>
<input name='autor' placeholder='Autor' required>
<input name='categoria' placeholder='Categoría' required>
<input name='isbn' placeholder='ISBN' required>
<input type='number' min='1' name='total_copias' placeholder='Copias' required>
<button>Añadir libro</button>
</form>
<table><tr><th>Título</th><th>Autor</th><th>Categoría</th><th>ISBN</th><th>Disponible</th></tr>{rows}</table>
"""
        return base_layout(content, self.query_msg())

    def render_socios(self) -> bytes:
        with self.db() as conn:
            socios = conn.execute("SELECT * FROM socios ORDER BY creado_en DESC").fetchall()
        rows = "".join(
            f"<tr><td>{s['nombre']}</td><td>{s['email']}</td><td>{s['telefono'] or ''}</td><td>{s['direccion'] or ''}</td></tr>"
            for s in socios
        )
        content = f"""
<h2>Socios</h2>
<form method='post' class='grid-form'>
<input name='nombre' placeholder='Nombre' required>
<input type='email' name='email' placeholder='Email' required>
<input name='telefono' placeholder='Teléfono'>
<input name='direccion' placeholder='Dirección'>
<button>Registrar socio</button>
</form>
<table><tr><th>Nombre</th><th>Email</th><th>Teléfono</th><th>Dirección</th></tr>{rows}</table>
"""
        return base_layout(content, self.query_msg())

    def render_prestamos(self) -> bytes:
        with self.db() as conn:
            conn.execute("UPDATE prestamos SET estado='atrasado' WHERE estado='activo' AND date(fecha_limite) < date('now')")
            conn.commit()
            prestamos = conn.execute(
                """SELECT p.*, l.titulo, s.nombre FROM prestamos p
                JOIN libros l ON l.id=p.libro_id JOIN socios s ON s.id=p.socio_id ORDER BY p.fecha_prestamo DESC"""
            ).fetchall()
            libros = conn.execute("SELECT id,titulo,copias_disponibles FROM libros ORDER BY titulo").fetchall()
            socios = conn.execute("SELECT id,nombre FROM socios ORDER BY nombre").fetchall()
        options_libros = "".join(
            f"<option value='{l['id']}'>{l['titulo']} ({l['copias_disponibles']} disp.)</option>" for l in libros
        )
        options_socios = "".join(f"<option value='{s['id']}'>{s['nombre']}</option>" for s in socios)
        rows = "".join(
            f"<tr><td>{p['id']}</td><td>{p['titulo']}</td><td>{p['nombre']}</td><td>{p['fecha_prestamo']}</td><td>{p['fecha_limite']}</td><td>{p['estado']}</td>"
            + (
                f"<td><form method='post' action='/prestamos/{p['id']}/devolver'><button>Devolver</button></form></td></tr>"
                if p["estado"] != "devuelto"
                else "<td>-</td></tr>"
            )
            for p in prestamos
        )
        content = f"""
<h2>Préstamos</h2>
<form method='post' class='grid-form'>
<select name='libro_id' required><option value=''>Libro</option>{options_libros}</select>
<select name='socio_id' required><option value=''>Socio</option>{options_socios}</select>
<button>Crear préstamo (14 días)</button>
</form>
<table><tr><th>ID</th><th>Libro</th><th>Socio</th><th>Inicio</th><th>Límite</th><th>Estado</th><th>Acción</th></tr>{rows}</table>
"""
        return base_layout(content, self.query_msg())

    def crear_libro(self, data: dict):
        with self.db() as conn:
            conn.execute(
                "INSERT INTO libros (titulo,autor,categoria,isbn,total_copias,copias_disponibles) VALUES (?,?,?,?,?,?)",
                (data["titulo"], data["autor"], data["categoria"], data["isbn"], int(data["total_copias"]), int(data["total_copias"])),
            )
            conn.commit()

    def crear_socio(self, data: dict):
        with self.db() as conn:
            conn.execute(
                "INSERT INTO socios (nombre,email,telefono,direccion) VALUES (?,?,?,?)",
                (data["nombre"], data["email"], data.get("telefono", ""), data.get("direccion", "")),
            )
            conn.commit()

    def crear_prestamo(self, data: dict) -> bool:
        libro_id, socio_id = int(data["libro_id"]), int(data["socio_id"])
        hoy, limite = date.today(), date.today() + timedelta(days=14)
        with self.db() as conn:
            libro = conn.execute("SELECT copias_disponibles FROM libros WHERE id=?", (libro_id,)).fetchone()
            if not libro or libro["copias_disponibles"] <= 0:
                return False
            conn.execute(
                "INSERT INTO prestamos (libro_id,socio_id,fecha_prestamo,fecha_limite,estado) VALUES (?,?,?,?, 'activo')",
                (libro_id, socio_id, hoy.isoformat(), limite.isoformat()),
            )
            conn.execute("UPDATE libros SET copias_disponibles=copias_disponibles-1 WHERE id=?", (libro_id,))
            conn.commit()
        return True

    def devolver_prestamo(self, prestamo_id: int):
        with self.db() as conn:
            p = conn.execute("SELECT * FROM prestamos WHERE id=?", (prestamo_id,)).fetchone()
            if not p or p["estado"] == "devuelto":
                return
            conn.execute("UPDATE prestamos SET estado='devuelto', fecha_devolucion=date('now') WHERE id=?", (prestamo_id,))
            conn.execute("UPDATE libros SET copias_disponibles=copias_disponibles+1 WHERE id=?", (p["libro_id"],))
            conn.commit()


def run(host: str = "0.0.0.0", port: int = 5000):
    init_db(DB_PATH)
    server = ThreadingHTTPServer((host, port), BibliotecaHandler)
    print(f"Servidor en http://{host}:{port}")
    server.serve_forever()


if __name__ == "__main__":
    run()
