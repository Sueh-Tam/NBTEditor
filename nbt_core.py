
import gzip
import zlib
import struct
import io
import json
from enum import Enum

class TagType(Enum):
    END = 0
    BYTE = 1
    SHORT = 2
    INT = 3
    LONG = 4
    FLOAT = 5
    DOUBLE = 6
    BYTE_ARRAY = 7
    STRING = 8
    LIST = 9
    COMPOUND = 10
    INT_ARRAY = 11
    LONG_ARRAY = 12

class NBTTag:
    def __init__(self, tag_type, name=None, value=None):
        self.tag_type = tag_type
        self.name = name
        self.value = value

    def to_json(self):
        if self.tag_type == TagType.COMPOUND:
            return {child.name: child.to_json() for child in self.value}
        elif self.tag_type == TagType.LIST:
            return [item.to_json() if isinstance(item, NBTTag) else item for item in self.value]
        elif self.tag_type in (TagType.BYTE_ARRAY, TagType.INT_ARRAY, TagType.LONG_ARRAY):
            return list(self.value)
        else:
            return self.value

    def __repr__(self):
        return f"NBTTag({self.tag_type.name}, {self.name}, {self.value})"

class NBTParser:
    def __init__(self):
        self.total_size = 0
        self.progress_callback = None

    def load(self, file_path, progress_callback=None):
        self.progress_callback = progress_callback
        with open(file_path, 'rb') as f:
            data = f.read()

        # Detect compression
        magic = data[:2]
        if magic == b'\x1f\x8b':  # GZIP
            print("Detected GZIP compression")
            with gzip.open(io.BytesIO(data), 'rb') as f:
                content = f.read()
            compression = 'gzip'
        elif magic == b'\x78\x9c' or magic == b'\x78\x01' or magic == b'\x78\xda': # ZLIB (approx)
             # ZLIB headers can vary, but usually start with 78
             try:
                 content = zlib.decompress(data)
                 print("Detected ZLIB compression")
                 compression = 'zlib'
             except:
                 content = data
                 compression = 'none'
        else:
            content = data
            compression = 'none'

        self.stream = io.BytesIO(content)
        self.total_size = len(content)
        root = self._read_tag()
        
        # Ensure 100% progress at the end
        if self.progress_callback:
            self.progress_callback(100)
            
        return root, compression

    def save(self, file_path, root_tag, compression='none'):
        self.stream = io.BytesIO()
        self._write_tag(root_tag)
        data = self.stream.getvalue()

        if compression == 'gzip':
            with gzip.open(file_path, 'wb') as f:
                f.write(data)
        elif compression == 'zlib':
            with open(file_path, 'wb') as f:
                f.write(zlib.compress(data))
        else:
            with open(file_path, 'wb') as f:
                f.write(data)

    def _read_byte(self):
        return struct.unpack('>b', self.stream.read(1))[0]

    def _read_short(self):
        return struct.unpack('>h', self.stream.read(2))[0]

    def _read_int(self):
        return struct.unpack('>i', self.stream.read(4))[0]

    def _read_long(self):
        return struct.unpack('>q', self.stream.read(8))[0]

    def _read_float(self):
        return struct.unpack('>f', self.stream.read(4))[0]

    def _read_double(self):
        return struct.unpack('>d', self.stream.read(8))[0]

    def _read_string(self):
        length = struct.unpack('>H', self.stream.read(2))[0]
        return self.stream.read(length).decode('utf-8')

    def _read_payload(self, tag_type):
        if tag_type == TagType.BYTE: return self._read_byte()
        elif tag_type == TagType.SHORT: return self._read_short()
        elif tag_type == TagType.INT: return self._read_int()
        elif tag_type == TagType.LONG: return self._read_long()
        elif tag_type == TagType.FLOAT: return self._read_float()
        elif tag_type == TagType.DOUBLE: return self._read_double()
        elif tag_type == TagType.BYTE_ARRAY:
            length = self._read_int()
            return list(struct.unpack(f'>{length}b', self.stream.read(length)))
        elif tag_type == TagType.STRING: return self._read_string()
        elif tag_type == TagType.LIST:
            item_type_id = self._read_byte()
            item_type = TagType(item_type_id)
            length = self._read_int()
            items = []
            for _ in range(length):
                items.append(NBTTag(item_type, None, self._read_payload(item_type)))
            return items
        elif tag_type == TagType.COMPOUND:
            children = []
            while True:
                child_type_id = self._read_byte()
                if child_type_id == 0: break
                child_type = TagType(child_type_id)
                name = self._read_string()
                value = self._read_payload(child_type)
                children.append(NBTTag(child_type, name, value))
            return children
        elif tag_type == TagType.INT_ARRAY:
            length = self._read_int()
            return list(struct.unpack(f'>{length}i', self.stream.read(length * 4)))
        elif tag_type == TagType.LONG_ARRAY:
            length = self._read_int()
            return list(struct.unpack(f'>{length}q', self.stream.read(length * 8)))
        return None

    def _read_tag(self):
        # Update progress periodically
        if self.progress_callback and self.total_size > 0:
            pos = self.stream.tell()
            # Calculate integer percentage 0-100
            percent = int((pos / self.total_size) * 100)
            self.progress_callback(percent)

        # Root tag usually has a type and a name
        tag_type_id = self._read_byte()
        if tag_type_id == 0: return None
        tag_type = TagType(tag_type_id)
        name = self._read_string()
        value = self._read_payload(tag_type)
        return NBTTag(tag_type, name, value)

    def _write_byte(self, val): self.stream.write(struct.pack('>b', val))
    def _write_short(self, val): self.stream.write(struct.pack('>h', val))
    def _write_int(self, val): self.stream.write(struct.pack('>i', val))
    def _write_long(self, val): self.stream.write(struct.pack('>q', val))
    def _write_float(self, val): self.stream.write(struct.pack('>f', val))
    def _write_double(self, val): self.stream.write(struct.pack('>d', val))
    def _write_string(self, val):
        encoded = val.encode('utf-8')
        self.stream.write(struct.pack('>H', len(encoded)))
        self.stream.write(encoded)

    def _write_payload(self, tag):
        if tag.tag_type == TagType.BYTE: self._write_byte(tag.value)
        elif tag.tag_type == TagType.SHORT: self._write_short(tag.value)
        elif tag.tag_type == TagType.INT: self._write_int(tag.value)
        elif tag.tag_type == TagType.LONG: self._write_long(tag.value)
        elif tag.tag_type == TagType.FLOAT: self._write_float(tag.value)
        elif tag.tag_type == TagType.DOUBLE: self._write_double(tag.value)
        elif tag.tag_type == TagType.BYTE_ARRAY:
            self._write_int(len(tag.value))
            self.stream.write(struct.pack(f'>{len(tag.value)}b', *tag.value))
        elif tag.tag_type == TagType.STRING: self._write_string(tag.value)
        elif tag.tag_type == TagType.LIST:
            # tag.value is a list of NBTTag objects
            if not tag.value:
                self._write_byte(TagType.END.value) # Empty list type
                self._write_int(0)
            else:
                self._write_byte(tag.value[0].tag_type.value)
                self._write_int(len(tag.value))
                for item in tag.value:
                    self._write_payload(item)
        elif tag.tag_type == TagType.COMPOUND:
            for child in tag.value:
                self._write_byte(child.tag_type.value)
                self._write_string(child.name)
                self._write_payload(child)
            self._write_byte(TagType.END.value)
        elif tag.tag_type == TagType.INT_ARRAY:
            self._write_int(len(tag.value))
            self.stream.write(struct.pack(f'>{len(tag.value)}i', *tag.value))
        elif tag.tag_type == TagType.LONG_ARRAY:
            self._write_int(len(tag.value))
            self.stream.write(struct.pack(f'>{len(tag.value)}q', *tag.value))

    def _write_tag(self, tag):
        self._write_byte(tag.tag_type.value)
        self._write_string(tag.name if tag.name else "")
        self._write_payload(tag)
