# formul8/views/settings_lists.py
# A reusable frame for managing various lists in the application settings.

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, QListWidget,
    QInputDialog, QMessageBox, QDialogButtonBox
)
from PyQt6.QtCore import Qt, pyqtSignal

# --- Local Imports ---
# REMOVED: from ..data_manager import data_manager
from ..ui_components import CustomMessageBox


class GenericListManagementFrame(QWidget):
    """
    A generic frame for adding, editing, and deleting items from a list
    stored in the application settings. It's initialized with a key
    to know which list it should be managing.
    """
    back_signal = pyqtSignal()

    # UPDATED: The constructor now accepts the data_manager instance.
    def __init__(self, list_key, title, data_manager, parent=None):
        super().__init__(parent)
        self.list_key = list_key
        self.title = title
        # RATIONALE: The passed-in DataManager is stored as an instance variable.
        self.data_manager = data_manager

        main_layout = QVBoxLayout(self)

        top_bar = QHBoxLayout()
        back_button = QPushButton("<- Back to Settings")
        back_button.clicked.connect(self.back_signal.emit)
        top_bar.addWidget(back_button)
        top_bar.addStretch()
        main_layout.addLayout(top_bar)

        header = QLabel(f"Manage {self.title}")
        header.setObjectName("HeaderLabel")
        header.setAlignment(Qt.AlignmentFlag.AlignCenter)
        main_layout.addWidget(header)

        self.list_widget = QListWidget()
        self.list_widget.itemDoubleClicked.connect(self._edit_item)
        main_layout.addWidget(self.list_widget)

        button_layout = QHBoxLayout()
        add_btn = QPushButton("Add...")
        edit_btn = QPushButton("Edit...")
        delete_btn = QPushButton("Delete")

        add_btn.clicked.connect(self._add_item)
        edit_btn.clicked.connect(self._edit_item)
        delete_btn.clicked.connect(self._delete_item)

        button_layout.addStretch()
        button_layout.addWidget(add_btn)
        button_layout.addWidget(edit_btn)
        button_layout.addWidget(delete_btn)
        button_layout.addStretch()
        main_layout.addLayout(button_layout)

    def on_show(self):
        """ When the frame is shown, populate it with the latest data. """
        self._populate_list_widget()

    def _get_list(self):
        """ Safely gets the list from the data manager's settings. """
        # UPDATED: Uses the instance variable self.data_manager
        return self.data_manager.data['settings'].get(self.list_key, [])

    def _populate_list_widget(self):
        """ Clears and repopulates the list widget from the data source. """
        self.list_widget.clear()
        self.list_widget.addItems(sorted(self._get_list()))

    def _add_item(self):
        """ Opens a dialog to add a new item to the list. """
        text, ok = QInputDialog.getText(self, f"Add New {self.title}", "Enter new value:")
        if ok and text:
            current_list = self._get_list()
            if text in current_list:
                QMessageBox.warning(self, "Duplicate", f"'{text}' already exists in this list.")
                return
            current_list.append(text)
            # UPDATED: Uses the instance variable self.data_manager
            self.data_manager.save_data()
            self._populate_list_widget()

    def _edit_item(self):
        """ Opens a dialog to edit the currently selected item. """
        selected_item = self.list_widget.currentItem()
        if not selected_item:
            QMessageBox.warning(self, "Selection Error", "Please select an item to edit.")
            return

        old_text = selected_item.text()
        new_text, ok = QInputDialog.getText(self, "Edit Item", "Enter new value:", text=old_text)

        if ok and new_text and new_text != old_text:
            current_list = self._get_list()
            if new_text in current_list:
                QMessageBox.warning(self, "Duplicate", f"'{new_text}' already exists in this list.")
                return

            try:
                index = current_list.index(old_text)
                current_list[index] = new_text
                # UPDATED: Uses the instance variable self.data_manager
                self.data_manager.save_data()
                self._populate_list_widget()
            except ValueError:
                pass  # Item might have been deleted

    def _delete_item(self):
        """ Deletes the currently selected item after confirmation. """
        selected_item = self.list_widget.currentItem()
        if not selected_item:
            QMessageBox.warning(self, "Selection Error", "Please select an item to delete.")
            return

        reply = CustomMessageBox.question(self, "Confirm Delete",
                                          f"Are you sure you want to delete '{selected_item.text()}'?")
        if reply == QDialogButtonBox.StandardButton.Yes:
            try:
                current_list = self._get_list()
                current_list.remove(selected_item.text())
                # UPDATED: Uses the instance variable self.data_manager
                self.data_manager.save_data()
                self._populate_list_widget()
            except ValueError:
                pass  # Item might have been deleted