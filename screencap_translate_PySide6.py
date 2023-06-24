#!/usr/bin/env python3
import sys
from PySide6.QtWidgets import QApplication
from st.qt_components import MainWindow

if __name__ == "__main__":
    app = QApplication([])
    window = MainWindow()
    window.resize(1200, 600)
    window.show()
    try:
        app.exec()
    except KeyboardInterrupt:
        sys.exit()
