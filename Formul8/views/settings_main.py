# formul8/views/settings_main.py
# The main navigation frame for all application settings.

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, QGroupBox, QRadioButton, QButtonGroup
)
from PyQt6.QtCore import Qt, pyqtSignal


class SettingsMenuFrame(QWidget):
    """
    Serves as the main menu for the settings section, providing navigation
    to more specific settings frames.
    """
    back_signal = pyqtSignal()
    show_list_management_signal = pyqtSignal(str, str)
    show_data_management_signal = pyqtSignal()
    show_scent_color_settings_signal = pyqtSignal()

    def __init__(self, data_manager, parent=None):
        super().__init__(parent)
        self.setObjectName("SettingsMenuFrame")
        self.data_manager = data_manager

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(15)

        top_bar = QHBoxLayout()
        back_button = QPushButton("<- Back to Main Menu")
        back_button.clicked.connect(self.back_signal.emit)
        top_bar.addWidget(back_button)
        top_bar.addStretch()
        main_layout.addLayout(top_bar)

        header = QLabel("Settings")
        header.setObjectName("HeaderLabel")
        header.setAlignment(Qt.AlignmentFlag.AlignCenter)
        main_layout.addWidget(header)

        # Helper to center group boxes
        def create_centered_group(group_box):
            wrapper_layout = QHBoxLayout()
            wrapper_layout.addStretch()
            wrapper_layout.addWidget(group_box)
            wrapper_layout.addStretch()
            return wrapper_layout

        # --- Application Defaults Group ---
        defaults_group = QGroupBox("Application Defaults")
        defaults_layout = QHBoxLayout(defaults_group)
        defaults_layout.addWidget(QLabel("Default Formulation View:"))
        self.grid_radio = QRadioButton("Grid")
        self.grid_radio.toggled.connect(self._on_view_mode_changed)
        self.list_radio = QRadioButton("List")
        self.list_radio.toggled.connect(self._on_view_mode_changed)
        self.view_mode_group = QButtonGroup(self)
        self.view_mode_group.addButton(self.grid_radio)
        self.view_mode_group.addButton(self.list_radio)
        defaults_layout.addWidget(self.grid_radio)
        defaults_layout.addWidget(self.list_radio)
        main_layout.addLayout(create_centered_group(defaults_group))

        # --- List Management Group ---
        list_mgmt_group = QGroupBox("Manage Dropdown Lists")
        list_mgmt_layout = QHBoxLayout(list_mgmt_group)
        list_mgmt_layout.setSpacing(10)
        btn_cat = QPushButton("Scent Categories")
        btn_cat.clicked.connect(lambda: self.show_list_management_signal.emit("scent_categories", "Scent Categories"))
        btn_sup = QPushButton("Suppliers")
        btn_sup.clicked.connect(lambda: self.show_list_management_signal.emit("suppliers", "Suppliers"))
        btn_brd = QPushButton("Brands")
        btn_brd.clicked.connect(lambda: self.show_list_management_signal.emit("brands", "Brands"))
        btn_dil = QPushButton("Diluents")
        btn_dil.clicked.connect(lambda: self.show_list_management_signal.emit("diluents", "Diluents"))
        list_mgmt_layout.addWidget(btn_cat)
        list_mgmt_layout.addWidget(btn_sup)
        list_mgmt_layout.addWidget(btn_brd)
        list_mgmt_layout.addWidget(btn_dil)
        main_layout.addLayout(create_centered_group(list_mgmt_group))

        # --- Feature Settings Group ---
        feature_settings_group = QGroupBox("Feature Settings")
        feature_settings_layout = QHBoxLayout(feature_settings_group)
        btn_scent_colors = QPushButton("Scent Profile Colors")
        btn_scent_colors.clicked.connect(self.show_scent_color_settings_signal.emit)
        feature_settings_layout.addWidget(btn_scent_colors)
        main_layout.addLayout(create_centered_group(feature_settings_group))

        # --- Data Management Group ---
        data_mgmt_group = QGroupBox("Data Management")
        data_mgmt_layout = QHBoxLayout(data_mgmt_group)
        data_mgmt_layout.setSpacing(10)
        btn_data_mgmt = QPushButton("Backup / Restore Data")
        btn_data_mgmt.clicked.connect(self.show_data_management_signal.emit)
        data_mgmt_layout.addWidget(btn_data_mgmt)
        main_layout.addLayout(create_centered_group(data_mgmt_group))

        main_layout.addStretch()

    def on_show(self):
        """ Read the current setting from the data_manager and update the UI. """
        self.grid_radio.blockSignals(True)
        self.list_radio.blockSignals(True)

        current_view_mode = self.data_manager.get_setting('default_formulation_view') or 'grid'
        if current_view_mode == 'grid':
            self.grid_radio.setChecked(True)
        else:
            self.list_radio.setChecked(True)

        self.grid_radio.blockSignals(False)
        self.list_radio.blockSignals(False)

    def _on_view_mode_changed(self):
        """ Save the new default view mode setting via the data_manager. """
        if self.view_mode_group.checkedButton():
            new_mode = 'grid' if self.grid_radio.isChecked() else 'list'
            if self.data_manager.get_setting('default_formulation_view') != new_mode:
                self.data_manager.save_setting('default_formulation_view', new_mode)