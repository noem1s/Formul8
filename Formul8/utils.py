# formul8/utils.py
# General utility functions.

import os
import sys
from PyQt6.QtCore import Qt

from .constants import (
    GRAMS_PER_ML, DROPS_PER_GRAM, GRAMS_PER_OUNCE_MASS, ML_PER_FL_OUNCE,
    GRAMS_PER_KG, GRAMS_PER_POUND, ML_PER_LITER, FL_OUNCES_PER_DRAM
)

try:
    from fpdf import FPDF, XPos, YPos
except ImportError:
    FPDF = None
    XPos = None
    YPos = None
from datetime import datetime


def convert_unit(value, from_unit, to_unit):
    """
    Converts a value from one unit to another using predefined constants.
    The canonical unit is grams (g).
    """
    if from_unit == to_unit:
        return value

    # First, convert the input value to our base unit (grams)
    value_in_grams = 0.0
    if from_unit == 'g':
        value_in_grams = value
    elif from_unit == 'mg':
        value_in_grams = value / 1000.0
    elif from_unit == 'kg':
        value_in_grams = value * GRAMS_PER_KG
    elif from_unit == 'oz':
        value_in_grams = value * GRAMS_PER_OUNCE_MASS
    elif from_unit == 'lb':
        value_in_grams = value * GRAMS_PER_POUND
    elif from_unit == 'mL':
        value_in_grams = value * GRAMS_PER_ML
    elif from_unit == 'L':
        value_in_grams = (value * ML_PER_LITER) * GRAMS_PER_ML
    elif from_unit == 'fl oz':
        value_in_grams = (value * ML_PER_FL_OUNCE) * GRAMS_PER_ML
    elif from_unit == 'fl dr':
        value_in_grams = (value * FL_OUNCES_PER_DRAM * ML_PER_FL_OUNCE) * GRAMS_PER_ML
    elif from_unit == 'gtts':
        value_in_grams = value / DROPS_PER_GRAM

    # Now, convert from grams to the target unit
    if to_unit == 'g':
        return value_in_grams
    elif to_unit == 'mg':
        return value_in_grams * 1000.0
    elif to_unit == 'kg':
        return value_in_grams / GRAMS_PER_KG
    elif to_unit == 'oz':
        return value_in_grams / GRAMS_PER_OUNCE_MASS
    elif to_unit == 'lb':
        return value_in_grams / GRAMS_PER_POUND
    elif to_unit == 'mL':
        return value_in_grams / GRAMS_PER_ML
    elif to_unit == 'L':
        return (value_in_grams / GRAMS_PER_ML) / ML_PER_LITER
    elif to_unit == 'fl oz':
        return (value_in_grams / GRAMS_PER_ML) / ML_PER_FL_OUNCE
    elif to_unit == 'fl dr':
        return ((value_in_grams / GRAMS_PER_ML) / ML_PER_FL_OUNCE) / (1.0 / FL_OUNCES_PER_DRAM)
    elif to_unit == 'gtts':
        return value_in_grams * DROPS_PER_GRAM

    return value  # Fallback for unknown units


class ReportPDF(FPDF):
    def __init__(self, orientation='P', unit='mm', format='Letter'):
        if FPDF is None:
            raise ImportError("The 'fpdf2' library is required for PDF export.")
        super().__init__(orientation, unit, format)
        self.report_title = "Formul8 Report"

    def header(self):
        # --- TILED WATERMARK LOGIC ---
        page_width = self.w
        page_height = self.h
        self.set_font('helvetica', 'B', 40)
        self.set_text_color(230, 230, 230)

        with self.local_context(fill_opacity=0.3):
            # RATIONALE: Using fixed spacing units creates a more uniform and predictable
            # grid pattern compared to fractional page dimensions.
            x_step = 75
            y_step = 60
            # Loop over an expanded area to ensure the rotated text covers the corners
            for y_pos in range(0, int(page_height) + y_step, y_step):
                for x_pos in range(0, int(page_width) + x_step, x_step):
                    with self.rotation(45, x=x_pos, y=y_pos):
                        self.text(x=x_pos, y=y_pos, text="Formul8")

        # --- ORIGINAL HEADER LOGIC ---
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