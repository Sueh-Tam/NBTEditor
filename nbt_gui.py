
import sys
import os
import json
from PySide6.QtWidgets import (QApplication, QMainWindow, QTreeWidget, QTreeWidgetItem, 
                               QFileDialog, QMenu, QMessageBox, QInputDialog, QVBoxLayout, 
                               QWidget, QLineEdit, QComboBox, QHBoxLayout, QLabel, QToolBar,
                               QSplitter, QTextEdit, QTreeWidgetItemIterator, QProgressBar)
from PySide6.QtCore import Qt, Slot, QThread, Signal
from PySide6.QtGui import QAction, QKeySequence, QIcon, QUndoStack, QUndoCommand

from nbt_core import NBTParser, NBTTag, TagType

class SearchWorker(QThread):
    finished = Signal(list) # List of matching NBTTag objects
    progress = Signal(int)

    def __init__(self, root_tag, query):
        super().__init__()
        self.root_tag = root_tag
        self.query = query.lower()
        self.max_results = 200 # Pagination limit

    def run(self):
        results = []
        if self.root_tag:
             self._search_recursive(self.root_tag, results)
        self.finished.emit(results)

    def _search_recursive(self, tag, results):
        if len(results) >= self.max_results:
            return

        # Check match
        name_match = tag.name and self.query in tag.name.lower()
        val_match = False
        
        # Optimize value check: only check primitives or short strings
        if tag.tag_type not in (TagType.COMPOUND, TagType.LIST, TagType.BYTE_ARRAY, TagType.INT_ARRAY, TagType.LONG_ARRAY):
             if str(tag.value).lower().find(self.query) != -1:
                 val_match = True
        
        if name_match or val_match:
            results.append(tag)

        # Recurse
        if tag.tag_type == TagType.COMPOUND:
            for child in tag.value:
                self._search_recursive(child, results)
                if len(results) >= self.max_results: return
        elif tag.tag_type == TagType.LIST:
            for child in tag.value:
                self._search_recursive(child, results)
                if len(results) >= self.max_results: return

class FileLoadWorker(QThread):
    progress = Signal(int)
    finished = Signal(object, str) # root_tag, compression
    error = Signal(str)

    def __init__(self, parser, file_path):
        super().__init__()
        self.parser = parser
        self.file_path = file_path

    def run(self):
        try:
            root_tag, compression = self.parser.load(self.file_path, self.progress.emit)
            self.finished.emit(root_tag, compression)
        except Exception as e:
            self.error.emit(str(e))

class EditValueCommand(QUndoCommand):
    def __init__(self, tag, item, new_value, old_value, description):
        super().__init__(description)
        self.tag = tag
        self.item = item
        self.new_value = new_value
        self.old_value = old_value

    def redo(self):
        self.tag.value = self.new_value
        self.item.setText(2, str(self.new_value))

    def undo(self):
        self.tag.value = self.old_value
        self.item.setText(2, str(self.old_value))

class DeleteTagCommand(QUndoCommand):
    def __init__(self, parent_tag, tag, index, parent_item, item, tree_widget, description):
        super().__init__(description)
        self.parent_tag = parent_tag
        self.tag = tag
        self.index = index
        self.parent_item = parent_item
        self.item = item
        self.tree_widget = tree_widget

    def redo(self):
        # Remove from data structure
        if self.parent_tag:
            if self.parent_tag.tag_type in (TagType.COMPOUND, TagType.LIST):
                if 0 <= self.index < len(self.parent_tag.value):
                    self.parent_tag.value.pop(self.index)
        
        # Remove from GUI
        if self.parent_item:
            self.parent_item.removeChild(self.item)
        else:
            index = self.tree_widget.indexOfTopLevelItem(self.item)
            self.tree_widget.takeTopLevelItem(index)

    def undo(self):
        # Restore to data structure
        if self.parent_tag:
            if self.parent_tag.tag_type in (TagType.COMPOUND, TagType.LIST):
                self.parent_tag.value.insert(self.index, self.tag)

        # Restore to GUI
        if self.parent_item:
            self.parent_item.insertChild(self.index, self.item)
        else:
            self.tree_widget.insertTopLevelItem(self.index, self.item)

class NBTEditorWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("NBT Editor Pro")
        self.resize(1200, 800)
        
        self.parser = NBTParser()
        self.current_file = None
        self.root_tag = None
        self.compression = 'none'
        self.undo_stack = QUndoStack(self)
        self.item_map = {} # Map NBTTag -> QTreeWidgetItem
        self.search_worker = None
        
        self.setup_ui()
        
    def setup_ui(self):
        # Central Widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)
        
        # Toolbar
        toolbar = QToolBar()
        self.addToolBar(toolbar)
        
        open_action = QAction("Open", self)
        open_action.setShortcut(QKeySequence.Open)
        open_action.triggered.connect(self.open_file)
        toolbar.addAction(open_action)
        
        save_action = QAction("Save", self)
        save_action.setShortcut(QKeySequence.Save)
        save_action.triggered.connect(self.save_file)
        toolbar.addAction(save_action)
        
        toolbar.addSeparator()
        
        undo_action = self.undo_stack.createUndoAction(self, "Undo")
        undo_action.setShortcut(QKeySequence.Undo)
        toolbar.addAction(undo_action)
        
        redo_action = self.undo_stack.createRedoAction(self, "Redo")
        redo_action.setShortcut(QKeySequence.Redo)
        toolbar.addAction(redo_action)

        toolbar.addSeparator()

        expand_action = QAction("Expand All", self)
        expand_action.triggered.connect(self.expand_all)
        toolbar.addAction(expand_action)

        collapse_action = QAction("Collapse All", self)
        collapse_action.triggered.connect(self.collapse_all)
        toolbar.addAction(collapse_action)
        
        # Search Bar
        search_layout = QHBoxLayout()
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search tags by name or value...")
        self.search_input.textChanged.connect(self.search_tree)
        search_layout.addWidget(QLabel("Search:"))
        search_layout.addWidget(self.search_input)
        layout.addLayout(search_layout)
        
        # Progress Bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setTextVisible(True)
        self.progress_bar.setFormat("Loading... %p%")
        self.statusBar().addPermanentWidget(self.progress_bar, 1)

        # Splitter for Tree and Value/Hex View
        splitter = QSplitter(Qt.Horizontal)
        layout.addWidget(splitter)
        
        # Tree Widget
        self.tree = QTreeWidget()
        self.tree.setHeaderLabels(["Name", "Type", "Value"])
        self.tree.setColumnWidth(0, 400)
        self.tree.setColumnWidth(1, 150)
        self.tree.setContextMenuPolicy(Qt.CustomContextMenu)
        self.tree.customContextMenuRequested.connect(self.open_context_menu)
        self.tree.itemDoubleClicked.connect(self.handle_double_click)
        self.tree.setAnimated(True) # Enable smooth animation
        splitter.addWidget(self.tree)
        
        # Shortcut for Delete
        delete_shortcut = QAction("Delete Item", self)
        delete_shortcut.setShortcut(QKeySequence.Delete)
        delete_shortcut.triggered.connect(self.delete_selected_item)
        self.addAction(delete_shortcut)
        
        # JSON Preview (Read-only for now)
        preview_layout = QVBoxLayout()
        preview_widget = QWidget()
        preview_widget.setLayout(preview_layout)
        
        preview_layout.addWidget(QLabel("JSON Preview:"))
        self.json_preview = QTextEdit()
        self.json_preview.setReadOnly(True)
        preview_layout.addWidget(self.json_preview)
        
        splitter.addWidget(preview_widget)
        splitter.setSizes([800, 400])

    def open_file(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "Open NBT File", "", "NBT Files (*.nbt *.dat *.schematic);;All Files (*)")
        if file_path:
            self.start_loading(file_path)

    def start_loading(self, file_path):
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)
        self.tree.clear()
        self.json_preview.clear()
        self.statusBar().showMessage(f"Loading {file_path}...")
        self.setEnabled(False) # Disable UI interaction

        self.worker = FileLoadWorker(self.parser, file_path)
        self.worker.progress.connect(self.progress_bar.setValue)
        self.worker.finished.connect(lambda root, comp: self.on_load_finished(file_path, root, comp))
        self.worker.error.connect(self.on_load_error)
        self.worker.start()

    def on_load_finished(self, file_path, root_tag, compression):
        self.root_tag = root_tag
        self.compression = compression
        self.current_file = file_path
        self.undo_stack.clear()
        
        self.refresh_tree()
        self.update_json_preview()
        
        self.progress_bar.setVisible(False)
        self.setEnabled(True)
        self.statusBar().showMessage(f"Loaded {file_path} ({self.compression})")
        self.worker = None

    def on_load_error(self, error_msg):
        self.progress_bar.setVisible(False)
        self.setEnabled(True)
        self.statusBar().showMessage("Load failed")
        QMessageBox.critical(self, "Error", f"Failed to load file: {error_msg}")
        self.worker = None

    def save_file(self):
        if not self.root_tag:
            return
            
        file_path = self.current_file
        if not file_path:
            file_path, _ = QFileDialog.getSaveFileName(self, "Save NBT File", "", "NBT Files (*.nbt *.dat);;All Files (*)")
        
        if file_path:
            try:
                self.parser.save(file_path, self.root_tag, self.compression)
                self.current_file = file_path
                self.statusBar().showMessage(f"Saved to {file_path}")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to save file: {str(e)}")

    def refresh_tree(self):
        self.tree.clear()
        self.item_map.clear()
        if self.root_tag:
            self.tree.setUpdatesEnabled(False)
            root_item = QTreeWidgetItem(self.tree)
            self.populate_item(root_item, self.root_tag)
            root_item.setExpanded(True)
            self.tree.setUpdatesEnabled(True)

    def populate_item(self, item, tag):
        self.item_map[id(tag)] = item
        item.setText(0, tag.name if tag.name is not None else "")
        item.setText(1, tag.tag_type.name)
        item.setData(0, Qt.UserRole, tag) # Store tag object
        
        if tag.tag_type == TagType.COMPOUND:
            item.setText(2, f"{len(tag.value)} entries")
            # Sort children by name for better UX? Or keep order? Keep order usually safer.
            for child in tag.value:
                child_item = QTreeWidgetItem(item)
                self.populate_item(child_item, child)
        elif tag.tag_type == TagType.LIST:
            item.setText(2, f"{len(tag.value)} entries")
            for i, child in enumerate(tag.value):
                child_item = QTreeWidgetItem(item)
                self.populate_item(child_item, child)
                
                # Check for ID to display
                display_text = f"[{i}]"
                if child.tag_type == TagType.COMPOUND:
                    found_id = self.find_entity_id(child)
                    if found_id:
                        display_text += f" ID: {found_id}"
                
                child_item.setText(0, display_text) # Override name with index
        elif tag.tag_type in (TagType.BYTE_ARRAY, TagType.INT_ARRAY, TagType.LONG_ARRAY):
             item.setText(2, f"Array of {len(tag.value)} items")
             # Optionally show items as children or just raw
             # Let's show first few items in value
             preview = str(tag.value[:10])
             if len(tag.value) > 10: preview += "..."
             item.setText(2, preview)
        else:
            item.setText(2, str(tag.value))
            # Mark as editable if primitive
            # Actually double click handles editing via dialog, so no need for Qt.ItemIsEditable flag which triggers inline delegate
            pass

    def find_entity_id(self, tag):
        # Search for 'id' string tag directly or inside 'nbt'/'tag' compounds
        # tag.value is a list of NBTTag objects for COMPOUND type
        if tag.tag_type != TagType.COMPOUND:
            return None

        for child in tag.value:
            if child.name == "id" and child.tag_type == TagType.STRING:
                return child.value
            
            # Check nested 'nbt' compound (common in structure files)
            if child.name == "nbt" and child.tag_type == TagType.COMPOUND:
                for grandchild in child.value:
                    if grandchild.name == "id" and grandchild.tag_type == TagType.STRING:
                        return grandchild.value
            
            # Check nested 'tag' compound (sometimes used)
            if child.name == "tag" and child.tag_type == TagType.COMPOUND:
                for grandchild in child.value:
                    if grandchild.name == "id" and grandchild.tag_type == TagType.STRING:
                        return grandchild.value
                        
            # Check 'EntityTag' (used in items spawning entities)
            if child.name == "EntityTag" and child.tag_type == TagType.COMPOUND:
                for grandchild in child.value:
                    if grandchild.name == "id" and grandchild.tag_type == TagType.STRING:
                        return grandchild.value
                        
        return None

    def update_json_preview(self):
        if self.root_tag:
            try:
                # Use QTimer to debounce if needed for large files
                json_str = json.dumps(self.root_tag.to_json(), indent=2, default=str)
                self.json_preview.setText(json_str)
            except:
                self.json_preview.setText("Error generating JSON preview")

    def handle_double_click(self, item, column):
        if column == 2:
            self.edit_item_value(item)

    def edit_item_value(self, item):
        tag = item.data(0, Qt.UserRole)
        if tag.tag_type in (TagType.COMPOUND, TagType.LIST):
            return 
        
        current_val = str(tag.value)
        
        # For arrays, we might want a different editor, but let's stick to primitives for now
        if tag.tag_type in (TagType.BYTE_ARRAY, TagType.INT_ARRAY, TagType.LONG_ARRAY):
             QMessageBox.information(self, "Info", "Array editing not supported in this version.")
             return

        new_val_str, ok = QInputDialog.getText(self, "Edit Value", f"Enter new value for {tag.tag_type.name}:", text=current_val)
        
        if ok and new_val_str != current_val:
            try:
                # Type conversion
                if tag.tag_type == TagType.BYTE: new_val = int(new_val_str)
                elif tag.tag_type == TagType.SHORT: new_val = int(new_val_str)
                elif tag.tag_type == TagType.INT: new_val = int(new_val_str)
                elif tag.tag_type == TagType.LONG: new_val = int(new_val_str)
                elif tag.tag_type == TagType.FLOAT: new_val = float(new_val_str)
                elif tag.tag_type == TagType.DOUBLE: new_val = float(new_val_str)
                elif tag.tag_type == TagType.STRING: new_val = new_val_str
                else: return

                command = EditValueCommand(tag, item, new_val, tag.value, f"Edit {tag.name}")
                self.undo_stack.push(command)
                self.update_json_preview()
                
            except ValueError:
                QMessageBox.warning(self, "Invalid Input", "Please enter a valid value for this type.")

    def search_tree(self, text):
        if not self.root_tag:
            return

        # Cancel previous search if running
        if self.search_worker and self.search_worker.isRunning():
            self.search_worker.terminate()
            self.search_worker.wait()

        if not text:
            # Show all
            self.tree.setUpdatesEnabled(False)
            # Iterate all items to show them is slow, but cleaner than tracking hidden state manually
            # Actually, collapsing all except root might be faster?
            # Or just setHidden(False) on all?
            # For 100k items, iteration is slow.
            # Best is to unhide only what we hid? 
            # Let's iterate top level and their children... still slow.
            # Faster: Collapse all.
            self.collapse_all()
            self.tree.topLevelItem(0).setExpanded(True)
            self.tree.setUpdatesEnabled(True)
            return

        # Start background search
        self.search_worker = SearchWorker(self.root_tag, text)
        self.search_worker.finished.connect(self.on_search_finished)
        self.search_worker.start()

    def on_search_finished(self, results):
        self.tree.setUpdatesEnabled(False)
        self.collapse_all() # Collapse everything first (or hide everything?)
        
        # Hiding everything is tricky because QTreeWidget doesn't have "hide all" efficiently
        # Strategy: 
        # 1. Collapse all (fast)
        # 2. For each result, expand path to root and select/highlight
        
        if not results:
             self.statusBar().showMessage("No matches found")
             self.tree.setUpdatesEnabled(True)
             return

        count = 0
        for tag in results:
            item = self.item_map.get(id(tag))
            if item:
                item.setHidden(False) # Ensure visible
                # Expand parents
                parent = item.parent()
                while parent:
                    parent.setHidden(False)
                    parent.setExpanded(True)
                    parent = parent.parent()
                count += 1
        
        self.tree.setUpdatesEnabled(True)
        self.statusBar().showMessage(f"Found {count} matches (showing first {len(results)})")

    def open_context_menu(self, position):
        item = self.tree.itemAt(position)
        if not item:
            return
            
        menu = QMenu()
        edit_action = menu.addAction("Edit Value")
        delete_action = menu.addAction("Delete Item")
        menu.addSeparator()
        
        # Add Export JSON for this subtree
        export_json_action = menu.addAction("Export Subtree as JSON")
        export_xml_action = menu.addAction("Export Subtree as XML")
        menu.addSeparator()
        
        expand_rec_action = menu.addAction("Expand Recursively")
        collapse_rec_action = menu.addAction("Collapse Recursively")
        
        action = menu.exec(self.tree.viewport().mapToGlobal(position))
        
        if action == edit_action:
            self.edit_item_value(item)
        elif action == delete_action:
            self.delete_selected_item()
        elif action == export_json_action:
            self.export_subtree_json(item)
        elif action == export_xml_action:
            self.export_subtree_xml(item)
        elif action == expand_rec_action:
            self.expand_recursive(item, True)
        elif action == collapse_rec_action:
            self.expand_recursive(item, False)

    def expand_recursive(self, item, expand):
        item.setExpanded(expand)
        for i in range(item.childCount()):
            self.expand_recursive(item.child(i), expand)

    def delete_selected_item(self):
        item = self.tree.currentItem()
        if not item:
            return

        tag = item.data(0, Qt.UserRole)
        parent_item = item.parent()
        
        # Identify parent tag and index
        parent_tag = None
        index = -1
        
        if parent_item:
            parent_tag = parent_item.data(0, Qt.UserRole)
            index = parent_item.indexOfChild(item)
        elif item == self.tree.topLevelItem(0):
            # Root item
            QMessageBox.warning(self, "Warning", "Cannot delete the root tag.")
            return

        if not parent_tag:
            return

        # Confirm deletion
        confirm = QMessageBox.question(
            self, 
            "Confirm Deletion", 
            f"Are you sure you want to delete '{tag.name if tag.name else 'Item'}' and all its children?",
            QMessageBox.Yes | QMessageBox.No
        )
        
        if confirm == QMessageBox.Yes:
            try:
                command = DeleteTagCommand(
                    parent_tag, tag, index, parent_item, item, self.tree, 
                    f"Delete {tag.name if tag.name else 'Item'}"
                )
                self.undo_stack.push(command)
                self.update_json_preview()
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to delete item: {e}")

    def export_subtree_json(self, item):
        tag = item.data(0, Qt.UserRole)
        if tag:
            file_path, _ = QFileDialog.getSaveFileName(self, "Export JSON", "", "JSON Files (*.json)")
            if file_path:
                try:
                    with open(file_path, 'w') as f:
                        json.dump(tag.to_json(), f, indent=2, default=str)
                    QMessageBox.information(self, "Success", "Exported successfully.")
                except Exception as e:
                    QMessageBox.critical(self, "Error", f"Failed to export: {e}")

    def export_subtree_xml(self, item):
        tag = item.data(0, Qt.UserRole)
        if tag:
            file_path, _ = QFileDialog.getSaveFileName(self, "Export XML", "", "XML Files (*.xml)")
            if file_path:
                try:
                    import xml.etree.ElementTree as ET
                    
                    def build_xml(tag_obj):
                        elem = ET.Element(tag_obj.tag_type.name)
                        if tag_obj.name:
                            elem.set("name", tag_obj.name)
                        
                        if tag_obj.tag_type == TagType.COMPOUND:
                            for child in tag_obj.value:
                                elem.append(build_xml(child))
                        elif tag_obj.tag_type == TagType.LIST:
                            elem.set("count", str(len(tag_obj.value)))
                            for child in tag_obj.value:
                                elem.append(build_xml(child))
                        else:
                            elem.text = str(tag_obj.value)
                        return elem

                    root_elem = build_xml(tag)
                    tree = ET.ElementTree(root_elem)
                    tree.write(file_path, encoding="utf-8", xml_declaration=True)
                    QMessageBox.information(self, "Success", "Exported successfully.")
                except Exception as e:
                    QMessageBox.critical(self, "Error", f"Failed to export: {e}")

    def expand_all(self):
        self.tree.expandAll()

    def collapse_all(self):
        self.tree.collapseAll()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = NBTEditorWindow()
    window.show()
    sys.exit(app.exec())
