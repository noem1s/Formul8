# formul8/views/ingredient_manager.py
# The main frame for viewing and managing the ingredient library.

from datetime import datetime

# --- PyQt6 Imports ---
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, QLineEdit,
    QMessageBox, QMenu, QFileDialog, QTextEdit, QDialogButtonBox, QTreeWidgetItem,
    QDialog
)
from PyQt6.QtCore import Qt, pyqtSignal, QTimer, QSettings

# --- Local Imports from our 'formul8' package ---
# REMOVED: from ..data_manager import data_manager
from ..ui_components import CustomDialog, CustomMessageBox, DraggableTree


# --- Helper Dialogs specific to this view (Unchanged) ---
class NotesWindow(CustomDialog):
    """ A simple dialog for viewing and editing ingredient notes. """

    def __init__(self, ingredient_obj, parent=None):
        super().__init__(parent)
        self.ingredient = ingredient_obj
        self.setWindowTitle(f"Notes for {self.ingredient.get('name', 'N/A')}")
        self.setMinimumSize(400, 300)
        layout = QVBoxLayout()
        self.setLayout(layout)
        self.notes_text = QTextEdit()
        self.notes_text.setPlainText(self.ingredient.get('notes', ''))
        layout.addWidget(self.notes_text)
        button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel)
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)

    def get_notes(self):
        return self.notes_text.toPlainText().strip()


class ExportChoiceDialog(QDialog):
    """ A dialog to let the user choose between PDF and Text file export. """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Choose Export Format")
        self.setModal(True)
        self.format = None

        layout = QVBoxLayout(self)
        self.setMinimumWidth(250)

        pdf_button = QPushButton("Export as PDF")
        pdf_button.clicked.connect(lambda: self.set_format('pdf'))

        txt_button = QPushButton("Export as Text File")
        txt_button.clicked.connect(lambda: self.set_format('txt'))

        layout.addWidget(pdf_button)
        layout.addWidget(txt_button)

    def set_format(self, format_choice):
        self.format = format_choice
        self.accept()


# --- Main View Frame ---
class IngredientManagementFrame(QWidget):
    """ The primary widget for displaying and interacting with the ingredient library. """
    back_signal = pyqtSignal()
    edit_ingredient_signal = pyqtSignal(dict)

    # UPDATED: The constructor now accepts the data_manager instance.
    def __init__(self, data_manager, parent=None):
        super().__init__(parent)

        # RATIONALE: The passed-in DataManager instance is stored as an instance
        # variable, making it accessible throughout this class via `self.data_manager`.
        self.data_manager = data_manager

        self.layout = QVBoxLayout(self)
        self.selected_ingredient_obj_for_action = None

        top_bar = QHBoxLayout()
        back_button = QPushButton("<- Back to Main Menu")
        back_button.clicked.connect(self.back_signal.emit)
        top_bar.addWidget(back_button)
        top_bar.addStretch()
        export_button = QPushButton("Export Library")
        export_button.clicked.connect(self.export_ingredient_library)
        top_bar.addWidget(export_button)
        self.layout.addLayout(top_bar)

        header = QLabel("Ingredient Library")
        header.setObjectName("HeaderLabel")
        header.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.layout.addWidget(header)

        search_layout = QHBoxLayout()
        search_layout.addWidget(QLabel("Search:"))
        self.search_entry = QLineEdit()
        self.search_entry.textChanged.connect(self.view_ingredients_gui)
        search_layout.addWidget(self.search_entry)
        clear_button = QPushButton("Clear")
        clear_button.clicked.connect(self.search_entry.clear)
        search_layout.addWidget(clear_button)
        self.layout.addLayout(search_layout)

        self.ingredient_tree = DraggableTree()
        self.ingredient_tree.header().setDefaultAlignment(Qt.AlignmentFlag.AlignCenter)
        self.columns = (
            "name", "conc", "diluent", "brand", "chem_name", "vendor", "cost", "note_type", "primary_cat",
            "secondary_cat")
        self.ingredient_tree.setColumnCount(len(self.columns))
        header_labels = [c.replace("_", " ").title() for c in self.columns]
        header_labels[self.columns.index('cost')] = 'Cost / g'
        self.ingredient_tree.setHeaderLabels(header_labels)
        self.ingredient_tree.itemDoubleClicked.connect(self.edit_selected_ingredient_gui)
        self.ingredient_tree.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.ingredient_tree.customContextMenuRequested.connect(self.show_context_menu)
        self.ingredient_tree.itemSelectionChanged.connect(self.on_treeview_selection_change)
        self.layout.addWidget(self.ingredient_tree)

        bottom_layout = QHBoxLayout()
        add_button = QPushButton("Add New Ingredient")
        add_button.clicked.connect(self.add_new_ingredient_gui)
        bottom_layout.addStretch()
        bottom_layout.addWidget(add_button)
        bottom_layout.addStretch()
        self.layout.addLayout(bottom_layout)

        self.status_label = QLabel("")
        self.status_label.setObjectName("StatusLabel")
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.layout.addWidget(self.status_label)
        self.status_timer = QTimer(self)
        self.status_timer.setSingleShot(True)
        self.status_timer.timeout.connect(self.status_label.clear)

    def on_show(self):
        self.view_ingredients_gui()
        self.load_column_widths()

    def show_status_message(self, text, is_error=False):
        self.status_label.setText(text)
        self.status_label.setProperty("error", is_error)
        self.status_label.style().polish(self.status_label)
        self.status_timer.start(3000)

    def save_column_widths(self):
        """Saves the current column widths of the ingredient tree to settings."""
        settings = QSettings()
        header_state = self.ingredient_tree.header().saveState()
        settings.setValue("ingredient_library/headerState", header_state)

    def load_column_widths(self):
        """Loads and applies column widths from settings."""
        settings = QSettings()
        header_state = settings.value("ingredient_library/headerState")
        if header_state:
            self.ingredient_tree.header().restoreState(header_state)

    def view_ingredients_gui(self):
        self.ingredient_tree.clear()
        search_term = self.search_entry.text().lower()
        # UPDATED: Uses the instance variable
        ingredients_list = self.data_manager.data.get('ingredients', [])

        ingredients_to_show = ingredients_list
        if search_term:
            ingredients_to_show = [
                ing for ing in ingredients_list if any(
                    search_term in str(ing.get(field, '')).lower()
                    for field in ['name', 'primary_category', 'notes']
                )
            ]

        for ing in sorted(ingredients_to_show, key=lambda x: x.get('name', '')):
            def clean_val(key, default=''):
                val = ing.get(key, default)
                return '' if str(val).strip().lower() in ('n/a', '') else str(val)

            item_data = [
                ing.get('name', ''),
                f"{ing.get('concentration', 0.0):.2f}%",
                clean_val('diluent') if ing.get('concentration', 100.0) < 100.0 else '',
                clean_val('brand'),
                clean_val('chemical_name'),
                clean_val('vendor'),
                f"${ing.get('cost', 0.0):.2f}",
                ing.get('note_type', 'Other'),
                ing.get('primary_category', 'Uncategorized'),
                clean_val('secondary_category')
            ]
            item = QTreeWidgetItem(item_data)
            item.setData(0, Qt.ItemDataRole.UserRole, ing['name'])

            align_left = Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter
            align_center = Qt.AlignmentFlag.AlignCenter
            align_right = Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter

            alignments = [
                align_left,  # Name
                align_center,  # Conc
                align_left,  # Diluent
                align_left,  # Brand
                align_left,  # Chem Name
                align_left,  # Vendor
                align_right,  # Cost
                align_center,  # Note Type
                align_center,  # Primary Cat
                align_center  # Secondary Cat
            ]
            for i, align in enumerate(alignments):
                item.setTextAlignment(i, align)

            self.ingredient_tree.addTopLevelItem(item)

        self.on_treeview_selection_change()

    def on_treeview_selection_change(self):
        selected = self.ingredient_tree.selectedItems()
        if selected:
            # UPDATED: Uses the instance variable
            self.selected_ingredient_obj_for_action = self.data_manager.get_ingredient_by_name(
                selected[0].data(0, Qt.ItemDataRole.UserRole))
            if self.selected_ingredient_obj_for_action:
                self.show_status_message(f"'{self.selected_ingredient_obj_for_action['name']}' selected.")
        else:
            self.selected_ingredient_obj_for_action = None
            self.status_label.clear()

    def show_context_menu(self, position):
        if not self.selected_ingredient_obj_for_action: return
        menu = QMenu(self)
        notes_action = menu.addAction("Notes...")
        edit_action = menu.addAction("Edit Ingredient")
        delete_action = menu.addAction("Delete Ingredient")
        action = menu.exec(self.ingredient_tree.mapToGlobal(position))

        if action == edit_action:
            self.edit_selected_ingredient_gui()
        elif action == delete_action:
            self.delete_ingredient_gui()
        elif action == notes_action:
            self.open_notes_window()

    def open_notes_window(self):
        if not self.selected_ingredient_obj_for_action: return
        dialog = NotesWindow(self.selected_ingredient_obj_for_action, self)
        if dialog.exec():
            self.selected_ingredient_obj_for_action['notes'] = dialog.get_notes()
            # UPDATED: Uses the instance variable
            self.data_manager.save_data()
            self.view_ingredients_gui()
            self.show_status_message(f"Notes for '{self.selected_ingredient_obj_for_action['name']}' updated.")

    def add_new_ingredient_gui(self):
        self.edit_ingredient_signal.emit({})

    def edit_selected_ingredient_gui(self):
        if self.selected_ingredient_obj_for_action:
            self.edit_ingredient_signal.emit(self.selected_ingredient_obj_for_action)

    def delete_ingredient_gui(self):
        if not self.selected_ingredient_obj_for_action: return
        reply = CustomMessageBox.question(self, "Confirm Delete",
                                          f"Delete '{self.selected_ingredient_obj_for_action['name']}'?")
        if reply == QDialogButtonBox.StandardButton.Yes:
            name = self.selected_ingredient_obj_for_action['name']
            # UPDATED: Uses the instance variable
            self.data_manager.data['ingredients'].remove(self.selected_ingredient_obj_for_action)
            self.data_manager.save_data()
            self.view_ingredients_gui()
            self.show_status_message(f"'{name}' deleted.")

    def export_ingredient_library(self):
        # UPDATED: Uses the instance variable
        if not self.data_manager.data['ingredients']:
            CustomMessageBox.warning(self, "Empty Library", "There are no ingredients to export.")
            return
        choice_dialog = ExportChoiceDialog(self)
        if not choice_dialog.exec():
            return

        if choice_dialog.format == 'txt':
            self._export_library_as_txt()
        elif choice_dialog.format == 'pdf':
            self._export_library_as_pdf()

    def _export_library_as_txt(self):
        default_name = f"formul8_ingredients_{datetime.now().strftime('%Y%m%d')}.txt"
        path, _ = QFileDialog.getSaveFileName(self, "Export Library as Text File", default_name, "Text Files (*.txt)")
        if not path:
            return

        # UPDATED: Uses the instance variable
        success, error_msg = self.data_manager.export_ingredients_to_txt(path)
        if success:
            QMessageBox.information(self, "Export Successful", f"Ingredient library exported to\n{path}")
        else:
            QMessageBox.critical(self, "Export Error", f"Could not export library:\n{error_msg}")

    def _export_library_as_pdf(self):
        default_name = f"formul8_ingredients_{datetime.now().strftime('%Y%m%d')}.pdf"
        path, _ = QFileDialog.getSaveFileName(self, "Export Library as PDF", default_name, "PDF Files (*.pdf)")
        if not path:
            return
        # UPDATED: Uses the instance variable
        success, error_msg = self.data_manager.export_ingredients_to_pdf(path)
        if success:
            QMessageBox.information(self, "Export Successful", f"Ingredient library exported to\n{path}")
        else:
            QMessageBox.critical(self, "Export Error", f"Could not export library:\n{error_msg}")