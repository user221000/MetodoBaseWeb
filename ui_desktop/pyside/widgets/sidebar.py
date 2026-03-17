# -*- coding: utf-8 -*-
"""
Sidebar personalizado con logo, navegación jerárquica y footer de usuario.
Secciones: PRINCIPAL, GIMNASIO, FINANZAS, SISTEMA.
"""
from PySide6.QtWidgets import (
    QFrame, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QSpacerItem, QSizePolicy, QWidget,
)
from PySide6.QtCore import Qt, Signal


class CustomSidebar(QFrame):
    """Sidebar de navegación con diseño verde premium."""

    navigation_changed = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("sidebar")
        self.setFixedWidth(260)
        self._nav_buttons: dict[str, QPushButton] = {}
        self._setup_ui()

    # ── Construcción ──────────────────────────────────────────────────────────

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # ── Logo ──────────────────────────────────────────────────────────────
        logo_container = QWidget()
        logo_container.setStyleSheet("background: transparent;")
        logo_layout = QVBoxLayout(logo_container)
        logo_layout.setContentsMargins(20, 24, 20, 0)
        logo_layout.setSpacing(3)

        logo_label = QLabel("Método Base")
        logo_label.setObjectName("logoLabel")
        logo_layout.addWidget(logo_label)

        version_label = QLabel("Sistema Nutricional v2.0")
        version_label.setObjectName("versionLabel")
        logo_layout.addWidget(version_label)

        layout.addWidget(logo_container)
        layout.addSpacing(28)

        # ── Sección PRINCIPAL ─────────────────────────────────────────────────
        layout.addWidget(self._create_section_label("PRINCIPAL"))

        self._add_nav("dashboard", "📊   Dashboard", layout)
        self._add_nav("clientes", "👥   Clientes", layout)
        self._add_nav("generar_plan", "📋   Generar Plan", layout)

        layout.addSpacing(20)

        # ── Sección GIMNASIO ──────────────────────────────────────────────────
        layout.addWidget(self._create_section_label("GIMNASIO"))

        self._add_nav("suscripciones", "💳   Suscripciones", layout)
        self._add_nav("clases", "🗓️   Clases", layout)
        self._add_nav("instructores", "🏋️   Instructores", layout)

        layout.addSpacing(20)

        # ── Sección FINANZAS ──────────────────────────────────────────────────
        layout.addWidget(self._create_section_label("FINANZAS"))

        self._add_nav("facturacion", "💰   Facturación", layout)
        self._add_nav("reportes", "📈   Reportes", layout)

        layout.addSpacing(20)

        # ── Sección SISTEMA ───────────────────────────────────────────────────
        layout.addWidget(self._create_section_label("SISTEMA"))

        self._add_nav("configuracion", "⚙️   Configuración", layout)
        self._add_nav("api_docs", "📖   API Docs", layout)

        # ── Spacer ────────────────────────────────────────────────────────────
        layout.addItem(
            QSpacerItem(20, 40, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding)
        )

        # ── Usuario Footer ────────────────────────────────────────────────────
        layout.addWidget(self._create_user_footer())

    def _create_section_label(self, text: str) -> QLabel:
        label = QLabel(text)
        label.setObjectName("sectionLabel")
        return label

    def _add_nav(self, page_id: str, text: str, layout: QVBoxLayout) -> None:
        btn = self._create_nav_button(text, page_id)
        self._nav_buttons[page_id] = btn
        layout.addWidget(btn)

    def _create_nav_button(self, text: str, page_id: str) -> QPushButton:
        btn = QPushButton(text)
        btn.setObjectName("navButton")
        btn.setCheckable(True)
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        btn.clicked.connect(lambda: self._on_nav_clicked(page_id))
        return btn

    def _create_user_footer(self) -> QFrame:
        footer = QFrame()
        footer.setObjectName("userFooter")

        layout = QHBoxLayout(footer)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(10)

        # Avatar circular
        avatar = QLabel("GM")
        avatar.setObjectName("userAvatar")
        avatar.setAlignment(Qt.AlignmentFlag.AlignCenter)
        avatar.setFixedSize(40, 40)
        layout.addWidget(avatar)

        # Información de usuario
        info_widget = QWidget()
        info_widget.setStyleSheet("background: transparent;")
        info_layout = QVBoxLayout(info_widget)
        info_layout.setContentsMargins(0, 0, 0, 0)
        info_layout.setSpacing(2)

        name_label = QLabel("Mi Gimnasio")
        name_label.setObjectName("userName")
        info_layout.addWidget(name_label)

        plan_label = QLabel("v2.0 Premium")
        plan_label.setObjectName("userPlan")
        info_layout.addWidget(plan_label)

        layout.addWidget(info_widget)
        layout.addStretch()

        return footer

    # ── Lógica de navegación ──────────────────────────────────────────────────

    def _on_nav_clicked(self, page_id: str) -> None:
        self._set_active(page_id)
        self.navigation_changed.emit(page_id)

    def _set_active(self, page_id: str) -> None:
        for pid, btn in self._nav_buttons.items():
            is_active = (pid == page_id)
            btn.setChecked(is_active)
            btn.setProperty("active", "true" if is_active else "false")
            btn.style().unpolish(btn)
            btn.style().polish(btn)
            btn.update()

    def set_active_page(self, page_id: str) -> None:
        """Activa programáticamente una página en el sidebar."""
        self._set_active(page_id)

    def activate_dashboard(self) -> None:
        self._set_active("dashboard")

    def activate_clientes(self) -> None:
        self._set_active("clientes")

    def activate_generar_plan(self) -> None:
        self._set_active("generar_plan")
