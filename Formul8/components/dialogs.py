# formul8/components/dialogs.py
# Contains all custom QDialog subclasses for the application.

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, QDialog,
    QDialogButtonBox, QColorDialog, QInputDialog, QStyle, QRadioButton,
    QGroupBox, QGridLayout, QComboBox, QDoubleSpinBox
)
from PyQt6.QtGui import QMouseEvent, QCloseEvent, QColor
from PyQt6.QtCore import Qt, pyqtSignal, QPropertyAnimation

from ..constants import NOTE_TYPES, DEFAULT_SCENT_CATEGORIES
from .widgets import CustomTitleBar


# --- Animated Custom Dialogs ---
class CustomDialog(QDialog):
    closing = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.Dialog)
        self.setWindowModality(Qt.WindowModality.ApplicationModal)
        self._animation = None
        self._is_closing = False

        self.root_layout = QVBoxLayout(self)
        self.root_layout.setContentsMargins(1, 1, 1, 1)
        self.root_layout.setSpacing(0)
        self.title_bar = CustomTitleBar(self)
        self.content_widget = QWidget()
        self.content_widget.setObjectName("DialogContentWidget")

        self.content_layout = QVBoxLayout(self.content_widget)
        self.content_layout.setContentsMargins(10, 10, 10, 10)

        self.root_layout.addWidget(self.title_bar)
        self.root_layout.addWidget(self.content_widget)

    def setLayout(self, layout):
        old_layout = self.content_widget.layout()
        if old_layout is not None:
            QWidget().setLayout(old_layout)
        self.content_widget.setLayout(layout)

    def setWindowTitle(self, title):
        super().setWindowTitle(title)
        self.title_bar.sync_maximize_button_state()

    def show_animated(self):
        self.setWindowOpacity(0.0)
        self.show()
        self._animation = QPropertyAnimation(self, b"windowOpacity")
        self._animation.setDuration(150)
        self._animation.setStartValue(0.0)
        self._animation.setEndValue(1.0)
        self._animation.start()

    def exec(self):
        self.show_animated()
        return super().exec()

    def accept(self):
        if self._is_closing: return
        self._is_closing = True
        self.closing.emit()
        self._animation = QPropertyAnimation(self, b"windowOpacity")
        self._animation.setDuration(150)
        self._animation.setStartValue(self.windowOpacity())
        self._animation.setEndValue(0.0)
        self._animation.finished.connect(super().accept)
        self._animation.start()

    def reject(self):
        if self._is_closing: return
        self._is_closing = True
        self.closing.emit()
        self._animation = QPropertyAnimation(self, b"windowOpacity")
        self._animation.setDuration(150)
        self._animation.setStartValue(self.windowOpacity())
        self._animation.setEndValue(0.0)
        self._animation.finished.connect(super().reject)
        self._animation.start()

    def closeEvent(self, event: QCloseEvent):
        if self._is_closing:
            super().closeEvent(event)
            return
        event.ignore()
        self.reject()


class CustomMessageBox(CustomDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.result = QDialogButtonBox.StandardButton.Cancel

    def accept(self):
        if self._is_closing: return
        self._is_closing = True
        self._animation = QPropertyAnimation(self, b"windowOpacity")
        self._animation.setDuration(150)
        self._animation.setStartValue(self.windowOpacity())
        self._animation.setEndValue(0.0)
        self._animation.finished.connect(lambda: self.done(QDialog.DialogCode.Accepted))
        self._animation.start()

    def reject(self):
        if self._is_closing: return
        self._is_closing = True
        self._animation = QPropertyAnimation(self, b"windowOpacity")
        self._animation.setDuration(150)
        self._animation.setStartValue(self.windowOpacity())
        self._animation.setEndValue(0.0)
        self._animation.finished.connect(lambda: self.done(QDialog.DialogCode.Rejected))
        self._animation.start()

    def _exec(self, title, text, icon, buttons, center_buttons=False):
        self.setWindowTitle(title)
        main_layout = QVBoxLayout()
        self.setLayout(main_layout)

        top_layout = QHBoxLayout()
        top_layout.setSpacing(15)
        main_layout.addLayout(top_layout)

        if icon:
            icon_label = QLabel()
            pixmap = self.style().standardIcon(icon).pixmap(48, 48)
            icon_label.setPixmap(pixmap)
            top_layout.addWidget(icon_label)

        text_label = QLabel(text)
        text_label.setWordWrap(True)
        top_layout.addWidget(text_label, 1)

        self.button_box = QDialogButtonBox(buttons)
        self.button_box.accepted.connect(self.accept)
        self.button_box.rejected.connect(self.reject)
        self.button_box.clicked.connect(self.on_button_clicked)

        button_container = QHBoxLayout()
        button_container.addStretch(1)
        button_container.addWidget(self.button_box)
        if center_buttons:
            button_container.addStretch(1)
        main_layout.addLayout(button_container)

        if self.exec() == QDialog.DialogCode.Accepted:
            return self.result
        return QDialogButtonBox.StandardButton.Cancel

    def on_button_clicked(self, button):
        self.result = self.button_box.standardButton(button)

    @staticmethod
    def question(parent, title, text):
        msg_box = CustomMessageBox(parent)
        msg_box.title_bar.hide()
        return msg_box._exec(title, text, QStyle.StandardPixmap.SP_MessageBoxQuestion,
                             QDialogButtonBox.StandardButton.Yes | QDialogButtonBox.StandardButton.No)

    @staticmethod
    def warning(parent, title, text):
        msg_box = CustomMessageBox(parent)
        return msg_box._exec(title, text, QStyle.StandardPixmap.SP_MessageBoxWarning,
                             QDialogButtonBox.StandardButton.Ok)

    @staticmethod
    def confirm_quit(parent, title, text):
        msg_box = CustomMessageBox(parent)
        msg_box.title_bar.hide()
        return msg_box._exec(title, text, QStyle.StandardPixmap.SP_MessageBoxQuestion,
                             QDialogButtonBox.StandardButton.Yes | QDialogButtonBox.StandardButton.Cancel,
                             center_buttons=True)


class SaveAsDialog(QDialog):
    """ A dialog to choose whether to save as a Formulation or an Accord. """

    def __init__(self, is_editing_accord=False, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Save As...")
        self.setModal(True)

        layout = QVBoxLayout(self)

        radio_layout = QHBoxLayout()
        self.formulation_radio = QRadioButton("Formulation")
        self.accord_radio = QRadioButton("Accord (reusable ingredient)")
        radio_layout.addWidget(self.formulation_radio)
        radio_layout.addStretch()
        radio_layout.addWidget(self.accord_radio)
        layout.addLayout(radio_layout)

        self.accord_properties_group = QGroupBox("Accord Properties")
        accord_layout = QGridLayout(self.accord_properties_group)
        accord_layout.addWidget(QLabel("Note Type:"), 0, 0)
        self.note_type_combo = QComboBox()
        self.note_type_combo.addItems([n for n in NOTE_TYPES if n != 'Solvent'])
        self.note_type_combo.setCurrentText("Other")
        accord_layout.addWidget(self.note_type_combo, 0, 1)

        accord_layout.addWidget(QLabel("Primary Category:"), 1, 0)
        self.category_combo = QComboBox()
        self.category_combo.addItems([c for c in DEFAULT_SCENT_CATEGORIES if c != 'Solvent'])
        self.category_combo.setCurrentText("Uncategorized")
        accord_layout.addWidget(self.category_combo, 1, 1)

        accord_layout.addWidget(QLabel("Secondary Category:"), 2, 0)
        self.secondary_category_combo = QComboBox()
        self.secondary_category_combo.addItems([c for c in DEFAULT_SCENT_CATEGORIES if c != 'Solvent'])
        self.secondary_category_combo.setCurrentText("Uncategorized")
        accord_layout.addWidget(self.secondary_category_combo, 2, 1)

        layout.addWidget(self.accord_properties_group)

        if is_editing_accord:
            self.accord_radio.setChecked(True)
        else:
            self.formulation_radio.setChecked(True)

        self.formulation_radio.toggled.connect(self._toggle_accord_properties)

        button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel)
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)

        self._toggle_accord_properties(self.formulation_radio.isChecked())

    def _toggle_accord_properties(self, is_formulation_selected):
        """
        Shows or hides the accord properties group and resizes the dialog to fit.
        """
        self.accord_properties_group.setVisible(not is_formulation_selected)
        self.adjustSize()

    def get_values(self):
        """ Returns a dictionary with the user's choices. """
        if self.accord_radio.isChecked():
            secondary_cat = self.secondary_category_combo.currentText()
            return {
                "type": "accord",
                "note_type": self.note_type_combo.currentText(),
                "primary_category": self.category_combo.currentText(),
                "secondary_category": "" if secondary_cat == "Uncategorized" else secondary_cat
            }
        else:
            return {"type": "formulation"}


class TweakDialog(QDialog):
    """A dialog to get a new percentage for an ingredient in an accord."""

    def __init__(self, ingredient_name, current_percent, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"Tweak {ingredient_name}")
        self.setModal(True)

        layout = QVBoxLayout(self)
        info_label = QLabel("Tweak your accord's percentages.\nAll other ingredients will be updated proportionally.")
        info_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(info_label)

        input_layout = QHBoxLayout()
        input_layout.addWidget(QLabel("New Percentage:"))
        self.spinbox = QDoubleSpinBox()
        self.spinbox.setRange(0.01, 99.99)
        self.spinbox.setDecimals(2)
        self.spinbox.setSuffix("%")
        self.spinbox.setValue(current_percent)
        input_layout.addWidget(self.spinbox)
        layout.addLayout(input_layout)

        button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)

    def get_new_percentage(self):
        """Returns the new value from the spinbox."""
        return self.spinbox.value()