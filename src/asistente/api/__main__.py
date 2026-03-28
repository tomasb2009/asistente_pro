"""Arranque: python -m asistente.api"""

from __future__ import annotations

import uvicorn

from asistente.config import get_settings


def main() -> None:
    s = get_settings()
    uvicorn.run(
        "asistente.api.app:app",
        host=s.api_host,
        port=s.api_port,
        reload=True,
    )


if __name__ == "__main__":
    main()
