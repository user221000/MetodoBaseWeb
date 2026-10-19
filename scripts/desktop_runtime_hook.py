"""Opt-in packaged Qt diagnostic; normal product startup is unchanged."""
import os


def _diagnostic() -> None:
    import json
    from pathlib import Path
    import socket
    import sys
    import tempfile

    root = Path(os.environ["METODOBASE_DESKTOP_SMOKE_DIR"])
    nonce = os.environ.get("METODOBASE_DESKTOP_SMOKE_NONCE", "")
    if (not root.is_absolute() or root.is_symlink() or root.resolve().parent != Path(tempfile.gettempdir()).resolve()
            or not root.name.startswith("metodobase-desktop-smoke-") or len(nonce) != 64
            or (root / ".desktop-smoke-marker").read_text(encoding="ascii") != nonce):
        os._exit(2)
    receipt = {"nonce": nonce, "ok": False}
    try:
        def denied(*args, **kwargs):
            raise OSError("Python sockets disabled in packaged diagnostic")
        socket.socket.connect = denied
        socket.socket.connect_ex = denied
        socket.create_connection = denied
        socket.getaddrinfo = denied
        socket.socket.sendto = denied
        receipt["python_network_blocked"] = True
        receipt["os_network_isolation_verified"] = False
        os.environ["QT_QPA_PLATFORM"] = "offscreen"
        os.environ["PYTHON_DOTENV_DISABLED"] = "1"
        from PySide6.QtWidgets import QApplication
        from PySide6.QtGui import QFontDatabase
        app = QApplication([])
        resources = Path(sys._MEIPASS)
        if QFontDatabase.addApplicationFont(str(resources / "fonts/Inter/Inter-Regular.ttf")) < 0:
            raise RuntimeError("Bundled font unavailable")
        from ui_desktop.pyside.theme_manager import ThemeManager
        from ui_desktop.pyside.ventana_login_unificada import VentanaLoginUnificada
        ThemeManager.instance().reload()
        window = VentanaLoginUnificada()
        window.show()
        app.processEvents()
        window.close()
        receipt.update(ok=app.platformName() == "offscreen", qt_platform=app.platformName(),
                       widget="VentanaLoginUnificada", product_flow_executed=False)
    except BaseException as exc:
        receipt["error_type"] = type(exc).__name__
    (root / "receipt.json").write_text(json.dumps(receipt), encoding="utf-8")
    # Exit before main.py business flow, activation or an application session.
    os._exit(0 if receipt["ok"] else 1)


if os.environ.get("METODOBASE_DESKTOP_SMOKE_DIR"):
    _diagnostic()
