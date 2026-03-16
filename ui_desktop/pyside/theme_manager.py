# -*- coding: utf-8 -*-
"""
ThemeManager — Sistema modular de temas visuales para Método Base.

Temas disponibles
─────────────────
  dark    Oscuro   SmartFit + macOS 2026 (naranja energía, fondo #070707)
  light   Claro    macOS Sonoma Light    (naranja, fondo blanco/gris)
  aurora  Aurora   Aura nórdica          (teal eléctrico + violeta, fondo #080C1A)

Uso rápido
──────────
    from ui_desktop.pyside.theme_manager import ThemeManager

    # Obtener instancia singleton y aplicar tema
    ThemeManager.instance().set_theme("aurora")

    # Ciclar al siguiente tema
    ThemeManager.instance().toggle_next()

    # Leer tema actual
    current = ThemeManager.instance().current_theme   # "dark" | "light" | "aurora"

    # Reaccionar a cambios
    ThemeManager.instance().theme_changed.connect(my_slot)

Widget selector
───────────────
    from ui_desktop.pyside.theme_manager import ThemeSwitcher

    switcher = ThemeSwitcher()
    topbar_layout.addWidget(switcher)

El tema elegido persiste entre sesiones en ~/.metodobase/theme_pref.json.
"""
from __future__ import annotations

import json
import os
from pathlib import Path

from PySide6.QtCore import QObject, QTimer, Signal
from PySide6.QtWidgets import QApplication, QButtonGroup, QHBoxLayout, QPushButton, QWidget

# ── Rutas de recursos ──────────────────────────────────────────────────────────
_BASE_DIR: Path = Path(__file__).parent.parent.parent   # raíz del proyecto
_STYLES_DIR: Path = _BASE_DIR / "assets" / "styles"     # assets/styles/
_PREF_FILE: Path = Path.home() / ".metodobase" / "theme_pref.json"

# Mapa nombre → ruta QSS; rutas alternativas para compatibilidad
_FALLBACK_DARK = _BASE_DIR / "ui_desktop" / "pyside" / "styles" / "dark_theme.qss"

_THEMES: dict[str, list[Path]] = {
    "dark":   [_STYLES_DIR / "dark.qss",   _FALLBACK_DARK],
    "light":  [_STYLES_DIR / "light.qss"],
    "aurora": [_STYLES_DIR / "aurora.qss"],
}

# Etiquetas mostradas en los botones del ThemeSwitcher
_LABELS: dict[str, str] = {
    "dark":   "🌙  Oscuro",
    "light":  "☀️  Claro",
    "aurora": "🌌  Aurora",
}

_THEME_ORDER = ["dark", "light", "aurora"]


# ── ThemeManager ────────────────────────────────────────────────────────────────

class ThemeManager(QObject):
    """
    Singleton que gestiona carga y alternancia de temas en tiempo de ejecución.

    El cambio de tema se realiza con una transición suave (fade breve) usando
    setWindowOpacity en la ventana activa, seguido de aplicación inmediata del
    nuevo QSS y restauración de opacidad.  En plataformas sin compositor la
    transición se omite de forma silenciosa.
    """

    #: Emitido tras cada cambio de tema; el argumento es el nombre del nuevo tema.
    theme_changed = Signal(str)

    _instance: "ThemeManager | None" = None

    def __init__(self) -> None:
        super().__init__()
        self._current: str = "dark"
        self._locked: bool = False          # debounce — evita cambios en ráfaga
        self._load_saved_pref()

    # ── API pública ─────────────────────────────────────────────────────────

    @classmethod
    def instance(cls) -> "ThemeManager":
        """Retorna la instancia singleton; la crea si no existe."""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    @property
    def current_theme(self) -> str:
        """Nombre del tema activo: 'dark' | 'light' | 'aurora'."""
        return self._current

    def set_theme(self, name: str, *, animated: bool = True) -> None:
        """
        Aplica el tema ``name`` al QApplication activo.

        Parameters
        ----------
        name:      'dark', 'light' o 'aurora'
        animated:  Si es True (defecto) aplica un breve fade en la ventana activa.
        """
        if name not in _THEMES or name == self._current or self._locked:
            return
        qss = self._load_qss(name)
        if qss is None:
            return

        if animated:
            self._apply_animated(name, qss)
        else:
            self._apply_instant(name, qss)

    def reload(self) -> None:
        """Fuerza la reaplicación del QSS del tema actual (omite el guard de igualdad).

        Útil en el arranque de la aplicación, donde `set_theme` se saltaría si
        el tema guardado coincide con el valor inicial de `_current`.
        """
        qss = self._load_qss(self._current)
        if qss is not None:
            self._apply_instant(self._current, qss)

    def toggle_next(self) -> None:
        """Cicla al siguiente tema en orden: dark → light → aurora → dark."""
        idx = _THEME_ORDER.index(self._current) if self._current in _THEME_ORDER else 0
        self.set_theme(_THEME_ORDER[(idx + 1) % len(_THEME_ORDER)])

    # ── Privados ─────────────────────────────────────────────────────────────

    def _load_qss(self, name: str) -> str | None:
        """Carga el QSS para el tema ``name``; prueba rutas en orden de preferencia."""
        candidates = _THEMES.get(name, [])
        for path in candidates:
            if path.exists():
                try:
                    return path.read_text(encoding="utf-8")
                except OSError:
                    continue
        return None

    def _apply_instant(self, name: str, qss: str) -> None:
        """Aplica el QSS directamente sin animación."""
        app = QApplication.instance()
        if app:
            app.setStyleSheet(qss)
        self._current = name
        self._save_pref()
        self.theme_changed.emit(name)

    # Plataformas que no soportan setWindowOpacity (Wayland y derivados)
    _PLATFORMS_NO_OPACITY = frozenset({"wayland", "wayland-egl", "wlroots", "offscreen"})

    @classmethod
    def _platform_supports_opacity(cls) -> bool:
        app = QApplication.instance()
        if app is None:
            return False
        return app.platformName().lower() not in cls._PLATFORMS_NO_OPACITY

    def _apply_animated(self, name: str, qss: str) -> None:
        """
        Transición suave:
          1. Reduce opacidad de la ventana activa a 0.80 (60 ms)
          2. Aplica el nuevo QSS
          3. Restaura opacidad a 1.0

        En plataformas que no soportan windowOpacity (Wayland, etc.) el tema
        se aplica de forma instantánea sin intentar el fade.
        """
        self._locked = True

        if not self._platform_supports_opacity():
            self._apply_instant(name, qss)
            QTimer.singleShot(120, self._unlock)
            return

        active = QApplication.activeWindow()

        if active:
            active.setWindowOpacity(0.78)

        def _commit() -> None:
            self._apply_instant(name, qss)
            if active:
                active.setWindowOpacity(1.0)
            QTimer.singleShot(120, self._unlock)

        QTimer.singleShot(60, _commit)

    def _unlock(self) -> None:
        self._locked = False

    def _load_saved_pref(self) -> None:
        """Carga la preferencia de tema guardada; usa 'dark' si no existe."""
        try:
            data = json.loads(_PREF_FILE.read_text(encoding="utf-8"))
            theme = data.get("theme", "dark")
            if theme in _THEMES:
                self._current = theme
        except (OSError, json.JSONDecodeError, KeyError):
            self._current = "dark"

    def _save_pref(self) -> None:
        """Persiste la preferencia actual en ~/.metodobase/theme_pref.json."""
        try:
            _PREF_FILE.parent.mkdir(parents=True, exist_ok=True)
            _PREF_FILE.write_text(
                json.dumps({"theme": self._current}, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
        except OSError:
            pass


# ── ThemeSwitcher ────────────────────────────────────────────────────────────────

class ThemeSwitcher(QWidget):
    """
    Widget compacto de selección de tema — tres botones toggle exclusivos.

    Diseño:
      [🌙 Oscuro]  [☀️ Claro]  [🌌 Aurora]

    El widget se auto-actualiza cuando el ThemeManager cambia el tema desde
    cualquier otro origen (teclado, arranque, etc.).

    Uso
    ───
        switcher = ThemeSwitcher(parent=topbar)
        topbar_layout.addWidget(switcher)
    """

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._manager = ThemeManager.instance()
        self._btns: dict[str, QPushButton] = {}
        self._group = QButtonGroup(self)
        self._group.setExclusive(True)
        self._build_ui()
        # Sincronizar estado cuando el tema cambia desde otro origen
        self._manager.theme_changed.connect(self._sync_checked)

    # ── Construcción ────────────────────────────────────────────────────────

    def _build_ui(self) -> None:
        lay = QHBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(4)

        current = self._manager.current_theme
        for key, label in _LABELS.items():
            btn = QPushButton(label)
            btn.setObjectName("btn_toggle")
            btn.setCheckable(True)
            btn.setChecked(key == current)
            btn.setFixedHeight(32)
            # Capturar ``key`` por valor con argumento por defecto
            btn.clicked.connect(lambda _checked, k=key: self._manager.set_theme(k))
            self._group.addButton(btn)
            self._btns[key] = btn
            lay.addWidget(btn)

    # ── Slots ────────────────────────────────────────────────────────────────

    def _sync_checked(self, name: str) -> None:
        """Marca el botón correcto sin disparar señales de clic."""
        btn = self._btns.get(name)
        if btn and not btn.isChecked():
            btn.blockSignals(True)
            btn.setChecked(True)
            btn.blockSignals(False)
