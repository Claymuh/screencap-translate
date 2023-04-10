import sys
import threading
from PySide6.QtCore import Qt, QRectF, QPointF, QLineF, Signal
from PySide6.QtGui import QPen, QBrush, QColor, QPainter, QPixmap, QAction, QTransform, QScreen, QKeySequence, QWheelEvent
from PySide6.QtWidgets import QApplication, QMainWindow, QGraphicsScene, QGraphicsView, QWidget, QVBoxLayout, QSlider, \
    QMenuBar, QFileDialog, QGraphicsPixmapItem, QPlainTextEdit, QHBoxLayout, QLabel, QPushButton, QSplitter, QComboBox, \
    QGridLayout, QCheckBox, QDoubleSpinBox
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

        # Start the global hotkeys listener thread
        self.take_screenshot_signal.connect(self.take_screenshot)
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
        self.auto_screenshot_checkbox = QCheckBox("Auto screenshot", self)
        self.auto_screenshot_interval_label = QLabel("Interval")
        self.auto_screenshot_interval_spinbox = QDoubleSpinBox(self)
        self.auto_screenshot_interval_spinbox.setMinimum(0.1)
        self.auto_screenshot_interval_spinbox.setSuffix(" s")
        self.auto_screenshot_interval_spinbox.setValue(1.0)
        self.auto_screenshot_interval_spinbox.setDecimals(1)
        # TODO: Add signal to reset QTimer if interval is changed while timer is active

        # Set up image display widget
        self.image = QPixmap()
        self.scene = QGraphicsScene(self)
        self.scene.setSceneRect(QRectF(self.image.rect()))

        self.image_item = self.scene.addPixmap(self.image)

        self.graphics_view = CustomGraphicsView(self.central_widget)
        self.graphics_view.setRenderHint(QPainter.Antialiasing)
        self.graphics_view.setScene(self.scene)

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
        self.auto_screenshot_interval_label.setAlignment(Qt.AlignRight | Qt.AlignCenter)
        top_grid.addWidget(self.screen_select_label, 0, 0)
        top_grid.addWidget(self.screen_select_box, 1, 0)
        top_grid.addWidget(self.screenshot_button, 0, 1)
        top_grid.addWidget(self.auto_screenshot_interval_spinbox, 1, 2)
        top_grid.addWidget(self.auto_screenshot_interval_label, 1, 1)
        top_grid.addWidget(self.auto_screenshot_checkbox, 0, 2)

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

        # Set up translate button
        self.translate_button = QPushButton("Translate!", self)
        self.translate_button.clicked.connect(self.translate_text)

        # Layout of the side bar
        central_widget = QWidget()
        layout_side = QVBoxLayout(central_widget)
        layout_side.addWidget(self.ocr_label)
        layout_side.addWidget(self.ocr_widget)
        layout_side.addWidget(self.translate_button)
        layout_side.addWidget(self.translated_label)
        layout_side.addWidget(self.translated_widget)

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

    def take_screenshot(self):
        screen = self.screen_list[self.screen_select_box.currentIndex()]
        pixmap = QScreen.grabWindow(screen)
        self.image_item.setPixmap(pixmap)
        self.scene.setSceneRect(QRectF(pixmap.rect()))
        self.graphics_view.fitInView(self.image_item, Qt.KeepAspectRatio)
        self.bring_to_foreground()

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

    def update_ocr_text(self, text):
        self.ocr_text = text
        self.ocr_text_history += self.ocr_text + "\n\n"
        self.ocr_widget.setPlainText(self.ocr_text)
        self.ocr_history_widget.setPlainText(self.ocr_text_history)

    def translate_text(self):
        self.translated_text = translate_text_deepl(self.ocr_text, DEEPL_KEY)
        self.translated_text_history += self.translated_text + "\n\n"
        self.translated_widget.setPlainText(self.translated_text)
        self.translated_history_widget.setPlainText(self.translated_text_history)


class CustomGraphicsView(QGraphicsView):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.selection_start = None
        self.selection_rect = None
        self.setDragMode(QGraphicsView.ScrollHandDrag)
        self.setInteractive(True)
        self.setRenderHint(QPainter.Antialiasing, True)
        self.setRenderHint(QPainter.SmoothPixmapTransform, True)

    def mousePressEvent(self, event):
        if event.buttons() == Qt.RightButton:
            self.selection_start = self.mapToScene(event.position().toPoint())
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if event.buttons() == Qt.RightButton:
            current_pos = self.mapToScene(event.position().toPoint())
            self.selection_rect = QRectF(self.selection_start, current_pos).normalized()
            self.scene().update()
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if self.selection_rect is not None:
            if hasattr(self, 'selection_item') and self.selection_item is not None:
                self.scene().removeItem(self.selection_item)
            pen = QPen(Qt.red, 2)
            self.selection_item = self.scene().addRect(self.selection_rect, pen)
            self.ocr_selection(self.selection_rect)
            self.selection_rect = None
        super().mouseReleaseEvent(event)

    def wheelEvent(self, event: QWheelEvent) -> None:
        if event.modifiers() == Qt.ControlModifier:
            zoom_factor = 1.25 if event.angleDelta().y() > 0 else 0.8
            self.scale(zoom_factor, zoom_factor)
        else:
            super().wheelEvent(event)

    def drawForeground(self, painter, rect):
        if self.selection_rect is not None:
            pen = QPen(Qt.red, 2)
            painter.setPen(pen)
            painter.drawRect(self.selection_rect)

    def ocr_selection(self, rect):
        selected_image = self.topLevelWidget().image_item.pixmap()
        roi = selected_image.copy(rect.toAlignedRect())
        image = ImageQt.fromqpixmap(roi)  # Convert to PIL image that is compatible with tesseract
        extracted_text = ocr_text(image, to_lang='eng', config=r'--psm 6')
        self.topLevelWidget().update_ocr_text(extracted_text)



if __name__ == "__main__":
    app = QApplication([])
    window = MainWindow()
    window.resize(1200, 600)
    window.show()
    try:
        app.exec()
    except KeyboardInterrupt:
        sys.exit()
