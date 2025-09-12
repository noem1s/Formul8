# formul8/views/ingredient_manager.py
# The main frame for viewing and managing the ingredient library.

from datetime import datetime

# --- PyQt6 Imports ---
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, QLineEdit,
    QMessageBox, QMenu, QFileDialog, QTextEdit, QDialogButtonBox, QTreeWidgetItem,
    QDialog, QStyle, QHeaderView
)
from PyQt6.QtCore import Qt, pyqtSignal, QTimer, QSettings, QPoint
from PyQt6.QtGui import QCursor

# --- Local Imports from our 'formul8' package ---
from ..components import CustomDialog, CustomMessageBox, DraggableTree, AccordItemWidget, TweakDialog
from ..constants import ACCORD_SYMBOL
from ..utils import format_for_display
from ..context_menu_handler import handle_tree_context_menu


# --- Helper Dialogs specific to this view ---
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
    edit_accord_signal = pyqtSignal(dict)  # Signal for editing accords

    def __init__(self, data_manager, parent=None):
        super().__init__(parent)
        self.data_manager = data_manager
        self.layout = QVBoxLayout(self)
        self.selected_item_name = None
        self.selected_item_type = None
        self.sort_state = (None, None)  # (column_index, order)

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
        self.ingredient_tree.setObjectName("IngredientManagerTree")
        self.ingredient_tree.header().setSectionsClickable(True)
        self.ingredient_tree.setSortingEnabled(True)
        self.columns = (
            "name", "conc", "diluent", "brand", "chem_name", "vendor", "cost", "note_type", "primary_cat",
            "secondary_cat")
        self.ingredient_tree.setColumnCount(len(self.columns))
        header_labels = [c.replace("_", " ").title() for c in self.columns]
        header_labels[self.columns.index('cost')] = 'Cost / g'
        self.ingredient_tree.setHeaderLabels(header_labels)
        self.ingredient_tree.header().setDefaultAlignment(Qt.AlignmentFlag.AlignCenter)
        self.ingredient_tree.itemDoubleClicked.connect(self.edit_selected_item_gui)
        self.ingredient_tree.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.ingredient_tree.customContextMenuRequested.connect(self.show_context_menu)
        self.ingredient_tree.itemSelectionChanged.connect(self.on_treeview_selection_change)
        self.ingredient_tree.itemSelectionChanged.connect(self._on_selection_changed)
        self.ingredient_tree.itemExpanded.connect(self._update_accord_indicator)
        self.ingredient_tree.itemCollapsed.connect(self._update_accord_indicator)
        self.ingredient_tree.header().sectionClicked.connect(
            lambda index: self._handle_sort_request(self.ingredient_tree, index)
        )
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

        header = self.ingredient_tree.header()
        header.setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        header.setStretchLastSection(True)

    def _update_accord_indicator(self, item):
        """Changes the expand/collapse icon for an accord item."""
        widget = self.sender().itemWidget(item, 0)
        if isinstance(widget, AccordItemWidget):
            widget.set_expanded(item.isExpanded())

    def _on_selection_changed(self):
        """Updates the visual state of all accord widgets based on tree selection."""
        for i in range(self.ingredient_tree.topLevelItemCount()):
            item = self.ingredient_tree.topLevelItem(i)
            if item:
                widget = self.ingredient_tree.itemWidget(item, 0)
                if isinstance(widget, AccordItemWidget):
                    widget.set_selected(item.isSelected())

    def _handle_sort_request(self, tree_widget, column_index):
        """
        Handles the three-state sorting logic for tree widgets.
        """
        current_sort_column, current_sort_order = self.sort_state

        new_sort_order = None
        if current_sort_column != column_index:
            new_sort_column = column_index
            new_sort_order = Qt.SortOrder.AscendingOrder
        elif current_sort_order == Qt.SortOrder.AscendingOrder:
            new_sort_column = column_index
            new_sort_order = Qt.SortOrder.DescendingOrder
        else:
            new_sort_column = None
            new_sort_order = None

        self.sort_state = (new_sort_column, new_sort_order)
        self.view_ingredients_gui()

        if new_sort_column is not None:
            tree_widget.header().setSortIndicator(new_sort_column, new_sort_order)
            tree_widget.header().setSortIndicatorShown(True)
        else:
            header = self.ingredient_tree.header()
            header.setSortIndicatorShown(False)
            header.setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
            header.setStretchLastSection(True)

    def show_status_message(self, text, is_error=False):
        self.status_label.setText(text)
        self.status_label.setProperty("error", is_error)
        self.status_label.style().polish(self.status_label)
        self.status_timer.start(3000)

    def save_column_widths(self):
        settings = QSettings()
        header_state = self.ingredient_tree.header().saveState()
        settings.setValue("ingredient_library/headerState", header_state)

    def load_column_widths(self):
        settings = QSettings()
        header_state = settings.value("ingredient_library/headerState")
        if header_state:
            self.ingredient_tree.header().restoreState(header_state)

    def view_ingredients_gui(self):
        """
        Populates the tree with ingredients and accords, showing accords as expandable folders.
        """
        self.ingredient_tree.clear()
        search_term = self.search_entry.text().lower()

        all_ingredients = self.data_manager.get_all_ingredients()

        materials_to_show = all_ingredients
        if search_term:
            materials_to_show = [
                item for item in all_ingredients if
                search_term in item.get('name', '').lower() or
                (item.get('type') == 'accord' and any(
                    search_term in entry.get('ingredient_name', '').lower() for entry in
                    self.data_manager.get_formulation_by_name(item.get('name', '')).get('entries', [])))
            ]

        sort_column, sort_order = self.sort_state
        if sort_column is not None:
            is_reverse = sort_order == Qt.SortOrder.DescendingOrder
            sort_key_map = {
                0: 'name', 1: 'concentration', 2: 'diluent', 3: 'brand', 4: 'chemical_name',
                5: 'vendor', 6: 'cost', 7: 'note_type', 8: 'primary_category', 9: 'secondary_category'
            }
            sort_key = sort_key_map.get(sort_column, 'name')

            if sort_key in ['concentration', 'cost']:
                materials_to_show.sort(key=lambda x: float(x.get(sort_key, 0)), reverse=is_reverse)
            else:
                materials_to_show.sort(key=lambda x: str(x.get(sort_key, '')).lower(), reverse=is_reverse)

        alignments = {
            1: Qt.AlignmentFlag.AlignCenter, 2: Qt.AlignmentFlag.AlignCenter,
            3: Qt.AlignmentFlag.AlignCenter, 4: Qt.AlignmentFlag.AlignCenter,
            5: Qt.AlignmentFlag.AlignCenter, 6: Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter,
            7: Qt.AlignmentFlag.AlignCenter, 8: Qt.AlignmentFlag.AlignCenter, 9: Qt.AlignmentFlag.AlignCenter,
        }

        for item_data in materials_to_show:
            parent_item = QTreeWidgetItem()
            parent_item.setData(0, Qt.ItemDataRole.UserRole,
                                {'name': item_data['name'], 'type': item_data.get('type', 'raw')})
            self.ingredient_tree.addTopLevelItem(parent_item)

            is_accord = item_data.get('type') == 'accord'
            if is_accord:
                item_widget = AccordItemWidget(item_data['name'])
                item_widget.set_tree_item(parent_item)
                self.ingredient_tree.setItemWidget(parent_item, 0, item_widget)
            else:
                parent_item.setText(0, item_data['name'])
                parent_item.setTextAlignment(0, Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)

            parent_item.setText(1, f"{item_data.get('concentration', 100.0):.2f}%")
            parent_item.setText(2, format_for_display(item_data.get('diluent', '')))
            parent_item.setText(3, format_for_display(item_data.get('brand', '')))
            parent_item.setText(4, format_for_display(item_data.get('chemical_name', '')))
            parent_item.setText(5, format_for_display(item_data.get('vendor', '')))
            parent_item.setText(6, f"${item_data.get('cost', 0.0):.2f}")
            parent_item.setText(7, format_for_display(item_data.get('note_type', 'Other')))
            parent_item.setText(8, format_for_display(item_data.get('primary_category', 'Uncategorized')))
            parent_item.setText(9, format_for_display(item_data.get('secondary_category', '')))

            for i, align in alignments.items():
                parent_item.setTextAlignment(i, align)

            if is_accord:
                accord_formula = self.data_manager.get_formulation_by_name(item_data['name'])
                if accord_formula:
                    self.data_manager.calculate_formulation_totals(accord_formula)
                    for entry in sorted(accord_formula.get('entries', []), key=lambda x: x['ingredient_name']):
                        child_data = [f"    - {entry['ingredient_name']}", f"     {entry.get('percentage', 0):.2f}%"]
                        child_item = QTreeWidgetItem(child_data)
                        child_item.setFlags(child_item.flags() & ~Qt.ItemFlag.ItemIsDragEnabled)
                        child_item.setTextAlignment(0, Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
                        child_item.setTextAlignment(1, Qt.AlignmentFlag.AlignCenter)
                        parent_item.addChild(child_item)

        self.on_treeview_selection_change()
        self._on_selection_changed()

    def on_treeview_selection_change(self):
        selected_items = self.ingredient_tree.selectedItems()
        if not selected_items or selected_items[0].parent() is not None:
            self.selected_item_name = None
            self.selected_item_type = None
            self.status_label.clear()
            if selected_items:
                selected_items[0].setSelected(False)
            return

        item_info = selected_items[0].data(0, Qt.ItemDataRole.UserRole)
        self.selected_item_name = item_info['name']
        self.selected_item_type = item_info['type']
        self.show_status_message(f"'{self.selected_item_name}' selected.")

    def show_context_menu(self, position):
        handle_tree_context_menu(self, self.ingredient_tree, position)

    def open_notes_window(self):
        if not self.selected_item_name or self.selected_item_type != 'raw': return
        ingredient = self.data_manager.get_ingredient_by_name(self.selected_item_name)
        if not ingredient: return

        dialog = NotesWindow(ingredient, self)
        if dialog.exec():
            ingredient['notes'] = dialog.get_notes()
            self.data_manager.save_ingredient(ingredient)
            self.view_ingredients_gui()
            self.show_status_message(f"Notes for '{ingredient['name']}' updated.")

    def add_new_ingredient_gui(self):
        # --- MODIFIED: Emit an empty dict instead of None to match signal signature ---
        self.edit_ingredient_signal.emit({})

    def edit_selected_item_gui(self):
        if not self.selected_item_name: return

        if self.selected_item_type == 'accord':
            accord_data = self.data_manager.get_formulation_by_name(self.selected_item_name)
            if accord_data:
                self.edit_accord_signal.emit(accord_data)
        else:
            ingredient_data = self.data_manager.get_ingredient_by_name(self.selected_item_name)
            if ingredient_data:
                self.edit_ingredient_signal.emit(ingredient_data)

    def delete_item_gui(self):
        if not self.selected_item_name: return

        item_type_str = "accord" if self.selected_item_type == 'accord' else "ingredient"
        reply = CustomMessageBox.question(self, f"Confirm Delete",
                                          f"Are you sure you want to delete the {item_type_str} '{self.selected_item_name}'?")
        if reply == QDialogButtonBox.StandardButton.Yes:
            name_to_delete = self.selected_item_name
            if self.selected_item_type == 'accord':
                self.data_manager.delete_formulation(name_to_delete)
            else:
                self.data_manager.delete_ingredient(name_to_delete)

            self.selected_item_name = None
            self.selected_item_type = None
            self.view_ingredients_gui()
            self.show_status_message(f"'{name_to_delete}' deleted.")

    def export_ingredient_library(self):
        if not self.data_manager.get_all_ingredients():
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

        success, error_msg = self.data_manager.export_ingredients_to_pdf(path)
        if success:
            QMessageBox.information(self, "Export Successful", f"Ingredient library exported to\n{path}")
        else:
            QMessageBox.critical(self, "Export Error", f"Could not export library:\n{error_msg}")