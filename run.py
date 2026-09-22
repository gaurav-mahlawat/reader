import sys

import uvicorn

from app.config import settings

if __name__ == "__main__":
    url = f"http://{settings.host}:{settings.port}"
    print(f"\n  Reader")
    print(f"  Open in browser: {url}\n")
    print("  Press Ctrl+C to stop.\n")
    try:
        uvicorn.run(
            "app.main:app",
            host=settings.host,
            port=settings.port,
            reload=False,
        )
    except OSError as e:
        if "10048" in str(e) or "address already in use" in str(e).lower():
            print(f"ERROR: Port {settings.port} is already in use.", file=sys.stderr)
            print(f"Close the other app or change PORT in .env", file=sys.stderr)
        else:
            raise