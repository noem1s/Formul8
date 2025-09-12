# formul8/utils.py
# General utility functions.

import os
import sys
from PyQt6.QtWidgets import QTreeWidgetItem
from PyQt6.QtCore import Qt

try:
    from fpdf import FPDF, XPos, YPos
except ImportError:
    FPDF = None
    XPos = None
    YPos = None
from datetime import datetime

class ReportPDF(FPDF):
    def __init__(self, orientation='P', unit='mm', format='Letter'):
        if FPDF is None:
            raise ImportError("The 'fpdf2' library is required for PDF export.")
        super().__init__(orientation, unit, format)
        self.report_title = "Formul8 Report"

    def header(self):
        self.set_font('helvetica', 'B', 16)
        self.set_text_color(152, 129, 167)
        self.cell(0, 10, self.report_title, border=False, new_x=XPos.LMARGIN, new_y=YPos.NEXT, align='C')
        self.ln(5)
        self.set_draw_color(220, 220, 220)
        self.line(self.get_x(), self.get_y(), self.get_x() + self.w - self.l_margin - self.r_margin, self.get_y())
        self.ln(10)

    def footer(self):
        self.set_y(-15)
        self.set_font('helvetica', 'I', 8)
        self.set_text_color(128)
        page_number_text = f'Page {self.page_no()} of {{nb}}'
        self.cell(0, 10, page_number_text, border=False, align='C')
        self.cell(0, 10, datetime.now().strftime("%Y-%m-%d %H:%M:%S"), border=False, align='R')

    def set_report_title(self, title):
        self.report_title = title


def populate_ingredient_tree(tree_widget, ingredients_to_show, data_manager):
    """
    A centralized utility to populate a QTreeWidget with ingredients and accord folders.
    RATIONALE: Consolidates duplicated code from multiple views into a single, maintainable function.
    """
    from .components import AccordItemWidget
    from .constants import ACCORD_SYMBOL

    tree_widget.clear()

    alignments = {}
    for i in range(tree_widget.header().count()):
        header_text = tree_widget.headerItem().text(i)
        if header_text in ["Conc", "Note", "Cat 1", "Cat 2", "Unit"]:
            alignments[i] = Qt.AlignmentFlag.AlignCenter
        elif header_text in ["Cost / g", "Quantity", "% in Conc.", "Cost"]:
            alignments[i] = Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
        else:
            alignments[i] = Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter

    for ing_data in ingredients_to_show:
        parent_item = QTreeWidgetItem()
        parent_item.setData(0, Qt.ItemDataRole.UserRole, {'name': ing_data['name'], 'type': ing_data.get('type', 'raw')})
        tree_widget.addTopLevelItem(parent_item)

        is_accord = ing_data.get('type') == 'accord'
        if is_accord:
            item_widget = AccordItemWidget(ing_data['name'])
            item_widget.set_tree_item(parent_item)
            tree_widget.setItemWidget(parent_item, 0, item_widget)
        else:
            parent_item.setText(0, ing_data['name'])

        if tree_widget.columnCount() > 1:
            parent_item.setText(1, f"{ing_data.get('concentration', 100.0):.2f}%")
        if tree_widget.columnCount() > 2:
            parent_item.setText(2, format_for_display(ing_data.get('note_type', 'Other')))
        if tree_widget.columnCount() > 3:
            parent_item.setText(3, format_for_display(ing_data.get('primary_category', 'Uncategorized')))
        if tree_widget.columnCount() > 4:
            parent_item.setText(4, format_for_display(ing_data.get('secondary_category', '')))
        if tree_widget.columnCount() > 5:
            parent_item.setText(5, f"${ing_data.get('cost', 0.0):.2f}")

        for col, align in alignments.items():
            parent_item.setTextAlignment(col, align)

        if is_accord:
            accord_formula = data_manager.get_formulation_by_name(ing_data['name'])
            if accord_formula:
                data_manager.calculate_formulation_totals(accord_formula)
                for entry in sorted(accord_formula.get('entries', []), key=lambda x: x['ingredient_name']):
                    child_data = [f"    - {entry['ingredient_name']}", f"     {entry.get('percentage', 0):.2f}%"]
                    child_item = QTreeWidgetItem(child_data)
                    child_item.setFlags(child_item.flags() & ~Qt.ItemFlag.ItemIsDragEnabled)
                    child_item.setTextAlignment(0, Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
                    child_item.setTextAlignment(1, Qt.AlignmentFlag.AlignCenter)
                    parent_item.addChild(child_item)


def resource_path(relative_path):
    """ Get absolute path to resource, works for dev and for PyInstaller. """
    try:
        base_path = sys._MEIPASS
    except AttributeError:
        base_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
    return os.path.join(base_path, 'assets', relative_path)


def format_for_display(value):
    """
    Converts 'Uncategorized' or 'N/A' to a blank string for clean UI display.
    """
    if str(value).strip().lower() in ('uncategorized', 'n/a', 'other'):
        return ""
    return str(value)