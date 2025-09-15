# formul8/views/ingredient_editor.py
# The form for adding a new ingredient or editing an existing one.

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QPushButton, QLabel, QLineEdit, QComboBox, QTextEdit, QDoubleSpinBox, QInputDialog,
    QGroupBox, QRadioButton, QButtonGroup
)
from PyQt6.QtCore import Qt, pyqtSignal, QTimer

# --- Local Imports ---
from ..constants import NOTE_TYPES
from ..components import ClickableLabel, CustomMessageBox


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
        form_layout.setColumnStretch(1, 1)

        self.type_label = QLabel("Ingredient Type:")

        self.type_widget = QWidget()
        type_layout = QHBoxLayout(self.type_widget)
        type_layout.setContentsMargins(0, 0, 0, 0)
        self.raw_radio = QRadioButton("Raw Material")
        self.premade_accord_radio = QRadioButton("Pre-made Accord")
        self.raw_radio.setChecked(True)

        self.type_button_group = QButtonGroup(self)
        self.type_button_group.addButton(self.raw_radio)
        self.type_button_group.addButton(self.premade_accord_radio)

        type_layout.addWidget(self.raw_radio)
        type_layout.addWidget(self.premade_accord_radio)
        type_layout.addStretch()

        form_layout.addWidget(self.type_label, 0, 0)
        form_layout.addWidget(self.type_widget, 0, 1)

        self.type_button_group.buttonClicked.connect(self._on_type_changed)

        # --- Form Widgets ---
        self.ing_name_entry = QLineEdit()
        self.ing_conc_spinbox = QDoubleSpinBox(maximum=100.0, minimum=0.0, decimals=2, value=100.0)
        self.ing_conc_spinbox.valueChanged.connect(self._on_concentration_change)

        # --- MODIFIED: Removed .setEditable(True) from these QComboBox widgets ---
        self.ing_diluent_combobox = QComboBox()
        self.ing_primary_category_combobox = QComboBox()
        self.ing_secondary_category_combobox = QComboBox()

        # --- UNCHANGED QComboBox widgets ---
        self.ing_brand_combobox = QComboBox()
        self.ing_vendor_combobox = QComboBox()
        self.ing_note_type_combobox = QComboBox()
        self.ing_note_type_combobox.addItems(NOTE_TYPES)

        self.ing_chem_entry = QLineEdit()
        self.ing_cost_spinbox = QDoubleSpinBox(maximum=10000.0, minimum=0.0, decimals=2)
        self.ing_notes_text = QTextEdit()

        # --- Form Layout Assembly (row numbers start from 1) ---
        form_layout.addWidget(QLabel("Name:"), 1, 0)
        form_layout.addWidget(self.ing_name_entry, 1, 1)

        self.concentration_label = QLabel("Concentration (%):")
        form_layout.addWidget(self.concentration_label, 2, 0)
        form_layout.addWidget(self.ing_conc_spinbox, 2, 1)

        self.diluent_label_widget = self._create_addable_label(
            "Diluted In:", self.ing_diluent_combobox, "diluents", dialog_title="Solvent"
        )
        form_layout.addWidget(self.diluent_label_widget, 3, 0)
        form_layout.addWidget(self.ing_diluent_combobox, 3, 1)

        brand_label_widget = self._create_addable_label("Brand:", self.ing_brand_combobox, "brands")
        form_layout.addWidget(brand_label_widget, 4, 0)
        form_layout.addWidget(self.ing_brand_combobox, 4, 1)

        self.chemical_name_label = QLabel("Chemical Name:")
        form_layout.addWidget(self.chemical_name_label, 5, 0)
        form_layout.addWidget(self.ing_chem_entry, 5, 1)

        vendor_label_widget = self._create_addable_label("Vendor/Supplier:", self.ing_vendor_combobox, "suppliers")
        form_layout.addWidget(vendor_label_widget, 6, 0)
        form_layout.addWidget(self.ing_vendor_combobox, 6, 1)

        form_layout.addWidget(QLabel("Cost per gram ($):"), 7, 0)
        form_layout.addWidget(self.ing_cost_spinbox, 7, 1)
        form_layout.addWidget(QLabel("Note Type:"), 8, 0)
        form_layout.addWidget(self.ing_note_type_combobox, 8, 1)

        form_layout.addWidget(QLabel("Primary Category:"), 9, 0)
        form_layout.addWidget(self.ing_primary_category_combobox, 9, 1)

        form_layout.addWidget(QLabel("Secondary Category:"), 10, 0)
        form_layout.addWidget(self.ing_secondary_category_combobox, 10, 1)

        form_layout.addWidget(QLabel("Notes:"), 11, 0, alignment=Qt.AlignmentFlag.AlignTop)
        form_layout.addWidget(self.ing_notes_text, 11, 1)

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

    def _create_addable_label(self, label_text, combo_box, list_key, dialog_title=None):
        """Creates a widget containing a label and a clickable '+' button."""
        widget = QWidget()
        layout = QHBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.setAlignment(Qt.AlignmentFlag.AlignLeft)

        label = QLabel(label_text)
        add_button = ClickableLabel("+")

        title_for_dialog = dialog_title if dialog_title else label_text.strip(':')
        add_button.clicked.connect(lambda: self._handle_add_new_list_item(list_key, combo_box, title_for_dialog))

        layout.addWidget(label)
        layout.addWidget(add_button, 0, Qt.AlignmentFlag.AlignTop)

        layout.addStretch()

        return widget

    def _handle_add_new_list_item(self, list_key, combo_box, title):
        """Handles the logic for the '+' button click."""
        text, ok = QInputDialog.getText(self, f"Add New {title}", f"Enter new {title.lower()}:")
        if ok and text:
            was_added = self.data_manager.add_list_item(list_key, text)
            if was_added:
                self._refresh_comboboxes()
                combo_box.setCurrentText(text)
                self.show_status_message(f"Added '{text}' to {title} list.")
            else:
                CustomMessageBox.warning(self, "Duplicate Item", f"'{text}' already exists in the {title} list.")

    def _refresh_comboboxes(self):
        """Reloads all combobox items from the data manager."""
        current_values = {
            "diluents": self.ing_diluent_combobox.currentText(),
            "brands": self.ing_brand_combobox.currentText(),
            "suppliers": self.ing_vendor_combobox.currentText(),
            "scent_categories": [
                self.ing_primary_category_combobox.currentText(),
                self.ing_secondary_category_combobox.currentText()
            ]
        }

        for combo, key in [
            (self.ing_diluent_combobox, 'diluents'),
            (self.ing_brand_combobox, 'brands'),
            (self.ing_vendor_combobox, 'suppliers'),
            (self.ing_primary_category_combobox, 'scent_categories'),
            (self.ing_secondary_category_combobox, 'scent_categories')
        ]:
            combo.clear()
            items = sorted(self.data_manager.get_setting(key) or [])
            if combo is self.ing_secondary_category_combobox:
                combo.addItems([""] + items)
            else:
                combo.addItems(items)

        self.ing_diluent_combobox.setCurrentText(current_values["diluents"])
        self.ing_brand_combobox.setCurrentText(current_values["brands"])
        self.ing_vendor_combobox.setCurrentText(current_values["suppliers"])
        self.ing_primary_category_combobox.setCurrentText(current_values["scent_categories"][0])
        self.ing_secondary_category_combobox.setCurrentText(current_values["scent_categories"][1])

    def on_show(self):
        """ This method is called by the main window when this frame becomes visible. """
        pass

    def show_status_message(self, text, is_error=False):
        self.status_label.setText(text)
        self.status_label.setProperty("error", is_error)
        self.status_label.style().polish(self.status_label)
        self.status_timer.start(3000)

    def _on_concentration_change(self, value):
        is_diluted = value < 100.0
        # Only show the diluent fields if it's a raw material
        show_diluent = is_diluted and self.raw_radio.isChecked()
        self.diluent_label_widget.setVisible(show_diluent)
        self.ing_diluent_combobox.setVisible(show_diluent)

    def _on_type_changed(self, button):
        # The button group signal sends the button that was clicked.
        is_raw = (button is self.raw_radio)
        self.concentration_label.setVisible(is_raw)
        self.ing_conc_spinbox.setVisible(is_raw)
        self.chemical_name_label.setVisible(is_raw)
        self.ing_chem_entry.setVisible(is_raw)
        # Trigger the concentration change logic to show/hide diluent fields
        self._on_concentration_change(self.ing_conc_spinbox.value())

    def setup_ingredient_for_editing(self, ingredient_data):
        self.clear_fields()
        self.editing_ingredient_obj_ref = ingredient_data if ingredient_data else None

        self.type_button_group.blockSignals(True)

        self._refresh_comboboxes()

        if ingredient_data and ingredient_data.get(
                'name'):  # Check for name to ensure it's not an empty dict for "add new"
            ingredient_type = ingredient_data.get('type', 'raw')
            if ingredient_type == 'premade_accord':
                self.premade_accord_radio.setChecked(True)
            else:
                self.raw_radio.setChecked(True)

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
            self.raw_radio.setChecked(True)
            self.show_status_message("Creating new ingredient.")
            self.save_add_button.show()
            self.save_close_button.setText("Save and Close")

        self.type_button_group.blockSignals(False)
        self._on_type_changed(self.type_button_group.checkedButton())

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

        original_name = self.editing_ingredient_obj_ref.get('name') if self.editing_ingredient_obj_ref else None
        if name.lower() != (original_name.lower() if original_name else None):
            if self.data_manager.get_ingredient_by_name(name):
                self.show_status_message(f"Error: An ingredient named '{name}' already exists.", is_error=True)
                return None

        is_premade_accord = self.premade_accord_radio.isChecked()

        ingredient_data = {
            "name": name,
            "type": 'premade_accord' if is_premade_accord else 'raw',
            "concentration": 100.0 if is_premade_accord else self.ing_conc_spinbox.value(),
            "diluent": "" if is_premade_accord else (
                self.ing_diluent_combobox.currentText().strip() if self.ing_conc_spinbox.value() < 100 else ""),
            "brand": self.ing_brand_combobox.currentText().strip(),
            "chemical_name": "" if is_premade_accord else self.ing_chem_entry.text().strip(),
            "vendor": self.ing_vendor_combobox.currentText().strip(),
            "cost": self.ing_cost_spinbox.value(),
            "note_type": self.ing_note_type_combobox.currentText(),
            "primary_category": self.ing_primary_category_combobox.currentText(),
            "secondary_category": self.ing_secondary_category_combobox.currentText(),
            "notes": self.ing_notes_text.toPlainText().strip()
        }

        if self.editing_ingredient_obj_ref:
            ingredient_data['original_name'] = self.editing_ingredient_obj_ref['name']

        if self.data_manager.save_ingredient(ingredient_data):
            return name
        else:
            self.show_status_message("Error: Could not save ingredient to database.", is_error=True)
            return None

    def save_and_add_another(self):
        saved_name = self._save_logic()
        if saved_name:
            self.show_status_message(f"'{saved_name}' saved. Ready for next.")
            self.setup_ingredient_for_editing(None)  # Reset for new ingredient

    def save_and_close(self):
        if self._save_logic():
            self.back_to_list_signal.emit()