# -*- coding: utf-8 -*-
"""Widgets de progreso reutilizables para operaciones largas."""
import customtkinter as ctk


class ProgressIndicator(ctk.CTkFrame):
    """
    Indicador de progreso con barra, etiqueta de estado y porcentaje.

    Uso::

        progress = ProgressIndicator(parent, width=400)
        progress.pack(pady=20)
        progress.set_progress(0.5, "Seleccionando alimentos...")
        progress.complete()   # marca como completado
        progress.reset()      # reinicia
    """

    def __init__(self, master, width: int = 400, **kwargs):
        super().__init__(master, fg_color="#1E1E1E", corner_radius=10,
                         border_width=1, border_color="#444444", **kwargs)
        self.width = width

        # Etiqueta de estado
        self.lbl_estado = ctk.CTkLabel(
            self, text="Preparando flujo de trabajo...", anchor="w",
            font=ctk.CTkFont(family="Segoe UI", size=12),
            text_color="#CCCCCC",
        )
        self.lbl_estado.pack(padx=16, pady=(12, 4), anchor="w")

        # Barra de progreso
        self.barra = ctk.CTkProgressBar(
            self, width=self.width, height=20, corner_radius=10,
            progress_color="#9B4FB0", fg_color="#2A2A2A",
            mode="determinate",
        )
        self.barra.set(0)
        self.barra.pack(padx=16, pady=(0, 6), fill="x")

        # Etiqueta de porcentaje
        self.lbl_pct = ctk.CTkLabel(
            self, text="0%",
            font=ctk.CTkFont(family="Segoe UI", size=14, weight="bold"),
            text_color="#9B4FB0",
        )
        self.lbl_pct.pack(pady=(0, 12))

    def set_progress(self, value: float, status: str = "") -> None:
        """Actualiza el progreso. ``value`` es 0.0 – 1.0."""
        value = max(0.0, min(1.0, value))
        self.barra.set(value)
        if status:
            self.lbl_estado.configure(text=status)
        self.lbl_pct.configure(text=f"{int(value * 100)}%")
        self.update_idletasks()

    def complete(self, status: str = "✓ Completado") -> None:
        """Marca como completado (verde)."""
        self.barra.set(1.0)
        self.barra.configure(progress_color="#4CAF50")
        self.lbl_estado.configure(text=status, text_color="#4CAF50")
        self.lbl_pct.configure(text="100%", text_color="#4CAF50")

    def error(self, mensaje: str = "Error en la operación") -> None:
        """Marca con error (rojo)."""
        self.lbl_estado.configure(text=f"✗ {mensaje}", text_color="#F44336")
        self.lbl_pct.configure(text_color="#F44336")

    def reset(self) -> None:
        """Reinicia el indicador."""
        self.barra.set(0)
        self.barra.configure(progress_color="#9B4FB0")
        self.lbl_estado.configure(text="Preparando flujo de trabajo...", text_color="#CCCCCC")
        self.lbl_pct.configure(text="0%", text_color="#9B4FB0")


class StepFlowIndicator(ctk.CTkFrame):
    """Indicador visual de pasos: Captura -> Preview -> Exportar."""

    COLOR_BG = "#1E1E1E"
    COLOR_BORDER = "#444444"
    COLOR_TEXT = "#F5F5F5"
    COLOR_MUTED = "#A8A8A8"
    COLOR_ACTIVE = "#9B4FB0"
    COLOR_DONE = "#4CAF50"

    def __init__(self, master, **kwargs):
        super().__init__(
            master,
            fg_color=self.COLOR_BG,
            corner_radius=10,
            border_width=1,
            border_color=self.COLOR_BORDER,
            **kwargs,
        )
        self.steps = ["Captura", "Preview", "Exportar"]
        self._active_step = 0
        self._completed_steps = set()
        self._dots = []
        self._labels = []
        self._connectors = []
        self._build()
        self.set_step(0)

    def _build(self) -> None:
        title = ctk.CTkLabel(
            self,
            text="Flujo de trabajo",
            font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"),
            text_color=self.COLOR_TEXT,
        )
        title.pack(anchor="w", padx=14, pady=(10, 0))

        row = ctk.CTkFrame(self, fg_color="transparent")
        row.pack(fill="x", padx=14, pady=(6, 8))
        row.grid_columnconfigure((0, 1, 2, 3, 4), weight=1)

        for i, step in enumerate(self.steps):
            cell = i * 2
            dot = ctk.CTkLabel(
                row,
                text=str(i + 1),
                width=28,
                height=28,
                corner_radius=14,
                fg_color="#2A2A2A",
                text_color=self.COLOR_MUTED,
                font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"),
            )
            dot.grid(row=0, column=cell, pady=(0, 4))
            self._dots.append(dot)

            label = ctk.CTkLabel(
                row,
                text=step,
                font=ctk.CTkFont(family="Segoe UI", size=11),
                text_color=self.COLOR_MUTED,
            )
            label.grid(row=1, column=cell)
            self._labels.append(label)

            if i < len(self.steps) - 1:
                connector = ctk.CTkFrame(
                    row,
                    height=2,
                    fg_color=self.COLOR_BORDER,
                    corner_radius=2,
                )
                connector.grid(row=0, column=cell + 1, sticky="ew", padx=6)
                self._connectors.append(connector)

    def set_step(self, step_idx: int) -> None:
        self._active_step = max(0, min(step_idx, len(self.steps) - 1))
        self._paint()

    def complete_step(self, step_idx: int) -> None:
        if 0 <= step_idx < len(self.steps):
            self._completed_steps.add(step_idx)
            self._paint()

    def reset(self) -> None:
        self._active_step = 0
        self._completed_steps.clear()
        self._paint()

    def _paint(self) -> None:
        for idx, dot in enumerate(self._dots):
            if idx in self._completed_steps:
                dot.configure(text="✓", fg_color=self.COLOR_DONE, text_color="#FFFFFF")
                self._labels[idx].configure(text_color=self.COLOR_DONE)
            elif idx == self._active_step:
                dot.configure(text=str(idx + 1), fg_color=self.COLOR_ACTIVE, text_color="#FFFFFF")
                self._labels[idx].configure(text_color=self.COLOR_TEXT)
            else:
                dot.configure(text=str(idx + 1), fg_color="#2A2A2A", text_color=self.COLOR_MUTED)
                self._labels[idx].configure(text_color=self.COLOR_MUTED)

        for idx, connector in enumerate(self._connectors):
            if idx in self._completed_steps:
                connector.configure(fg_color=self.COLOR_DONE)
            elif idx < self._active_step:
                connector.configure(fg_color=self.COLOR_ACTIVE)
            else:
                connector.configure(fg_color=self.COLOR_BORDER)


class SpinnerIndicator(ctk.CTkFrame):
    """
    Indicador de carga tipo spinner para operaciones sin progreso medible.

    Uso::

        spinner = SpinnerIndicator(parent)
        spinner.pack(pady=20)
        spinner.start("Procesando...")
        spinner.stop()
    """

    _CHARS = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]

    def __init__(self, master, **kwargs):
        super().__init__(master, fg_color="transparent", **kwargs)
        self.label = ctk.CTkLabel(
            self, text="⏳ Procesando…",
            font=ctk.CTkFont(family="Segoe UI", size=12),
            text_color="#CCCCCC",
        )
        self.label.pack()
        self._running = False
        self._idx = 0

    def start(self, message: str = "Procesando…") -> None:
        self._running = True
        self.label.configure(text=f"{self._CHARS[0]} {message}", text_color="#CCCCCC")
        self._animate()

    def stop(self) -> None:
        self._running = False
        self.label.configure(text="✓ Completado", text_color="#4CAF50")

    def _animate(self) -> None:
        if not self._running:
            return
        self._idx = (self._idx + 1) % len(self._CHARS)
        current = self.label.cget("text")
        if current:
            self.label.configure(text=self._CHARS[self._idx] + current[1:])
        self.after(100, self._animate)
