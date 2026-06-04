from __future__ import annotations

import argparse
import sys


def main() -> None:
    parser = argparse.ArgumentParser(prog="flowprint")
    sub = parser.add_subparsers(dest="command")

    ed = sub.add_parser("editor", help="Lanza el editor visual + backend")
    ed.add_argument("--host", default="127.0.0.1")
    ed.add_argument("--port", type=int, default=8000)
    ed.add_argument("--reload", action="store_true", help="Recarga al cambiar archivos (dev)")

    sv = sub.add_parser("serve", help="Lanza solo el backend/API, sin editor")
    sv.add_argument("--host", default="0.0.0.0")
    sv.add_argument("--port", type=int, default=8000)
    sv.add_argument("--reload", action="store_true")

    args = parser.parse_args()

    if args.command == "editor":
        _run(args.host, args.port, args.reload, open_browser=True)
    elif args.command == "serve":
        _run(args.host, args.port, args.reload, open_browser=False)
    else:
        parser.print_help()
        sys.exit(1)


def _run(host: str, port: int, reload: bool, open_browser: bool) -> None:
    try:
        import uvicorn
    except ImportError:
        print("Error: uvicorn no está instalado. Ejecuta: pip install flowprint")
        sys.exit(1)

    if open_browser:
        import threading
        import webbrowser
        url = f"http://{host}:{port}"
        print(f"Flowprint editor → {url}")
        threading.Timer(1.5, webbrowser.open, args=[url]).start()
    else:
        print(f"Flowprint API → http://{host}:{port}")

    uvicorn.run(
        "flowprint.api:app",
        host=host,
        port=port,
        reload=reload,
    )


if __name__ == "__main__":
    main()
