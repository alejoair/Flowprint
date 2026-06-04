from __future__ import annotations

import argparse
import sys


def main() -> None:
    parser = argparse.ArgumentParser(prog="flowprint")
    sub = parser.add_subparsers(dest="command")

    ed = sub.add_parser("editor", help="Lanza el servidor de Flowprint")
    ed.add_argument("--host", default="127.0.0.1")
    ed.add_argument("--port", type=int, default=8000)
    ed.add_argument("--reload", action="store_true", help="Recarga al cambiar archivos (dev)")

    args = parser.parse_args()

    if args.command == "editor":
        _run_editor(args.host, args.port, args.reload)
    else:
        parser.print_help()
        sys.exit(1)


def _run_editor(host: str, port: int, reload: bool) -> None:
    try:
        import uvicorn
    except ImportError:
        print("Error: uvicorn no está instalado. Ejecuta: pip install flowprint")
        sys.exit(1)

    print(f"Flowprint editor → http://{host}:{port}")
    uvicorn.run(
        "flowprint.api:app",
        host=host,
        port=port,
        reload=reload,
    )


if __name__ == "__main__":
    main()
