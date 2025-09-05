# formul8/views/main_menu.py
# The main menu screen for the application.

from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QDesktopServices
from PyQt6.QtCore import QUrl
from urllib.parse import quote

# RATIONALE: Import the constants and our new custom widget
from ..constants import GITHUB_ICON_SVG, INSTAGRAM_ICON_SVG, GITHUB_ICON_SVG_HOVER, INSTAGRAM_ICON_SVG_HOVER
from ..ui_components import HoverIconLink


class MainMenuFrame(QWidget):
    """
    The first screen the user sees. Provides top-level navigation.
    It emits signals that the main window connects to in order to switch frames.
    """
    # Define signals that will be emitted when buttons are clicked
    show_ingredients_signal = pyqtSignal()
    show_formulations_signal = pyqtSignal()
    show_settings_signal = pyqtSignal()

    def __init__(self, main_win, data_manager, parent=None):
        super().__init__(parent)
        self.setObjectName("MainMenuFrame")
        self.data_manager = data_manager

        main_layout = QVBoxLayout(self)

        center_menu_container = QWidget()
        center_menu_layout = QVBoxLayout(center_menu_container)
        center_menu_layout.setSpacing(25)
        center_menu_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.title_label = QLabel("Formul8")
        self.title_label.setObjectName("MainMenuHeaderLabel")
        self.title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        center_menu_layout.addWidget(self.title_label)
        center_menu_layout.addSpacing(30)

        def add_centered_button(layout, button):
            h_layout = QHBoxLayout()
            h_layout.addStretch()
            h_layout.addWidget(button)
            h_layout.addStretch()
            layout.addLayout(h_layout)

        btn_ingredients = QPushButton("Ingredient Library")
        btn_ingredients.setObjectName("MainMenuButton")
        btn_ingredients.clicked.connect(self.show_ingredients_signal.emit)
        add_centered_button(center_menu_layout, btn_ingredients)

        btn_formulations = QPushButton("Formulation Manager")
        btn_formulations.setObjectName("MainMenuButton")
        btn_formulations.clicked.connect(self.show_formulations_signal.emit)
        add_centered_button(center_menu_layout, btn_formulations)

        btn_settings = QPushButton("Settings")
        btn_settings.setObjectName("MainMenuButton")
        btn_settings.clicked.connect(self.show_settings_signal.emit)
        add_centered_button(center_menu_layout, btn_settings)

        btn_exit = QPushButton("Exit Application")
        btn_exit.setObjectName("MainMenuButton")
        btn_exit.clicked.connect(main_win.close)

        # --- Social and Support Links ---
        links_layout = QHBoxLayout()
        links_layout.setSpacing(15)
        links_layout.setContentsMargins(15, 30, 0, 10)

        # UPDATED: Use the new HoverIconLink widget
        github_url = "https://github.com/noem1s"
        github_label = HoverIconLink(
            normal_svg=GITHUB_ICON_SVG,
            hover_svg=GITHUB_ICON_SVG_HOVER,
            url=github_url,
            tooltip="report a bug or request a feature on gitHub"
        )
        links_layout.addWidget(github_label)

        # UPDATED: Use the new HoverIconLink widget
        instagram_url = "https://www.instagram.com/_.noemis._/?hl=en"
        instagram_label = HoverIconLink(
            normal_svg=INSTAGRAM_ICON_SVG,
            hover_svg=INSTAGRAM_ICON_SVG_HOVER,
            url=instagram_url,
            tooltip="follow me on instagram!!!"
        )
        links_layout.addWidget(instagram_label)

        links_layout.addStretch()

        # --- Layout Assembly ---
        main_layout.addStretch(1)
        main_layout.addWidget(center_menu_container)
        main_layout.addStretch(2)

        bottom_bar_layout = QHBoxLayout()
        bottom_bar_layout.addLayout(links_layout, 1)
        bottom_bar_layout.addWidget(btn_exit)
        bottom_bar_layout.addStretch(1)

        main_layout.addLayout(bottom_bar_layout)
        main_layout.setContentsMargins(20, 20, 20, 20)

    def on_show(self):
        """ A hook for any logic that needs to run when this frame becomes visible. """
        pass