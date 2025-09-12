# formul8/context_menu_handler.py
# A centralized handler for creating, positioning, and executing context menus.

from PyQt6.QtWidgets import QMenu
from PyQt6.QtGui import QCursor
from PyQt6.QtCore import QPoint, Qt

from .components import TweakDialog, CustomMessageBox


def handle_tree_context_menu(view, tree, position):
    """
    A single, centralized function to handle all right-click context menus for QTreeWidgets.
    It builds the menu based on the clicked item and connects actions to the appropriate
    handler methods provided by the calling view instance.

    Args:
        view: The instance of the parent view (e.g., self from IngredientManagementFrame).
        tree: The QTreeWidget instance that was clicked.
        position: The QPoint of the right-click.
    """
    item = tree.itemAt(position)
    if not item:
        return

    menu = QMenu(tree)

    # --- Menu for child items (ingredients within an accord) ---
    if item.parent():
        tweak_action = menu.addAction("Tweak Percentage...")

        # We define a nested function to handle the tweak logic.
        def _tweak_logic():
            accord_item = item.parent()
            accord_name = accord_item.data(0, Qt.ItemDataRole.UserRole)['name']

            # Child item text is like "    - IngredientName"
            ingredient_name = item.text(0).strip().lstrip('- ')

            # Percentage can be in different columns depending on the view
            percent_text = ""
            if tree.objectName() == "FormulationCreatorTree":
                percent_text = item.text(3)  # Percentage is in the 4th column
            elif tree.objectName() == "IngredientManagerTree":
                percent_text = item.text(1)  # Percentage is in the 2nd column

            try:
                current_percent = float(percent_text.strip().rstrip('%'))
            except (ValueError, IndexError):
                return  # Fail silently if text is not a valid percentage

            dialog = TweakDialog(ingredient_name, current_percent, view)
            if dialog.exec():
                new_percent = dialog.get_new_percentage()
                success = view.data_manager.tweak_accord_ingredient(accord_name, ingredient_name, new_percent)
                if success:
                    view.show_status_message(f"Accord '{accord_name}' tweaked successfully.")
                    # on_show is a generic way to call the view's refresh method
                    if hasattr(view, 'on_show'):
                        view.on_show()
                else:
                    CustomMessageBox.warning(view, "Tweak Error",
                                             "Could not apply tweak. The accord may have a total quantity of zero or no other ingredients to scale.")

        tweak_action.triggered.connect(_tweak_logic)

    # --- Menu for top-level items (ingredients or accords) ---
    else:
        # --- MODIFIED: This check is specific to the ingredient manager's workflow ---
        # It should not block the formulation creator's context menu.
        if view.__class__.__name__ == 'IngredientManagementFrame':
            if not view.selected_item_name:
                return

        item_data = item.data(0, Qt.ItemDataRole.UserRole)
        if not item_data: return

        # This relies on the view having set self.selected_item_type for the manager
        item_type = getattr(view, 'selected_item_type', item_data.get('type'))

        if item_type == 'raw' and hasattr(view, 'open_notes_window'):
            menu.addAction("Notes...").triggered.connect(view.open_notes_window)

        if hasattr(view, 'edit_selected_item_gui'):
            menu.addAction("Edit...").triggered.connect(view.edit_selected_item_gui)
        if hasattr(view, 'delete_item_gui'):
            menu.addAction("Delete").triggered.connect(view.delete_item_gui)

        # Special case for formulation creator's highlight feature
        if hasattr(view, 'set_highlight_color'):
            if menu.actions():
                menu.addSeparator()
            menu.addAction("Set Highlight Color").triggered.connect(view.set_highlight_color)
            menu.addAction("Clear Highlight").triggered.connect(view.clear_highlight)

    # --- Execute Menu with Dynamic Positioning ---
    if menu.actions():
        # Position the menu's bottom-left corner near the cursor
        menu_size = menu.sizeHint()
        cursor_pos = QCursor.pos()
        final_pos = QPoint(cursor_pos.x(), cursor_pos.y() - menu_size.height())
        menu.exec(final_pos)