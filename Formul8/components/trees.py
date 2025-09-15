# formul8/components/trees.py
# Contains specialized QTreeWidget subclasses for drag-and-drop functionality.

from PyQt6.QtWidgets import QTreeWidget
from PyQt6.QtGui import QDrag, QPixmap, QPainter, QFont, QFontMetrics, QPalette
from PyQt6.QtCore import Qt, QMimeData, QPoint, pyqtSignal

# --- Local Imports ---
from .widgets import ClickableHeader


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


class DraggableTree(QTreeWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setDragEnabled(True)
        self.setSelectionMode(QTreeWidget.SelectionMode.ExtendedSelection)
        self.setDragDropMode(QTreeWidget.DragDropMode.DragOnly)
        self.setIndentation(0)
        self.setHeader(ClickableHeader(Qt.Orientation.Horizontal, self))

        # --- FIX: Apply a stylesheet for perfect header text alignment ---
        self.header().setStyleSheet("""
            QHeaderView::section {
                text-align: center;
                padding: 0px 4px;
            }
        """)

    def startDrag(self, supportedActions):
        drag = QDrag(self)
        mime_data = QMimeData()

        item_names = []
        for item in self.selectedItems():
            item_data = item.data(0, Qt.ItemDataRole.UserRole)
            if item_data and 'name' in item_data:
                item_names.append(item_data['name'])

        if not item_names:
            return

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
        self.setHeader(ClickableHeader(Qt.Orientation.Horizontal, self))

        # --- FIX: Apply a stylesheet for perfect header text alignment ---
        self.header().setStyleSheet("""
            QHeaderView::section {
                text-align: center;
                padding: 0px 4px;
            }
        """)

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
        # NOTE: Inherits the custom header and its stylesheet from DroppableTree

    def startDrag(self, supportedActions):
        drag = QDrag(self)
        mime_data = QMimeData()

        item_names = []
        for item in self.selectedItems():
            item_data = item.data(0, Qt.ItemDataRole.UserRole)
            if item_data and 'name' in item_data:
                item_names.append(item_data['name'])

        if not item_names:
            return

        mime_data.setText("\n".join(item_names))
        drag.setMimeData(mime_data)

        pixmap = _create_drag_pixmap(item_names, self.palette())
        drag.setPixmap(pixmap)
        drag.setHotSpot(QPoint(-10, -2))
        drag.exec(supportedActions)