# formul8/components/helpers.py
# Contains UI helper functions that are not widgets themselves.

from PyQt6.QtWidgets import QWidget, QVBoxLayout, QStackedLayout
from PyQt6.QtGui import QPixmap, QPainter, QFont, QFontMetrics, QPalette, QIcon
from PyQt6.QtCore import Qt, QByteArray
from PyQt6.QtSvg import QSvgRenderer


def create_svg_icon(svg_string, color):
    """
    Creates a QIcon from an SVG string, dynamically setting its fill color.
    """
    colored_svg = svg_string.replace('#COLOR_PLACEHOLDER#', color)
    svg_bytes = QByteArray(colored_svg.encode('utf-8'))
    renderer = QSvgRenderer(svg_bytes)
    pixmap = QPixmap(renderer.defaultSize())
    pixmap.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pixmap)
    renderer.render(painter)
    painter.end()
    return QIcon(pixmap)


def _update_fade_visibility(tree, top_fade, bottom_fade):
    """Shows or hides the fade widgets based on scroll position."""
    scrollbar = tree.verticalScrollBar()
    min_val, max_val = scrollbar.minimum(), scrollbar.maximum()

    if max_val <= min_val:
        top_fade.setVisible(False)
        bottom_fade.setVisible(False)
        return

    current_val = scrollbar.value()
    top_fade.setVisible(current_val > min_val)
    bottom_fade.setVisible(current_val < max_val)


def update_fades(tree, top_fade, bottom_fade):
    """Public function to manually trigger an update of the fade visibility."""
    _update_fade_visibility(tree, top_fade, bottom_fade)


def create_fading_tree_widget(tree_widget_class):
    """
    Creates a tree widget inside a container with fade overlays.
    """
    container = QWidget()
    stack_layout = QStackedLayout(container)
    stack_layout.setStackingMode(QStackedLayout.StackingMode.StackAll)

    tree_widget = tree_widget_class()
    tree_widget.setStyleSheet("QTreeWidget { background: transparent; border: none; }")
    tree_widget.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOn)
    tree_widget.verticalScrollBar().setStyleSheet("QScrollBar { width: 0px; }")

    overlay = QWidget()
    overlay.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
    overlay_layout = QVBoxLayout(overlay)
    overlay_layout.setContentsMargins(0, 0, 0, 0)
    overlay_layout.setSpacing(0)

    top_fade = QWidget()
    top_fade.setFixedHeight(20)
    bottom_fade = QWidget()
    bottom_fade.setFixedHeight(20)

    top_fade.setStyleSheet(
        "background-color: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 rgba(28, 31, 36, 255), stop:1 rgba(28, 31, 36, 0));")
    bottom_fade.setStyleSheet(
        "background-color: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 rgba(28, 31, 36, 0), stop:1 rgba(28, 31, 36, 255));")

    overlay_layout.addWidget(top_fade)
    overlay_layout.addStretch()
    overlay_layout.addWidget(bottom_fade)

    stack_layout.addWidget(tree_widget)
    stack_layout.addWidget(overlay)

    scrollbar = tree_widget.verticalScrollBar()
    scrollbar.valueChanged.connect(lambda: _update_fade_visibility(tree_widget, top_fade, bottom_fade))
    scrollbar.rangeChanged.connect(lambda: _update_fade_visibility(tree_widget, top_fade, bottom_fade))

    return container, tree_widget, top_fade, bottom_fade