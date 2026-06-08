"""
GestorAlmacén Pro — Punto de entrada
Lanza el servidor Flask y abre el navegador automáticamente.

Para Windows .exe: pyinstaller --onefile --windowed --name GestorAlmacen main.py
"""
from __future__ import annotations

import os
import sys
import threading
import time
import webbrowser

# Add project root to path when running as .exe
if getattr(sys, "frozen", False):
    base_dir = sys._MEIPASS  # type: ignore[attr-defined]
    os.chdir(os.path.dirname(sys.executable))
else:
    base_dir = os.path.dirname(os.path.abspath(__file__))

sys.path.insert(0, base_dir)

HOST = "127.0.0.1"
PORT = 5000
URL = f"http://{HOST}:{PORT}"


def open_browser():
    time.sleep(1.5)
    webbrowser.open(URL)


def main():
    from gestoralmacen.app import create_app

    app = create_app()

    print(f"\n{'='*50}")
    print(f"  GestorAlmacén Pro — Química del Sur S.L.")
    print(f"  Servidor iniciado en {URL}")
    print(f"  Usuario por defecto: jgarcia / admin123")
    print(f"{'='*50}\n")

    threading.Thread(target=open_browser, daemon=True).start()

    app.run(host=HOST, port=PORT, debug=False, use_reloader=False)


if __name__ == "__main__":
    main()
