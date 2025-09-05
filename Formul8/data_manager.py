# formul8/data_manager.py
# This is the "Model" of the application, handling all data operations.

import json
import os
import shutil
from datetime import datetime
from .utils import resource_path
from .constants import (
    DEFAULT_SCENT_CATEGORIES, DEFAULT_SUPPLIERS, DEFAULT_BRANDS,
    DEFAULT_DILUENTS, DEFAULT_SCENT_PROFILE_COLORS
)

# --- PDF Export Library ---
from fpdf import FPDF
from PyQt6.QtWidgets import QFileDialog, QMessageBox


# Helper function to create a persistent data path in the user's AppData folder
def get_user_data_path(filename="perfume_data.json"):
    """
    Returns the full path to the user's data file.
    Creates the application's data directory if it doesn't exist.
    Path will be like: C:/Users/YourUser/AppData/Roaming/Formul8/perfume_data.json
    """
    app_name = "Formul8"
    # Get the AppData\Roaming directory
    app_data_dir = os.path.join(os.getenv('APPDATA'), app_name)

    # Create the directory if it doesn't exist
    os.makedirs(app_data_dir, exist_ok=True)

    return os.path.join(app_data_dir, filename)


class DataManager:
    """ Manages loading, accessing, and saving of all application data. """

    def __init__(self, data_filename="perfume_data.json"):
        # Path for user's saved data (read/write)
        self.data_file = get_user_data_path(data_filename)
        # Path for the initial/bundled data (read-only)
        self.bundle_data_file = resource_path(f"assets/{data_filename}")
        self.data = self._load_data()

    def _load_data(self):
        """
        Loads data from the user's persistent file. If it doesn't exist,
        it copies and loads the initial data from the application bundle.
        """
        data = {}

        # 1. Try to load the user's saved data file first.
        if os.path.exists(self.data_file):
            try:
                with open(self.data_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
            except (json.JSONDecodeError, IOError):
                print(f"Warning: Could not read {self.data_file}. A backup will be created and a fresh file used.")
                # If the user file is corrupt, back it up and proceed to load from bundle
                try:
                    shutil.copy(self.data_file, f"{self.data_file}.bak")
                except IOError:
                    pass  # Can't even back it up, just overwrite
                data = {}  # Reset data to ensure we load from bundle

        # 2. If no user data was loaded, load the initial data from the bundle.
        if not data:
            print("No user data found. Loading initial data from bundle.")
            try:
                with open(self.bundle_data_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                # After loading initial data, save it immediately to the user's path
                # This creates the user's own copy for future use.
                self._save_data_to_path(self.data_file, data)
            except (FileNotFoundError, json.JSONDecodeError):
                print(f"Warning: Could not read bundled data file {self.bundle_data_file}.")
                data = {}  # Fallback to empty if even bundled data is missing

        # Ensure top-level keys exist
        data.setdefault('ingredients', [])
        data.setdefault('formulations', [])
        data.setdefault('settings', {})

        # Ensure default settings exist
        settings = data['settings']
        settings.setdefault('scent_categories', DEFAULT_SCENT_CATEGORIES)
        settings.setdefault('suppliers', DEFAULT_SUPPLIERS)
        settings.setdefault('brands', DEFAULT_BRANDS)
        settings.setdefault('diluents', DEFAULT_DILUENTS)
        settings.setdefault('default_formulation_view', 'grid')
        settings.setdefault('scent_profile_colors', DEFAULT_SCENT_PROFILE_COLORS)

        # Data integrity checks for older data formats
        for ing in data['ingredients']:
            ing.setdefault('cost', 0.0)
            ing.setdefault('note_type', 'Other')
            ing.setdefault('notes', '')
            ing.setdefault('diluent', '')
        for form in data.get('formulations', []):
            form.setdefault('calculated_total_cost', 0.0)
            for entry in form.get('entries', []):
                entry.setdefault('unit', form.get('unit', 'gram'))
                entry.setdefault('highlight_color', None)

        return data

    def _save_data_to_path(self, path, data_to_save):
        """Saves a data dictionary to a specific file path."""
        try:
            with open(path, 'w', encoding='utf-8') as f:
                json.dump(data_to_save, f, indent=4)
            return True
        except IOError as e:
            print(f"FATAL: Could not save data to {path}. Error: {e}")
            return False

    def save_data(self):
        """ Saves the current data dictionary to the user's persistent data file. """
        self._save_data_to_path(self.data_file, self.data)

    def get_ingredient_by_name(self, name):
        if not name:
            return None
        for ing in self.data['ingredients']:
            if ing.get('name', '').lower() == name.lower():
                return ing
        return None

    def get_formulation_by_name(self, name):
        if not name:
            return None
        for form in self.data['formulations']:
            if form.get('name', '').lower() == name.lower():
                return form
        return None

    def calculate_formulation_totals(self, formulation):
        """ Calculates totals for a formulation object and updates it in place. """
        concentrate_grams, solvent_grams, total_cost = 0.0, 0.0, 0.0

        for entry in formulation.get('entries', []):
            ing = self.get_ingredient_by_name(entry.get('ingredient_name'))
            if not ing:
                continue

            quantity = entry.get('quantity', 0.0)
            # Cost per gram of pure material
            eff_cost = ing.get('cost', 0.0)
            if ing.get('concentration', 100.0) < 100.0:
                eff_cost = (ing.get('cost', 0.0) / ing.get('concentration', 100.0)) * 100.0

            entry['cost'] = quantity * eff_cost
            total_cost += entry['cost']

            if ing.get('note_type') == 'Solvent':
                solvent_grams += quantity
            else:
                concentrate_grams += quantity

        total_grams = concentrate_grams + solvent_grams

        for entry in formulation.get('entries', []):
            ing = self.get_ingredient_by_name(entry.get('ingredient_name'))
            if not ing:
                continue

            quantity = entry.get('quantity', 0.0)
            if ing.get('note_type') == 'Solvent':
                # For solvents, calculate percentage of the total formula
                entry['percentage'] = (quantity / total_grams) * 100 if total_grams > 0 else 0
            else:
                # For aromatics, calculate percentage within the concentrate
                entry['percentage'] = (quantity / concentrate_grams) * 100 if concentrate_grams > 0 else 0

        formulation.update({
            'calculated_concentrate_grams': concentrate_grams,
            'calculated_solvent_grams': solvent_grams,
            'calculated_total_grams': total_grams,
            'calculated_total_cost': total_cost,
            'calculated_concentrate_strength': (concentrate_grams / total_grams) * 100 if total_grams > 0 else 0
        })

    def scale_formulation(self, original_formula, new_name, method, value):
        """
        Creates a new, scaled formulation based on an original.

        :param original_formula: The formula dictionary to scale.
        :param new_name: The name for the new scaled formula.
        :param method: The string name of the scaling method.
        :param value: The numerical value for the scaling operation.
        :return: The new formula dictionary if successful, None otherwise.
        """
        self.calculate_formulation_totals(original_formula)
        current_concentrate = original_formula.get('calculated_concentrate_grams', 0.0)
        current_total = original_formula.get('calculated_total_grams', 0.0)
        scaling_factor = 1.0

        if method == "By Factor":
            if value <= 0: return None
            scaling_factor = value
        elif method == "By Percentage Factor":
            if value <= 0: return None
            scaling_factor = value / 100.0
        elif method == "To New Concentrate Weight":
            if current_concentrate == 0: return None
            scaling_factor = value / current_concentrate
        elif method == "To New Total Weight":
            if current_total == 0: return None
            scaling_factor = value / current_total
        elif method == "Normalize Concentrate to 100g":
            if current_concentrate == 0: return None
            scaling_factor = 100.0 / current_concentrate
        else:
            return None  # Unknown method

        new_entries = []
        for entry in original_formula.get('entries', []):
            # For "Normalize", we skip solvents entirely, creating a pure compound.
            if method == "Normalize Concentrate to 100g":
                ing = self.get_ingredient_by_name(entry.get('ingredient_name'))
                if ing and ing.get('note_type') == 'Solvent':
                    continue

            new_entry = entry.copy()
            new_entry['quantity'] = new_entry.get('quantity', 0.0) * scaling_factor
            new_entries.append(new_entry)

        new_formula = {
            "name": new_name,
            "unit": "gram",
            "entries": new_entries
        }

        self.data['formulations'].append(new_formula)
        return new_formula

    def export_ingredients_to_txt(self, filepath):
        """Exports the full ingredient library to a formatted text file."""
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write("Formul8 Ingredient Library Export\n")
                f.write(f"Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write("=" * 40 + "\n\n")

                for ing in sorted(self.data['ingredients'], key=lambda x: x.get('name', '')):
                    f.write(f"Ingredient: {ing.get('name', 'N/A')}\n")
                    f.write(f"  - Concentration: {ing.get('concentration', 100.0):.2f}%\n")
                    f.write(f"  - Cost per Gram: ${ing.get('cost', 0.0):.2f}\n")
                    f.write(f"  - Note Type: {ing.get('note_type', 'N/A')}\n")
                    f.write(f"  - Categories: {ing.get('primary_category', '')}, {ing.get('secondary_category', '')}\n")
                    f.write(f"  - Supplier: {ing.get('supplier', '')}\n")
                    f.write(f"  - Notes: {ing.get('notes', '')}\n\n")
            return True, None
        except Exception as e:
            return False, str(e)

    def export_ingredients_to_pdf(self, filepath):
        """Exports the full ingredient library to a PDF file."""
        try:
            pdf = FPDF()
            pdf.add_page()
            pdf.set_font("Helvetica", size=16, style='B')
            pdf.cell(0, 10, "Ingredient Library", ln=True, align='C')
            pdf.set_font("Helvetica", size=8)
            pdf.cell(0, 5, f"Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", ln=True, align='C')
            pdf.ln(10)

            pdf.set_font("Helvetica", size=10, style='B')
            col_widths = [50, 20, 20, 20, 50]
            headers = ['Ingredient', 'Conc.', 'Note', 'Cost/g', 'Categories']
            for header, width in zip(headers, col_widths):
                pdf.cell(width, 7, header, border=1, align='C')
            pdf.ln()

            pdf.set_font("Helvetica", size=9)
            for ing in sorted(self.data['ingredients'], key=lambda x: x.get('name', '')):
                cats = f"{ing.get('primary_category', '')}, {ing.get('secondary_category', '')}".strip(', ')
                row = [
                    ing.get('name', ''),
                    f"{ing.get('concentration', 100.0):.1f}%",
                    ing.get('note_type', ''),
                    f"${ing.get('cost', 0.0):.2f}",
                    cats
                ]
                for item, width in zip(row, col_widths):
                    pdf.cell(width, 6, str(item), border=1)
                pdf.ln()

            pdf.output(filepath)
            return True, None
        except Exception as e:
            return False, str(e)

    def export_formula_to_txt(self, formula, filepath):
        """Exports a single formula to a formatted text file."""
        try:
            self.calculate_formulation_totals(formula)  # Ensure totals are fresh
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(f"Formulation: {formula.get('name', 'N/A')}\n")
                f.write(f"Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write("=" * 40 + "\n")
                f.write(f"Total Weight: {formula.get('calculated_total_grams', 0.0):.2f}g\n")
                f.write(f"Concentrate Weight: {formula.get('calculated_concentrate_grams', 0.0):.2f}g\n")
                f.write(f"Solvent Weight: {formula.get('calculated_solvent_grams', 0.0):.2f}g\n")
                f.write(f"Concentrate Strength: {formula.get('calculated_concentrate_strength', 0.0):.2f}%\n")
                f.write(f"Total Cost: ${formula.get('calculated_total_cost', 0.0):.2f}\n")
                f.write("-" * 40 + "\n\n")

                f.write(f"{'Ingredient':<30} {'Qty (g)':>10} {'% in Conc.':>12} {'Cost':>10}\n")
                f.write(f"{'-' * 30} {'-' * 10} {'-' * 12} {'-' * 10}\n")

                for entry in sorted(formula['entries'], key=lambda x: x['ingredient_name']):
                    ing = self.get_ingredient_by_name(entry['ingredient_name'])
                    percent_str = f"{entry.get('percentage', 0.0):.2f}%" if ing.get('note_type') != 'Solvent' else "N/A"

                    f.write(
                        f"{entry['ingredient_name']:<30} {entry.get('quantity', 0.0):>10.4f} {percent_str:>12} ${entry.get('cost', 0.0):>9.2f}\n")
            return True, None
        except Exception as e:
            return False, str(e)

    def export_formula_to_pdf(self, formula, filepath):
        """Exports a single formula to a PDF file."""
        try:
            self.calculate_formulation_totals(formula)  # Ensure totals are fresh
            pdf = FPDF()
            pdf.add_page()

            # Title
            pdf.set_font("Helvetica", size=20, style='B')
            pdf.cell(0, 10, f"Formulation: {formula.get('name', 'N/A')}", ln=True, align='C')
            pdf.ln(5)

            # Summary Box
            pdf.set_font("Helvetica", size=10)
            summary_text = (
                f"Total Weight: {formula.get('calculated_total_grams', 0.0):.2f}g\n"
                f"Concentrate Weight: {formula.get('calculated_concentrate_grams', 0.0):.2f}g\n"
                f"Concentrate Strength: {formula.get('calculated_concentrate_strength', 0.0):.2f}%\n"
                f"Total Cost: ${formula.get('calculated_total_cost', 0.0):.2f}"
            )
            pdf.multi_cell(0, 6, summary_text, border=1, align='L')
            pdf.ln(10)

            # Table Header
            pdf.set_font("Helvetica", size=10, style='B')
            col_widths = [80, 30, 30, 30]
            headers = ['Ingredient', 'Quantity (g)', '% in Conc.', 'Cost']
            for header, width in zip(headers, col_widths):
                pdf.cell(width, 7, header, border=1, align='C')
            pdf.ln()

            # Table Rows
            pdf.set_font("Helvetica", size=9)
            for entry in sorted(formula['entries'], key=lambda x: x['ingredient_name']):
                ing = self.get_ingredient_by_name(entry['ingredient_name'])
                percent_str = f"{entry.get('percentage', 0.0):.2f}%" if ing.get('note_type') != 'Solvent' else "N/A"
                row = [
                    entry['ingredient_name'],
                    f"{entry.get('quantity', 0.0):.4f}",
                    percent_str,
                    f"${entry.get('cost', 0.0):.2f}"
                ]
                pdf.cell(col_widths[0], 6, row[0], border=1)
                pdf.cell(col_widths[1], 6, row[1], border=1, align='R')
                pdf.cell(col_widths[2], 6, row[2], border=1, align='R')
                pdf.cell(col_widths[3], 6, row[3], border=1, align='R')
                pdf.ln()

            pdf.output(filepath)
            return True, None
        except Exception as e:
            return False, str(e)