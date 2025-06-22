import sys
import os
from PySide6.QtWidgets import QApplication
from gui import MotionMagnificationApp

if __name__ == "__main__":
    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    
    app = QApplication(sys.argv)
    window = MotionMagnificationApp()
    window.show()
    sys.exit(app.exec())
