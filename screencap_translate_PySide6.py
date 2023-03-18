import sys
from PySide6.QtCore import Qt, QRectF, QPointF, QLineF
from PySide6.QtGui import QPen, QBrush, QColor, QPainter, QPixmap, QAction, QTransform
from PySide6.QtWidgets import QApplication, QMainWindow, QGraphicsScene, QGraphicsView, QWidget, QVBoxLayout, QSlider, QMenuBar, QFileDialog, QGraphicsPixmapItem

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setup_ui()

    def setup_ui(self):
        self.setWindowTitle("Image Region Selector")
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)

        self.menu_bar = QMenuBar()
        self.setMenuBar(self.menu_bar)

        self.file_menu = self.menu_bar.addMenu("File")

        self.quit_action = QAction("Quit", self)
        self.quit_action.setShortcut("Ctrl+Q")
        self.quit_action.triggered.connect(self.close)
        self.file_menu.addAction(self.quit_action)

        self.open_image_action = QAction("Open Image", self)
        self.open_image_action.setShortcut("Ctrl+O")
        self.open_image_action.triggered.connect(self.open_image)
        self.file_menu.addAction(self.open_image_action)

        self.image = QPixmap()

        self.scene = QGraphicsScene(self)
        self.scene.setSceneRect(QRectF(self.image.rect()))

        self.image_item = self.scene.addPixmap(self.image)

        self.graphics_view = CustomGraphicsView(self.central_widget)
        self.graphics_view.setRenderHint(QPainter.Antialiasing)
        self.graphics_view.setScene(self.scene)

        self.zoom_slider = QSlider(Qt.Horizontal)
        self.zoom_slider.setMinimum(10)
        self.zoom_slider.setMaximum(200)
        self.zoom_slider.setValue(100)
        self.zoom_slider.setTickInterval(10)
        self.zoom_slider.setTickPosition(QSlider.TicksBelow)

        self.zoom_slider.valueChanged.connect(self.set_zoom)

        layout = QVBoxLayout()
        layout.addWidget(self.graphics_view)
        layout.addWidget(self.zoom_slider)
        self.central_widget.setLayout(layout)

        self.selection_item = None

    def set_zoom(self, value):
        factor = value / 100
        self.graphics_view.setTransform(QTransform.fromScale(factor, factor))

    def open_image(self):
        options = QFileDialog.Options()
        options |= QFileDialog.DontUseNativeDialog
        fileName, _ = QFileDialog.getOpenFileName(self, "Open Image", "", "Image Files (*.png *.jpg *.bmp);;All Files (*)", options=options)
        if fileName:
            self.load_image(fileName)

    def load_image(self, file_path):
        pixmap = QPixmap(file_path)
        self.image_item.setPixmap(pixmap)
        self.scene.setSceneRect(QRectF(pixmap.rect()))


class CustomGraphicsView(QGraphicsView):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.selection_start = None
        self.selection_rect = None

    def mousePressEvent(self, event):
        self.selection_start = self.mapToScene(event.pos())

    def mouseMoveEvent(self, event):
        if event.buttons() == Qt.LeftButton:
            current_pos = self.mapToScene(event.pos())
            self.selection_rect = QRectF(self.selection_start, current_pos).normalized()
            self.scene().update()
    
    def mouseReleaseEvent(self, event):
        if self.selection_rect is not None:
            if hasattr(self, 'selection_item') and self.selection_item is not None:
                self.scene().removeItem(self.selection_item)
            pen = QPen(Qt.red, 2)
            self.selection_item = self.scene().addRect(self.selection_rect, pen)
            self.selection_rect = None
        else:
            item = self.scene().itemAt(event.scenePos(), QTransform())
            if item is self.image_item:
                self.scene().clearSelection()

    def drawForeground(self, painter, rect):
        if self.selection_rect is not None:
            pen = QPen(Qt.red, 2)
            painter.setPen(pen)
            painter.drawRect(self.selection_rect)

if __name__ == "__main__":
    app = QApplication([])
    window = MainWindow()
    window.resize(800, 600)
    window.show()
    try:
        app.exec()
    except KeyboardInterrupt:
        sys.exit()
