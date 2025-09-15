# formul8/views/formulation_main.py
# A container frame that holds the 'Create' and 'View' formulation frames in a tabbed layout.

from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QTabBar, QFrame, QPushButton, QStackedLayout, \
    QSizePolicy
from PyQt6.QtCore import pyqtSignal, Qt, QTimer

# --- Local Imports ---
from ..components import AnimatedStackedWidget
from .formulation_creator import CreateFormulationFrame
from .formulation_viewer import ViewEditFormulationsFrame


class FormulationMainFrame(QWidget):
    """
    A container widget that uses a QTabBar to switch between the formulation
    creator/editor and the formulation viewer.
    """
    back_signal = pyqtSignal()

    def __init__(self, data_manager, parent=None):
        super().__init__(parent)
        self.data_manager = data_manager
        self._viewer_preloaded = False

        layout = QVBoxLayout(self)
        layout.setSpacing(0)
        layout.setContentsMargins(10, 10, 10, 10)

        # --- Re-architected top bar for perfect title centering ---
        top_bar_widget = QWidget()
        # --- FIX: Constrain the top bar's height to prevent extra space ---
        top_bar_widget.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)
        top_bar_layout = QStackedLayout(top_bar_widget)
        top_bar_layout.setStackingMode(QStackedLayout.StackingMode.StackAll)

        # Layer 0: Button
        button_container = QWidget()
        button_layout = QHBoxLayout(button_container)
        button_layout.setContentsMargins(0, 0, 0, 0)
        back_button = QPushButton("<- Back to Main Menu")
        back_button.clicked.connect(self.back_signal.emit)
        button_layout.addWidget(back_button)
        button_layout.addStretch()

        # Layer 1: Title
        header = QLabel("Formulation Manager")
        header.setObjectName("HeaderLabel")
        header.setAlignment(Qt.AlignmentFlag.AlignCenter)
        # Make title transparent to clicks so the back button works if under it
        header.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)

        # Add layers to stack (last widget added is on top)
        top_bar_layout.addWidget(button_container)
        top_bar_layout.addWidget(header)

        layout.addWidget(top_bar_widget)

        self.tab_bar = QTabBar()
        self.tab_bar.setExpanding(False)
        tab_bar_layout = QHBoxLayout()
        tab_bar_layout.addStretch()
        tab_bar_layout.addWidget(self.tab_bar)
        tab_bar_layout.addStretch()
        layout.addLayout(tab_bar_layout)

        line_separator = QFrame()
        line_separator.setFrameShape(QFrame.Shape.HLine)
        layout.addWidget(line_separator)

        self.page_stack = AnimatedStackedWidget()
        layout.addWidget(self.page_stack)

        self.create_frame = CreateFormulationFrame(data_manager=self.data_manager)
        self.view_edit_frame = ViewEditFormulationsFrame(data_manager=self.data_manager)

        self.tab_bar.addTab("Create / Edit")
        self.page_stack.addWidget(self.create_frame)
        self.tab_bar.addTab("View All")
        self.page_stack.addWidget(self.view_edit_frame)

        self.tab_bar.currentChanged.connect(self._on_tab_changed)
        self.view_edit_frame.edit_formulation_signal.connect(self.handle_edit_request)

    def handle_edit_request(self, formula_data):
        """
        Public slot to load a formulation or accord into the editor and switch to it.
        This is called from the main window when an edit is requested from another view.
        """
        self.create_frame.setup_for_editing(formula_data)
        create_frame_index = self.page_stack.indexOf(self.create_frame)
        self.tab_bar.setCurrentIndex(create_frame_index)

    def _on_tab_changed(self, index):
        widget = self.page_stack.widget(index)
        if not widget:
            return

        if hasattr(widget, 'on_show'):
            widget.on_show()

        self.page_stack.set_current_widget_animated(widget)

        if widget is not self.create_frame and self.create_frame.editing_formulation_obj_ref:
            self.create_frame.reset_formulation_creation()

    def on_show(self):
        if not self._viewer_preloaded:
            QTimer.singleShot(0, self.preload_viewer)

        current_widget = self.page_stack.currentWidget()
        if hasattr(current_widget, 'on_show'):
            current_widget.on_show()

    def preload_viewer(self):
        """
        Forces the hidden viewer frame to adopt the geometry of the visible
        creator frame, then tells it to build its layout. This is pre-loading.
        """
        visible_geometry = self.create_frame.geometry()
        self.view_edit_frame.setGeometry(visible_geometry)
        self.view_edit_frame.build_view()
        self._viewer_preloaded = True