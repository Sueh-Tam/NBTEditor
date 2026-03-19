
import sys
import os

# Add the current directory to sys.path to allow imports
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(current_dir)

from nbt_gui import NBTEditorWindow
from PySide6.QtWidgets import QApplication

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = NBTEditorWindow()
    window.show()
    sys.exit(app.exec())
