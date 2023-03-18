import os
from PySide6.QtCore import Qt, QRectF, QPointF, QLineF
from PySide6.QtGui import QPen, QBrush, QColor, QTransform, QPainter, QPixmap, QAction, QPixmap
from PySide6.QtWidgets import QApplication, QMainWindow, QGraphicsScene, QGraphicsView, QWidget, QVBoxLayout, QSlider, QMenuBar, QFileDialog, QGraphicsPixmapItem


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setup_ui()

    def setup_ui(self):
        self.setWindowTitle("Image Region Selector")
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)

        # Create a menu bar
        self.menu_bar = QMenuBar()
        self.setMenuBar(self.menu_bar)

        # Add a "File" menu to the menu bar
        self.file_menu = self.menu_bar.addMenu("File")

        # Add a "Quit" action to the "File" menu
        self.quit_action = QAction("Quit", self)
        self.quit_action.setShortcut("Ctrl+Q")
        self.quit_action.triggered.connect(self.close)
        self.file_menu.addAction(self.quit_action)
        self.open_image_action = QAction("Open Image", self)
        self.open_image_action.setShortcut("Ctrl+O")
        self.open_image_action.triggered.connect(self.open_image)
        self.file_menu.addAction(self.open_image_action)

        # Load the image
        self.image = QPixmap("example.jpg")

        # Create a QGraphicsScene and set its size to the image size
        self.scene = QGraphicsScene(self)
        self.scene.setSceneRect(QRectF(self.image.rect()))

        # Create a QGraphicsPixmapItem and add it to the scene
        self.image_item = self.scene.addPixmap(self.image)

        # Add a QGraphicsView to the central widget
        self.graphics_view = QGraphicsView(self.central_widget)
        self.graphics_view.setRenderHint(QPainter.Antialiasing)
        self.graphics_view.setScene(self.scene)

        # Add a QSlider to control the zoom level
        self.zoom_slider = QSlider(Qt.Horizontal)
        self.zoom_slider.setMinimum(1)
        self.zoom_slider.setMaximum(500)
        self.zoom_slider.setValue(100)
        self.zoom_slider.setTickInterval(10)
        self.zoom_slider.setTickPosition(QSlider.TicksBelow)

        # Connect the QSlider's valueChanged signal to a method that sets the zoom level of the QGraphicsView
        self.zoom_slider.valueChanged.connect(self.set_zoom)

        # Add the QGraphicsView and QSlider to the layout
        layout = QVBoxLayout()
        layout.addWidget(self.graphics_view)
        layout.addWidget(self.zoom_slider)
        self.central_widget.setLayout(layout)

    def set_zoom(self, value):
        factor = value / 100
        self.graphics_view.setTransform(QTransform.fromScale(factor, factor))

    def mousePressEvent(self, event):
        self.selection_start = event.scenePos()
        self.selection_rect = None

    def mouseMoveEvent(self, event):
        if event.buttons() == Qt.LeftButton:
            current_pos = event.scenePos()
            self.selection_rect = QRectF(self.selection_start, current_pos).normalized()
            self.scene.update()

    def open_image(self):
        options = QFileDialog.Options()
        options |= QFileDialog.DontUseNativeDialog
        fileName, _ = QFileDialog.getOpenFileName(self, "Open Image", "", "Image Files (*.png *.jpg *.bmp);;All Files (*)", options=options)
        if fileName:
            pixmap = QPixmap(fileName)
            self.item = QGraphicsPixmapItem(pixmap)
            self.scene.addItem(self.item)

    def mouseReleaseEvent(self, event):
        if self.selection_rect is not None:
            self.scene.removeItem(self.selection_item)
            pen = QPen(Qt.red, 2)
            self.selection_item = self.scene.addRect(self.selection_rect, pen)
            self.selection_rect = None
        else:
            item = self.scene.itemAt(event.scenePos(), QTransform())
            if item is self.image_item:
                self.scene.clearSelection()

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
        os._exit()
