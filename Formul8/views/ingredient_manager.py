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
from ..components import (
    CustomDialog, CustomMessageBox, DraggableTree, AccordItemWidget,
    configure_accord_item_display, create_fading_tree_widget
)
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
        self.sort_state = (None, None)

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
        # --- FIX: Use addWidget for QWidgets, not addLayout ---
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

        ing_container, self.ingredient_tree, self.top_fade, self.bottom_fade = create_fading_tree_widget(DraggableTree)
        self.ingredient_tree.setObjectName("IngredientManagerTree")
        self.ingredient_tree.setSortingEnabled(False)
        self.columns = (
            "name", "conc", "diluent", "brand", "chem_name", "vendor", "cost", "note_type", "primary_cat",
            "secondary_cat")
        self.ingredient_tree.setColumnCount(len(self.columns))
        self.original_header_labels = [c.replace("_", " ").title() for c in self.columns]
        self.original_header_labels[self.columns.index('cost')] = 'Cost / g'
        self.ingredient_tree.setHeaderLabels(self.original_header_labels)

        self.ingredient_tree.header().setDefaultAlignment(Qt.AlignmentFlag.AlignCenter)
        self.ingredient_tree.itemDoubleClicked.connect(self.edit_selected_item_gui)
        self.ingredient_tree.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.ingredient_tree.customContextMenuRequested.connect(self.show_context_menu)
        self.ingredient_tree.itemSelectionChanged.connect(self.on_treeview_selection_change)
        self.ingredient_tree.itemSelectionChanged.connect(self._on_selection_changed)
        self.ingredient_tree.itemExpanded.connect(self._update_accord_indicator)
        self.ingredient_tree.itemCollapsed.connect(self._update_accord_indicator)
        self.ingredient_tree.header().customSectionClicked.connect(
            lambda index: self._handle_sort_request(self.ingredient_tree, index)
        )
        self.layout.addWidget(ing_container)

        header_widget = self.ingredient_tree.header()
        header_widget.setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        header_widget.setStretchLastSection(False)
        header_widget.sectionResized.connect(self.save_column_widths)
        header_widget.sectionMoved.connect(self.save_column_widths)

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
        QTimer.singleShot(0, self._initial_fade_update)
        QTimer.singleShot(0, self._adjust_fade_positions)

    def _initial_fade_update(self):
        """Force an update of the fades after the UI is shown."""
        from ..components import update_fades
        update_fades(self.ingredient_tree, self.top_fade, self.bottom_fade)

    def _adjust_fade_positions(self):
        """Sets a top margin on the fade overlays to position them below the headers."""
        header_height = self.ingredient_tree.header().height()
        overlay_widget = self.top_fade.parentWidget()
        if overlay_widget:
            overlay_widget.layout().setContentsMargins(0, header_height, 0, 0)

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

    def _update_header_labels(self):
        """
        Updates header labels to show a unicode sort indicator instead of using
        Qt's buggy native indicator, which causes alignment issues.
        """
        sort_column, sort_order = self.sort_state
        new_labels = self.original_header_labels[:]

        if sort_column is not None:
            label_text = new_labels[sort_column]
            if sort_order == Qt.SortOrder.AscendingOrder:
                new_labels[sort_column] = f" {label_text} ▲"
            else:
                new_labels[sort_column] = f" {label_text} ▼"

        self.ingredient_tree.setHeaderLabels(new_labels)

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
        Populates the tree with ingredients and accords using the centralized helper.
        """
        self._update_header_labels()

        expanded_item_names = set()
        for i in range(self.ingredient_tree.topLevelItemCount()):
            item = self.ingredient_tree.topLevelItem(i)
            if item and item.isExpanded():
                item_data = item.data(0, Qt.ItemDataRole.UserRole)
                if item_data and 'name' in item_data:
                    expanded_item_names.add(item_data['name'])

        self.ingredient_tree.clear()
        search_term = self.search_entry.text().lower()

        all_ingredients = self.data_manager.get_all_ingredients()

        materials_to_show = all_ingredients
        if search_term:
            materials_to_show = [
                item for item in all_ingredients if
                search_term in item.get('name', '').lower() or
                (item.get('type') in ['formulation_accord', 'premade_accord'] and any(
                    search_term in entry.get('ingredient_name', '').lower() for entry in
                    (self.data_manager.get_formulation_by_name(item.get('name', '')) or {}).get('entries', [])))
            ]

        sort_column, sort_order = self.sort_state
        if sort_column is not None:
            is_reverse = sort_order == Qt.SortOrder.DescendingOrder
            sort_key_map = {
                0: 'name', 1: 'concentration', 2: 'diluent', 3: 'brand', 4: 'chemical_name',
                5: 'vendor', 6: 'cost', 7: 'note_type', 8: 'primary_category', 9: 'secondary_category'
            }
            sort_key = sort_key_map.get(sort_column, 'name')

            def sort_func(x):
                val = x.get(sort_key)
                if sort_key in ["concentration", "cost"]:
                    return float(str(val or '0').strip('%$ '))
                return str(val or '').lower()

            materials_to_show.sort(key=sort_func, reverse=is_reverse)

        alignments = {
            1: Qt.AlignmentFlag.AlignCenter, 2: Qt.AlignmentFlag.AlignCenter,
            3: Qt.AlignmentFlag.AlignCenter, 4: Qt.AlignmentFlag.AlignCenter,
            5: Qt.AlignmentFlag.AlignCenter, 6: Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter,
            7: Qt.AlignmentFlag.AlignCenter, 8: Qt.AlignmentFlag.AlignCenter, 9: Qt.AlignmentFlag.AlignCenter,
        }

        self.ingredient_tree.itemSelectionChanged.disconnect()
        for item_data in materials_to_show:
            parent_item = QTreeWidgetItem()
            parent_item.setData(0, Qt.ItemDataRole.UserRole,
                                {'name': item_data['name'], 'type': item_data.get('type', 'raw')})

            if item_data.get('type', 'raw') not in ['formulation_accord', 'premade_accord']:
                parent_item.setText(0, item_data['name'])

            parent_item.setText(1, f"{item_data.get('concentration', 100.0):.2f}%")
            parent_item.setText(2, format_for_display(item_data.get('diluent', '')))
            parent_item.setText(3, format_for_display(item_data.get('brand', '')))
            parent_item.setText(4, format_for_display(item_data.get('chemical_name', '')))
            parent_item.setText(5, format_for_display(item_data.get('vendor', '')))
            parent_item.setText(6, f"${item_data.get('cost', 0.0):.2f}")
            parent_item.setText(7, format_for_display(item_data.get('note_type', 'Other')))
            parent_item.setText(8, format_for_display(item_data.get('primary_category', 'Uncategorized')))
            parent_item.setText(9, format_for_display(item_data.get('secondary_category', '')))

            self.ingredient_tree.addTopLevelItem(parent_item)

            if item_data['name'] in expanded_item_names:
                parent_item.setExpanded(True)

            configure_accord_item_display(
                parent_item=parent_item,
                item_data=item_data,
                data_manager=self.data_manager,
                tree_widget=self.ingredient_tree,
                child_percentage_column=1,
                child_name_prefix="    - "
            )

            for i, align in alignments.items():
                if i < parent_item.columnCount():
                    parent_item.setTextAlignment(i, align)

        self.ingredient_tree.itemSelectionChanged.connect(self.on_treeview_selection_change)
        self.ingredient_tree.itemSelectionChanged.connect(self._on_selection_changed)

        self.on_treeview_selection_change()
        self._on_selection_changed()

        from ..components import update_fades
        QTimer.singleShot(0, lambda: update_fades(self.ingredient_tree, self.top_fade, self.bottom_fade))

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
        self.edit_ingredient_signal.emit({})

    def edit_selected_item_gui(self):
        if not self.selected_item_name: return

        if self.selected_item_type == 'formulation_accord':
            accord_data = self.data_manager.get_formulation_by_name(self.selected_item_name)
            if accord_data:
                self.edit_accord_signal.emit(accord_data)
        else:  # Handles 'raw' and 'premade_accord'
            ingredient_data = self.data_manager.get_ingredient_by_name(self.selected_item_name)
            if ingredient_data:
                self.edit_ingredient_signal.emit(ingredient_data)

    def delete_item_gui(self):
        if not self.selected_item_name: return

        item_type_str = "accord" if self.selected_item_type in ['formulation_accord',
                                                                'premade_accord'] else "ingredient"
        reply = CustomMessageBox.question(self, f"Confirm Delete",
                                          f"Are you sure you want to delete the {item_type_str} '{self.selected_item_name}'?")
        if reply == QDialogButtonBox.StandardButton.Yes:
            name_to_delete = self.selected_item_name
            if self.selected_item_type == 'formulation_accord':
                self.data_manager.delete_formulation(name_to_delete)  # This also deletes the ingredient part
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
            QMessageBox.information(self, "Export Successful", f"Ingredient library exported to:\n{path}")
        else:
            QMessageBox.critical(self, "Export Error", f"Could not export library:\n{error_msg}")

    def _export_library_as_pdf(self):
        default_name = f"formul8_ingredients_{datetime.now().strftime('%Y%m%d')}.pdf"
        path, _ = QFileDialog.getSaveFileName(self, "Export Library as PDF", default_name, "PDF Files (*.pdf)")
        if not path:
            return

        success, error_msg = self.data_manager.export_ingredients_to_pdf(path)
        if success:
            QMessageBox.information(self, "Export Successful", f"Ingredient library exported to:\n{path}")
        else:
            QMessageBox.critical(self, "Export Error", f"Could not export library:\n{error_msg}")