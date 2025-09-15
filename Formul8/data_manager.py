# formul8/data_manager.py
# This is the "Model" of the application, handling all data operations via SQLite.

import json
import os
import shutil
import sqlite3
from datetime import datetime
from . import database
from .constants import (
    DEFAULT_SCENT_CATEGORIES, DEFAULT_SUPPLIERS, DEFAULT_BRANDS,
    DEFAULT_DILUENTS, DEFAULT_SCENT_PROFILE_COLORS
)
# --- RATIONALE: We need the ReportPDF utility for PDF exports ---
from .utils import ReportPDF, convert_unit


class DataManager:
    """ Manages loading, accessing, and saving of all application data via an SQLite database. """

    def __init__(self):
        self.conn = database.initialize_database()
        self._ensure_default_settings()

    def _ensure_default_settings(self):
        """Ensures that default settings are present in the database."""
        defaults = {
            'scent_categories': DEFAULT_SCENT_CATEGORIES,
            'suppliers': DEFAULT_SUPPLIERS,
            'brands': DEFAULT_BRANDS,
            'diluents': DEFAULT_DILUENTS,
            'default_formulation_view': 'grid',
            'scent_profile_colors': DEFAULT_SCENT_PROFILE_COLORS
        }
        for key, value in defaults.items():
            if self.get_setting(key) is None:
                self.save_setting(key, value)

    def get_all_ingredients(self):
        """Retrieves all ingredients from the database, sorted by most recently added."""
        try:
            cur = self.conn.cursor()
            cur.execute("SELECT * FROM ingredients ORDER BY date_added DESC")
            return [dict(row) for row in cur.fetchall()]
        except sqlite3.Error as e:
            print(f"Database error getting ingredients: {e}")
            return []

    def get_all_formulations(self):
        """Retrieves all formulations, including their entries."""
        formulations = {}
        try:
            cur = self.conn.cursor()
            cur.execute("SELECT * FROM formulations")
            for row in cur.fetchall():
                formulations[row['name']] = dict(row)
                formulations[row['name']]['entries'] = []

            cur.execute("SELECT * FROM formulation_entries")
            for row in cur.fetchall():
                form_name = row['formulation_name']
                if form_name in formulations:
                    formulations[form_name]['entries'].append(dict(row))

            return list(formulations.values())
        except sqlite3.Error as e:
            print(f"Database error getting formulations: {e}")
            return []

    def save_data(self):
        """Commits any pending transaction. Most operations now commit themselves."""
        if self.conn:
            self.conn.commit()

    def get_ingredient_by_name(self, name):
        if not name: return None
        try:
            cur = self.conn.cursor()
            cur.execute("SELECT * FROM ingredients WHERE lower(name) = ?", (name.lower(),))
            row = cur.fetchone()
            return dict(row) if row else None
        except sqlite3.Error as e:
            print(f"Database error in get_ingredient_by_name: {e}")
            return None

    def get_formulation_by_name(self, name):
        if not name: return None
        try:
            cur = self.conn.cursor()
            cur.execute("SELECT * FROM formulations WHERE lower(name) = ?", (name.lower(),))
            form_row = cur.fetchone()
            if not form_row:
                return None

            formulation = dict(form_row)
            formulation['entries'] = []

            cur.execute("SELECT * FROM formulation_entries WHERE formulation_name = ?", (formulation['name'],))
            entries = cur.fetchall()
            formulation['entries'] = [dict(entry) for entry in entries]
            return formulation
        except sqlite3.Error as e:
            print(f"Database error in get_formulation_by_name: {e}")
            return None

    def save_ingredient(self, ingredient_data):
        """Inserts or updates an ingredient, handling potential name changes."""
        original_name = ingredient_data.get('original_name', ingredient_data['name'])
        is_update = self.get_ingredient_by_name(original_name) is not None

        try:
            cur = self.conn.cursor()
            if is_update:
                # When updating, we don't change the date_added
                cur.execute("""
                    UPDATE ingredients SET
                    name=?, type=?, concentration=?, diluent=?, brand=?, chemical_name=?, vendor=?, cost=?,
                    note_type=?, primary_category=?, secondary_category=?, notes=?
                    WHERE name=?
                """, (
                    ingredient_data.get('name'), ingredient_data.get('type'),
                    ingredient_data.get('concentration'), ingredient_data.get('diluent'),
                    ingredient_data.get('brand'), ingredient_data.get('chemical_name'),
                    ingredient_data.get('vendor'), ingredient_data.get('cost'),
                    ingredient_data.get('note_type'), ingredient_data.get('primary_category'),
                    ingredient_data.get('secondary_category'), ingredient_data.get('notes'),
                    original_name
                ))
            else:
                # When inserting, we add the current timestamp
                now_iso = datetime.now().isoformat()
                cur.execute("""
                    INSERT INTO ingredients (name, type, concentration, diluent, brand, chemical_name, vendor, cost, note_type, primary_category, secondary_category, notes, date_added)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    ingredient_data.get('name'), ingredient_data.get('type'),
                    ingredient_data.get('concentration'), ingredient_data.get('diluent'),
                    ingredient_data.get('brand'), ingredient_data.get('chemical_name'),
                    ingredient_data.get('vendor'), ingredient_data.get('cost'),
                    ingredient_data.get('note_type'), ingredient_data.get('primary_category'),
                    ingredient_data.get('secondary_category'), ingredient_data.get('notes'),
                    now_iso
                ))
            self.conn.commit()
            return True
        except sqlite3.Error as e:
            print(f"Database error saving ingredient: {e}")
            return False

    def save_formulation(self, formula_data):
        """Saves a complete formulation, overwriting if it exists."""
        name = formula_data['name']
        try:
            cur = self.conn.cursor()
            cur.execute("INSERT OR REPLACE INTO formulations (name, unit, is_accord) VALUES (?, ?, ?)",
                        (name, formula_data.get('unit'), formula_data.get('is_accord', False)))

            cur.execute("DELETE FROM formulation_entries WHERE formulation_name=?", (name,))

            for entry in formula_data.get('entries', []):
                cur.execute("""
                    INSERT INTO formulation_entries (formulation_name, ingredient_name, quantity, unit, highlight_color)
                    VALUES (?, ?, ?, ?, ?)
                """, (
                    name, entry['ingredient_name'], entry['quantity'], entry['unit'], entry['highlight_color']
                ))
            self.conn.commit()
            return True
        except sqlite3.Error as e:
            print(f"Database error saving formulation: {e}")
            return False

    def delete_ingredient(self, name):
        """Deletes an ingredient by name."""
        try:
            cur = self.conn.cursor()
            cur.execute("DELETE FROM ingredients WHERE name=?", (name,))
            self.conn.commit()
            return cur.rowcount > 0
        except sqlite3.Error as e:
            print(f"Database error deleting ingredient: {e}")
            return False

    def delete_formulation(self, name):
        """Deletes a formulation and its corresponding accord-ingredient if it exists."""
        formula = self.get_formulation_by_name(name)
        if not formula:
            return False

        try:
            cur = self.conn.cursor()
            if formula.get('is_accord'):
                self.delete_ingredient(name)

            cur.execute("DELETE FROM formulations WHERE name=?", (name,))
            self.conn.commit()
            return cur.rowcount > 0
        except sqlite3.Error as e:
            print(f"Database error deleting formulation: {e}")
            return False

    def create_accord_as_ingredient(self, formulation_obj, note_type, primary_category, secondary_category):
        """
        Creates or updates an ingredient entry for a given accord formulation.
        """
        self.calculate_formulation_totals(formulation_obj)
        total_cost = formulation_obj.get('calculated_total_cost', 0.0)
        total_grams = formulation_obj.get('calculated_total_grams', 0.0)
        cost_per_gram = (total_cost / total_grams) if total_grams > 0 else 0

        accord_ingredient_data = {
            "name": formulation_obj['name'],
            "type": "formulation_accord",
            "concentration": 100.0,
            "cost": cost_per_gram,
            "note_type": note_type,
            "primary_category": primary_category,
            "secondary_category": secondary_category,
            "diluent": "", "brand": "", "chemical_name": "", "vendor": "",
            "notes": "This is a user-created accord."
        }
        self.save_ingredient(accord_ingredient_data)

    def calculate_formulation_totals(self, formulation):
        concentrate_grams, solvent_grams, total_cost = 0.0, 0.0, 0.0
        for entry in formulation.get('entries', []):
            quantity = entry.get('quantity', 0.0)
            ing = self.get_ingredient_by_name(entry.get('ingredient_name'))
            if not ing:
                entry['cost'] = 0.0
                continue

            if ing.get('type', 'raw') in ['formulation_accord', 'premade_accord']:
                entry['cost'] = quantity * ing.get('cost', 0.0)
                total_cost += entry['cost']
                concentrate_grams += quantity
            else:  # It's a raw material
                eff_cost = ing.get('cost', 0.0)
                conc = ing.get('concentration', 100.0)
                if conc < 100.0:
                    eff_cost = (ing.get('cost', 0.0) / conc) * 100.0 if conc > 0 else 0
                entry['cost'] = quantity * eff_cost
                total_cost += entry['cost']
                if ing.get('note_type') == 'Solvent':
                    solvent_grams += quantity
                else:
                    concentrate_grams += quantity
        total_grams = concentrate_grams + solvent_grams
        for entry in formulation.get('entries', []):
            quantity = entry.get('quantity', 0.0)
            ing = self.get_ingredient_by_name(entry.get('ingredient_name'))
            if ing and ing.get('note_type') == 'Solvent':
                entry['percentage'] = (quantity / total_grams) * 100 if total_grams > 0 else 0
            else:
                entry['percentage'] = (quantity / concentrate_grams) * 100 if concentrate_grams > 0 else 0
        formulation.update({
            'calculated_concentrate_grams': concentrate_grams,
            'calculated_solvent_grams': solvent_grams,
            'calculated_total_grams': total_grams,
            'calculated_total_cost': total_cost,
            'calculated_concentrate_strength': (concentrate_grams / total_grams) * 100 if total_grams > 0 else 0
        })

    def scale_formulation(self, original_formula, new_name, method, value):
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
            return None
        new_entries = []
        for entry in original_formula.get('entries', []):
            if method == "Normalize Concentrate to 100g":
                ing = self.get_ingredient_by_name(entry.get('ingredient_name'))
                if ing and ing.get('note_type') == 'Solvent':
                    continue
            new_entry = entry.copy()
            new_entry['quantity'] = new_entry.get('quantity', 0.0) * scaling_factor
            new_entries.append(new_entry)
        new_formula = {
            "name": new_name, "unit": "gram", "entries": new_entries,
            "is_accord": original_formula.get('is_accord', False)
        }
        self.save_formulation(new_formula)
        return new_formula

    def tweak_accord_ingredient(self, accord_name, ingredient_name, new_percentage):
        """
        Adjusts an ingredient's percentage in an accord and proportionally scales the others.
        """
        accord = self.get_formulation_by_name(accord_name)
        if not accord or not accord['is_accord']:
            return False

        self.calculate_formulation_totals(accord)

        target_entry = None
        other_entries = []
        for e in accord['entries']:
            if e['ingredient_name'].lower() == ingredient_name.lower():
                target_entry = e
            else:
                other_entries.append(e)

        if not target_entry or new_percentage < 0 or new_percentage > 100:
            return False

        other_total_percent = sum(e.get('percentage', 0.0) for e in other_entries)
        if other_total_percent <= 0 and len(other_entries) > 0:
            remaining_percent = 100.0 - new_percentage
            percent_per_other = remaining_percent / len(other_entries)
            for entry in other_entries:
                entry['percentage'] = percent_per_other
        elif other_total_percent > 0:
            remaining_percent = 100.0 - new_percentage
            scale_factor = remaining_percent / other_total_percent
            for entry in other_entries:
                entry['percentage'] *= scale_factor

        target_entry['percentage'] = new_percentage

        original_concentrate_weight = accord.get('calculated_concentrate_grams', 0.0)
        if original_concentrate_weight <= 0:
            original_concentrate_weight = 100.0

        for entry in accord['entries']:
            entry['quantity'] = (entry.get('percentage', 0.0) / 100.0) * original_concentrate_weight

        self.save_formulation(accord)

        accord_ing = self.get_ingredient_by_name(accord_name)
        if accord_ing:
            self.create_accord_as_ingredient(
                accord,
                accord_ing.get('note_type'),
                accord_ing.get('primary_category'),
                accord_ing.get('secondary_category')
            )
        return True

    def get_setting(self, key):
        try:
            cur = self.conn.cursor()
            cur.execute("SELECT value FROM settings WHERE key=?", (key,))
            row = cur.fetchone()
            return json.loads(row['value']) if row else None
        except (sqlite3.Error, json.JSONDecodeError) as e:
            print(f"Database error getting setting '{key}': {e}")
            return None

    def save_setting(self, key, value):
        try:
            cur = self.conn.cursor()
            cur.execute("INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)", (key, json.dumps(value)))
            self.conn.commit()
        except sqlite3.Error as e:
            print(f"Database error saving setting '{key}': {e}")

    def add_list_item(self, list_key, item_value):
        """Adds a new unique item to a specified list in settings."""
        item_value = item_value.strip()
        if not item_value:
            return False

        current_list = self.get_setting(list_key) or []
        if any(existing.lower() == item_value.lower() for existing in current_list):
            return False

        current_list.append(item_value)
        self.save_setting(list_key, current_list)
        return True

    # --- EXPORT FUNCTIONALITY ---

    def export_ingredients_to_txt(self, path):
        """Exports the entire ingredient library to a formatted text file."""
        try:
            ingredients = sorted(self.get_all_ingredients(), key=lambda i: i['name'].lower())
            with open(path, 'w', encoding='utf-8') as f:
                f.write(f"Formul8 Ingredient Library Export\n")
                f.write(f"Exported on: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n")
                f.write("=" * 80 + "\n\n")

                # RATIONALE: Using f-string padding creates clean, aligned columns for maximum readability.
                f.write(f"{'Name':<35} {'Type':<20} {'Cost/g':>10} {'Note':<10}\n")
                f.write(f"{'-' * 35} {'-' * 20} {'-' * 10} {'-' * 10}\n")

                for ing in ingredients:
                    name = ing.get('name', 'N/A')
                    ing_type = ing.get('type', 'raw').replace('_', ' ').title()
                    cost = f"${ing.get('cost', 0.0):.2f}"
                    note = ing.get('note_type', 'N/A')
                    f.write(f"{name:<35} {ing_type:<20} {cost:>10} {note:<10}\n")

            return True, None
        except Exception as e:
            return False, str(e)

    def export_formula_to_txt(self, formula, path):
        """Exports a single formulation to a formatted text file."""
        try:
            with open(path, 'w', encoding='utf-8') as f:
                f.write(f"Formulation: {formula.get('name', 'Untitled')}\n")
                f.write(f"Exported on: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n")
                f.write("=" * 80 + "\n\n")

                f.write("[Ingredients]\n")
                f.write(f"{'Name':<35} {'Quantity (g)':>15} {'% in Conc.':>15} {'Cost':>12}\n")
                f.write(f"{'-' * 35} {'-' * 15} {'-' * 15} {'-' * 12}\n")

                # RATIONALE: We must recalculate totals here to ensure the export reflects the exact state.
                self.calculate_formulation_totals(formula)
                for entry in sorted(formula.get('entries', []), key=lambda x: x['ingredient_name']):
                    name = entry.get('ingredient_name', 'N/A')
                    qty = f"{entry.get('quantity', 0.0):.4f}"
                    percent = f"{entry.get('percentage', 0.0):.2f}%"
                    cost = f"${entry.get('cost', 0.0):.2f}"
                    f.write(f"{name:<35} {qty:>15} {percent:>15} {cost:>12}\n")

                f.write("\n" + "=" * 80 + "\n")
                f.write("[Totals]\n")
                f.write(f"{'Concentrate:':<25} {formula.get('calculated_concentrate_grams', 0.0):.2f}g\n")
                f.write(f"{'Solvent:':<25} {formula.get('calculated_solvent_grams', 0.0):.2f}g\n")
                f.write(f"{'Total Weight:':<25} {formula.get('calculated_total_grams', 0.0):.2f}g\n")
                f.write(f"{'Concentrate Strength:':<25} {formula.get('calculated_concentrate_strength', 0.0):.2f}%\n")
                f.write(f"{'Total Cost:':<25} ${formula.get('calculated_total_cost', 0.0):.2f}\n")

            return True, None
        except Exception as e:
            return False, str(e)

    def export_ingredients_to_pdf(self, path):
        """Exports the entire ingredient library to a PDF file."""
        try:
            if ReportPDF is None:
                return False, "PDF export library (fpdf2) is not installed."

            pdf = ReportPDF()
            pdf.set_report_title("Ingredient Library")
            pdf.add_page()
            pdf.set_font("helvetica", size=10)

            pdf.set_font("helvetica", "B", 10)
            pdf.set_fill_color(240, 240, 240)
            pdf.set_text_color(0, 0, 0)
            pdf.cell(80, 8, "Name", border=1, fill=True, align='C')
            pdf.cell(40, 8, "Type", border=1, fill=True, align='C')
            pdf.cell(25, 8, "Cost/g", border=1, fill=True, align='C')
            pdf.cell(45, 8, "Note / Category", border=1, fill=True, align='C')
            pdf.ln()

            pdf.set_font("helvetica", size=9)
            pdf.set_text_color(0, 0, 0)
            ingredients = sorted(self.get_all_ingredients(), key=lambda i: i['name'].lower())

            for ing in ingredients:
                if pdf.get_y() > 250:
                    pdf.add_page()
                    pdf.set_font("helvetica", "B", 10)
                    pdf.cell(80, 8, "Name", border=1, fill=True, align='C')
                    pdf.cell(40, 8, "Type", border=1, fill=True, align='C')
                    pdf.cell(25, 8, "Cost/g", border=1, fill=True, align='C')
                    pdf.cell(45, 8, "Note / Category", border=1, fill=True, align='C')
                    pdf.ln()
                    pdf.set_font("helvetica", size=9)

                note_cat = f"{ing.get('note_type', '')} / {ing.get('primary_category', '')}"

                # --- FIX: Robust row drawing logic ---
                y_before = pdf.get_y()
                pdf.multi_cell(80, 6, ing.get('name', ''), border='L', align='L')
                y_after_multi_cell = pdf.get_y()

                pdf.set_y(y_before)  # Return to the original Y position
                pdf.set_x(pdf.l_margin + 80)  # Explicitly set X for the next column

                # Draw the rest of the cells using the calculated height of the multi_cell
                cell_height = y_after_multi_cell - y_before
                pdf.cell(40, cell_height, ing.get('type', 'raw').replace('_', ' ').title(), border='L', align='C')
                pdf.cell(25, cell_height, f"${ing.get('cost', 0.0):.2f}", border='L', align='R')
                pdf.multi_cell(45, 6, note_cat, border='LR', align='C', new_x="LMARGIN", new_y="NEXT")

            pdf.output(path)
            return True, None
        except Exception as e:
            return False, str(e)

    def export_formula_to_pdf(self, formula, path):
        """Exports a single formulation to a PDF file."""
        try:
            if ReportPDF is None:
                return False, "PDF export library (fpdf2) is not installed."

            pdf = ReportPDF()
            pdf.set_report_title(f"Formulation: {formula.get('name', 'Untitled')}")
            pdf.add_page()

            pdf.set_font("helvetica", "B", 12)
            pdf.cell(0, 10, "Summary", new_x="LMARGIN", new_y="NEXT")
            self.calculate_formulation_totals(formula)
            summary_data = {
                "Concentrate Weight:": f"{formula.get('calculated_concentrate_grams', 0.0):.2f}g",
                "Solvent Weight:": f"{formula.get('calculated_solvent_grams', 0.0):.2f}g",
                "Total Weight:": f"{formula.get('calculated_total_grams', 0.0):.2f}g",
                "Concentrate Strength:": f"{formula.get('calculated_concentrate_strength', 0.0):.2f}%",
                "Total Cost:": f"${formula.get('calculated_total_cost', 0.0):.2f}"
            }
            pdf.set_font("helvetica", size=10)
            for label, value in summary_data.items():
                pdf.set_font("helvetica", "B")
                pdf.cell(50, 6, label)
                pdf.set_font("helvetica", "")
                pdf.cell(50, 6, value, new_x="LMARGIN", new_y="NEXT")
            pdf.ln(5)

            pdf.set_font("helvetica", "B", 12)
            pdf.cell(0, 10, "Ingredients", new_x="LMARGIN", new_y="NEXT")
            pdf.set_font("helvetica", "B", 10)
            pdf.set_fill_color(240, 240, 240)
            pdf.set_text_color(0, 0, 0)
            pdf.cell(90, 8, "Name", border=1, fill=True, align='C')
            pdf.cell(30, 8, "Qty (g)", border=1, fill=True, align='C')
            pdf.cell(30, 8, "% in Conc.", border=1, fill=True, align='C')
            pdf.cell(40, 8, "Cost", border=1, fill=True, align='C')
            pdf.ln()

            pdf.set_font("helvetica", size=9)
            pdf.set_text_color(0, 0, 0)
            for entry in sorted(formula.get('entries', []), key=lambda x: x['ingredient_name']):
                if pdf.get_y() > 250:
                    pdf.add_page()
                    pdf.set_font("helvetica", "B", 10)
                    pdf.cell(90, 8, "Name", border=1, fill=True, align='C')
                    pdf.cell(30, 8, "Qty (g)", border=1, fill=True, align='C')
                    pdf.cell(30, 8, "% in Conc.", border=1, fill=True, align='C')
                    pdf.cell(40, 8, "Cost", border=1, fill=True, align='C')
                    pdf.ln()
                    pdf.set_font("helvetica", size=9)

                # --- FIX: Robust row drawing logic ---
                y_before = pdf.get_y()
                # Draw the name cell, which might wrap
                pdf.multi_cell(90, 6, entry.get('ingredient_name', ''), border='L', align='L')
                y_after_multi_cell = pdf.get_y()

                # Return to the original Y position for this row
                pdf.set_y(y_before)
                # Explicitly set X for the start of the second column
                pdf.set_x(pdf.l_margin + 90)

                # Calculate the height the name cell occupied
                cell_height = y_after_multi_cell - y_before

                # Draw the remaining cells, all with the same calculated height
                pdf.cell(30, cell_height, f"{entry.get('quantity', 0.0):.4f}", border='L', align='R')
                pdf.cell(30, cell_height, f"{entry.get('percentage', 0.0):.2f}%", border='L', align='R')
                pdf.cell(40, cell_height, f"${entry.get('cost', 0.0):.2f}", border='LR', align='R')
                pdf.ln(cell_height)  # Move down by the height of the row

            pdf.cell(190, 0, "", border="T")

            pdf.output(path)
            return True, None
        except Exception as e:
            return False, str(e)