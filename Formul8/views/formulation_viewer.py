# formul8/views/formulation_viewer.py
# The frame for viewing, searching, and managing all saved formulations.

import math
from datetime import datetime

# --- PyQt6 Imports ---
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QPushButton, QLabel, QLineEdit,
    QStackedWidget, QScrollArea, QFrame, QSizePolicy, QFileDialog, QMessageBox,
    QComboBox, QDoubleSpinBox, QDialogButtonBox, QDialog
)
from PyQt6.QtGui import QPainter, QColor, QBrush, QPolygonF, QPen, QResizeEvent, QPaintEvent, QConicalGradient
from PyQt6.QtCore import Qt, QPointF, pyqtSignal, QTimer

# --- Local Imports ---
from ..components import CustomDialog, CustomMessageBox
from ..constants import ACCORD_SYMBOL


class ScentFingerprintWidget(QWidget):
    def __init__(self, formulation_data, data_manager, parent=None):
        super().__init__(parent)
        self.formulation_data = formulation_data
        self.data_manager = data_manager
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.setToolTip("A visual fingerprint of the formula's scent profile.")
        self.category_percentages = self._calculate_category_percentages()

    def _calculate_category_percentages(self):
        totals = {}
        concentrate_entries = [e for e in self.formulation_data.get('entries', []) if
                               (ing := self.data_manager.get_ingredient_by_name(e.get('ingredient_name'))) and ing.get(
                                   'note_type') != 'Solvent']
        total_quantity = sum(entry.get('quantity', 0.0) for entry in concentrate_entries)
        if total_quantity == 0: return {}
        for entry in concentrate_entries:
            ing_data = self.data_manager.get_ingredient_by_name(entry.get('ingredient_name'))
            if ing_data:
                category = ing_data.get('primary_category', 'Uncategorized');
                totals[category] = totals.get(category, 0) + entry.get('quantity', 0.0)
        return {cat: (qty / total_quantity) * 100 for cat, qty in totals.items()}

    def paintEvent(self, event: QPaintEvent):
        painter = QPainter(self);
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        center = QPointF(self.rect().center());
        radius = min(center.x(), center.y()) - 5

        all_categories = self.data_manager.get_setting('scent_categories') or []
        categories = sorted([cat for cat in all_categories if cat in self.category_percentages])

        if not categories: return
        num_cats = len(categories);
        angle_step = 360 / num_cats
        painter.setPen(QPen(QColor("#5c6370"), 1, Qt.PenStyle.DotLine))
        for i in range(num_cats):
            angle = math.radians(i * angle_step - 90);
            end_point = QPointF(center.x() + radius * math.cos(angle), center.y() + radius * math.sin(angle));
            painter.drawLine(center, end_point)
        max_percentage = max(self.category_percentages.values()) if self.category_percentages else 0
        if max_percentage == 0: return
        points = []
        for i, category in enumerate(categories):
            percentage = self.category_percentages.get(category, 0);
            point_radius = radius * (percentage / max_percentage);
            angle = math.radians(i * angle_step - 90);
            points.append(
                QPointF(center.x() + point_radius * math.cos(angle), center.y() + point_radius * math.sin(angle)))
        fingerprint_polygon = QPolygonF(points);
        gradient = QConicalGradient(center, -90);
        color_map = self.data_manager.get_setting('scent_profile_colors') or {};
        default_color = QColor("#808080")
        for i, category in enumerate(categories): color = QColor(
            color_map.get(category, default_color.name())); position = i / num_cats; gradient.setColorAt(position,
                                                                                                         color)
        if categories:
            first_color = QColor(color_map.get(categories[0], default_color.name()));
            gradient.setColorAt(1.0, first_color)
        painter.setBrush(QBrush(gradient));
        painter.setPen(QPen(QColor("#5c6370"), 1));
        painter.drawPolygon(fingerprint_polygon)


class ExportChoiceDialog(QDialog):
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


class ScaleFormulationDialog(QDialog):
    def __init__(self, formula_name, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Scale Formulation")
        self.setMinimumWidth(400)

        main_layout = QVBoxLayout(self)
        form_layout = QGridLayout()

        form_layout.addWidget(QLabel("New Formula Name:"), 0, 0)
        self.name_edit = QLineEdit(f"{formula_name} - Scaled")
        form_layout.addWidget(self.name_edit, 0, 1)

        form_layout.addWidget(QLabel("Scaling Method:"), 1, 0)
        self.method_combo = QComboBox()
        self.methods = ["To New Concentrate Weight", "To New Total Weight", "By Factor", "By Percentage Factor",
                        "Normalize Concentrate to 100g"]
        self.method_combo.addItems(self.methods)
        form_layout.addWidget(self.method_combo, 1, 1)

        main_layout.addLayout(form_layout)

        self.input_stack = QStackedWidget()
        main_layout.addWidget(self.input_stack)

        # Input widgets for the stacked layout
        conc_widget = QWidget();
        conc_layout = QHBoxLayout(conc_widget);
        self.conc_weight_spin = QDoubleSpinBox(decimals=2, maximum=10000.0, value=30.0);
        conc_layout.addWidget(QLabel("New Concentrate Weight (g):"));
        conc_layout.addWidget(self.conc_weight_spin);
        self.input_stack.addWidget(conc_widget)
        total_widget = QWidget();
        total_layout = QHBoxLayout(total_widget);
        self.total_weight_spin = QDoubleSpinBox(decimals=2, maximum=10000.0, value=50.0);
        total_layout.addWidget(QLabel("New Total Weight (g):"));
        total_layout.addWidget(self.total_weight_spin);
        self.input_stack.addWidget(total_widget)
        factor_widget = QWidget();
        factor_layout = QHBoxLayout(factor_widget);
        self.factor_spin = QDoubleSpinBox(decimals=4, maximum=1000.0, value=2.0);
        factor_layout.addWidget(QLabel("Scaling Factor:"));
        factor_layout.addWidget(self.factor_spin);
        self.input_stack.addWidget(factor_widget)
        percent_widget = QWidget();
        percent_layout = QHBoxLayout(percent_widget);
        self.percent_spin = QDoubleSpinBox(decimals=2, maximum=10000.0, value=150.0);
        percent_layout.addWidget(QLabel("Percentage (%):"));
        percent_layout.addWidget(self.percent_spin);
        self.input_stack.addWidget(percent_widget)
        normalize_label = QLabel("This will create a 100g version of the pure concentrate.");
        normalize_label.setAlignment(Qt.AlignmentFlag.AlignCenter);
        self.input_stack.addWidget(normalize_label)

        self.method_combo.currentIndexChanged.connect(self.input_stack.setCurrentIndex)

        button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        main_layout.addWidget(button_box)

    def get_values(self):
        method = self.method_combo.currentText()
        value = 0.0
        if method == self.methods[0]:
            value = self.conc_weight_spin.value()
        elif method == self.methods[1]:
            value = self.total_weight_spin.value()
        elif method == self.methods[2]:
            value = self.factor_spin.value()
        elif method == self.methods[3]:
            value = self.percent_spin.value()
        return self.name_edit.text().strip(), method, value


class ViewEditFormulationsFrame(QWidget):
    edit_formulation_signal = pyqtSignal(dict)

    def __init__(self, data_manager, parent=None):
        super().__init__(parent)
        self.data_manager = data_manager
        self.selected_formula_name = None
        self.view_mode = self.data_manager.get_setting('default_formulation_view') or 'grid'

        main_layout = QVBoxLayout(self)
        top_bar = QHBoxLayout()
        search_layout = QHBoxLayout()
        self.search_entry = QLineEdit()
        self.search_entry.setPlaceholderText("Search formulations...")
        self.search_entry.textChanged.connect(self.build_view)
        search_layout.addWidget(QLabel("Search:"))
        search_layout.addWidget(self.search_entry)
        top_bar.addLayout(search_layout)
        self.toggle_view_btn = QPushButton()
        self.toggle_view_btn.setCheckable(True)
        self.toggle_view_btn.setObjectName("ViewToggle")
        self.toggle_view_btn.clicked.connect(self.toggle_view)
        top_bar.addWidget(self.toggle_view_btn)
        top_bar.addStretch()
        self.edit_btn = QPushButton("Edit Selected")
        self.scale_btn = QPushButton("Scale Formula")
        self.delete_btn = QPushButton("Delete Selected")
        self.export_btn = QPushButton("Export Selected")
        self.edit_btn.clicked.connect(self.edit_selected_formulation)
        self.scale_btn.clicked.connect(self.scale_selected_formulation)
        self.delete_btn.clicked.connect(self.delete_selected_formulation)
        self.export_btn.clicked.connect(self.export_selected_formulation)
        [top_bar.addWidget(btn) for btn in [self.edit_btn, self.scale_btn, self.delete_btn, self.export_btn]]
        main_layout.addLayout(top_bar)

        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOn)
        self.scroll_area.verticalScrollBar().setProperty("float", True)
        main_layout.addWidget(self.scroll_area)

        self._update_view_toggle_button()
        self.update_button_states()

    def on_show(self):
        self.build_view()

    def build_view(self):
        content_container = QWidget()
        search_term = self.search_entry.text().lower()
        formulations = self.data_manager.get_all_formulations()
        filtered = [f for f in formulations if
                    search_term in f.get('name', '').lower()] if search_term else formulations
        sorted_formulations = sorted(filtered, key=lambda x: x.get('name', ''))

        if not sorted_formulations:
            layout = QVBoxLayout(content_container)
            no_results_label = QLabel("No formulations found." if search_term else "No formulations in library.")
            no_results_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            layout.addWidget(no_results_label)
            self.scroll_area.setWidget(content_container)
            return

        if self.view_mode == 'grid':
            wrapper_layout = QHBoxLayout(content_container)
            wrapper_layout.addStretch(1)
            grid_layout = QGridLayout()
            grid_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
            num_columns = 4
            for i, formula in enumerate(sorted_formulations):
                grid_layout.addWidget(self.create_formula_grid_card(formula), i // num_columns, i % num_columns)
            wrapper_layout.addLayout(grid_layout)
            wrapper_layout.addStretch(1)
        else:  # List view
            list_layout = QVBoxLayout(content_container)
            list_layout.setSpacing(5)
            list_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
            for formula in sorted_formulations:
                list_layout.addWidget(self.create_formula_list_card(formula))
        self.scroll_area.setWidget(content_container)
        self.update_button_states()

    def _update_view_toggle_button(self):
        if self.view_mode == 'list':
            self.toggle_view_btn.setChecked(True);
            self.toggle_view_btn.setText("❖");
            self.toggle_view_btn.setToolTip(
                "Switch to Grid View")
        else:
            self.toggle_view_btn.setChecked(False);
            self.toggle_view_btn.setText("☰");
            self.toggle_view_btn.setToolTip(
                "Switch to List View")

    def toggle_view(self):
        self.view_mode = 'list' if self.view_mode == 'grid' else 'grid';
        self.data_manager.save_setting('default_formulation_view', self.view_mode)
        self._update_view_toggle_button();
        self.build_view()

    def create_formula_grid_card(self, formula):
        card = QFrame();
        card.formula_name = formula.get('name', '');
        card.setObjectName("CardFrame");
        card.setFrameShape(QFrame.Shape.StyledPanel);
        card.setMinimumSize(240, 200);
        card.setMaximumSize(260, 220)
        card_layout = QVBoxLayout(card);

        name_text = f"{formula.get('name', '')} {ACCORD_SYMBOL}" if formula.get('is_accord') else formula.get('name',
                                                                                                              '')
        name_label = QLabel(name_text)

        name_label.setObjectName("CardHeaderLabel");
        name_label.setWordWrap(True);
        card_layout.addWidget(name_label);
        card_layout.addStretch()
        info_container = QWidget();
        info_layout = QHBoxLayout(info_container);
        info_layout.setContentsMargins(0, 0, 0, 0);
        self.data_manager.calculate_formulation_totals(formula)
        info_text = (
            f"<b>Ingredients:</b> {len(formula.get('entries', []))}<br>"f"<b>Strength:</b> {formula.get('calculated_concentrate_strength', 0.0):.1f}%<br>"f"<b>Weight:</b> {formula.get('calculated_total_grams', 0.0):.2f}g<br>"f"<b>Cost:</b> ${formula.get('calculated_total_cost', 0.0):.2f}");
        info_layout.addWidget(QLabel(info_text), 1)
        fingerprint_widget = ScentFingerprintWidget(formula, data_manager=self.data_manager);
        fingerprint_widget.setFixedSize(140, 140);
        info_layout.addWidget(fingerprint_widget, 0)
        card_layout.addWidget(info_container);
        card.mousePressEvent = lambda event, name=formula.get('name', ''): self.on_formula_select(name, card);
        return card

    def create_formula_list_card(self, formula):
        card = QFrame();
        card.formula_name = formula.get('name', '');
        card.setObjectName("CardFrame");
        card.setFrameShape(QFrame.Shape.StyledPanel);
        card.setMinimumHeight(130)
        card_layout = QHBoxLayout(card);
        card_layout.setContentsMargins(10, 5, 5, 5);
        card_layout.setSpacing(10);
        text_container = QWidget();
        text_layout = QVBoxLayout(text_container);
        text_layout.setContentsMargins(0, 0, 0, 0);
        text_layout.setSpacing(5)

        name_text = f"{formula.get('name', '')} {ACCORD_SYMBOL}" if formula.get('is_accord') else formula.get('name',
                                                                                                              '')
        name_label = QLabel(name_text)

        name_label.setObjectName("CardHeaderLabel");
        name_label.setWordWrap(True)
        self.data_manager.calculate_formulation_totals(formula)
        stats_text = (
            f"<b>Ingredients:</b> {len(formula.get('entries', []))}  |  "f"<b>Strength:</b> {formula.get('calculated_concentrate_strength', 0.0):.1f}%  |  "f"<b>Weight:</b> {formula.get('calculated_total_grams', 0.0):.2f}g  |  "f"<b>Cost:</b> ${formula.get('calculated_total_cost', 0.0):.2f}")
        text_layout.addWidget(name_label);
        text_layout.addWidget(QLabel(stats_text));
        text_layout.addStretch()
        fingerprint_widget = ScentFingerprintWidget(formula, data_manager=self.data_manager);
        fingerprint_widget.setFixedSize(120, 120)
        card_layout.addWidget(text_container, 1);
        card_layout.addWidget(fingerprint_widget, 0);
        card.mousePressEvent = lambda event, name=formula.get('name', ''): self.on_formula_select(name, card);
        return card

    def on_formula_select(self, formula_name, clicked_card):
        self.selected_formula_name = formula_name
        container = self.scroll_area.widget()
        if container:
            for card in container.findChildren(QFrame, "CardFrame"):
                is_selected = (card == clicked_card)
                card.setProperty("selected", is_selected)
                card.style().polish(card)
        self.update_button_states()

    def update_button_states(self):
        enabled = self.selected_formula_name is not None;
        [btn.setEnabled(enabled) for btn in
         [self.edit_btn, self.scale_btn, self.delete_btn,
          self.export_btn]]

    def edit_selected_formulation(self):
        if self.selected_formula_name:
            if formula := self.data_manager.get_formulation_by_name(
                    self.selected_formula_name): self.edit_formulation_signal.emit(formula)

    def delete_selected_formulation(self):
        if not self.selected_formula_name:
            return
        formula = self.data_manager.get_formulation_by_name(self.selected_formula_name)
        if not formula:
            return

        item_type_str = "accord" if formula.get('is_accord') else "formulation"
        reply = CustomMessageBox.question(self, f"Confirm Delete",
                                          f"Are you sure you want to delete the {item_type_str} '{formula['name']}'?")

        if reply == QDialogButtonBox.StandardButton.Yes:
            self.data_manager.delete_formulation(formula['name'])
            self.selected_formula_name = None
            self.build_view()

    def scale_selected_formulation(self):
        if not (self.selected_formula_name and (
                formula := self.data_manager.get_formulation_by_name(self.selected_formula_name))):
            return

        dialog = ScaleFormulationDialog(formula['name'], self)
        if not dialog.exec():
            return

        new_name, method, value = dialog.get_values()

        if not new_name or (
                new_name.lower() != formula['name'].lower() and self.data_manager.get_formulation_by_name(new_name)):
            CustomMessageBox.warning(self, "Invalid Name", "New formula name cannot be empty and must be unique.")
            return

        new_formula = self.data_manager.scale_formulation(formula, new_name, method, value)

        if new_formula:
            self.build_view()
            QMessageBox.information(self, "Success", f"Formula scaled and saved as '{new_name}'.")
        else:
            QMessageBox.critical(self, "Scaling Error", "Could not scale the formula. "
                                                        "Check if the concentrate or total weight is zero.")

    def export_selected_formulation(self):
        if not self.selected_formula_name: return
        choice_dialog = ExportChoiceDialog(self)
        if not choice_dialog.exec(): return

        formula = self.data_manager.get_formulation_by_name(self.selected_formula_name)
        if not formula:
            QMessageBox.critical(self, "Error", "Could not find the selected formula.")
            return

        if choice_dialog.format == 'txt':
            default_name = f"{formula.get('name', 'formula')}.txt"
            path, _ = QFileDialog.getSaveFileName(self, "Export Formula as Text", default_name, "Text Files (*.txt)")
            if path:
                success, error_msg = self.data_manager.export_formula_to_txt(formula, path)
                if success:
                    QMessageBox.information(self, "Export Successful", f"Formula successfully exported to:\n{path}")
                else:
                    QMessageBox.critical(self, "Export Error", f"Could not export formula:\n{error_msg}")

        elif choice_dialog.format == 'pdf':
            default_name = f"{formula.get('name', 'formula')}.pdf"
            path, _ = QFileDialog.getSaveFileName(self, "Export Library as PDF", default_name, "PDF Documents (*.pdf)")
            if path:
                success, error_msg = self.data_manager.export_formula_to_pdf(formula, path)
                if success:
                    QMessageBox.information(self, "Export Successful", f"Formula successfully exported to:\n{path}")
                else:
                    QMessageBox.critical(self, "Export Error", f"Could not export formula:\n{error_msg}")