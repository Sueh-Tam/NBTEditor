
import os
import sys
import unittest
import struct
import io

# Add parent dir to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from nbt_core import NBTParser, NBTTag, TagType

class TestNBTParser(unittest.TestCase):
    def setUp(self):
        self.parser = NBTParser()

    def test_primitive_tags(self):
        # Create a simple compound with primitives
        root = NBTTag(TagType.COMPOUND, "Root", [])
        byte_tag = NBTTag(TagType.BYTE, "ByteVal", 127)
        short_tag = NBTTag(TagType.SHORT, "ShortVal", 32000)
        int_tag = NBTTag(TagType.INT, "IntVal", 123456789)
        long_tag = NBTTag(TagType.LONG, "LongVal", 1234567890123456789)
        float_tag = NBTTag(TagType.FLOAT, "FloatVal", 3.14159)
        double_tag = NBTTag(TagType.DOUBLE, "DoubleVal", 1.23456789)
        string_tag = NBTTag(TagType.STRING, "StringVal", "Hello NBT")
        
        root.value = [byte_tag, short_tag, int_tag, long_tag, float_tag, double_tag, string_tag]
        
        # Save to memory
        self.parser.save("test_primitive.nbt", root, compression='none')
        
        # Load back
        loaded_root, comp = self.parser.load("test_primitive.nbt")
        self.assertEqual(comp, 'none')
        self.assertEqual(loaded_root.name, "Root")
        self.assertEqual(len(loaded_root.value), 7)
        
        # Verify values
        val_map = {tag.name: tag for tag in loaded_root.value}
        self.assertEqual(val_map["ByteVal"].value, 127)
        self.assertEqual(val_map["ShortVal"].value, 32000)
        self.assertEqual(val_map["IntVal"].value, 123456789)
        self.assertEqual(val_map["LongVal"].value, 1234567890123456789)
        self.assertAlmostEqual(val_map["FloatVal"].value, 3.14159, places=4)
        self.assertAlmostEqual(val_map["DoubleVal"].value, 1.23456789, places=7)
        self.assertEqual(val_map["StringVal"].value, "Hello NBT")
        
        # Clean up
        if os.path.exists("test_primitive.nbt"):
            os.remove("test_primitive.nbt")

    def test_compression_gzip(self):
        root = NBTTag(TagType.COMPOUND, "Root", [])
        root.value.append(NBTTag(TagType.STRING, "Test", "Compressed"))
        
        self.parser.save("test_gzip.nbt", root, compression='gzip')
        
        loaded_root, comp = self.parser.load("test_gzip.nbt")
        self.assertEqual(comp, 'gzip')
        self.assertEqual(loaded_root.value[0].value, "Compressed")
        
        if os.path.exists("test_gzip.nbt"):
            os.remove("test_gzip.nbt")

    def test_list_tag(self):
        root = NBTTag(TagType.COMPOUND, "Root", [])
        list_tag = NBTTag(TagType.LIST, "MyList", [])
        # List of Ints
        items = [
            NBTTag(TagType.INT, None, 1),
            NBTTag(TagType.INT, None, 2),
            NBTTag(TagType.INT, None, 3)
        ]
        list_tag.value = items
        root.value.append(list_tag)
        
        self.parser.save("test_list.nbt", root)
        loaded_root, _ = self.parser.load("test_list.nbt")
        
        loaded_list = loaded_root.value[0]
        self.assertEqual(loaded_list.tag_type, TagType.LIST)
        self.assertEqual(len(loaded_list.value), 3)
        self.assertEqual(loaded_list.value[0].value, 1)
        self.assertEqual(loaded_list.value[2].value, 3)
        
        if os.path.exists("test_list.nbt"):
            os.remove("test_list.nbt")

    def test_deletion(self):
        # Test logic for deleting items from Compound and List
        
        # 1. Deletion from Compound
        root = NBTTag(TagType.COMPOUND, "Root", [])
        child1 = NBTTag(TagType.STRING, "Child1", "Val1")
        child2 = NBTTag(TagType.INT, "Child2", 2)
        root.value = [child1, child2]
        
        # Simulate deleting Child1
        # Find index
        idx = root.value.index(child1)
        root.value.pop(idx)
        
        self.assertEqual(len(root.value), 1)
        self.assertEqual(root.value[0].name, "Child2")
        
        # Undo (insert back)
        root.value.insert(idx, child1)
        self.assertEqual(len(root.value), 2)
        self.assertEqual(root.value[0].name, "Child1")
        
        # 2. Deletion from List
        list_tag = NBTTag(TagType.LIST, "MyList", [])
        item1 = NBTTag(TagType.INT, None, 10)
        item2 = NBTTag(TagType.INT, None, 20)
        list_tag.value = [item1, item2]
        
        # Simulate deleting item at index 1
        deleted_item = list_tag.value.pop(1)
        self.assertEqual(deleted_item.value, 20)
        self.assertEqual(len(list_tag.value), 1)
        
        # Undo
        list_tag.value.insert(1, deleted_item)
        self.assertEqual(len(list_tag.value), 2)
        self.assertEqual(list_tag.value[1].value, 20)

if __name__ == '__main__':
    unittest.main()
