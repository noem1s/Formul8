# formul8/views/formulation_creator.py
# The core frame for creating and editing formulations with live analysis views.

import math

# --- PyQt6 Imports ---
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QPushButton, QLabel, QLineEdit,
    QGroupBox, QFrame, QColorDialog, QDoubleSpinBox, QTreeWidgetItem, QMenu
)
from PyQt6.QtGui import QPainter, QColor, QBrush, QPolygonF, QPaintEvent, QPalette
from PyQt6.QtCore import Qt, QPointF, QRectF, pyqtSignal, QTimer, QSettings

# --- Third-party Libraries ---
import matplotlib.pyplot as plt
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas

# --- Local Imports ---
# REMOVED: from ..data_manager import data_manager
from ..ui_components import CustomDialog, CustomMessageBox, DragAndDropTree
from ..constants import NOTE_TYPES


class PyramidWidget(QWidget):
    """Draws the scent note pyramid."""

    def __init__(self, data_manager, parent=None):
        super().__init__(parent)
        self.data_manager = data_manager
        self.setMinimumSize(400, 400)
        self.pyramid_colors = {"Top": QColor("#e5c07b"), "TopMid": QColor("#be9f91"), "Middle": QColor("#9881a7"),
                               "MidBase": QColor("#7d98cd"), "Base": QColor("#61afef"), "Other": QColor("#5c6370")}
        self.percentages = {}

    def update_data(self, formulation_data):
        totals = {note_type: 0 for note_type in NOTE_TYPES}
        concentrate_entries = [e for e in formulation_data.get('entries', []) if
                               (ing := self.data_manager.get_ingredient_by_name(e.get('ingredient_name'))) and ing.get(
                                   'note_type') != 'Solvent']
        total_quantity = sum(entry.get('quantity', 0.0) for entry in concentrate_entries)

        if total_quantity > 0:
            for entry in concentrate_entries:
                ing_data = self.data_manager.get_ingredient_by_name(entry.get('ingredient_name'))
                if ing_data:
                    totals[ing_data.get('note_type', 'Other')] += entry.get('quantity', 0.0)
            self.percentages = {key: (value / total_quantity) * 100 for key, value in totals.items()}
        else:
            self.percentages = {}
        self.update()

    def paintEvent(self, event: QPaintEvent):
        if not self.percentages: return
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.fillRect(self.rect(), self.palette().color(QPalette.ColorRole.Window))

        width, height = self.width() - 40, self.height() - 80
        x_center, y_offset = self.width() / 2, 20
        y_current = y_offset
        note_tiers = ["Top", "TopMid", "Middle", "MidBase", "Base"]
        display_names = {"Top": "Top", "TopMid": "Top-Mid", "Middle": "Mid", "MidBase": "Mid-Base", "Base": "Base"}

        for note_type in note_tiers:
            percentage = self.percentages.get(note_type, 0)
            if percentage > 0:
                y_start = y_current
                y_end = y_start + (height * (percentage / 100))

                def get_x_at_y(y): return (width / 2) * ((y - y_offset) / height) if height > 0 else 0

                poly = QPolygonF(
                    [QPointF(x_center - get_x_at_y(y_start), y_start), QPointF(x_center + get_x_at_y(y_start), y_start),
                     QPointF(x_center + get_x_at_y(y_end), y_end), QPointF(x_center - get_x_at_y(y_end), y_end)])
                painter.setBrush(self.pyramid_colors.get(note_type, QColor("gray")))
                painter.setPen(Qt.PenStyle.NoPen)
                painter.drawPolygon(poly)
                painter.setPen(Qt.GlobalColor.white)
                painter.drawText(QRectF(x_center - 100, y_start, 200, y_end - y_start), Qt.AlignmentFlag.AlignCenter,
                                 f"{display_names.get(note_type, note_type)}\n{percentage:.1f}%")
                y_current = y_end


class PyramidWindow(CustomDialog):
    def __init__(self, data_manager, parent=None):
        super().__init__(parent)
        self.data_manager = data_manager
        self.setWindowTitle("Formula Pyramid (Live)")
        self.setMinimumSize(450, 500)
        self.main_layout = QVBoxLayout()
        self.setLayout(self.main_layout)
        self.pyramid_widget = PyramidWidget(data_manager=self.data_manager)
        self.other_label = QLabel()
        self.other_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.main_layout.addWidget(self.pyramid_widget)
        self.main_layout.addWidget(self.other_label)

    def update_data(self, formulation_data):
        self.pyramid_widget.update_data(formulation_data)
        other_percentage = self.pyramid_widget.percentages.get('Other', 0) + self.pyramid_widget.percentages.get(
            'Modifier', 0)
        self.other_label.setText(f"Modifiers/Other: {other_percentage:.1f}%" if other_percentage > 0 else "")
        self.other_label.setVisible(other_percentage > 0)


class ScentProfileWindow(CustomDialog):
    def __init__(self, data_manager, parent=None):
        super().__init__(parent)
        self.data_manager = data_manager
        self.setWindowTitle("Scent Profile Analysis (Live)")
        self.setMinimumSize(800, 550)
        self.main_layout = QVBoxLayout()
        self.setLayout(self.main_layout)
        self.canvas = None

    def update_data(self, formulation_data):
        if self.canvas:
            self.main_layout.removeWidget(self.canvas)
            self.canvas.deleteLater()

        totals = {}
        concentrate_entries = [e for e in formulation_data.get('entries', []) if
                               (ing := self.data_manager.get_ingredient_by_name(e.get('ingredient_name'))) and ing.get(
                                   'note_type') != 'Solvent']
        total_quantity = sum(entry.get('quantity', 0.0) for entry in concentrate_entries)

        if total_quantity == 0:
            self.canvas = QLabel("Formula has no aromatic ingredients.")
            self.main_layout.addWidget(self.canvas)
            return

        for entry in concentrate_entries:
            ing_data = self.data_manager.get_ingredient_by_name(entry.get('ingredient_name'))
            if ing_data:
                category = ing_data.get('primary_category', 'Uncategorized')
                totals[category] = totals.get(category, 0) + entry.get('quantity', 0.0)

        color_map = self.data_manager.data['settings'].get('scent_profile_colors', {})
        labels = list(totals.keys())
        colors = [color_map.get(label, "#808080") for label in labels]

        fig, ax = plt.subplots(figsize=(6, 5), subplot_kw=dict(aspect="equal"))
        fig.patch.set_facecolor(self.palette().color(QPalette.ColorRole.Window).name())
        wedges, _, autotexts = ax.pie(totals.values(), wedgeprops=dict(width=0.5), autopct='%1.1f%%', startangle=90,
                                      textprops=dict(color="w"), colors=colors)
        ax.legend(wedges, labels, title="Categories", loc="center left", bbox_to_anchor=(1, 0, 0.5, 1),
                  labelcolor='white', facecolor='#343a40', edgecolor='#5c6370')
        plt.setp(autotexts, size=8, weight="bold")
        ax.set_title("Primary Scent Profile of Concentrate", color='white')

        self.canvas = FigureCanvas(fig)
        self.main_layout.addWidget(self.canvas)


class CreateFormulationFrame(QWidget):
    formulation_updated = pyqtSignal(dict)

    def __init__(self, data_manager, parent=None):
        super().__init__(parent)
        self.data_manager = data_manager
        self.editing_formulation_obj_ref = None
        self.formulation_entries = []
        self.pyramid_window = None
        self.scent_profile_window = None

        main_layout = QVBoxLayout(self)

        details_group = QGroupBox("Formulation Details");
        details_layout = QGridLayout(details_group);
        self.formulation_name_entry = QLineEdit();
        details_layout.addWidget(QLabel("Formulation Name:"), 0, 0);
        details_layout.addWidget(self.formulation_name_entry, 0, 1);
        self.status_label = QLabel();
        self.status_label.setObjectName("StatusLabel");
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter);
        details_layout.addWidget(self.status_label, 1, 0, 1, 2);
        main_layout.addWidget(details_group)
        content_layout = QHBoxLayout();
        content_layout.setSpacing(15)
        available_panel = QGroupBox("Available Ingredients (Drag to add)");
        available_layout = QVBoxLayout(available_panel);
        self.available_ing_tree = DragAndDropTree();
        self.available_ing_tree.setHeaderLabels(["Ingredient", "Conc", "Note", "Cat 1", "Cat 2", "Cost / g"]);
        self.available_ing_tree.header().setDefaultAlignment(Qt.AlignmentFlag.AlignCenter);
        self.available_ing_tree.ingredient_dropped_in.connect(self.remove_ingredient_from_formula);
        available_layout.addWidget(self.available_ing_tree);
        content_layout.addWidget(available_panel, 1)
        current_panel = QGroupBox("Current Formulation (Drag out to remove)");
        current_layout = QVBoxLayout(current_panel);
        self.formulation_tree = DragAndDropTree();
        self.formulation_tree.setHeaderLabels(["Ingredient", "Quantity", "Unit", "% in Conc.", "Cost"]);
        self.formulation_tree.header().setDefaultAlignment(Qt.AlignmentFlag.AlignCenter);
        self.formulation_tree.ingredient_dropped_in.connect(self.add_ingredient_to_formula);
        self.formulation_tree.itemDoubleClicked.connect(self.on_cell_double_click);
        self.formulation_tree.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu);
        self.formulation_tree.customContextMenuRequested.connect(self.show_highlight_menu);
        current_layout.addWidget(self.formulation_tree)
        totals_frame = QFrame();
        totals_frame.setObjectName("CardFrame");
        totals_layout = QHBoxLayout(totals_frame);
        self.conc_grams_label = QLabel("Conc: 0.00g");
        self.solvent_grams_label = QLabel("Solvent: 0.00g");
        self.total_grams_label = QLabel("Total: 0.00g");
        self.conc_strength_label = QLabel("Strength: 0.00%");
        self.total_cost_label = QLabel("Cost: $0.00");
        totals_layout.addWidget(self.conc_grams_label);
        totals_layout.addStretch();
        totals_layout.addWidget(self.solvent_grams_label);
        totals_layout.addStretch();
        totals_layout.addWidget(self.total_grams_label);
        totals_layout.addStretch();
        totals_layout.addWidget(self.conc_strength_label);
        totals_layout.addStretch();
        totals_layout.addWidget(self.total_cost_label);
        current_layout.addWidget(totals_frame);
        content_layout.addWidget(current_panel, 1);
        main_layout.addLayout(content_layout)

        # --- Bottom Buttons ---
        self.save_button = QPushButton("Save Formulation")
        self.save_button.clicked.connect(self.save_formulation)
        clear_button = QPushButton("Clear All")
        clear_button.clicked.connect(self.reset_formulation_creation)
        pyramid_button = QPushButton("Pyramid")
        pyramid_button.clicked.connect(self.show_pyramid_view)
        profile_button = QPushButton("Scent Profile")
        profile_button.clicked.connect(self.show_scent_profile_view)

        # Create layouts for two button groups to align with the panels above
        left_buttons_layout = QHBoxLayout()
        left_buttons_layout.setSpacing(15)
        left_buttons_layout.setContentsMargins(0, 0, 0, 0)
        left_buttons_layout.addStretch()  # Pushes buttons to the right
        left_buttons_layout.addWidget(self.save_button)
        left_buttons_layout.addWidget(clear_button)

        right_buttons_layout = QHBoxLayout()
        right_buttons_layout.setSpacing(15)
        right_buttons_layout.setContentsMargins(0, 0, 0, 0)
        right_buttons_layout.addWidget(pyramid_button)
        right_buttons_layout.addWidget(profile_button)
        right_buttons_layout.addStretch()  # Pushes buttons to the left

        # Main bottom bar that holds the two button groups
        bottom_bar = QHBoxLayout()
        # This spacing becomes the gap in the middle, matching the panel gap
        bottom_bar.setSpacing(15)
        bottom_bar.addLayout(left_buttons_layout, 1)
        bottom_bar.addLayout(right_buttons_layout, 1)

        main_layout.addLayout(bottom_bar)

        self.status_timer = QTimer(self);
        self.status_timer.setSingleShot(True);
        self.status_timer.timeout.connect(self.status_label.clear)

    def on_show(self):
        self.populate_available_ingredients()
        self.load_column_widths()

    def show_status_message(self, text, is_error=False):
        self.status_label.setText(text)
        self.status_label.setProperty("error", is_error)
        self.status_label.style().polish(self.status_label)
        self.status_timer.start(3000)

    def save_column_widths(self):
        """Saves the column widths for both tree views in this frame."""
        settings = QSettings()
        settings.setValue("creator/availableHeaderState", self.available_ing_tree.header().saveState())
        settings.setValue("creator/formulationHeaderState", self.formulation_tree.header().saveState())

    def load_column_widths(self):
        """Loads and applies column widths for both tree views."""
        settings = QSettings()
        available_state = settings.value("creator/availableHeaderState")
        if available_state:
            self.available_ing_tree.header().restoreState(available_state)

        formulation_state = settings.value("creator/formulationHeaderState")
        if formulation_state:
            self.formulation_tree.header().restoreState(formulation_state)

    def remove_ingredient_from_formula(self, names_to_remove):
        count_before = len(self.formulation_entries)
        self.formulation_entries = [e for e in self.formulation_entries if e['ingredient_name'] not in names_to_remove]
        if len(self.formulation_entries) < count_before:
            self.update_current_formula_display()

    def reset_formulation_creation(self):
        if self.pyramid_window: self.pyramid_window.close()
        if self.scent_profile_window: self.scent_profile_window.close()
        self.editing_formulation_obj_ref = None
        self.formulation_name_entry.clear()
        self.formulation_entries = []
        self.status_label.clear()
        self.save_button.setText("Save Formulation")
        self.populate_available_ingredients()
        self.update_current_formula_display()

    def setup_for_editing(self, formula_data):
        self.reset_formulation_creation()
        self.editing_formulation_obj_ref = formula_data
        self.formulation_name_entry.setText(formula_data.get('name', ''))
        self.formulation_entries = [entry.copy() for entry in formula_data.get('entries', [])]
        self.save_button.setText("Update Formulation")
        self.update_current_formula_display()

    def populate_available_ingredients(self):
        self.available_ing_tree.clear()
        align_left = Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter
        align_center = Qt.AlignmentFlag.AlignCenter
        align_right = Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter

        for ing in sorted(self.data_manager.data['ingredients'], key=lambda x: x.get('name', '')):
            def clean_val(key, default=''):
                val = ing.get(key, default)
                return '' if str(val).strip().lower() in ('n/a', '') else str(val)

            item_data = [
                ing.get('name', ''),
                f"{ing.get('concentration', 0.0):.2f}%",
                ing.get('note_type', 'Other'),
                ing.get('primary_category', 'Uncategorized'),
                clean_val('secondary_category'),
                f"${ing.get('cost', 0.0):.2f}"
            ]
            item = QTreeWidgetItem(item_data)

            alignments = [align_left, align_center, align_center, align_center, align_center, align_right]
            for i, align in enumerate(alignments):
                item.setTextAlignment(i, align)

            self.available_ing_tree.addTopLevelItem(item)

    def add_ingredient_to_formula(self, ingredient_names):
        for name in ingredient_names:
            if not any(entry['ingredient_name'].lower() == name.lower() for entry in self.formulation_entries):
                self.formulation_entries.append(
                    {"ingredient_name": name, "quantity": 0.0, "unit": "gram", "highlight_color": None})
        self.update_current_formula_display()

    def on_cell_double_click(self, item, column):
        if column != 1: return
        try:
            original_value = float(item.text(1))
        except (ValueError, TypeError):
            original_value = 0.0

        spinbox = QDoubleSpinBox()
        spinbox.setDecimals(4);
        spinbox.setRange(0, 99999);
        spinbox.setValue(original_value)
        spinbox.editingFinished.connect(lambda: self.update_quantity_from_spinbox(item, spinbox))
        self.formulation_tree.setItemWidget(item, column, spinbox)
        spinbox.setFocus()

    def update_quantity_from_spinbox(self, item, spinbox):
        for entry in self.formulation_entries:
            if entry['ingredient_name'] == item.text(0):
                entry['quantity'] = spinbox.value()
                break
        self.formulation_tree.setItemWidget(item, 1, None)
        self.update_current_formula_display()

    def show_highlight_menu(self, position):
        menu = QMenu(self)
        set_color = menu.addAction("Set Highlight Color")
        clear_color = menu.addAction("Clear Highlight")
        action = menu.exec(self.formulation_tree.mapToGlobal(position))
        if action == set_color:
            self.set_highlight_color()
        elif action == clear_color:
            self.clear_highlight()

    def set_highlight_color(self):
        color = QColorDialog.getColor()
        if color.isValid():
            for item in self.formulation_tree.selectedItems():
                for entry in self.formulation_entries:
                    if entry['ingredient_name'] == item.text(0):
                        entry['highlight_color'] = color.name()
            self.update_current_formula_display()

    def clear_highlight(self):
        for item in self.formulation_tree.selectedItems():
            for entry in self.formulation_entries:
                if entry['ingredient_name'] == item.text(0):
                    entry['highlight_color'] = None
        self.update_current_formula_display()

    def update_current_formula_display(self):
        self.formulation_tree.clear()
        temp_formulation = {"entries": self.formulation_entries}
        self.data_manager.calculate_formulation_totals(temp_formulation)

        align_left = Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter
        align_center = Qt.AlignmentFlag.AlignCenter
        align_right = Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter

        for entry in sorted(self.formulation_entries, key=lambda x: x['ingredient_name']):
            percent_display = f"{entry.get('percentage', 0.0):.2f}%"
            item_data = [entry['ingredient_name'], f"{entry.get('quantity', 0.0):.4f}", 'g', percent_display,
                         f"${entry.get('cost', 0.0):.2f}"]
            item = QTreeWidgetItem(item_data)

            alignments = [align_left, align_right, align_center, align_right, align_right]
            for i, align in enumerate(alignments):
                item.setTextAlignment(i, align)

            if color_hex := entry.get('highlight_color'):
                for i in range(item.columnCount()):
                    item.setBackground(i, QBrush(QColor(color_hex)))
            self.formulation_tree.addTopLevelItem(item)

        totals = temp_formulation
        self.conc_grams_label.setText(f"Conc: {totals.get('calculated_concentrate_grams', 0.0):.2f}g")
        self.solvent_grams_label.setText(f"Solvent: {totals.get('calculated_solvent_grams', 0.0):.2f}g")
        self.total_grams_label.setText(f"Total: {totals.get('calculated_total_grams', 0.0):.2f}g")
        self.conc_strength_label.setText(f"Strength: {totals.get('calculated_concentrate_strength', 0.0):.2f}%")
        self.total_cost_label.setText(f"Total Cost: ${totals.get('calculated_total_cost', 0.0):.2f}")

        self.formulation_updated.emit(temp_formulation)

    def save_formulation(self):
        name = self.formulation_name_entry.text().strip()
        if not name or not self.formulation_entries:
            CustomMessageBox.warning(self, "Validation Error",
                                     "Formulation must have a name and at least one ingredient.")
            return

        is_editing = self.editing_formulation_obj_ref is not None
        if any(f['name'].lower() == name.lower() and (not is_editing or f is not self.editing_formulation_obj_ref) for f
               in self.data_manager.data['formulations']):
            CustomMessageBox.warning(self, "Validation Error", f"Formulation '{name}' already exists.")
            return

        if is_editing:
            self.editing_formulation_obj_ref['name'] = name
            self.editing_formulation_obj_ref['entries'] = self.formulation_entries
            self.data_manager.calculate_formulation_totals(self.editing_formulation_obj_ref)
            self.show_status_message(f"Formulation '{name}' updated successfully!")
        else:
            new_formulation = {"name": name, "unit": "gram", "entries": self.formulation_entries}
            self.data_manager.calculate_formulation_totals(new_formulation)
            self.data_manager.data['formulations'].append(new_formulation)
            self.show_status_message(f"Formulation '{name}' saved successfully!")

        self.data_manager.save_data()
        self.reset_formulation_creation()

    def show_pyramid_view(self):
        if not self.pyramid_window:
            self.pyramid_window = PyramidWindow(data_manager=self.data_manager, parent=self)
            self.pyramid_window.closing.connect(lambda: setattr(self, 'pyramid_window', None))
            self.formulation_updated.connect(self.pyramid_window.update_data)
        self.pyramid_window.update_data({"entries": self.formulation_entries})
        self.pyramid_window.show_animated()
        self.pyramid_window.activateWindow()

    def show_scent_profile_view(self):
        if not self.scent_profile_window:
            self.scent_profile_window = ScentProfileWindow(data_manager=self.data_manager, parent=self)
            self.formulation_updated.connect(self.scent_profile_window.update_data)
            self.scent_profile_window.closing.connect(lambda: setattr(self, 'scent_profile_window', None))
        self.scent_profile_window.update_data({"entries": self.formulation_entries})
        self.scent_profile_window.show_animated()
        self.scent_profile_window.activateWindow()