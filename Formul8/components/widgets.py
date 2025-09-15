# formul8/components/widgets.py
# Contains core, non-dialog custom widgets for the application.

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, QStackedWidget,
    QStyle, QGraphicsOpacityEffect, QTreeWidgetItem, QHeaderView
)
from PyQt6.QtGui import (
    QMouseEvent, QPaintEvent, QColor, QIcon, QPixmap, QPainter, QFont,
    QFontMetrics, QPalette, QCursor, QGuiApplication
)
from PyQt6.QtCore import (
    Qt, QTimer, pyqtSignal, QPoint, QPropertyAnimation, QEasingCurve,
    QParallelAnimationGroup, QRect, QEvent, QRectF
)
from urllib.parse import quote

from ..constants import ACCORD_SYMBOL
from .helpers import create_svg_icon


class ClickableHeader(QHeaderView):
    """
    A custom QHeaderView that emits a reliable click signal for a column,
    bypassing conflicts with the parent widget's drag-and-drop handling.
    """
    customSectionClicked = pyqtSignal(int)

    def __init__(self, orientation, parent=None):
        super().__init__(orientation, parent)
        self.setSectionsClickable(True)
        # Let the header manage its own cursor to show resize handles correctly
        self.setCursor(Qt.CursorShape.PointingHandCursor)

    def mousePressEvent(self, event: QMouseEvent):
        """
        Handles mouse press events to differentiate between sorting clicks
        and resize drags.
        """
        # If the cursor is the resize handle, let the default behavior take over
        # and do not emit our custom click signal.
        if self.cursor().shape() == Qt.CursorShape.SplitHCursor:
            super().mousePressEvent(event)
            return

        # Otherwise, it's a sort click.
        logical_index = self.logicalIndexAt(event.position().toPoint())
        if logical_index != -1:
            self.customSectionClicked.emit(logical_index)

        super().mousePressEvent(event)


class HoverIconLink(QLabel):
    """
    A custom QLabel that acts as a hyperlink and changes its icon color on hover.
    """

    def __init__(self, normal_svg, hover_svg, url, tooltip, parent=None):
        super().__init__(parent)
        self.normal_svg = normal_svg
        self.hover_svg = hover_svg
        self.url = url

        self.setOpenExternalLinks(True)
        self.setToolTip(tooltip)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFixedSize(24, 24)

        self._set_icon(self.normal_svg)

    def _set_icon(self, svg_data):
        """Helper to set the label's rich text with the correct SVG data."""
        self.setText(
            f'<a href="{self.url}">'
            f'<img src="data:image/svg+xml;utf8,{quote(svg_data)}" />'
            '</a>'
        )

    def enterEvent(self, event):
        """Called when the mouse enters the widget's area."""
        self._set_icon(self.hover_svg)
        super().enterEvent(event)

    def leaveEvent(self, event):
        """Called when the mouse leaves the widget's area."""
        self._set_icon(self.normal_svg)
        super().leaveEvent(event)


class ClickableLabel(QLabel):
    """
    A custom QLabel that emits a 'clicked' signal and changes color on hover.
    """
    clicked = pyqtSignal()

    def __init__(self, text, parent=None):
        super().__init__(text, parent)
        self.normal_color = self.palette().color(QPalette.ColorRole.WindowText).name()
        self.hover_color = self.palette().color(QPalette.ColorRole.Highlight).name()
        self.setStyleSheet(f"color: {self.normal_color}; font-weight: bold; font-size: 10pt; padding-left: 3px;")
        self.setCursor(Qt.CursorShape.PointingHandCursor)

    def mousePressEvent(self, event: QMouseEvent):
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit()
        super().mousePressEvent(event)

    def enterEvent(self, event):
        self.setStyleSheet(f"color: {self.hover_color}; font-weight: bold; font-size: 10pt; padding-left: 3px;")
        super().enterEvent(event)

    def leaveEvent(self, event):
        self.setStyleSheet(f"color: {self.normal_color}; font-weight: bold; font-size: 10pt; padding-left: 3px;")
        super().leaveEvent(event)


class HoverLabel(QLabel):
    """ A simple QLabel that emits signals on mouse enter, leave, and click. """
    hover_enter = pyqtSignal()
    hover_leave = pyqtSignal()
    clicked = pyqtSignal()

    def enterEvent(self, event):
        self.hover_enter.emit()
        super().enterEvent(event)

    def leaveEvent(self, event):
        self.hover_leave.emit()
        super().leaveEvent(event)

    def mousePressEvent(self, event: QMouseEvent):
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit()
        super().mousePressEvent(event)


class AccordItemWidget(QWidget):
    """
    A custom widget for displaying an accord in a QTreeWidget.
    Handles its own expand/collapse icon and hover effects.
    """
    ARROW_RIGHT_SVG = '<svg xmlns="http://www.w3.org/2000/svg" width="12" height="12"><path d="M 4 2 L 8 6 L 4 10" fill="none" stroke="#COLOR_PLACEHOLDER#" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/></svg>'
    ARROW_DOWN_SVG = '<svg xmlns="http://www.w3.org/2000/svg" width="12" height="12"><path d="M 2 4 L 6 8 L 10 4" fill="none" stroke="#COLOR_PLACEHOLDER#" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/></svg>'

    def __init__(self, name, parent=None):
        super().__init__(parent)
        self.name = name
        self.is_expanded = False
        self.is_selected = False
        self.tree_item = None

        self.normal_color = "#ffffff"
        self.hover_color = "#9881a7"
        self.selected_color = "#ffffff"

        self.arrow_icon_collapsed = create_svg_icon(self.ARROW_RIGHT_SVG, self.normal_color)
        self.arrow_icon_expanded = create_svg_icon(self.ARROW_DOWN_SVG, self.normal_color)
        self.arrow_icon_selected = create_svg_icon(self.ARROW_RIGHT_SVG, self.selected_color)
        self.arrow_icon_selected_expanded = create_svg_icon(self.ARROW_DOWN_SVG, self.selected_color)
        self.arrow_icon_collapsed_hover = create_svg_icon(self.ARROW_RIGHT_SVG, self.hover_color)
        self.arrow_icon_expanded_hover = create_svg_icon(self.ARROW_DOWN_SVG, self.hover_color)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(2, 0, 4, 0)
        layout.setSpacing(0)
        layout.setAlignment(Qt.AlignmentFlag.AlignLeft)

        self.arrow_label = HoverLabel()
        self.arrow_label.setCursor(Qt.CursorShape.PointingHandCursor)
        self.arrow_label.setFixedSize(14, 22)
        self.arrow_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.arrow_label.hover_enter.connect(self._handle_hover_enter)
        self.arrow_label.hover_leave.connect(self._handle_hover_leave)
        self.arrow_label.clicked.connect(self._on_arrow_clicked)
        layout.addWidget(self.arrow_label)

        self.name_label = QLabel(name)
        self.name_label.setStyleSheet("color: #ffffff; font-size: 10pt; margin-left: 2px; margin-right: 6px;")

        self.symbol_label = QLabel(ACCORD_SYMBOL)
        self.symbol_label.setStyleSheet("color: #ffffff; font-size: 10pt;")

        layout.addWidget(self.name_label)
        layout.addWidget(self.symbol_label)
        layout.addStretch()  # Ensure it doesn't fill the whole row

        self._update_arrow_icon()

    def set_tree_item(self, item: QTreeWidgetItem):
        """Stores a reference to the tree item this widget belongs to."""
        self.tree_item = item

    def mouseDoubleClickEvent(self, event: QMouseEvent):
        """
        Accepts the double-click event ONLY if it's over the expand/collapse arrow.
        This prevents accidentally editing while double-clicking the arrow, but allows
        double-clicking the name to correctly trigger the edit action.
        """
        if self.arrow_label.geometry().contains(event.position().toPoint()):
            event.accept()
            return

        super().mouseDoubleClickEvent(event)

    def _on_arrow_clicked(self):
        """Toggles the expanded state of the parent tree item when the arrow is clicked."""
        if self.tree_item:
            self.tree_item.setExpanded(not self.tree_item.isExpanded())

    def _handle_hover_enter(self):
        if not self.is_selected:
            self._update_arrow_icon(is_hovering=True)

    def _handle_hover_leave(self):
        if not self.is_selected:
            self._update_arrow_icon(is_hovering=False)

    def _update_arrow_icon(self, is_hovering=False):
        if self.is_selected:
            icon = self.arrow_icon_selected_expanded if self.is_expanded else self.arrow_icon_selected
        elif is_hovering:
            icon = self.arrow_icon_expanded_hover if self.is_expanded else self.arrow_icon_collapsed_hover
        else:
            icon = self.arrow_icon_expanded if self.is_expanded else self.arrow_icon_collapsed

        self.arrow_label.setPixmap(icon.pixmap(16, 16))

    def set_expanded(self, expanded):
        self.is_expanded = expanded
        self._update_arrow_icon()

    def set_selected(self, selected):
        self.is_selected = selected
        self._update_arrow_icon()


class CustomTitleBar(QWidget):
    def __init__(self, parent):
        super().__init__(parent)
        self.parent_window = parent
        self.setObjectName("CustomTitleBar")
        self.setAutoFillBackground(True)
        self.setFixedHeight(32)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 0, 0, 0)
        layout.setSpacing(0)

        layout.addStretch()

        self.minimize_button = QPushButton()
        self.minimize_button.setObjectName("TitleBarButton")
        self.minimize_button.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_TitleBarMinButton))
        self.minimize_button.clicked.connect(self.parent_window.showMinimized)

        self.maximize_button = QPushButton()
        self.maximize_button.setObjectName("TitleBarButton")
        self.maximize_button.setCheckable(True)
        self.maximize_button.toggled.connect(self.on_maximize_toggled)

        self.close_button = QPushButton()
        self.close_button.setObjectName("TitleBarCloseButton")
        self.close_button.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_TitleBarCloseButton))
        self.close_button.clicked.connect(self.parent_window.close)

        layout.addWidget(self.minimize_button)
        layout.addWidget(self.maximize_button)
        layout.addWidget(self.close_button)

        self.drag_position = None
        if hasattr(parent, 'windowStateChanged'):
            parent.windowStateChanged.connect(self.sync_maximize_button_state)

        self.sync_maximize_button_state()

    def on_maximize_toggled(self, checked):
        if self.parent_window.isMaximized():
            self.parent_window.showNormal()
        else:
            self.parent_window.showMaximized()

    def sync_maximize_button_state(self):
        is_maximized = self.parent_window.isMaximized()
        self.maximize_button.blockSignals(True)
        self.maximize_button.setChecked(is_maximized)
        self.maximize_button.blockSignals(False)
        if is_maximized:
            self.maximize_button.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_TitleBarNormalButton))
        else:
            self.maximize_button.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_TitleBarMaxButton))

    def mousePressEvent(self, event: QMouseEvent):
        if event.button() == Qt.MouseButton.LeftButton:
            if self.childAt(event.position().toPoint()) in [self.minimize_button, self.maximize_button,
                                                            self.close_button]:
                return
            self.drag_position = event.globalPosition().toPoint() - self.parent_window.frameGeometry().topLeft()
            event.accept()

    def mouseMoveEvent(self, event: QMouseEvent):
        if event.buttons() == Qt.MouseButton.LeftButton and self.drag_position is not None:
            if self.parent_window.isMaximized():
                self.maximize_button.toggle()
                self.drag_position = QPoint(self.width() // 2, self.height() // 2)
                self.parent_window.move(event.globalPosition().toPoint() - self.drag_position)
            else:
                self.parent_window.move(event.globalPosition().toPoint() - self.drag_position)
            event.accept()

    def mouseDoubleClickEvent(self, event: QMouseEvent):
        if event.button() == Qt.MouseButton.LeftButton:
            self.maximize_button.toggle()
            event.accept()

    def mouseReleaseEvent(self, event: QMouseEvent):
        self.drag_position = None
        event.accept()


class AnimatedStackedWidget(QStackedWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.fade_duration = 100
        self._next_widget = None
        self._animation = None
        self._overlay = QLabel(self)
        self._overlay.hide()
        self._overlay.setScaledContents(True)
        self._opacity_effect = QGraphicsOpacityEffect(self._overlay)
        self._overlay.setGraphicsEffect(self._opacity_effect)

    def set_current_widget_animated(self, widget):
        if self.currentWidget() == widget:
            return
        if self._animation and self._animation.state() == QPropertyAnimation.State.Running:
            self._animation.stop()
        self._next_widget = widget
        current_widget = self.currentWidget()
        if current_widget:
            self._fade_out_current(current_widget)
        else:
            self.setCurrentWidget(widget)

    def _fade_out_current(self, current_widget):
        pixmap = QPixmap(current_widget.size())
        current_widget.render(pixmap)
        self._overlay.setPixmap(pixmap)
        self._overlay.setGeometry(current_widget.geometry())
        self._overlay.show()
        current_widget.hide()
        self._animation = QPropertyAnimation(self._opacity_effect, b"opacity")
        self._animation.setDuration(self.fade_duration)
        self._animation.setStartValue(1.0)
        self._animation.setEndValue(0.0)
        self._animation.finished.connect(self._on_fade_out_finished)
        self._animation.start()

    def _on_fade_out_finished(self):
        self.setCurrentWidget(self._next_widget)
        self._fade_in_next()

    def _fade_in_next(self):
        next_widget = self.currentWidget()
        next_widget.hide()
        pixmap = QPixmap(next_widget.size())
        next_widget.render(pixmap)
        self._overlay.setPixmap(pixmap)
        self._overlay.setGeometry(next_widget.geometry())
        self._overlay.show()
        self._animation = QPropertyAnimation(self._opacity_effect, b"opacity")
        self._animation.setDuration(self.fade_duration)
        self._animation.setStartValue(0.0)
        self._animation.setEndValue(1.0)
        self._animation.finished.connect(self._on_fade_in_finished)
        self._animation.start()

    def _on_fade_in_finished(self):
        self.currentWidget().show()
        self._overlay.hide()
        self._animation = None
        self._next_widget = None


class AnimatedSplashScreen(QWidget):
    def __init__(self, pixmap, version_text, duration_ms=2500):
        super().__init__(parent=None)
        self.pixmap = pixmap
        self.version_text = version_text
        self.duration = duration_ms
        self.progress = 0.0

        self.setWindowFlags(Qt.WindowType.SplashScreen | Qt.WindowType.FramelessWindowHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setFixedSize(self.pixmap.size())

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_progress)
        self.timer.start(20)

    def update_progress(self):
        self.progress += (self.timer.interval() / self.duration)
        if self.progress > 1.0:
            self.progress = 1.0
        self.update()

    def paintEvent(self, event: QPaintEvent):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.drawPixmap(self.rect(), self.pixmap)
        painter.setPen(QColor("#abb2bf"))
        painter.setFont(QFont("Segoe UI", 10))
        painter.drawText(self.rect().adjusted(0, 0, 0, -10),
                         Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignBottom, self.version_text)

        bar_height = 15
        bar_margin_x = self.width() * 0.1
        bar_y = self.height() * 0.75
        bar_rect = QRectF(bar_margin_x, bar_y, self.width() - (2 * bar_margin_x), bar_height)

        painter.setBrush(QColor("#21252b"))
        painter.setPen(QColor("#5c6370"))
        painter.drawRoundedRect(bar_rect, 5, 5)

        if self.progress > 0:
            fill_width = bar_rect.width() * self.progress
            fill_rect = QRectF(bar_rect.x(), bar_rect.y(), fill_width, bar_rect.height())
            painter.setBrush(QColor("#9881a7"))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawRoundedRect(fill_rect, 5, 5)

    def showEvent(self, event):
        self.center()
        super().showEvent(event)

    def center(self):
        if screen := QGuiApplication.primaryScreen():
            screen_geometry = screen.availableGeometry()
            self.move(screen_geometry.center() - self.rect().center())

    def closeEvent(self, event):
        self.timer.stop()
        super().closeEvent(event)