"""
Desktop entrypoint for PeachAlgo Coach.

- Fixed local port, single instance
- No console window when packaged
- System tray: Open / Quit
- Opens browser only after the server is actually ready
- Writes a launch log under %LOCALAPPDATA%\\PeachAlgoCoach\\
"""

from __future__ import annotations

import atexit
import logging
import os
import socket
import sys
import threading
import time
import traceback
import webbrowser
from pathlib import Path

APP_MUTEX_NAME = "Local\\PeachAlgoCoach_SingleInstance_v1"
DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 8765


def _ensure_backend_on_path() -> None:
    here = Path(__file__).resolve().parent
    if str(here) not in sys.path:
        sys.path.insert(0, str(here))


def _log_dir() -> Path:
    base = Path(os.environ.get("LOCALAPPDATA") or (Path.home() / "AppData" / "Local"))
    path = base / "PeachAlgoCoach"
    path.mkdir(parents=True, exist_ok=True)
    return path


def _ensure_stdio() -> None:
    """
    Windowed frozen apps (PyInstaller runw / console=False) set
    sys.stdout/sys.stderr to None. uvicorn's ColourizedFormatter then
    crashes on stdout.isatty() and the server never binds.
    """
    log_path = _log_dir() / "desktop.log"
    if sys.stdout is None or sys.stderr is None:
        try:
            stream = open(log_path, "a", encoding="utf-8", buffering=1)
        except Exception:
            stream = open(os.devnull, "w")
        if sys.stdout is None:
            sys.stdout = stream  # type: ignore[assignment]
        if sys.stderr is None:
            sys.stderr = stream  # type: ignore[assignment]


def _setup_logging() -> Path:
    _ensure_stdio()
    log_path = _log_dir() / "desktop.log"
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        handlers=[
            logging.FileHandler(log_path, encoding="utf-8"),
        ],
        force=True,
    )
    for name in ("uvicorn", "uvicorn.error", "uvicorn.access", "asyncio"):
        logging.getLogger(name).setLevel(logging.INFO)
    return log_path


log = logging.getLogger("peachalgo.desktop")


def _open_browser(url: str) -> None:
    try:
        webbrowser.open(url)
        log.info("opened browser: %s", url)
    except Exception:
        log.exception("failed to open browser")


def _tcp_open(host: str, port: int, timeout: float = 0.4) -> bool:
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except OSError:
        return False


def _http_ok(url: str, timeout: float = 1.0) -> bool:
    import urllib.error
    import urllib.request

    try:
        req = urllib.request.Request(url, headers={"User-Agent": "PeachAlgoCoach/desktop"})
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return 200 <= getattr(resp, "status", 200) < 500
    except (urllib.error.URLError, TimeoutError, OSError):
        return False


def _wait_ready(host: str, port: int, health_url: str, timeout_sec: float = 40.0) -> bool:
    """Wait until TCP accepts and health endpoint responds."""
    deadline = time.time() + timeout_sec
    while time.time() < deadline:
        if _tcp_open(host, port, timeout=0.3) and _http_ok(health_url, timeout=0.8):
            return True
        time.sleep(0.15)
    return False


class SingleInstanceLock:
    """Windows named mutex, with localhost lock-port fallback."""

    LOCK_PORT = 48765

    def __init__(self) -> None:
        self._mutex = None
        self._sock: socket.socket | None = None
        self.owned = False

    def acquire(self) -> bool:
        if sys.platform == "win32":
            try:
                import ctypes
                from ctypes import wintypes

                kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
                # Reset last error before CreateMutex so ERROR_ALREADY_EXISTS is trustworthy.
                ctypes.set_last_error(0)
                kernel32.CreateMutexW.argtypes = [
                    wintypes.LPVOID,
                    wintypes.BOOL,
                    wintypes.LPCWSTR,
                ]
                kernel32.CreateMutexW.restype = wintypes.HANDLE
                handle = kernel32.CreateMutexW(None, False, APP_MUTEX_NAME)
                if not handle:
                    log.warning("CreateMutexW failed")
                    return False
                self._mutex = handle
                if ctypes.get_last_error() == 183:  # ERROR_ALREADY_EXISTS
                    log.info("mutex already owned by another process")
                    return False
                self.owned = True
                log.info("mutex acquired")
                return True
            except Exception:
                log.exception("mutex path failed; trying socket lock")

        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 0)
            sock.bind(("127.0.0.1", self.LOCK_PORT))
            sock.listen(1)
            self._sock = sock
            self.owned = True
            log.info("socket lock acquired on %s", self.LOCK_PORT)
            return True
        except OSError:
            try:
                sock.close()
            except Exception:
                pass
            log.info("socket lock busy")
            return False

    def release(self) -> None:
        if self._sock is not None:
            try:
                self._sock.close()
            except Exception:
                pass
            self._sock = None
        if self._mutex is not None and sys.platform == "win32":
            try:
                import ctypes

                ctypes.WinDLL("kernel32").CloseHandle(self._mutex)
            except Exception:
                pass
            self._mutex = None
        self.owned = False


def _make_tray_icon_image():
    from PIL import Image, ImageDraw

    size = 64
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    draw.ellipse((6, 10, 58, 58), fill=(255, 154, 110, 255))
    draw.ellipse((16, 18, 34, 34), fill=(255, 210, 180, 220))
    draw.ellipse((34, 4, 52, 22), fill=(88, 168, 96, 255))
    return img


class DesktopApp:
    def __init__(self, host: str, port: int, url: str, open_browser: bool) -> None:
        self.host = host
        self.port = port
        self.url = url
        self.open_browser = open_browser
        # Prefer lightweight /api/ready so we don't block on catalog parse.
        self.health_url = f"http://{host}:{port}/api/ready"
        self.full_health_url = f"http://{host}:{port}/api/health"
        self._server = None
        self._tray = None
        self._lock = SingleInstanceLock()
        self._stop = threading.Event()
        self._server_error: str | None = None
        self._ready = threading.Event()

    def _start_server(self) -> None:
        """
        Run uvicorn in a dedicated thread with its own asyncio loop.
        Windowed frozen apps often break if the loop is inherited from main.
        """
        import asyncio

        try:
            log.info("server thread starting")
            # Critical on Windows + frozen + non-main thread:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

            # stdio must exist before uvicorn.Config (formatter calls isatty).
            _ensure_stdio()

            import uvicorn
            from app.main import app

            config = uvicorn.Config(
                app,
                host=self.host,
                port=self.port,
                log_level="warning",
                access_log=False,
                loop="asyncio",
                http="h11",
                # Avoid ColourizedFormatter entirely in windowed builds.
                log_config=None,
            )
            self._server = uvicorn.Server(config)
            self._server.install_signal_handlers = lambda: None  # type: ignore[method-assign]

            async def _serve() -> None:
                assert self._server is not None
                await self._server.serve()

            loop.run_until_complete(_serve())
            log.info("server thread stopped cleanly")
        except Exception:
            self._server_error = traceback.format_exc()
            log.error("server thread crashed:\n%s", self._server_error)
        finally:
            try:
                loop = asyncio.get_event_loop()
                if not loop.is_closed():
                    loop.close()
            except Exception:
                pass

    def _quit(self, icon=None, _item=None) -> None:
        log.info("quit requested")
        self._stop.set()
        server = self._server
        if server is not None:
            server.should_exit = True
        if icon is not None:
            try:
                icon.stop()
            except Exception:
                pass
        elif self._tray is not None:
            try:
                self._tray.stop()
            except Exception:
                pass
        threading.Timer(1.2, lambda: os._exit(0)).start()

    def _open(self, _icon=None, _item=None) -> None:
        if _http_ok(self.health_url, timeout=0.8):
            _open_browser(self.url)
        else:
            log.warning("open requested but health not ok")
            _open_browser(self.url)

    def _open_log(self, _icon=None, _item=None) -> None:
        path = _log_dir() / "desktop.log"
        try:
            os.startfile(str(path))  # type: ignore[attr-defined]
        except Exception:
            _open_browser(path.as_uri())

    def _run_tray(self, *, failed: bool = False) -> None:
        import pystray
        from pystray import MenuItem as Item

        image = _make_tray_icon_image()
        if failed:
            menu = pystray.Menu(
                Item("启动失败 — 打开日志", self._open_log, default=True),
                Item("退出", self._quit),
            )
            title = "黄桃算法教练（启动失败）"
        else:
            menu = pystray.Menu(
                Item("打开黄桃算法教练", self._open, default=True),
                Item("打开日志", self._open_log),
                Item("退出", self._quit),
            )
            title = "黄桃算法教练"

        self._tray = pystray.Icon("PeachAlgoCoach", image, title, menu)
        self._tray.run()

    def run(self) -> int:
        from app.config import settings

        log.info(
            "launch host=%s port=%s frozen=%s db=%s problems=%s static=%s",
            self.host,
            self.port,
            getattr(sys, "frozen", False),
            settings.db_path,
            settings.problems_path,
            settings.static_dir,
        )

        # 1) Already healthy → only open browser.
        if _http_ok(self.health_url, timeout=0.6):
            log.info("existing healthy instance detected")
            if self.open_browser:
                _open_browser(self.url)
            return 0

        # 2) Single instance.
        if not self._lock.acquire():
            log.info("another instance owns lock; waiting for ready")
            if _wait_ready(self.host, self.port, self.health_url, timeout_sec=20.0):
                if self.open_browser:
                    _open_browser(self.url)
                return 0
            log.warning("lock held but service never became ready")
            if self.open_browser:
                _open_browser(self.url)
            return 0

        atexit.register(self._lock.release)

        # 3) Port occupied by non-app process.
        if _tcp_open(self.host, self.port) and not _http_ok(self.health_url, timeout=0.6):
            log.error("port %s busy by unknown process", self.port)
            if self.open_browser:
                _open_browser(self.url)
            self._lock.release()
            return 1

        # Pre-import on this thread so the server thread only serves.
        t_import = time.perf_counter()
        try:
            import app.main  # noqa: F401
            log.info("pre-import app.main in %.2fs", time.perf_counter() - t_import)
        except Exception:
            log.exception("pre-import failed")
            self._run_tray(failed=True)
            self._lock.release()
            return 1

        server_thread = threading.Thread(
            target=self._start_server,
            name="uvicorn",
            daemon=True,
        )
        t0 = time.perf_counter()
        server_thread.start()

        ready = _wait_ready(self.host, self.port, self.health_url, timeout_sec=45.0)
        elapsed = time.perf_counter() - t0
        if ready:
            log.info("server ready in %.2fs", elapsed)
            self._ready.set()
            if self.open_browser:
                _open_browser(self.url)
        else:
            log.error(
                "server NOT ready after %.2fs (thread_alive=%s error=%s)",
                elapsed,
                server_thread.is_alive(),
                bool(self._server_error),
            )
            # Do not open a dead page by default — show tray failure menu.
            try:
                self._run_tray(failed=True)
            finally:
                server = self._server
                if server is not None:
                    server.should_exit = True
                self._lock.release()
            return 1

        try:
            self._run_tray(failed=False)
        except Exception:
            log.exception("tray failed; keeping server alive until stop")
            while server_thread.is_alive() and not self._stop.is_set():
                time.sleep(0.5)

        server = self._server
        if server is not None:
            server.should_exit = True
        server_thread.join(timeout=3.0)
        self._lock.release()
        log.info("shutdown complete")
        return 0


def main() -> int:
    _ensure_backend_on_path()
    log_path = _setup_logging()
    log.info("==== PeachAlgo Coach desktop start ====")
    log.info("log file: %s", log_path)

    try:
        from app.config import settings
    except Exception:
        log.exception("failed to import settings")
        return 1

    host = os.environ.get("COACH_HOST", settings.host or DEFAULT_HOST)
    port = int(os.environ.get("COACH_PORT", str(settings.port or DEFAULT_PORT)))
    open_browser = (
        os.environ.get("COACH_OPEN_BROWSER", "1" if settings.open_browser else "0") != "0"
    )
    url = f"http://{host}:{port}/"

    return DesktopApp(host=host, port=port, url=url, open_browser=open_browser).run()


if __name__ == "__main__":
    raise SystemExit(main())
