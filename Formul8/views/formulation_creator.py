# formul8/views/formulation_creator.py
# The core frame for creating and editing formulations with live analysis views.

import math

# --- PyQt6 Imports ---
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QPushButton, QLabel, QLineEdit,
    QGroupBox, QFrame, QColorDialog, QDoubleSpinBox, QTreeWidgetItem, QMenu,
    QStackedLayout, QStyle, QHeaderView, QRadioButton, QButtonGroup, QSizePolicy
)
from PyQt6.QtGui import QPainter, QColor, QBrush, QPolygonF, QPaintEvent, QPalette, QCursor
from PyQt6.QtCore import Qt, QPointF, QRectF, pyqtSignal, QTimer, QSettings, QPoint

# --- Third-party Libraries ---
import matplotlib.pyplot as plt
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas

# --- Local Imports ---
from ..components import (
    CustomDialog, CustomMessageBox, DragAndDropTree, SaveAsDialog, AccordItemWidget,
    create_fading_tree_widget, TweakDialog, update_fades, configure_accord_item_display
)
from ..constants import (
    ACCORD_SYMBOL, NOTE_TYPES, FORMULATION_UNITS, FORMULATION_UNITS_DISPLAY,
    FORMULATION_UNITS_ABBREVIATED, MASS_UNITS, VOLUME_UNITS
)
from ..utils import format_for_display, convert_unit
from ..context_menu_handler import handle_tree_context_menu


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
                    # RATIONALE: Use note_type for pyramid, not primary_category
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
        self.setWindowModality(Qt.WindowModality.NonModal)
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
        self.setWindowModality(Qt.WindowModality.NonModal)
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

        color_map = self.data_manager.get_setting('scent_profile_colors') or {}
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
        self.available_sort_state = (None, None)
        self.formulation_sort_state = (None, None)
        self.current_display_unit = 'g'

        main_layout = QVBoxLayout(self)

        details_group = QGroupBox("Formulation Details");
        details_layout = QGridLayout(details_group);
        details_layout.setColumnStretch(1, 1)

        self.formulation_name_entry = QLineEdit();
        details_layout.addWidget(QLabel("Formulation Name:"), 0, 0);
        details_layout.addWidget(self.formulation_name_entry, 0, 1);

        unit_label = QLabel("Display Unit:")
        unit_label.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignRight)

        unit_selection_widget = QWidget()
        unit_selection_layout = QHBoxLayout(unit_selection_widget)
        unit_selection_layout.setContentsMargins(0, 0, 0, 0)
        unit_selection_layout.setSpacing(15)

        self.unit_button_group = QButtonGroup(self)

        mass_group = QGroupBox("Mass")
        mass_layout = QHBoxLayout(mass_group)
        mass_layout.addStretch()
        for unit in MASS_UNITS:
            display_text = FORMULATION_UNITS_DISPLAY.get(unit, unit)
            radio = QRadioButton(display_text)
            radio.setProperty("logical_unit", unit)
            self.unit_button_group.addButton(radio)
            mass_layout.addWidget(radio)
            if unit == 'g':
                radio.setChecked(True)
        mass_layout.addStretch()

        volume_group = QGroupBox("Volume & Count")
        volume_layout = QHBoxLayout(volume_group)
        volume_layout.addStretch()
        for unit in VOLUME_UNITS:
            display_text = FORMULATION_UNITS_DISPLAY.get(unit, unit)
            radio = QRadioButton(display_text)
            radio.setProperty("logical_unit", unit)
            self.unit_button_group.addButton(radio)
            volume_layout.addWidget(radio)
        volume_layout.addStretch()

        unit_selection_layout.addStretch(1)
        unit_selection_layout.addWidget(mass_group)
        unit_selection_layout.addWidget(volume_group)
        unit_selection_layout.addStretch(3.8)

        self.unit_button_group.buttonClicked.connect(self._on_unit_changed)
        details_layout.addWidget(unit_label, 1, 0)
        details_layout.addWidget(unit_selection_widget, 1, 1)

        main_layout.addWidget(details_group)
        content_layout = QHBoxLayout();
        content_layout.setSpacing(15)

        # --- AVAILABLE INGREDIENTS PANEL ---
        available_panel = QGroupBox("Available Ingredients (Drag to add)");
        available_layout = QVBoxLayout(available_panel);

        self.ing_search_bar = QLineEdit()
        self.ing_search_bar.setPlaceholderText("Search for an ingredient...")
        self.ing_search_bar.textChanged.connect(self._filter_available_ingredients)
        available_layout.addWidget(self.ing_search_bar)

        available_ing_container, self.available_ing_tree, self.avail_top_fade, self.avail_bottom_fade = create_fading_tree_widget(
            DragAndDropTree)
        self.available_ing_tree.setColumnCount(6)
        self.available_original_labels = ["Ingredient", "   Conc", "Note", "Cat 1", "Cat 2", "Cost / g"]
        self.available_ing_tree.setHeaderLabels(self.available_original_labels)
        self.available_ing_tree.setSortingEnabled(False)
        self.available_ing_tree.header().customSectionClicked.connect(
            lambda index: self._handle_sort_request(self.available_ing_tree, index)
        )
        self.available_ing_tree.header().setDefaultAlignment(Qt.AlignmentFlag.AlignCenter)
        self.available_ing_tree.ingredient_dropped_in.connect(self.remove_ingredient_from_formula)
        self.available_ing_tree.itemExpanded.connect(self._update_accord_indicator)
        self.available_ing_tree.itemCollapsed.connect(self._update_accord_indicator)
        self.available_ing_tree.itemSelectionChanged.connect(self._on_selection_changed)

        avail_header = self.available_ing_tree.header()
        avail_header.setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        avail_header.setStretchLastSection(False)
        avail_header.sectionResized.connect(self.save_column_widths)
        avail_header.sectionMoved.connect(self.save_column_widths)

        available_layout.addWidget(available_ing_container)
        content_layout.addWidget(available_panel, 1)

        # --- CURRENT FORMULATION PANEL ---
        current_panel = QGroupBox("Current Formulation (Drag out to remove)");
        current_layout = QVBoxLayout(current_panel);

        formulation_tree_container, self.formulation_tree, self.form_top_fade, self.form_bottom_fade = create_fading_tree_widget(
            DragAndDropTree)
        self.formulation_tree.setObjectName("FormulationCreatorTree")
        self.formulation_tree.setColumnCount(5)
        self.formulation_original_labels = ["Ingredient", "Quantity", "Unit", "% in Conc.", "Cost"]
        self.formulation_tree.setHeaderLabels(self.formulation_original_labels)
        self.formulation_tree.setSortingEnabled(False)
        self.formulation_tree.header().customSectionClicked.connect(
            lambda index: self._handle_sort_request(self.formulation_tree, index)
        )
        self.formulation_tree.header().setDefaultAlignment(Qt.AlignmentFlag.AlignCenter)
        self.formulation_tree.ingredient_dropped_in.connect(self.add_ingredient_to_formula)
        self.formulation_tree.itemDoubleClicked.connect(self.on_cell_double_click)
        self.formulation_tree.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.formulation_tree.customContextMenuRequested.connect(self.show_context_menu)
        self.formulation_tree.itemExpanded.connect(self._update_accord_indicator)
        self.formulation_tree.itemCollapsed.connect(self._update_accord_indicator)
        self.formulation_tree.itemSelectionChanged.connect(self._on_selection_changed)

        form_header = self.formulation_tree.header()
        form_header.setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        form_header.setStretchLastSection(False)
        form_header.sectionResized.connect(self.save_column_widths)
        form_header.sectionMoved.connect(self.save_column_widths)

        current_layout.addWidget(formulation_tree_container)

        totals_frame = QFrame()
        totals_frame.setObjectName("CardFrame")
        totals_frame.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        totals_layout = QGridLayout(totals_frame)

        self.conc_grams_label = QLabel("Conc: 0.00g")
        self.solvent_grams_label = QLabel("Solvent: 0.00g")
        self.total_grams_label = QLabel("Total: 0.00g")
        self.conc_strength_label = QLabel("Strength: 0.00%")
        self.total_cost_label = QLabel("Cost: $0.00")

        totals_layout.addWidget(self.conc_grams_label, 0, 0, alignment=Qt.AlignmentFlag.AlignCenter)
        totals_layout.addWidget(self.solvent_grams_label, 0, 1, alignment=Qt.AlignmentFlag.AlignCenter)
        totals_layout.addWidget(self.total_grams_label, 0, 2, alignment=Qt.AlignmentFlag.AlignCenter)
        totals_layout.addWidget(self.conc_strength_label, 0, 3, alignment=Qt.AlignmentFlag.AlignCenter)
        totals_layout.addWidget(self.total_cost_label, 0, 4, alignment=Qt.AlignmentFlag.AlignCenter)

        for i in range(5):
            totals_layout.setColumnStretch(i, 1)

        current_layout.addWidget(totals_frame)
        content_layout.addWidget(current_panel, 1)
        main_layout.addLayout(content_layout)

        self.status_label = QLabel("")
        self.status_label.setObjectName("StatusLabel")
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        main_layout.addWidget(self.status_label)

        # --- Bottom Buttons ---
        self.save_button = QPushButton("Save...")
        self.save_button.clicked.connect(self.save_formulation)
        clear_button = QPushButton("Clear All")
        clear_button.clicked.connect(self.reset_formulation_creation)
        pyramid_button = QPushButton("Pyramid")
        pyramid_button.clicked.connect(self.show_pyramid_view)
        profile_button = QPushButton("Scent Profile")
        profile_button.clicked.connect(self.show_scent_profile_view)

        left_buttons_layout = QHBoxLayout()
        left_buttons_layout.setSpacing(15)
        left_buttons_layout.setContentsMargins(0, 0, 0, 0)
        left_buttons_layout.addStretch()
        left_buttons_layout.addWidget(self.save_button)
        left_buttons_layout.addWidget(clear_button)

        right_buttons_layout = QHBoxLayout()
        right_buttons_layout.setSpacing(15)
        right_buttons_layout.setContentsMargins(0, 0, 0, 0)
        right_buttons_layout.addWidget(pyramid_button)
        right_buttons_layout.addWidget(profile_button)
        right_buttons_layout.addStretch()

        bottom_bar = QHBoxLayout()
        bottom_bar.setSpacing(15)
        bottom_bar.addLayout(left_buttons_layout, 1)
        bottom_bar.addLayout(right_buttons_layout, 1)

        main_layout.addLayout(bottom_bar)

        self.status_timer = QTimer(self)
        self.status_timer.setSingleShot(True)
        self.status_timer.timeout.connect(self.status_label.clear)

    def on_show(self):
        self.update_current_formula_display()
        self._filter_available_ingredients()
        self.load_column_widths()
        QTimer.singleShot(0, self._initial_fade_update)
        QTimer.singleShot(0, self._adjust_fade_positions)

    def _on_unit_changed(self, button):
        """Handles the user selecting a new display unit."""
        self.current_display_unit = button.property("logical_unit")
        self.update_current_formula_display()

    def _adjust_fade_positions(self):
        """
        Sets a top margin on the fade overlays to position them below the headers.
        """
        from ..components import update_fades
        header_height = self.available_ing_tree.header().height()
        overlay_widget = self.avail_top_fade.parentWidget()
        if overlay_widget:
            overlay_widget.layout().setContentsMargins(0, header_height, 0, 0)

        header_height = self.formulation_tree.header().height()
        overlay_widget = self.form_top_fade.parentWidget()
        if overlay_widget:
            overlay_widget.layout().setContentsMargins(0, header_height, 0, 0)

    def _initial_fade_update(self):
        """Force an update of the fades after the UI is shown."""
        from ..components import update_fades
        update_fades(self.available_ing_tree, self.avail_top_fade, self.avail_bottom_fade)
        update_fades(self.formulation_tree, self.form_top_fade, self.form_bottom_fade)

    def _update_accord_indicator(self, item):
        """Changes the expand/collapse icon for an accord item."""
        widget = self.sender().itemWidget(item, 0)
        if isinstance(widget, AccordItemWidget):
            widget.set_expanded(item.isExpanded())

    def _on_selection_changed(self):
        """Updates the visual state of all accord widgets based on tree selection."""
        sender_tree = self.sender()
        if not sender_tree: return

        for i in range(sender_tree.topLevelItemCount()):
            item = sender_tree.topLevelItem(i)
            if item:
                widget = sender_tree.itemWidget(item, 0)
                if isinstance(widget, AccordItemWidget):
                    widget.set_selected(item.isSelected())

    def _update_header_labels(self):
        """
        Updates header labels to show a unicode sort indicator instead of using
        Qt's buggy native indicator, which causes alignment issues.
        """
        # Update available ingredients tree header
        sort_column, sort_order = self.available_sort_state
        new_labels = self.available_original_labels[:]
        if sort_column is not None:
            if sort_order == Qt.SortOrder.AscendingOrder:
                new_labels[sort_column] += " ▲"
            else:
                new_labels[sort_column] += " ▼"
        self.available_ing_tree.setHeaderLabels(new_labels)

        # Update current formulation tree header
        sort_column, sort_order = self.formulation_sort_state
        new_labels = self.formulation_original_labels[:]
        if sort_column is not None:
            if sort_order == Qt.SortOrder.AscendingOrder:
                new_labels[sort_column] += " ▲"
            else:
                new_labels[sort_column] += " ▼"
        self.formulation_tree.setHeaderLabels(new_labels)

    def _handle_sort_request(self, tree_widget, column_index):
        """
        Handles the three-state sorting logic for tree widgets.
        """
        if tree_widget is self.formulation_tree and column_index == 2:  # Unit column
            return

        is_available_tree = tree_widget is self.available_ing_tree

        if is_available_tree:
            current_sort_column, current_sort_order = self.available_sort_state
        else:
            current_sort_column, current_sort_order = self.formulation_sort_state

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

        if is_available_tree:
            self.available_sort_state = (new_sort_column, new_sort_order)
            self._filter_available_ingredients()
        else:
            self.formulation_sort_state = (new_sort_column, new_sort_order)
            self.update_current_formula_display()

    def show_status_message(self, text, is_error=False):
        self.status_label.setText(text)
        self.status_label.setProperty("error", is_error)
        self.status_label.style().polish(self.status_label)
        self.status_timer.start(3000)

    def save_column_widths(self):
        """Saves the column widths for both tree views in this frame."""
        settings = QSettings()
        available_state = self.available_ing_tree.header().saveState()
        formulation_state = self.formulation_tree.header().saveState()
        settings.setValue("creator/availableHeaderState", available_state)
        settings.setValue("creator/formulationHeaderState", formulation_state)

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
            self._filter_available_ingredients()

    def reset_formulation_creation(self):
        if self.pyramid_window: self.pyramid_window.close()
        if self.scent_profile_window: self.scent_profile_window.close()
        self.editing_formulation_obj_ref = None
        self.formulation_name_entry.clear()
        self.ing_search_bar.clear()
        self.formulation_entries = []
        self.status_label.clear()
        self.save_button.setText("Save...")
        self.available_sort_state = (None, None)
        self.formulation_sort_state = (None, None)
        self._update_header_labels()
        self._filter_available_ingredients()
        self.update_current_formula_display()

    def setup_for_editing(self, formula_data):
        self.reset_formulation_creation()
        self.editing_formulation_obj_ref = formula_data
        self.formulation_name_entry.setText(formula_data.get('name', ''))
        self.formulation_entries = [entry.copy() for entry in formula_data.get('entries', [])]
        self.save_button.setText("Update...")
        self.update_current_formula_display()
        self._filter_available_ingredients()

    def _filter_available_ingredients(self):
        """Filters and sorts the available ingredients list."""
        self._update_header_labels()
        expanded_item_names = set()
        for i in range(self.available_ing_tree.topLevelItemCount()):
            item = self.available_ing_tree.topLevelItem(i)
            if item and item.isExpanded():
                item_data = item.data(0, Qt.ItemDataRole.UserRole)
                if item_data and 'name' in item_data:
                    expanded_item_names.add(item_data['name'])

        self.available_ing_tree.clear()
        search_term = self.ing_search_bar.text().lower()

        all_ingredients = self.data_manager.get_all_ingredients()
        current_formula_names = {e['ingredient_name'] for e in self.formulation_entries}

        ingredients_to_show = [
            ing for ing in all_ingredients if ing['name'] not in current_formula_names
        ]

        if self.editing_formulation_obj_ref and self.editing_formulation_obj_ref.get('is_accord'):
            accord_name_being_edited = self.editing_formulation_obj_ref.get('name')
            ingredients_to_show = [
                ing for ing in ingredients_to_show if ing.get('name') != accord_name_being_edited
            ]

        if search_term:
            ingredients_to_show = [
                ing for ing in ingredients_to_show if
                search_term in ing.get('name', '').lower() or
                (ing.get('type') in ['formulation_accord', 'premade_accord'] and any(
                    search_term in entry.get('ingredient_name', '').lower() for entry in
                    (self.data_manager.get_formulation_by_name(ing.get('name', '')) or {}).get('entries', [])))
            ]

        sort_column, sort_order = self.available_sort_state
        if sort_column is not None:
            is_reverse = sort_order == Qt.SortOrder.DescendingOrder
            sort_keys = ["name", "concentration", "note_type", "primary_category", "secondary_category", "cost"]
            sort_key = sort_keys[sort_column]

            def sort_func(x):
                val = x.get(sort_key)
                if sort_key in ["concentration", "cost"]:
                    return float(str(val or '0').strip('%$ '))
                return str(val or '').lower()

            ingredients_to_show.sort(key=sort_func, reverse=is_reverse)

        alignments = {
            1: Qt.AlignmentFlag.AlignCenter, 2: Qt.AlignmentFlag.AlignCenter,
            3: Qt.AlignmentFlag.AlignCenter, 4: Qt.AlignmentFlag.AlignCenter,
            5: Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
        }

        for ing_data in ingredients_to_show:
            parent_item = QTreeWidgetItem()
            parent_item.setData(0, Qt.ItemDataRole.UserRole,
                                {'name': ing_data['name'], 'type': ing_data.get('type', 'raw')})

            if ing_data.get('type', 'raw') not in ['formulation_accord', 'premade_accord']:
                parent_item.setText(0, ing_data['name'])

            parent_item.setText(1, f"{ing_data.get('concentration', 100.0):.2f}%")
            parent_item.setText(2, format_for_display(ing_data.get('note_type', 'Other')))
            parent_item.setText(3, format_for_display(ing_data.get('primary_category', 'Uncategorized')))
            parent_item.setText(4, format_for_display(ing_data.get('secondary_category', '')))
            parent_item.setText(5, f"${ing_data.get('cost', 0.0):.2f}")

            self.available_ing_tree.addTopLevelItem(parent_item)

            if ing_data['name'] in expanded_item_names:
                parent_item.setExpanded(True)

            configure_accord_item_display(
                parent_item=parent_item,
                item_data=ing_data,
                data_manager=self.data_manager,
                tree_widget=self.available_ing_tree,
                child_percentage_column=1,
                child_name_prefix="    - "
            )

            for i, align in alignments.items():
                if i < parent_item.columnCount():
                    parent_item.setTextAlignment(i, align)

        from ..components import update_fades
        QTimer.singleShot(0, lambda: update_fades(self.available_ing_tree, self.avail_top_fade,
                                                  self.avail_bottom_fade))
        QTimer.singleShot(0, self._on_selection_changed)

    def add_ingredient_to_formula(self, ingredient_names):
        for name in ingredient_names:
            if not any(entry['ingredient_name'].lower() == name.lower() for entry in self.formulation_entries):
                self.formulation_entries.append(
                    {"ingredient_name": name, "quantity": 0.0, "unit": "gram", "highlight_color": None})
        self.update_current_formula_display()
        self._filter_available_ingredients()

    def on_cell_double_click(self, item, column):
        if column != 1 or (item and item.parent() is not None):
            return

        quantity_in_grams = 0.0
        item_data = item.data(0, Qt.ItemDataRole.UserRole)
        name_to_find = item_data['name']
        for entry in self.formulation_entries:
            if entry['ingredient_name'] == name_to_find:
                quantity_in_grams = entry.get('quantity', 0.0)
                break

        original_value = convert_unit(quantity_in_grams, 'g', self.current_display_unit)

        spinbox = QDoubleSpinBox()
        spinbox.setDecimals(4)
        spinbox.setRange(0, 99999)
        spinbox.setValue(original_value)
        spinbox.editingFinished.connect(lambda: self.update_quantity_from_spinbox(item, spinbox))
        self.formulation_tree.setItemWidget(item, column, spinbox)
        spinbox.setFocus()

    def update_quantity_from_spinbox(self, item, spinbox):
        item_data = item.data(0, Qt.ItemDataRole.UserRole)
        name_to_update = item_data['name']

        value_in_display_unit = spinbox.value()
        value_in_grams = convert_unit(value_in_display_unit, self.current_display_unit, 'g')

        for entry in self.formulation_entries:
            if entry['ingredient_name'] == name_to_update:
                entry['quantity'] = value_in_grams
                break
        self.formulation_tree.setItemWidget(item, 1, None)
        self.update_current_formula_display()

    def show_context_menu(self, position):
        handle_tree_context_menu(self, self.formulation_tree, position)

    def set_highlight_color(self):
        color = QColorDialog.getColor()
        if color.isValid():
            for item in self.formulation_tree.selectedItems():
                item_data = item.data(0, Qt.ItemDataRole.UserRole)
                name_to_update = item_data['name']
                for entry in self.formulation_entries:
                    if entry['ingredient_name'] == name_to_update:
                        entry['highlight_color'] = color.name()
            self.update_current_formula_display()

    def clear_highlight(self):
        for item in self.formulation_tree.selectedItems():
            item_data = item.data(0, Qt.ItemDataRole.UserRole)
            name_to_update = item_data['name']
            for entry in self.formulation_entries:
                if entry['ingredient_name'] == name_to_update:
                    entry['highlight_color'] = None
        self.update_current_formula_display()

    def update_current_formula_display(self):
        """
        Rebuilds the 'Current Formulation' tree, showing accords as expandable folders.
        """
        self._update_header_labels()
        expanded_item_names = set()
        for i in range(self.formulation_tree.topLevelItemCount()):
            item = self.formulation_tree.topLevelItem(i)
            if item and item.isExpanded():
                item_data = item.data(0, Qt.ItemDataRole.UserRole)
                if item_data and 'name' in item_data:
                    expanded_item_names.add(item_data['name'])

        self.formulation_tree.clear()

        full_entries_data = []
        for entry in self.formulation_entries:
            ing_data = self.data_manager.get_ingredient_by_name(entry['ingredient_name'])
            if ing_data:
                combined_data = {**ing_data, **entry}
                full_entries_data.append(combined_data)

        sort_column, sort_order = self.formulation_sort_state
        if sort_column is not None:
            is_reverse = sort_order == Qt.SortOrder.DescendingOrder
            sort_keys = ["name", "quantity", "unit", "percentage", "cost"]
            sort_key = sort_keys[sort_column]

            if sort_key in ["percentage", "cost"]:
                self.data_manager.calculate_formulation_totals({'entries': full_entries_data})

            def sort_func(x):
                val = x.get(sort_key)
                if sort_key in ["quantity", "percentage", "cost"]:
                    return float(str(val or '0').strip('%$ '))
                return str(val or '').lower()

            full_entries_data.sort(key=sort_func, reverse=is_reverse)

        temp_formulation = {"entries": full_entries_data}
        self.data_manager.calculate_formulation_totals(temp_formulation)

        alignments = {
            1: Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter,
            2: Qt.AlignmentFlag.AlignCenter,
            3: Qt.AlignmentFlag.AlignCenter | Qt.AlignmentFlag.AlignVCenter,
            4: Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
        }

        for ing_data in temp_formulation['entries']:
            parent_item = QTreeWidgetItem()
            parent_item.setData(0, Qt.ItemDataRole.UserRole,
                                {'name': ing_data['name'], 'type': ing_data.get('type', 'raw')})

            if ing_data.get('type', 'raw') not in ['formulation_accord', 'premade_accord']:
                parent_item.setText(0, ing_data['name'])

            quantity_in_grams = ing_data.get('quantity', 0.0)
            display_quantity = convert_unit(quantity_in_grams, 'g', self.current_display_unit)
            display_unit_text = FORMULATION_UNITS_ABBREVIATED.get(self.current_display_unit,
                                                                  self.current_display_unit)

            parent_item.setText(1, f"{display_quantity:.4f}")
            parent_item.setText(2, display_unit_text)
            parent_item.setText(3, f"{ing_data.get('percentage', 0.0):.2f}%")
            parent_item.setText(4, f"${ing_data.get('cost', 0.0):.2f}")

            self.formulation_tree.addTopLevelItem(parent_item)

            if ing_data['name'] in expanded_item_names:
                parent_item.setExpanded(True)

            for i, align in alignments.items():
                parent_item.setTextAlignment(i, align)

            if color_hex := ing_data.get('highlight_color'):
                for i in range(parent_item.columnCount()):
                    parent_item.setBackground(i, QBrush(QColor(color_hex)))

            configure_accord_item_display(
                parent_item=parent_item,
                item_data=ing_data,
                data_manager=self.data_manager,
                tree_widget=self.formulation_tree,
                child_percentage_column=3,
                child_name_prefix="    - "
            )

        totals = temp_formulation
        conc_grams = totals.get('calculated_concentrate_grams', 0.0)
        solvent_grams = totals.get('calculated_solvent_grams', 0.0)
        total_grams = totals.get('calculated_total_grams', 0.0)

        display_conc = convert_unit(conc_grams, 'g', self.current_display_unit)
        display_solvent = convert_unit(solvent_grams, 'g', self.current_display_unit)
        display_total = convert_unit(total_grams, 'g', self.current_display_unit)
        display_unit_text = FORMULATION_UNITS_ABBREVIATED.get(self.current_display_unit,
                                                              self.current_display_unit)

        self.conc_grams_label.setText(f"Conc: {display_conc:.2f}{display_unit_text}")
        self.solvent_grams_label.setText(f"Solvent: {display_solvent:.2f}{display_unit_text}")
        self.total_grams_label.setText(f"Total: {display_total:.2f}{display_unit_text}")
        self.conc_strength_label.setText(f"Strength: {totals.get('calculated_concentrate_strength', 0.0):.2f}%")
        self.total_cost_label.setText(f"Total Cost: ${totals.get('calculated_total_cost', 0.0):.2f}")

        self.formulation_updated.emit(temp_formulation)
        from ..components import update_fades
        QTimer.singleShot(0, lambda: update_fades(self.formulation_tree, self.form_top_fade,
                                                  self.form_bottom_fade))
        QTimer.singleShot(0, self._on_selection_changed)

    def save_formulation(self):
        # 1. Validation
        name = self.formulation_name_entry.text().strip()
        if not name or not self.formulation_entries:
            CustomMessageBox.warning(self, "Validation Error", "A name and at least one ingredient are required.")
            return

        is_editing = self.editing_formulation_obj_ref is not None
        original_name = self.editing_formulation_obj_ref.get('name') if is_editing else None

        if name.lower() != (original_name.lower() if original_name else None):
            if self.data_manager.get_formulation_by_name(name) or self.data_manager.get_ingredient_by_name(name):
                CustomMessageBox.warning(self, "Validation Error", f"An item named '{name}' already exists.")
                return

        # 2. Get User Intent
        was_accord = is_editing and self.editing_formulation_obj_ref.get('is_accord', False)
        dialog = SaveAsDialog(is_editing_accord=was_accord, parent=self)
        if not dialog.exec():
            return

        save_details = dialog.get_values()
        is_now_accord = save_details['type'] == 'accord'

        # If the name changed while editing, we need to handle the original
        if is_editing and name.lower() != original_name.lower():
            self.data_manager.delete_formulation(original_name)

        # If it was an accord but now isn't (or name changed), remove old accord-ingredient
        if was_accord and (not is_now_accord or name.lower() != original_name.lower()):
            self.data_manager.delete_ingredient(original_name)

        formulation_obj = {
            "name": name,
            "entries": self.formulation_entries,
            "is_accord": is_now_accord,
            "unit": "gram"
        }
        self.data_manager.save_formulation(formulation_obj)

        if is_now_accord:
            self.data_manager.create_accord_as_ingredient(
                formulation_obj,
                save_details['note_type'],
                save_details['primary_category'],
                save_details['secondary_category']
            )

        self.show_status_message(f"'{name}' saved successfully as a {save_details['type']}!")
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
            self.scent_profile_window.closing.connect(lambda: setattr(self, 'scent_profile_window', None))
            self.formulation_updated.connect(self.scent_profile_window.update_data)
        self.scent_profile_window.update_data({"entries": self.formulation_entries})
        self.scent_profile_window.show_animated()
        self.scent_profile_window.activateWindow()