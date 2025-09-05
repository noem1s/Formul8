# formul8/views/settings_data.py
# Frame for handling data backup and restore operations.

import shutil
from datetime import datetime

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, QGroupBox,
    QFileDialog, QMessageBox, QApplication, QDialogButtonBox
)
from PyQt6.QtCore import pyqtSignal, Qt

# --- Local Imports ---
# REMOVED: from ..data_manager import data_manager
from ..ui_components import CustomMessageBox


class DataManagementFrame(QWidget):
    """
    Provides UI for backing up the current data file and restoring from a backup.
    """
    back_signal = pyqtSignal()

    # UPDATED: The constructor now accepts the data_manager instance.
    def __init__(self, data_manager, parent=None):
        super().__init__(parent)
        self.setObjectName("DataManagementFrame")

        # RATIONALE: The passed-in DataManager is stored as an instance variable.
        self.data_manager = data_manager

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(15)

        top_bar = QHBoxLayout()
        back_button = QPushButton("<- Back to Settings")
        back_button.clicked.connect(self.back_signal.emit)
        top_bar.addWidget(back_button)
        top_bar.addStretch()
        main_layout.addLayout(top_bar)

        header = QLabel("Data Management")
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

        # --- Backup Group ---
        backup_group = QGroupBox("Backup")
        backup_layout = QVBoxLayout(backup_group)
        backup_layout.addWidget(QLabel("Backup your entire library and formulations to a safe location."))
        backup_btn = QPushButton("Backup Data...")
        backup_btn.clicked.connect(self._backup_data)
        backup_layout.addWidget(backup_btn)
        main_layout.addLayout(create_centered_group(backup_group))

        # --- Restore Group ---
        restore_group = QGroupBox("Restore")
        restore_layout = QVBoxLayout(restore_group)
        restore_layout.addWidget(QLabel("WARNING: Restoring will overwrite all current data."))
        restore_btn = QPushButton("Restore Data...")
        restore_btn.clicked.connect(self._restore_data)
        restore_layout.addWidget(restore_btn)
        main_layout.addLayout(create_centered_group(restore_group))

        main_layout.addStretch()

    def on_show(self):
        pass

    def _backup_data(self):
        """ Copies the current data file to a user-selected location. """
        default_name = f"formul8_backup_{datetime.now().strftime('%Y%m%d')}.json"
        # UPDATED: Uses the instance variable self.data_manager
        source_file = self.data_manager.data_file

        path, _ = QFileDialog.getSaveFileName(self, "Backup Data File", default_name, "JSON Files (*.json)")
        if path:
            try:
                shutil.copy(source_file, path)
                QMessageBox.information(self, "Backup Successful", f"Data successfully backed up to:\n{path}")
            except Exception as e:
                QMessageBox.critical(self, "Backup Error", f"Could not create backup:\n{e}")

    def _restore_data(self):
        """ Overwrites the current data file with a user-selected backup. """
        reply = CustomMessageBox.question(self, "Restore Data",
                                          "This will overwrite your current data and restart the application.\n"
                                          "Any unsaved changes will be lost.\n\n"
                                          "Are you sure you want to continue?")
        if reply != QDialogButtonBox.StandardButton.Yes:
            return

        path, _ = QFileDialog.getOpenFileName(self, "Select Backup File to Restore", "", "JSON Files (*.json)")
        if path:
            try:
                # UPDATED: Uses the instance variable self.data_manager
                destination_file = self.data_manager.data_file
                shutil.copy(path, destination_file)
                QMessageBox.information(self, "Restore Successful",
                                        "Data successfully restored.\nThe application will now restart.")
                # A simple way to reload data is to restart the app
                qApp = QApplication.instance()
                qApp.exit(88)  # Custom exit code to signal restart
            except Exception as e:
                QMessageBox.critical(self, "Restore Error", f"Could not restore from backup:\n{e}")