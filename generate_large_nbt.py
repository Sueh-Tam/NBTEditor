
import sys
import os
import time
import random

# Add parent dir to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from nbt_core import NBTParser, NBTTag, TagType

def create_large_nbt(num_items=100000):
    root = NBTTag(TagType.COMPOUND, "Root", [])
    
    # Create a list of items
    items_list = NBTTag(TagType.LIST, "Items", [])
    
    print(f"Generating {num_items} items...")
    start_time = time.time()
    
    items = []
    for i in range(num_items):
        item = NBTTag(TagType.COMPOUND, None, [
            NBTTag(TagType.STRING, "id", f"minecraft:item_{i}"),
            NBTTag(TagType.BYTE, "Count", random.randint(1, 64)),
            NBTTag(TagType.SHORT, "Damage", random.randint(0, 100)),
            NBTTag(TagType.COMPOUND, "tag", [
                NBTTag(TagType.STRING, "Name", f"Custom Name {i}"),
                NBTTag(TagType.LIST, "Lore", [
                    NBTTag(TagType.STRING, None, f"Lore line 1 for item {i}"),
                    NBTTag(TagType.STRING, None, f"Lore line 2 for item {i}")
                ])
            ])
        ])
        items.append(item)
    
    items_list.value = items
    root.value.append(items_list)
    
    print(f"Generation took {time.time() - start_time:.2f}s")
    return root

def save_large_nbt(root, filename="large_test.nbt"):
    parser = NBTParser()
    print(f"Saving to {filename}...")
    start_time = time.time()
    parser.save(filename, root, compression='gzip')
    print(f"Save took {time.time() - start_time:.2f}s")

if __name__ == "__main__":
    root = create_large_nbt(10000) # Start with 10k for quick test
    save_large_nbt(root)
