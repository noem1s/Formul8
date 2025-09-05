# formul8/ui_components.py
# A collection of reusable, custom UI components.

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, QTreeWidget,
    QDialog, QStackedWidget, QDialogButtonBox, QMenu, QFileDialog, QListWidget,
    QColorDialog, QInputDialog, QStyle, QGraphicsOpacityEffect
)
from PyQt6.QtGui import (
    QDrag, QMouseEvent, QPaintEvent, QCloseEvent, QColor, QBrush, QIcon, QPixmap,
    QPainter, QFont, QGuiApplication, QFontMetrics, QPalette
)
from PyQt6.QtCore import (
    Qt, QTimer, pyqtSignal, QMimeData, QPoint, QPropertyAnimation, QEasingCurve,
    QParallelAnimationGroup, QRect, QEvent, QRectF
)
from urllib.parse import quote

try:
    from fpdf import FPDF, XPos, YPos
except ImportError:
    FPDF = None
    XPos = None
    YPos = None
from datetime import datetime


# --- Helper function for creating drag visuals ---
def _create_drag_pixmap(item_names, palette):
    """
    Dynamically creates a pixmap to show while dragging items.
    """
    if not item_names:
        return QPixmap()

    item_count = len(item_names)
    if item_count == 1:
        text = item_names[0]
    else:
        text = f"{item_names[0]} (+{item_count - 1} more)"

    font = QFont("Segoe UI", 8)
    font_metrics = QFontMetrics(font)
    text_width = font_metrics.horizontalAdvance(text)

    pixmap_width = text_width + 16
    pixmap_height = 26

    pixmap = QPixmap(pixmap_width, pixmap_height)
    pixmap.fill(Qt.GlobalColor.transparent)

    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)

    bg_color = palette.color(QPalette.ColorRole.Highlight)
    bg_color.setAlpha(220)
    painter.setBrush(bg_color)
    painter.setPen(Qt.PenStyle.NoPen)
    painter.drawRoundedRect(pixmap.rect(), 4, 4)

    text_color = palette.color(QPalette.ColorRole.HighlightedText)
    painter.setPen(text_color)
    painter.setFont(font)
    painter.drawText(pixmap.rect(), Qt.AlignmentFlag.AlignCenter, text)

    painter.end()
    return pixmap


# --- NEW: Hover-aware Icon Link Widget ---
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
        self.setFixedSize(24, 24)  # Ensure a consistent clickable area

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


# --- Custom Title Bar ---
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


# --- Animated Custom Dialogs ---
class CustomDialog(QDialog):
    closing = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.Dialog)
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


# --- Draggable/Droppable Tree Widgets ---
class DraggableTree(QTreeWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setDragEnabled(True)
        self.setSelectionMode(QTreeWidget.SelectionMode.ExtendedSelection)
        self.setDragDropMode(QTreeWidget.DragDropMode.DragOnly)
        self.setIndentation(0)

    def startDrag(self, supportedActions):
        drag = QDrag(self)
        mime_data = QMimeData()

        item_names = [item.text(0) for item in self.selectedItems()]
        mime_data.setText("\n".join(item_names))
        drag.setMimeData(mime_data)

        pixmap = _create_drag_pixmap(item_names, self.palette())
        drag.setPixmap(pixmap)

        drag.setHotSpot(QPoint(-10, -2))

        drag.exec(supportedActions)


class DroppableTree(QTreeWidget):
    ingredient_dropped_in = pyqtSignal(list)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAcceptDrops(True)
        self.setDragDropMode(QTreeWidget.DragDropMode.DropOnly)
        self.setIndentation(0)

    def dragEnterEvent(self, event):
        if event.mimeData().hasText():
            event.acceptProposedAction()

    def dragMoveEvent(self, event):
        if event.mimeData().hasText():
            event.acceptProposedAction()

    def dropEvent(self, event):
        if event.mimeData().hasText():
            item_names = event.mimeData().text().split("\n")
            self.ingredient_dropped_in.emit(item_names)
            event.acceptProposedAction()


class DragAndDropTree(DroppableTree):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setDragEnabled(True)
        self.setSelectionMode(QTreeWidget.SelectionMode.ExtendedSelection)
        self.setDragDropMode(QTreeWidget.DragDropMode.DragDrop)
        self.setIndentation(0)

    def startDrag(self, supportedActions):
        drag = QDrag(self)
        mime_data = QMimeData()

        item_names = [item.text(0) for item in self.selectedItems()]
        mime_data.setText("\n".join(item_names))
        drag.setMimeData(mime_data)

        pixmap = _create_drag_pixmap(item_names, self.palette())
        drag.setPixmap(pixmap)

        drag.setHotSpot(QPoint(-10, -2))

        drag.exec(supportedActions)


# --- Animated Stacked Widget ---
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


# --- PDF Generation Class ---
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


# --- Animated Splash Screen with Loading Bar (ADDED) ---
class AnimatedSplashScreen(QWidget):
    def __init__(self, pixmap, version_text, duration_ms=2500):
        super().__init__()
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