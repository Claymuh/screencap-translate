import threading

from PIL import ImageQt
from PySide6.QtCore import Qt, QRectF, Signal, QTimer, QRect
from PySide6.QtGui import QPen, QBrush, QColor, QPainter, QPixmap, QAction, QTransform, QScreen, QWheelEvent, QPalette
from PySide6.QtWidgets import QApplication, QMainWindow, QGraphicsScene, QGraphicsView, QWidget, QVBoxLayout, QSlider, \
    QMenuBar, QFileDialog, QPlainTextEdit, QHBoxLayout, QLabel, QPushButton, QSplitter, QComboBox, \
    QGridLayout, QDoubleSpinBox, QGraphicsRectItem, QGraphicsItem, QCheckBox
from pynput import keyboard
import numpy as np

import config
import st.ocr
import st.translate
import st.image_process


class MainWindow(QMainWindow):
    take_screenshot_signal = Signal()
    ocr_signal = Signal()
    translate_signal = Signal()
    open_overlay_window_signal = Signal()

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
        self.auto_screenshot_timer.timeout.connect(self.screenshot_timer_event)

        self.timers = {}  # Ephemeral timers for temporary highlighting, etc.

        self.take_screenshot_signal.connect(self.take_screenshot)
        #self.take_screenshot_signal.connect(self.bring_to_foreground)
        self.ocr_signal.connect(self.ocr_image_selection)
        self.translate_signal.connect(self.translate_text)
        self.open_overlay_window_signal.connect(self.open_subwindow)

        # Start the global hotkeys listener thread
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

        # Always on top menu entry
        self.screenshot_overlay_action = QAction("Overlay", self)
        self.screenshot_overlay_action.triggered.connect(self.open_overlay_window_signal)
        self.window_menu.addAction(self.screenshot_overlay_action)

    def set_up_left_widget(self):

        widget_left = QWidget()

        # Set up screen select ComboBox
        self.screen_select_label = QLabel("Screen", widget_left)
        self.screen_select_box = QComboBox(widget_left)
        self.screen_select_box.addItems(map(lambda x: x.name(), self.screen_list))

        # Set up screenshot button
        self.screenshot_button = QPushButton("Take Screenshot", widget_left)
        self.screenshot_button.clicked.connect(self.take_screenshot)

        self.auto_screenshot_button = QPushButton("Auto screenshot", widget_left)
        self.auto_screenshot_button.clicked.connect(self.toggle_auto_screenshot)
        self.auto_screenshot_button.setCheckable(True)

        self.auto_screenshot_interval_label = QLabel("Interval", widget_left)

        self.auto_screenshot_interval_spinbox = QDoubleSpinBox(widget_left)
        self.auto_screenshot_interval_spinbox.setMinimum(0.1)
        self.auto_screenshot_interval_spinbox.setSuffix(" s")
        self.auto_screenshot_interval_spinbox.setValue(1.0)
        self.auto_screenshot_interval_spinbox.setDecimals(1)
        self.auto_screenshot_interval_spinbox.valueChanged.connect(self.update_timer_interval)

        # Set up image display widget
        self.graphics_view = CustomGraphicsView(widget_left)

        # Set up zoom slider
        self.zoom_slider = QSlider(Qt.Horizontal, widget_left)
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

        # Set up and populate dropdown menus
        self.ocr_lang_combobox = QComboBox(self.central_widget)
        self.ocr_lang_combobox.insertItems(0, st.ocr.get_available_ocr_languages())
        self.translation_lang_combobox = QComboBox(self.central_widget)
        self.translation_lang_combobox.insertItems(0, st.translate.DEEPL_LANGUAGES.keys())

        # set up labels
        self.ocr_label = QLabel("OCR")
        self.ocr_label.setAlignment(Qt.AlignCenter)
        self.translated_label = QLabel("Translation")
        self.translated_label.setAlignment(Qt.AlignCenter)

        # Set up buttons & checkboxes
        self.ocr_button = QPushButton("OCR", self)
        self.ocr_button.clicked.connect(self.ocr_image_selection)

        self.auto_ocr_checkbox = QCheckBox("Auto", self)

        self.translate_button = QPushButton("Translate!", self)
        self.translate_button.clicked.connect(self.translate_text)

        self.auto_translate_checkbox = QCheckBox("Auto", self)

        # Layout of the side bar
        central_widget = QWidget()

        layout_ocr_menu = QHBoxLayout()
        layout_ocr_menu.addWidget(self.ocr_lang_combobox)
        layout_ocr_menu.addStretch()
        layout_ocr_menu.addWidget(self.ocr_button)
        layout_ocr_menu.addStretch()
        layout_ocr_menu.addWidget(self.auto_ocr_checkbox)

        layout_translate_menu = QHBoxLayout()
        layout_translate_menu.addWidget(self.translation_lang_combobox)
        layout_translate_menu.addStretch()
        layout_translate_menu.addWidget(self.translate_button)
        layout_translate_menu.addStretch()
        layout_translate_menu.addWidget(self.auto_translate_checkbox)

        layout_toplevel = QVBoxLayout(central_widget)
        layout_toplevel.addWidget(self.ocr_label)
        layout_toplevel.addLayout(layout_ocr_menu)
        layout_toplevel.addWidget(self.ocr_widget)
        layout_toplevel.addWidget(self.translated_label)
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
                {config.HOTKEY_SCREENSHOT: self.take_screenshot_signal.emit,
                 config.HOTKEY_OCR: self.ocr_signal.emit,
                 config.HOTKEY_TRANSLATE: self.translate_signal.emit,
                 config.HOTKEY_OVERLAY: self.open_overlay_window_signal.emit}
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

    def screenshot_timer_event(self):
        self.take_screenshot()
        if self.auto_ocr_checkbox.isChecked() and self.graphics_view.has_selection_changed(0.98):
            self.ocr_image_selection()
            self.highlight_widget_temporarily(self.ocr_widget, 500)
            if self.auto_translate_checkbox.isChecked():
                self.translate_text()
                self.highlight_widget_temporarily(self.translated_widget, 500)
        self.scroll_histories_to_bottom()

    def scroll_histories_to_bottom(self):
        scrollbar_ocr = self.ocr_history_widget.verticalScrollBar()
        scrollbar_ocr.setValue(scrollbar_ocr.maximum())
        scrollbar_translated = self.translated_history_widget.verticalScrollBar()
        scrollbar_translated.setValue(scrollbar_translated.maximum())

    def highlight_widget_temporarily(self, widget, time=500):
        widget.setStyleSheet("border: 1px solid red")
        self.timers[widget] = QTimer()
        self.timers[widget].setSingleShot(True)
        self.timers[widget].timeout.connect(lambda: self.reset_stylesheet_for_widget(widget))
        self.timers[widget].start(time)

    def reset_stylesheet_for_widget(self, widget):
        widget.setStyleSheet("")

    def ocr_image_selection(self):
        self.ocr_text = self.graphics_view.ocr_selection(self.ocr_lang_combobox.currentText())
        self.ocr_text_history += self.ocr_text + "\n\n"
        self.ocr_widget.setPlainText(self.ocr_text)
        self.ocr_history_widget.setPlainText(self.ocr_text_history)

    def ocr_image(self):
        self.ocr_text = self.graphics_view.ocr_whole_pixmap(self.ocr_lang_combobox.currentText())
        self.ocr_text_history += self.ocr_text + "\n\n"
        self.ocr_widget.setPlainText(self.ocr_text)
        self.ocr_history_widget.setPlainText(self.ocr_text_history)

    def translate_text(self):
        if self.ocr_text:
            self.translated_text = st.translate.translate_text_deepl(self.ocr_text,
                                                                     api_key=config.DEEPL_KEY,
                                                                     target_lang=self.translation_lang_combobox.currentText())
            self.translated_text_history += self.translated_text + "\n\n"
            self.translated_widget.setPlainText(self.translated_text)
            self.translated_history_widget.setPlainText(self.translated_text_history)

    def open_subwindow(self):
        screen = self.screen_list[self.screen_select_box.currentIndex()]
        self.subwindow = ScreenShotTool(screen)
        self.subwindow.screenshot_taken_signal.connect(lambda x: self.graphics_view.update_pixmap(x))
        self.subwindow.screenshot_taken_signal.connect(self.ocr_image)


class CustomGraphicsView(QGraphicsView):
    def __init__(self, parent=None):
        super().__init__(parent)

        self.MIN_ZOOM = 0.1
        self.MAX_ZOOM = 2

        self.selection_has_changed = False

        self.setScene(QGraphicsScene(self))

        self.image_item = self.scene().addPixmap(QPixmap())
        self.old_selection_pixmap = None

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
        zoom_factor = 1.25
        if event.modifiers() == Qt.ControlModifier:
            if event.angleDelta().y() > 0:
                if self.transform().m11() * (zoom_factor) < self.MAX_ZOOM:
                    self.scale(zoom_factor, zoom_factor)
            else:
                if self.transform().m11() * (1 / zoom_factor) > self.MIN_ZOOM:
                    self.scale(1 / zoom_factor, 1 / zoom_factor)
            self.topLevelWidget().zoom_slider.setValue(int(self.transform().m11() * 100))
        else:
            super().wheelEvent(event)

    def update_pixmap(self, new_pixmap):
        self.old_selection_pixmap = self.get_selection_pixmap().copy()  # save a copy of the pixmap for comparison
        self.image_item.setPixmap(new_pixmap)
        self.scene().setSceneRect(QRectF(new_pixmap.rect()))
        self.fit_in_view()
        self.selection_has_changed = self.has_selection_changed()

    def ocr_whole_pixmap(self, lang: str = "") -> str:
        image = np.array(ImageQt.fromqpixmap(self.image_item.pixmap()))  # Convert to numpy array that is compatible with tesseract
        extracted_text = st.ocr.ocr_text(image, to_lang=lang, config=r'--psm 6')
        return extracted_text

    def ocr_selection(self, lang: str = "") -> str:
        selection = self.get_selection_pixmap()
        if not selection.isNull():
            image = np.array(ImageQt.fromqpixmap(selection))  # Convert to numpy array that is compatible with tesseract
            extracted_text = st.ocr.ocr_text(image, to_lang=lang, config=r'--psm 6')
            return extracted_text
        return ""

    def fit_in_view(self):
        self.fitInView(self.image_item, Qt.KeepAspectRatio)

    def has_selection_changed(self, threshold: float = 0.98):
        if not self.old_selection_pixmap:
            return True
        old = np.array(ImageQt.fromqpixmap(self.old_selection_pixmap))
        new = np.array(ImageQt.fromqpixmap(self.get_selection_pixmap()))
        if old.shape != new.shape:
            return True
        similarity = st.image_process.get_image_similarity(old, new)
        return similarity < threshold

    def get_selection_pixmap(self):
        selected_image = self.image_item.pixmap()
        return selected_image.copy(self.rectangle.sceneBoundingRect().toAlignedRect())

class SelectionRectangle(QGraphicsRectItem):
    def __init__(self, *args):
        super().__init__(*args)

        self.handles = []

        self.setFlag(QGraphicsItem.ItemIsMovable, True)
        #self.setFlag(QGraphicsItem.ItemIsSelectable, True)
        self.setBrush(QBrush(QColor(100, 100, 200, 100)))
        self.setPen(QPen(Qt.black, 2))

    def add_handle(self, size=15):
        # Bottom right handle
        xy_br = self.boundingRect().bottomRight()
        handle_br = DragHandle(xy_br.x()-size/2, xy_br.y()-size/2, size, size, parent=self)
        self.handles.append(handle_br)

        # Top left handle
        xy_tl = self.boundingRect().topLeft()
        handle_tl = DragHandle(xy_tl.x()-size/2, xy_tl.y()-size/2, size, size, parent=self)
        self.handles.append(handle_tl)

    def resize_to_handle_pos(self):
        for handle in self.handles:
            handle_pos = handle.sceneBoundingRect()
            new_rect = self.rect()

            if handle == self.handles[0]:  # Bottom right handle
                new_rect.setBottomRight(handle_pos.center() - self.scenePos())
            elif handle == self.handles[1]:  # Top left handle
                new_rect.setTopLeft(handle_pos.center() - self.scenePos())

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


class ScreenShotTool(QWidget):
    screenshot_taken_signal = Signal(QPixmap)

    def __init__(self, screen):
        super().__init__()
        self.screen: QScreen = screen
        self.initUI()
        self.start = None
        self.end = None

    def initUI(self):
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Dialog)
        self.setWindowState(self.windowState() | Qt.WindowFullScreen)
        self.setGeometry(self.screen.geometry())
        self.setWindowOpacity(0.1);
        self.setStyleSheet("QWidget{background: #0000AA}")
        self.show()

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Escape:
            self.close()

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.start = event.pos()

    def mouseMoveEvent(self, event):
        if self.start is not None:
            self.end = event.pos()
            self.update()

    def mouseReleaseEvent(self, event):
        if self.start is not None and self.end is not None:
            rect = QRect(self.start, self.end).normalized()
            self.setWindowOpacity(0.0)
            self.update()
            QApplication.processEvents()
            screenshot = self.screen.grabWindow(0, rect.x(), rect.y(), rect.width(), rect.height())
            self.screenshot_taken_signal.emit(screenshot)
            self.close()

    def paintEvent(self, event):
        if self.start is not None and self.end is not None:
            painter = QPainter(self)
            painter.setPen(QPen(Qt.red, 2, Qt.DashLine))
            painter.setBrush(Qt.transparent)
            painter.drawRect(QRect(self.start, self.end))
