# formul8/views/settings_colors.py
# Frame for customizing the colors used in the scent profile charts.

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, QScrollArea, QColorDialog
)
from PyQt6.QtGui import QColor
from PyQt6.QtCore import Qt, pyqtSignal

# --- Local Imports ---
# REMOVED: from ..data_manager import data_manager


class ScentProfileSettingsFrame(QWidget):
    """
    Allows the user to customize the colors associated with each scent category.
    The UI is dynamically generated based on the scent categories in the settings.
    """
    back_signal = pyqtSignal()

    # UPDATED: The constructor now accepts the data_manager instance.
    def __init__(self, data_manager, parent=None):
        super().__init__(parent)
        # RATIONALE: The passed-in DataManager is stored as an instance variable.
        self.data_manager = data_manager

        main_layout = QVBoxLayout(self)

        top_bar = QHBoxLayout()
        back_button = QPushButton("<- Back to Settings")
        back_button.clicked.connect(self.back_signal.emit)
        top_bar.addWidget(back_button)
        top_bar.addStretch()
        main_layout.addLayout(top_bar)

        header = QLabel("Scent Profile Colors")
        header.setObjectName("HeaderLabel")
        header.setAlignment(Qt.AlignmentFlag.AlignCenter)
        main_layout.addWidget(header)

        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        main_layout.addWidget(self.scroll_area)

        self.scroll_content = QWidget()
        self.scroll_area.setWidget(self.scroll_content)
        self.content_layout = QVBoxLayout(self.scroll_content)
        self.content_layout.setAlignment(Qt.AlignmentFlag.AlignTop)

    def on_show(self):
        """ When the frame becomes visible, rebuild the color list. """
        self._populate_color_settings()

    def _populate_color_settings(self):
        """
        Dynamically creates a row for each scent category with a color picker button.
        """
        # Clear any existing widgets
        while self.content_layout.count():
            item = self.content_layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()

        # UPDATED: Uses the instance variable self.data_manager
        settings = self.data_manager.data['settings']
        categories = sorted(settings.get('scent_categories', []))
        color_map = settings.get('scent_profile_colors', {})
        default_color = "#808080"

        for category in categories:
            color_hex = color_map.get(category, default_color)

            row_widget = QWidget()
            row_layout = QHBoxLayout(row_widget)

            label = QLabel(category)
            label.setStyleSheet("font-size: 11pt; font-weight: bold;")

            color_button = QPushButton(color_hex.upper())
            color_button.setFixedSize(150, 40)
            self._update_button_style(color_button, color_hex)

            # Use a lambda to capture the specific category and button for the slot
            color_button.clicked.connect(
                lambda _, cat=category, btn=color_button: self._on_color_button_clicked(cat, btn)
            )

            row_layout.addWidget(label)
            row_layout.addStretch()
            row_layout.addWidget(color_button)

            self.content_layout.addWidget(row_widget)

    def _get_text_color_for_bg(self, bg_hex):
        """ Determines if black or white text is more readable on a given background color. """
        color = QColor(bg_hex)
        return "white" if color.lightnessF() < 0.5 else "black"

    def _update_button_style(self, button, color_hex):
        """ Helper function to apply the correct stylesheet to a color button. """
        text_color = self._get_text_color_for_bg(color_hex)
        button.setStyleSheet(
            f"background-color: {color_hex}; color: {text_color}; "
            "border-radius: 4px; font-weight: bold;"
        )

    def _on_color_button_clicked(self, category, button):
        """ Opens a color dialog and updates the setting if a new color is chosen. """
        # UPDATED: Uses the instance variable self.data_manager
        current_color_hex = self.data_manager.data['settings']['scent_profile_colors'].get(category, "#808080")
        new_color = QColorDialog.getColor(QColor(current_color_hex), self, f"Select Color for {category}")

        if new_color.isValid():
            new_hex = new_color.name()
            # UPDATED: Uses the instance variable self.data_manager
            self.data_manager.data['settings']['scent_profile_colors'][category] = new_hex
            self.data_manager.save_data()

            button.setText(new_hex.upper())
            self._update_button_style(button, new_hex)