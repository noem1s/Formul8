# main.py (in your root project folder)
# The main entry point for the Formul8 application.

# --- Block 1: Standard Library Imports ---
import sys
import os
import time
import traceback

# --- Block 2: Add Project to Python Path ---
# RATIONALE: This block MUST come before any 'from formul8...' imports.
# It finds the project's root directory and adds it to the list of places
# Python looks for modules, ensuring the 'formul8' package can be found.
project_root = os.path.dirname(os.path.abspath(__file__))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# --- Block 3: Third-Party Library Imports ---
from PyQt6.QtWidgets import QApplication, QMessageBox
from PyQt6.QtGui import QPalette, QColor, QFont, QPixmap, QPainter, QIcon
from PyQt6.QtCore import Qt

# --- Block 4: Local Application Imports ---
# These can now be imported successfully because the path was set in Block 2.
from Formul8.utils import resource_path
from Formul8.main_window import MainWindow
from Formul8.ui_components import AnimatedSplashScreen
from Formul8.constants import APP_VERSION


def main():
    """Application entry point."""

    def exception_hook(exctype, value, tb):
        """Global exception handler to catch and display fatal errors."""
        if exctype != SystemExit:
            traceback.print_exception(exctype, value, tb)
            QMessageBox.critical(None, "Fatal Error", f"A fatal error occurred:\n{value}\n\nSee console for details.")
        sys.exit(1)

    sys.excepthook = exception_hook

    app = QApplication(sys.argv)
    app.setOrganizationName("Formul8")
    app.setApplicationName("Formul8App")

    app_icon = QIcon(resource_path('app_icon.ico'))
    app.setWindowIcon(app_icon)

    # --- Palette and Styling ---
    dark_palette = QPalette()
    dark_palette.setColor(QPalette.ColorRole.Window, QColor("#282c34"))
    dark_palette.setColor(QPalette.ColorRole.WindowText, QColor("#abb2bf"))
    dark_palette.setColor(QPalette.ColorRole.Base, QColor("#21252b"))
    dark_palette.setColor(QPalette.ColorRole.AlternateBase, QColor("#282c34"))
    dark_palette.setColor(QPalette.ColorRole.ToolTipBase, Qt.GlobalColor.white)
    dark_palette.setColor(QPalette.ColorRole.ToolTipText, Qt.GlobalColor.black)
    dark_palette.setColor(QPalette.ColorRole.Text, QColor("#abb2bf"))
    dark_palette.setColor(QPalette.ColorRole.Button, QColor("#343a40"))
    dark_palette.setColor(QPalette.ColorRole.ButtonText, QColor("#abb2bf"))
    dark_palette.setColor(QPalette.ColorRole.BrightText, Qt.GlobalColor.red)
    dark_palette.setColor(QPalette.ColorRole.Link, QColor("#61afef"))
    dark_palette.setColor(QPalette.ColorRole.Highlight, QColor("#9881a7"))
    dark_palette.setColor(QPalette.ColorRole.HighlightedText, QColor("#ffffff"))
    app.setPalette(dark_palette)

    try:
        with open(resource_path('style.qss'), 'r') as f:
            app.setStyleSheet(f.read())
    except FileNotFoundError:
        print("Warning: style.qss not found. The application will run with default styling.")

    # --- Splash Screen ---
    pixmap = QPixmap(400, 250)
    pixmap.fill(QColor(dark_palette.color(QPalette.ColorRole.Window)))
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    painter.setPen(QColor("#9881a7"))
    painter.setFont(QFont("Segoe UI", 48, QFont.Weight.Bold))
    title_rect = pixmap.rect().translated(0, -20)
    painter.drawText(title_rect, Qt.AlignmentFlag.AlignCenter, "Formul8")
    painter.end()

    splash = AnimatedSplashScreen(pixmap, f"Version {APP_VERSION}", duration_ms=2500)
    splash.show()
    app.processEvents()

    # --- Main Window Launch ---
    main_window = MainWindow()
    main_window.setWindowIcon(app_icon)

    # --- NEW: Install the main window as a global event filter ---
    app.installEventFilter(main_window)

    start_time = time.time()
    while time.time() < start_time + 2.5:
        app.processEvents()

    splash.close()
    main_window.fade_in()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()