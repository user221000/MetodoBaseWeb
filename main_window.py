"""Launcher de UI PySide6 principal.

Este archivo existe para evitar confusiones si se ejecuta directo.
"""
import sys

from PySide6.QtWidgets import QApplication

from ui_desktop.pyside.main_window import MainWindow


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
