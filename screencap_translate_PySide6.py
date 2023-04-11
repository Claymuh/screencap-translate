import sys
import threading
from PySide6.QtCore import Qt, QRectF, QPointF, QLineF, Signal, QTimer, QSizeF
from PySide6.QtGui import QPen, QBrush, QColor, QPainter, QPixmap, QAction, QTransform, QScreen, QKeySequence, QWheelEvent, QMouseEvent
from PySide6.QtWidgets import QApplication, QMainWindow, QGraphicsScene, QGraphicsView, QWidget, QVBoxLayout, QSlider, \
    QMenuBar, QFileDialog, QGraphicsPixmapItem, QPlainTextEdit, QHBoxLayout, QLabel, QPushButton, QSplitter, QComboBox, \
    QGridLayout, QCheckBox, QDoubleSpinBox, QGraphicsRectItem, QGraphicsItem
from PIL import ImageQt
from pynput import keyboard

from st.ocr import ocr_text
from st.translate import translate_text_deepl

from config import DEEPL_KEY, HOTKEY

class MainWindow(QMainWindow):
    take_screenshot_signal = Signal()

    def __init__(self):
        super().__init__()
        self.screen_list = QApplication.screens()
        self.set_up_menu_bar()
        self.setup_ui()

        self.ocr_text = ""
        self.ocr_text_history = ""
        self.translated_text = ""
        self.translated_text_history = ""

        self.auto_screenshot_timer = QTimer(self)
        self.auto_screenshot_timer.setInterval(1000)
        self.auto_screenshot_timer.timeout.connect(self.take_screenshot)

        # Start the global hotkeys listener thread
        self.take_screenshot_signal.connect(self.take_screenshot)
        self.take_screenshot_signal.connect(self.bring_to_foreground)
        self.listener = threading.Thread(target=self.set_up_hotkeys)
        self.listener.daemon = True
        self.listener.start()


    def setup_ui(self):
        self.setWindowTitle("Screenshot Translator")
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.main_splitter = QSplitter()

        self.set_up_left_widget()
        self.set_up_central_widget()
        self.set_up_right_widget()

        main_layout = QVBoxLayout()
        main_layout.addWidget(self.main_splitter)
        self.central_widget.setLayout(main_layout)

    def set_up_menu_bar(self):
        # Set up the menu bar
        self.menu_bar = QMenuBar()
        self.setMenuBar(self.menu_bar)

        self.file_menu = self.menu_bar.addMenu("File")
        self.window_menu = self.menu_bar.addMenu("Window")

        # Quit menu entry
        self.quit_action = QAction("Quit", self)
        self.quit_action.setShortcut("Ctrl+Q")
        self.quit_action.triggered.connect(self.close)
        self.file_menu.addAction(self.quit_action)

        # Open image menu entry
        self.open_image_action = QAction("Open Image", self)
        self.open_image_action.setShortcut("Ctrl+O")
        self.open_image_action.triggered.connect(self.open_image)
        self.file_menu.addAction(self.open_image_action)

        # Always on top menu entry
        self.always_on_top_action = QAction("Always on top", self)
        self.always_on_top_action.setCheckable(True)
        self.always_on_top_action.triggered.connect(self.toggle_always_on_top)
        self.window_menu.addAction(self.always_on_top_action)

    def set_up_left_widget(self):

        # Set up screen select ComboBox
        self.screen_select_label = QLabel("Screen")
        self.screen_select_box = QComboBox(self)
        self.screen_select_box.addItems(map(lambda x: x.name(), self.screen_list))

        # Set up screenshot button
        self.screenshot_button = QPushButton("Take Screenshot", self)
        self.screenshot_button.clicked.connect(self.take_screenshot)

        self.auto_screenshot_button = QPushButton("Auto screenshot", self)
        self.auto_screenshot_button.clicked.connect(self.toggle_auto_screenshot)
        self.auto_screenshot_button.setCheckable(True)

        self.auto_screenshot_interval_label = QLabel("Interval")

        self.auto_screenshot_interval_spinbox = QDoubleSpinBox(self)
        self.auto_screenshot_interval_spinbox.setMinimum(0.1)
        self.auto_screenshot_interval_spinbox.setSuffix(" s")
        self.auto_screenshot_interval_spinbox.setValue(1.0)
        self.auto_screenshot_interval_spinbox.setDecimals(1)
        self.auto_screenshot_interval_spinbox.valueChanged.connect(self.update_timer_interval)

        # Set up image display widget
        self.graphics_view = CustomGraphicsView(self.central_widget)

        # Set up zoom slider
        self.zoom_slider = QSlider(Qt.Horizontal)
        self.zoom_slider.setMinimum(10)
        self.zoom_slider.setMaximum(200)
        self.zoom_slider.setValue(100)
        self.zoom_slider.setTickInterval(10)
        self.zoom_slider.setTickPosition(QSlider.TicksBelow)

        self.zoom_slider.valueChanged.connect(self.set_zoom)

        # Layout of the top part (above the screenshot view)
        top_grid = QGridLayout()

        # Layout of the image view
        self.auto_screenshot_interval_label.setAlignment(Qt.AlignCenter)
        top_grid.addWidget(self.screen_select_label, 0, 0)
        top_grid.addWidget(self.screen_select_box, 1, 0)
        top_grid.addWidget(self.screenshot_button, 0, 1)
        top_grid.addWidget(self.auto_screenshot_interval_spinbox, 1, 2)
        top_grid.addWidget(self.auto_screenshot_interval_label, 0, 2)
        top_grid.addWidget(self.auto_screenshot_button, 1, 1)

        widget_left = QWidget()
        layout_img_view = QVBoxLayout(widget_left)
        layout_img_view.addLayout(top_grid)
        layout_img_view.addWidget(self.graphics_view)
        layout_img_view.addWidget(self.zoom_slider)

        self.main_splitter.addWidget(widget_left)

    def set_up_central_widget(self):
        # Set up OCR text edit widget
        self.ocr_widget = QPlainTextEdit(self.central_widget)
        self.ocr_widget.setReadOnly(True)

        # Set up translated text edit widget
        self.translated_widget = QPlainTextEdit(self.central_widget)
        self.translated_widget.setReadOnly(True)

        # set up labels
        self.ocr_label = QLabel("OCRed text")
        self.translated_label = QLabel("Translated text")

        # Set up buttons
        self.ocr_button = QPushButton("OCR", self)
        self.ocr_button.clicked.connect(self.ocr_image_selection)

        self.translate_button = QPushButton("Translate!", self)
        self.translate_button.clicked.connect(self.translate_text)

        # Layout of the side bar
        central_widget = QWidget()

        layout_ocr_menu = QHBoxLayout()
        layout_ocr_menu.addWidget(self.ocr_label)
        layout_ocr_menu.addWidget(self.ocr_button)

        layout_translate_menu = QHBoxLayout()
        layout_translate_menu.addWidget(self.translated_label)
        layout_translate_menu.addWidget(self.translate_button)

        layout_toplevel = QVBoxLayout(central_widget)
        layout_toplevel.addLayout(layout_ocr_menu)
        layout_toplevel.addWidget(self.ocr_widget)
        layout_toplevel.addLayout(layout_translate_menu)
        layout_toplevel.addWidget(self.translated_widget)

        self.main_splitter.addWidget(central_widget)

    def set_up_right_widget(self):
        # Set up OCR text edit widget
        self.ocr_history_widget = QPlainTextEdit(self.central_widget)
        self.ocr_history_widget.setReadOnly(True)

        # Set up translated text edit widget
        self.translated_history_widget = QPlainTextEdit(self.central_widget)
        self.translated_history_widget.setReadOnly(True)

        # set up labels
        self.ocr_history_label = QLabel("OCR history")
        self.translated_history_label = QLabel("Translated History")

        # Layout of the side bar
        right_widget = QWidget()
        layout_side = QVBoxLayout(right_widget)
        layout_side.addWidget(self.ocr_history_label)
        layout_side.addWidget(self.ocr_history_widget)
        layout_side.addWidget(self.translated_history_label)
        layout_side.addWidget(self.translated_history_widget)

        self.main_splitter.addWidget(right_widget)

    def set_up_hotkeys(self):
        with keyboard.GlobalHotKeys(
            {HOTKEY: self.take_screenshot_signal.emit}
        ) as hk:
            hk.join()

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
        self.graphics_view.fitInView(self.image_item, Qt.KeepAspectRatio)

    def bring_to_foreground(self):
        # Get window into the foreground and focus, then reset status to be able to repeat this process
        self.setWindowFlags(self.windowFlags() | Qt.WindowStaysOnTopHint)
        self.setWindowState(Qt.WindowState.WindowActive)
        self.show()  # Applies new flags
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowStaysOnTopHint)
        self.setWindowState(Qt.WindowState.WindowNoState)
        self.show()

    def toggle_always_on_top(self, checked):
        if checked:
            print("true")
            self.setWindowFlags(self.windowFlags() | Qt.WindowStaysOnTopHint)
        else:
            print("false")
            self.setWindowFlags(self.windowFlags() & ~Qt.WindowStaysOnTopHint)
        self.show()

    def toggle_auto_screenshot(self):
        if self.auto_screenshot_button.isChecked():
            self.auto_screenshot_timer.start()
        else:
            self.auto_screenshot_timer.stop()

    def update_timer_interval(self, value):
        self.auto_screenshot_timer.setInterval(value * 1000)

    def take_screenshot(self):
        screen = self.screen_list[self.screen_select_box.currentIndex()]
        pixmap = QScreen.grabWindow(screen)
        self.graphics_view.update_pixmap(pixmap)

    def ocr_image_selection(self):
        self.ocr_text = self.graphics_view.ocr_selection()
        self.ocr_text_history += self.ocr_text + "\n\n"
        self.ocr_widget.setPlainText(self.ocr_text)
        self.ocr_history_widget.setPlainText(self.ocr_text_history)

    def translate_text(self):
        if self.ocr_text:
            self.translated_text = translate_text_deepl(self.ocr_text, DEEPL_KEY)
            self.translated_text_history += self.translated_text + "\n\n"
            self.translated_widget.setPlainText(self.translated_text)
            self.translated_history_widget.setPlainText(self.translated_text_history)


class CustomGraphicsView(QGraphicsView):
    def __init__(self, parent=None):
        super().__init__(parent)

        self.setScene(QGraphicsScene(self))

        self.image_item = self.scene().addPixmap(QPixmap())
        self.scene().setSceneRect(QRectF(self.image_item.pixmap().rect()))

        self.setDragMode(QGraphicsView.ScrollHandDrag)
        self.setInteractive(True)
        self.setRenderHint(QPainter.SmoothPixmapTransform, True)

        # Create the initial selectable rectangle
        self.rectangle = SelectionRectangle(QRectF(0, 0, 500, 500))

        # Add the rectangle to the scene
        self.scene().addItem(self.rectangle)
        self.rectangle.add_handle()

    def wheelEvent(self, event: QWheelEvent) -> None:
        if event.modifiers() == Qt.ControlModifier:
            zoom_factor = 1.25 if event.angleDelta().y() > 0 else 0.8
            self.scale(zoom_factor, zoom_factor)
        else:
            super().wheelEvent(event)

    def update_pixmap(self, new_pixmap):
        self.image_item.setPixmap(new_pixmap)
        self.scene().setSceneRect(QRectF(new_pixmap.rect()))
        self.fit_in_view()

    def ocr_selection(self) -> str:
        selected_image = self.image_item.pixmap()
        if not selected_image.isNull():
            roi = selected_image.copy(self.rectangle.sceneBoundingRect().toAlignedRect())
            image = ImageQt.fromqpixmap(roi)  # Convert to PIL image that is compatible with tesseract
            extracted_text = ocr_text(image, to_lang='eng', config=r'--psm 6')
            return extracted_text
        return ""

    def fit_in_view(self):
        self.fitInView(self.image_item, Qt.KeepAspectRatio)


class SelectionRectangle(QGraphicsRectItem):
    def __init__(self, *args):
        super().__init__(*args)

        self.handle = None

        self.setFlag(QGraphicsItem.ItemIsMovable, True)
        #self.setFlag(QGraphicsItem.ItemIsSelectable, True)
        self.setBrush(QBrush(QColor(100, 100, 200, 100)))
        self.setPen(QPen(Qt.black, 2))

    def add_handle(self, size=15):
        xy = self.boundingRect().bottomRight()
        self.handle = DragHandle(xy.x()-size/2, xy.y()-size/2, size, size, parent=self)
        self.scene().addItem(self.handle)

    def resize_to_handle_pos(self):
        handle_pos = self.handle.sceneBoundingRect()
        new_rect = QRectF(0, 0, 0, 0)
        new_rect.setBottomRight(handle_pos.center() - self.scenePos())
        self.setRect(new_rect)


class DragHandle(QGraphicsRectItem):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.setBrush(QBrush(QColor(255, 255, 0)))
        self.setPen(QPen(Qt.black, 2))
        self.setFlag(QGraphicsItem.ItemIsMovable, True)
        #self.setFlag(QGraphicsItem.ItemIsSelectable, True)
        self.setCursor(Qt.SizeAllCursor)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.setBrush(QColor(255, 0, 0))
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        self.parentItem().resize_to_handle_pos()
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.setBrush(QColor(255, 255, 0))
        super().mouseReleaseEvent(event)


if __name__ == "__main__":
    app = QApplication([])
    window = MainWindow()
    window.resize(1200, 600)
    window.show()
    try:
        app.exec()
    except KeyboardInterrupt:
        sys.exit()
