# formul8/views/ingredient_editor.py
# The form for adding a new ingredient or editing an existing one.

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QPushButton, QLabel, QLineEdit, QComboBox, QTextEdit, QDoubleSpinBox
)
from PyQt6.QtCore import Qt, pyqtSignal, QTimer

# --- Local Imports ---
from ..constants import NOTE_TYPES


class EditIngredientFrame(QWidget):
    """
    A form widget for creating a new ingredient or editing an existing one.
    It emits a signal when the user is done, so the main window can switch back.
    """
    back_to_list_signal = pyqtSignal()

    def __init__(self, data_manager, parent=None):
        super().__init__(parent)
        self.data_manager = data_manager

        self.editing_ingredient_obj_ref = None

        self.layout = QVBoxLayout(self)
        self.header_label = QLabel("Add/Edit Ingredient")
        self.header_label.setObjectName("HeaderLabel")
        self.header_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.layout.addWidget(self.header_label)

        form_layout = QGridLayout()
        self.ing_name_entry = QLineEdit()
        self.ing_conc_spinbox = QDoubleSpinBox(maximum=100.0, minimum=0.0, decimals=2, value=100.0)
        self.ing_conc_spinbox.valueChanged.connect(self._on_concentration_change)
        self.ing_diluent_combobox = QComboBox()
        self.ing_diluent_combobox.setEditable(True)

        self.ing_brand_combobox = QComboBox()
        # REMOVED: self.ing_brand_combobox.setEditable(True)
        self.ing_chem_entry = QLineEdit()
        self.ing_vendor_combobox = QComboBox()
        # REMOVED: self.ing_vendor_combobox.setEditable(True)
        self.ing_cost_spinbox = QDoubleSpinBox(maximum=10000.0, minimum=0.0, decimals=2)
        self.ing_note_type_combobox = QComboBox()
        self.ing_note_type_combobox.addItems(NOTE_TYPES)
        self.ing_primary_category_combobox = QComboBox()
        self.ing_primary_category_combobox.setEditable(True)
        self.ing_secondary_category_combobox = QComboBox()
        self.ing_secondary_category_combobox.setEditable(True)

        self.ing_notes_text = QTextEdit()

        # --- Form Layout ---
        form_layout.addWidget(QLabel("Name:"), 0, 0)
        form_layout.addWidget(self.ing_name_entry, 0, 1)
        form_layout.addWidget(QLabel("Concentration (%):"), 1, 0)
        form_layout.addWidget(self.ing_conc_spinbox, 1, 1)
        self.diluent_label = QLabel("Diluted In:")
        form_layout.addWidget(self.diluent_label, 2, 0)
        form_layout.addWidget(self.ing_diluent_combobox, 2, 1)
        form_layout.addWidget(QLabel("Brand:"), 3, 0)
        form_layout.addWidget(self.ing_brand_combobox, 3, 1)
        form_layout.addWidget(QLabel("Chemical Name:"), 4, 0)
        form_layout.addWidget(self.ing_chem_entry, 4, 1)
        form_layout.addWidget(QLabel("Vendor/Supplier:"), 5, 0)
        form_layout.addWidget(self.ing_vendor_combobox, 5, 1)
        form_layout.addWidget(QLabel("Cost per gram ($):"), 6, 0)
        form_layout.addWidget(self.ing_cost_spinbox, 6, 1)
        form_layout.addWidget(QLabel("Note Type:"), 7, 0)
        form_layout.addWidget(self.ing_note_type_combobox, 7, 1)
        form_layout.addWidget(QLabel("Primary Category:"), 8, 0)
        form_layout.addWidget(self.ing_primary_category_combobox, 8, 1)
        form_layout.addWidget(QLabel("Secondary Category:"), 9, 0)
        form_layout.addWidget(self.ing_secondary_category_combobox, 9, 1)
        form_layout.addWidget(QLabel("Notes:"), 10, 0)
        form_layout.addWidget(self.ing_notes_text, 10, 1)
        self.layout.addLayout(form_layout)

        self.status_label = QLabel("")
        self.status_label.setObjectName("StatusLabel")
        self.layout.addWidget(self.status_label, alignment=Qt.AlignmentFlag.AlignCenter)

        # --- Button Layout ---
        button_layout = QHBoxLayout()
        self.save_add_button = QPushButton("Save and Add Another")
        self.save_add_button.clicked.connect(self.save_and_add_another)
        self.save_close_button = QPushButton("Save and Close")
        self.save_close_button.clicked.connect(self.save_and_close)
        self.close_button = QPushButton("Cancel")
        self.close_button.clicked.connect(self.back_to_list_signal.emit)
        button_layout.addStretch()
        button_layout.addWidget(self.save_add_button)
        button_layout.addWidget(self.save_close_button)
        button_layout.addWidget(self.close_button)
        button_layout.addStretch()
        self.layout.addLayout(button_layout)

        self.status_timer = QTimer(self)
        self.status_timer.setSingleShot(True)
        self.status_timer.timeout.connect(self.status_label.clear)

    def on_show(self):
        """ This method can be used if any logic needs to run when the frame is shown. """
        pass

    def show_status_message(self, text, is_error=False):
        self.status_label.setText(text)
        self.status_label.setProperty("error", is_error)
        self.status_label.style().polish(self.status_label)
        self.status_timer.start(3000)

    def _on_concentration_change(self, value):
        is_diluted = value < 100.0
        self.diluent_label.setVisible(is_diluted)
        self.ing_diluent_combobox.setVisible(is_diluted)

    def setup_ingredient_for_editing(self, ingredient_data):
        self.clear_fields()
        self.editing_ingredient_obj_ref = ingredient_data if ingredient_data else None

        settings = self.data_manager.data['settings']

        # Populate dropdowns
        for combo, key in [
            (self.ing_primary_category_combobox, 'scent_categories'),
            (self.ing_secondary_category_combobox, 'scent_categories'),
            (self.ing_vendor_combobox, 'suppliers'),
            (self.ing_brand_combobox, 'brands'),
            (self.ing_diluent_combobox, 'diluents')
        ]:
            combo.clear()
            items = sorted(settings.get(key, []))
            if combo is self.ing_secondary_category_combobox:
                combo.addItems([""] + items)
            else:
                combo.addItems(items)

        if ingredient_data:
            self.header_label.setText("Edit Ingredient")
            self.ing_name_entry.setText(ingredient_data.get('name', ''))
            self.ing_conc_spinbox.setValue(ingredient_data.get('concentration', 100.0))
            self.ing_brand_combobox.setCurrentText(ingredient_data.get('brand', ''))
            self.ing_chem_entry.setText(ingredient_data.get('chemical_name', ''))
            self.ing_vendor_combobox.setCurrentText(ingredient_data.get('vendor', ''))
            self.ing_cost_spinbox.setValue(ingredient_data.get('cost', 0.0))
            self.ing_diluent_combobox.setCurrentText(ingredient_data.get('diluent', ''))
            self.ing_note_type_combobox.setCurrentText(ingredient_data.get('note_type', 'Other'))
            self.ing_primary_category_combobox.setCurrentText(ingredient_data.get('primary_category', 'Uncategorized'))
            self.ing_secondary_category_combobox.setCurrentText(ingredient_data.get('secondary_category', ''))
            self.ing_notes_text.setPlainText(ingredient_data.get('notes', ''))
            self.show_status_message(f"Editing '{ingredient_data.get('name', '')}'.")
            self.save_add_button.hide()
            self.save_close_button.setText("Update and Close")
        else:
            self.header_label.setText("Add New Ingredient")
            self.show_status_message("Creating new ingredient.")
            self.save_add_button.show()
            self.save_close_button.setText("Save and Close")

        self._on_concentration_change(self.ing_conc_spinbox.value())

    def clear_fields(self):
        for w in [self.ing_name_entry, self.ing_chem_entry, self.ing_notes_text]: w.clear()
        for c in [self.ing_brand_combobox, self.ing_vendor_combobox, self.ing_diluent_combobox,
                  self.ing_secondary_category_combobox]: c.setCurrentIndex(-1)
        self.ing_conc_spinbox.setValue(100.0)
        self.ing_cost_spinbox.setValue(0.0)
        self.ing_note_type_combobox.setCurrentText("Other")
        self.ing_primary_category_combobox.setCurrentText("Uncategorized")
        self.ing_name_entry.setFocus()

    def _save_logic(self):
        name = self.ing_name_entry.text().strip()
        if not name:
            self.show_status_message("Error: Ingredient name cannot be empty.", is_error=True)
            return None

        is_editing = bool(self.editing_ingredient_obj_ref)
        for ing in self.data_manager.data['ingredients']:
            if ing['name'].lower() == name.lower() and (not is_editing or ing is not self.editing_ingredient_obj_ref):
                self.show_status_message(f"Error: An ingredient named '{name}' already exists.", is_error=True)
                return None

        ingredient_data = {
            "name": name,
            "concentration": self.ing_conc_spinbox.value(),
            "diluent": self.ing_diluent_combobox.currentText().strip() if self.ing_conc_spinbox.value() < 100 else "",
            "brand": self.ing_brand_combobox.currentText().strip(),
            "chemical_name": self.ing_chem_entry.text().strip(),
            "vendor": self.ing_vendor_combobox.currentText().strip(),
            "cost": self.ing_cost_spinbox.value(),
            "note_type": self.ing_note_type_combobox.currentText(),
            "primary_category": self.ing_primary_category_combobox.currentText(),
            "secondary_category": self.ing_secondary_category_combobox.currentText(),
            "notes": self.ing_notes_text.toPlainText().strip()
        }

        if is_editing:
            self.editing_ingredient_obj_ref.update(ingredient_data)
        else:
            self.data_manager.data['ingredients'].append(ingredient_data)

        self.data_manager.save_data()
        return name

    def save_and_add_another(self):
        saved_name = self._save_logic()
        if saved_name:
            self.show_status_message(f"'{saved_name}' saved. Ready for next.")
            self.clear_fields()

    def save_and_close(self):
        if self._save_logic():
            self.back_to_list_signal.emit()