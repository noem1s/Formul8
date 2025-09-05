# formul8/main_window.py
# This is the "Controller" of the application, managing views and user interaction.

from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QApplication, QDialogButtonBox, QTreeWidget, QListWidget
)
from PyQt6.QtGui import QGuiApplication, QCloseEvent
from PyQt6.QtCore import Qt, QSettings, QPoint, QPropertyAnimation, QEasingCurve, QParallelAnimationGroup, QRect, QEvent

# RATIONALE: Type Hinting Imports for a clean editor
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .views.main_menu import MainMenuFrame
    from .views.ingredient_manager import IngredientManagementFrame
    from .views.ingredient_editor import EditIngredientFrame
    from .views.formulation_main import FormulationMainFrame
    from .views.settings_main import SettingsMenuFrame
    from .views.settings_lists import GenericListManagementFrame
    from .views.settings_colors import ScentProfileSettingsFrame
    from .views.settings_data import DataManagementFrame

from .constants import APP_VERSION
from .ui_components import CustomTitleBar, AnimatedStackedWidget, CustomMessageBox
from .data_manager import DataManager


class MainWindow(QMainWindow):
    """ The main application window that holds and manages all other frames. """

    def __init__(self):
        super().__init__()
        self._animation = None
        self._is_closing = False
        self._normal_geometry = None
        self._is_animating_state_change = False

        self.history = []
        self.frame_names = {}

        self.data_manager = DataManager()

        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowMinimizeButtonHint)
        self.setWindowTitle(f"Formul8 - Version {APP_VERSION}")
        self.setGeometry(100, 100, 1200, 850)
        self.center()

        main_container = QWidget()
        main_container.setObjectName("MainContainer")
        main_layout = QVBoxLayout(main_container)
        main_layout.setContentsMargins(1, 1, 1, 1)
        main_layout.setSpacing(0)

        self.title_bar = CustomTitleBar(self)
        main_layout.addWidget(self.title_bar)

        self.stacked_widget = AnimatedStackedWidget()
        main_layout.addWidget(self.stacked_widget)

        self.setCentralWidget(main_container)

        self.frames = {}
        self._create_frames()
        self._connect_signals()
        self.show_frame("MainMenu")

    def _create_frames(self):
        """ Instantiates all the different screen/frame widgets for the application. """
        # Lazy imports to prevent circular dependencies at startup
        from .views.main_menu import MainMenuFrame
        from .views.ingredient_manager import IngredientManagementFrame
        from .views.ingredient_editor import EditIngredientFrame
        from .views.formulation_main import FormulationMainFrame
        from .views.settings_main import SettingsMenuFrame
        from .views.settings_lists import GenericListManagementFrame
        from .views.settings_colors import ScentProfileSettingsFrame
        from .views.settings_data import DataManagementFrame

        self.frames["MainMenu"] = MainMenuFrame(main_win=self, data_manager=self.data_manager)
        self.frames["Ingredients"] = IngredientManagementFrame(data_manager=self.data_manager)
        self.frames["EditIngredient"] = EditIngredientFrame(data_manager=self.data_manager)
        self.frames["Formulations"] = FormulationMainFrame(data_manager=self.data_manager)
        self.frames["Settings"] = SettingsMenuFrame(data_manager=self.data_manager)
        self.frames["ScentProfileSettings"] = ScentProfileSettingsFrame(data_manager=self.data_manager)
        self.frames["DataManagement"] = DataManagementFrame(data_manager=self.data_manager)

        self.frames["ManageScentCategories"] = GenericListManagementFrame("scent_categories", "Scent Categories",
                                                                          data_manager=self.data_manager)
        self.frames["ManageSuppliers"] = GenericListManagementFrame("suppliers", "Suppliers",
                                                                    data_manager=self.data_manager)
        self.frames["ManageBrands"] = GenericListManagementFrame("brands", "Brands", data_manager=self.data_manager)
        self.frames["ManageDiluents"] = GenericListManagementFrame("diluents", "Diluents",
                                                                   data_manager=self.data_manager)

        for name, frame in self.frames.items():
            self.stacked_widget.addWidget(frame)

        self.frame_names = {widget: name for name, widget in self.frames.items()}

        for frame in self.frames.values():
            list_widgets = frame.findChildren(QListWidget)
            tree_widgets = frame.findChildren(QTreeWidget)
            for widget in list_widgets + tree_widgets:
                widget.installEventFilter(self)

    def _connect_signals(self):
        """ Connects signals between frames to handle navigation. """
        main_menu = self.frames["MainMenu"]
        main_menu.show_ingredients_signal.connect(lambda: self.show_frame("Ingredients"))
        main_menu.show_formulations_signal.connect(lambda: self.show_frame("Formulations"))
        main_menu.show_settings_signal.connect(lambda: self.show_frame("Settings"))

        ing_manager = self.frames["Ingredients"]
        ing_manager.back_signal.connect(self.go_back)
        ing_manager.edit_ingredient_signal.connect(self.show_edit_ingredient_frame)

        # --- THIS IS THE FIX ---
        # The "Cancel" button on the Edit screen now uses the history system.
        self.frames["EditIngredient"].back_to_list_signal.connect(self.go_back)

        formulation_main_frame = self.frames["Formulations"]
        formulation_main_frame.back_signal.connect(self.go_back)

        settings_menu = self.frames["Settings"]
        settings_menu.back_signal.connect(self.go_back)
        settings_menu.show_data_management_signal.connect(lambda: self.show_frame("DataManagement"))
        settings_menu.show_scent_color_settings_signal.connect(lambda: self.show_frame("ScentProfileSettings"))
        settings_menu.show_list_management_signal.connect(self.show_list_management_frame)

        self.frames["DataManagement"].back_signal.connect(self.go_back)
        self.frames["ScentProfileSettings"].back_signal.connect(self.go_back)
        self.frames["ManageScentCategories"].back_signal.connect(self.go_back)
        self.frames["ManageSuppliers"].back_signal.connect(self.go_back)
        self.frames["ManageBrands"].back_signal.connect(self.go_back)
        self.frames["ManageDiluents"].back_signal.connect(self.go_back)

    def show_frame(self, name):
        """ Switches the animated stacked widget to the specified frame and updates history. """
        current_widget = self.stacked_widget.currentWidget()
        if current_widget:
            current_name = self.frame_names.get(current_widget)
            if current_name and current_name != name:
                self.history.append(current_name)

        if hasattr(current_widget, 'save_column_widths'):
            current_widget.save_column_widths()

        frame = self.frames.get(name)
        if frame:
            if hasattr(frame, 'on_show'):
                frame.on_show()
            self.stacked_widget.set_current_widget_animated(frame)

    def show_edit_ingredient_frame(self, data):
        """ Special handler to pass data to the edit ingredient frame before showing it. """
        self.frames["EditIngredient"].setup_ingredient_for_editing(data)
        self.show_frame("EditIngredient")

    def show_list_management_frame(self, key, title):
        """ Special handler for the generic list management frame. """
        frame_key = f"Manage{title.replace(' ', '')}"
        self.show_frame(frame_key)

    def go_back(self):
        """ Navigates to the previous frame in the history stack. """
        if self.history:
            frame_name = self.history.pop()
            frame_to_show = self.frames.get(frame_name)
            if frame_to_show:
                if hasattr(frame_to_show, 'on_show'):
                    frame_to_show.on_show()
                self.stacked_widget.set_current_widget_animated(frame_to_show)

    def eventFilter(self, source, event):
        """
        Filters events globally for the entire application.
        """
        if event.type() == QEvent.Type.MouseButtonPress:
            button = event.button()
            if button == Qt.MouseButton.BackButton:
                self.go_back()
                return True
            if button == Qt.MouseButton.ForwardButton:
                return True

        return super().eventFilter(source, event)

    def center(self):
        if screen := QGuiApplication.primaryScreen():
            cp = screen.availableGeometry().center()
            qr = self.frameGeometry()
            qr.moveCenter(cp)
            self.move(qr.topLeft())

    def save_ui_settings(self):
        """ Saves UI state like column widths to QSettings. """
        current_widget = self.stacked_widget.currentWidget()
        if hasattr(current_widget, 'save_column_widths'):
            current_widget.save_column_widths()

    def closeEvent(self, event: QCloseEvent):
        """
        Overrides the default close event to ensure a graceful and complete shutdown.
        This is the ONLY safe way to exit the application.
        """
        if self._is_closing:
            event.accept()
            return

        reply = CustomMessageBox.confirm_quit(self, 'Confirm Quit', 'Are you sure you want to quit?')
        if reply != QDialogButtonBox.StandardButton.Yes:
            event.ignore()
            return

        self._is_closing = True
        event.ignore()
        self.save_ui_settings()

        self.data_manager.save_data()

        self._animation = QPropertyAnimation(self, b"windowOpacity")
        self._animation.setDuration(150)
        self._animation.setStartValue(1.0)
        self._animation.setEndValue(0.0)
        self._animation.finished.connect(QApplication.instance().quit)
        self._animation.start()

    # --- Window Animations and Event Handling (These remain unchanged) ---
    def changeEvent(self, event: QEvent):
        if event.type() == QEvent.Type.WindowStateChange and event.oldState() & Qt.WindowState.WindowMinimized:
            if not self._is_animating_state_change: self._animate_unminimize()
            event.accept()
            return
        super().changeEvent(event)

    def showMaximized(self):
        if self.isMaximized() or self._is_animating_state_change: super().showMaximized(); return
        self._is_animating_state_change = True
        self._normal_geometry = self.geometry()
        self._animation = QPropertyAnimation(self, b"geometry");
        self._animation.setDuration(200);
        self._animation.setStartValue(self._normal_geometry)
        if screen := QGuiApplication.primaryScreen(): self._animation.setEndValue(screen.availableGeometry())
        self._animation.setEasingCurve(QEasingCurve.Type.InOutCubic);
        self._animation.finished.connect(self._on_maximize_animation_finished);
        self._animation.start()

    def _on_maximize_animation_finished(self):
        self.setWindowState(Qt.WindowState.WindowMaximized);
        self._is_animating_state_change = False;
        self._animation = None

    def showNormal(self):
        if self.isMaximized() and not self._is_animating_state_change:
            self._is_animating_state_change = True
            if self._normal_geometry is None:
                if screen := QGuiApplication.primaryScreen():
                    screen_geom = screen.availableGeometry()
                    fallback_rect = QRect(0, 0, 1200, 850);
                    fallback_rect.moveCenter(screen_geom.center());
                    self._normal_geometry = fallback_rect
            self._animation = QPropertyAnimation(self, b"geometry");
            self._animation.setDuration(200);
            self._animation.setStartValue(self.geometry());
            self._animation.setEndValue(self._normal_geometry)
            self._animation.setEasingCurve(QEasingCurve.Type.InOutCubic);
            self._animation.finished.connect(self._on_restore_animation_finished);
            self._animation.start()
        else:
            super().showNormal()

    def _on_restore_animation_finished(self):
        self.setWindowState(Qt.WindowState.WindowNoState);
        self.setGeometry(self._normal_geometry);
        self._is_animating_state_change = False;
        self._animation = None

    def _animate_unminimize(self):
        self._is_animating_state_change = True
        if self._normal_geometry is None:
            if screen := QGuiApplication.primaryScreen():
                screen_geom = screen.availableGeometry()
                fallback_rect = QRect(0, 0, 1200, 850);
                fallback_rect.moveCenter(screen_geom.center());
                self._normal_geometry = fallback_rect
        end_rect = self._normal_geometry
        if screen := QGuiApplication.primaryScreen():
            start_rect = QRect(end_rect.center().x(), screen.availableGeometry().bottom(), 0, 0)
        else:
            start_rect = QRect(end_rect.center(), QRect.zero())
        self.setWindowState(Qt.WindowState.WindowNoState);
        self.setGeometry(start_rect);
        self.setWindowOpacity(0.0);
        self.show()
        self.anim_group = QParallelAnimationGroup(self)
        geom_anim = QPropertyAnimation(self, b"geometry");
        geom_anim.setDuration(250);
        geom_anim.setStartValue(start_rect);
        geom_anim.setEndValue(end_rect);
        geom_anim.setEasingCurve(QEasingCurve.Type.OutQuad)
        opacity_anim = QPropertyAnimation(self, b"windowOpacity");
        opacity_anim.setDuration(250);
        opacity_anim.setStartValue(0.0);
        opacity_anim.setEndValue(1.0);
        opacity_anim.setEasingCurve(QEasingCurve.Type.OutQuad)
        self.anim_group.addAnimation(geom_anim);
        self.anim_group.addAnimation(opacity_anim);
        self.anim_group.finished.connect(self._on_unminimize_animation_finished);
        self.anim_group.start()

    def _on_unminimize_animation_finished(self):
        self._is_animating_state_change = False;
        self.anim_group = None;
        self.activateWindow();
        self.raise_()

    def showMinimized(self):
        if self.isMinimized() or self._is_animating_state_change: super().showMinimized(); return
        if not self.isMaximized(): self._normal_geometry = self.geometry()
        self._is_animating_state_change = True
        self.anim_group = QParallelAnimationGroup(self)
        geom_anim = QPropertyAnimation(self, b"geometry");
        geom_anim.setDuration(250)
        start_rect = self.geometry()
        if screen := QGuiApplication.primaryScreen():
            end_rect = QRect(start_rect.center().x(), screen.availableGeometry().bottom(), 0, 0)
        else:
            end_rect = QRect(start_rect.center(), QRect.zero())
        geom_anim.setStartValue(start_rect);
        geom_anim.setEndValue(end_rect);
        geom_anim.setEasingCurve(QEasingCurve.Type.InQuad)
        opacity_anim = QPropertyAnimation(self, b"windowOpacity");
        opacity_anim.setDuration(250);
        opacity_anim.setStartValue(1.0);
        opacity_anim.setEndValue(0.0);
        opacity_anim.setEasingCurve(QEasingCurve.Type.InQuad)
        self.anim_group.addAnimation(geom_anim);
        self.anim_group.addAnimation(opacity_anim);
        self.anim_group.finished.connect(self._on_minimize_animation_finished);
        self.anim_group.start()

    def _on_minimize_animation_finished(self):
        self.setWindowState(Qt.WindowState.WindowMinimized);
        self.setWindowOpacity(1.0);
        self._is_animating_state_change = False;
        self.anim_group = None

    def fade_in(self):
        self.setWindowOpacity(0.0);
        self.show()
        self._animation = QPropertyAnimation(self, b"windowOpacity");
        self._animation.setDuration(200);
        self._animation.setStartValue(0.0);
        self._animation.setEndValue(1.0);
        self._animation.start()