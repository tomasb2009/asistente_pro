"""
Entrada CLI para probar el pipeline sin micrófono todavía.

Uso:
  python -m asistente.main "¿Qué hora es en Tokyo?"
"""

from __future__ import annotations

import argparse
import asyncio
import sys

from asistente.pipeline import run_pipeline


def main() -> None:
    parser = argparse.ArgumentParser(description="Asistente personal (texto → respuesta)")
    parser.add_argument(
        "message",
        nargs="?",
        help="Mensaje del usuario; si se omite, se lee de stdin",
    )
    args = parser.parse_args()
    text = args.message
    if not text:
        text = sys.stdin.read().strip()
    if not text:
        parser.print_help()
        sys.exit(1)
    reply = asyncio.run(run_pipeline(text))
    print(reply)


if __name__ == "__main__":
    main()
