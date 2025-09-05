# formul8/utils.py
# General utility functions.

import os
import sys


def resource_path(relative_path):
    """ Get absolute path to resource, works for dev and for PyInstaller. """
    try:
        # PyInstaller creates a temp folder and stores path in _MEIPASS
        base_path = sys._MEIPASS
    except AttributeError:
        # In development, the base path is the project root (one level up from this file's directory)
        base_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))

    # Rationale: This now correctly joins from the project root to the 'assets' folder.
    return os.path.join(base_path, 'assets', relative_path)