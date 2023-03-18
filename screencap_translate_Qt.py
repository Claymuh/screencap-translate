from PyQt5.QtWidgets import QApplication, QMainWindow, QGraphicsScene, QGraphicsView, QGraphicsPixmapItem, QFileDialog, QAction, QGraphicsRectItem
from PyQt5.QtGui import QPixmap, QPainter, QPen
from PyQt5.QtCore import Qt, QPointF, QRectF, QSizeF

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Image Selector")
        self.scene = QGraphicsScene()
        self.view = QGraphicsView(self.scene)
        self.setCentralWidget(self.view)

        self.create_actions()
        self.create_menus()

        # Connect mouse events to view widget
        self.view.mousePressEvent = self.mousePressEvent
        self.view.mouseMoveEvent = self.mouseMoveEvent
        self.view.mouseReleaseEvent = self.mouseReleaseEvent

        self.prev_selection_rect = None

    def create_actions(self):
        self.open_image_action = QAction("Open Image", self)
        self.open_image_action.setShortcut("Ctrl+O")
        self.open_image_action.triggered.connect(self.open_image)

    def create_menus(self):
        self.file_menu = self.menuBar().addMenu("File")
        self.file_menu.addAction(self.open_image_action)

    def open_image(self):
        options = QFileDialog.Options()
        options |= QFileDialog.DontUseNativeDialog
        fileName, _ = QFileDialog.getOpenFileName(self,"Open Image", "","Image Files (*.png *.jpg *.bmp);;All Files (*)", options=options)
        if fileName:
            pixmap = QPixmap(fileName)
            self.item = QGraphicsPixmapItem(pixmap)
            self.scene.addItem(self.item)

    def mousePressEvent(self, event):
        self.selection_start = self.view.mapToScene(event.pos())
        self.selection_rect = QGraphicsRectItem()
        self.selection_rect.setPen(QPen(Qt.red, 2, Qt.SolidLine))
        self.scene.addItem(self.selection_rect)
        self.selection_rect.setRect(QRectF(self.selection_start, QSizeF(0,0)))

    def draw_selection_rect(self):
        pen = QPen(Qt.red, 2, Qt.SolidLine)
        rect = self.get_selection_rect()
        if self.prev_selection_rect is not None:
            self.scene.removeItem(self.prev_selection_rect)
        self.prev_selection_rect = self.scene.addRect(rect, pen)

    def mouseMoveEvent(self, event):
        current_pos = self.view.mapToScene(event.pos())
        rect = QRectF(self.selection_start, current_pos).normalized()
        self.selection_rect.setRect(rect)

    def mouseReleaseEvent(self, event):
        self.selection_end = self.view.mapToScene(event.pos())
        self.draw_selection_rect()
        self.scene.removeItem(self.selection_rect)

    def get_selection_rect(self):
        x1 = min(self.selection_start.x(), self.selection_end.x())
        y1 = min(self.selection_start.y(), self.selection_end.y())
        x2 = max(self.selection_start.x(), self.selection_end.x())
        y2 = max(self.selection_start.y(), self.selection_end.y())
        return QRectF(QPointF(x1, y1), QPointF(x2, y2))


if __name__ == "__main__":
    app = QApplication([])
    window = MainWindow()
    window.resize(800, 600)
    window.show()
    app.exec_()
