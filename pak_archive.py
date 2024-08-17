import struct
from typing import List, Dict
from pathlib import Path


class PAKArchive:
    """
    PAK file is a custom archive format used by the Luca System Engine.
    It consists of four main sections: Header, File table, File names, and File data.
    File compression is not applied.

    1. header structure (36 bytes):
       - total header size (4 bytes): total size of header + file table + file names
       - file count (4 bytes): number of files in the archive
       - ID start (4 bytes): something for image archives
       - block size (4 bytes): used for some alignment
       - unknown1 (4 bytes): purpose unknown
       - unknown2 (4 bytes): purpose unknown
       - unknown3 (4 bytes): purpose unknown
       - unknown4 (4 bytes): purpose unknown
       - flags (4 x 1 byte): idk, just copy from original

    2. file table:
       consists of entries for each file, where each entry contains:
       - offset (4 bytes): file data offset in block units (multiply by Block Size for byte offset)
       - size (4 bytes): size of the file in bytes
        total size = 8 bytes * file count

    3. file names:
       - starts at the offset specified in the header
       - contains null-terminated ASCII strings for each file name
       - the order corresponds to the order of entries in the File Table

    4. file data:
       - raw file data stored sequentially
       - each file starts at the offset specified in its File Table entry

    some notes:
    - all multibyte integers are stored in little-endian format
    - files are not compressed within the archive
    - the format does not include any checksums or error-checking mechanisms
    """

    def __init__(self, original_file: str):
        self.file_path = original_file
        self.file_count: int = 0
        self.files: List[Dict[str, any]] = []
        self.header: Dict[str, any] = {}
        self.read_header()

    def read_header(self) -> None:
        """Read and parse the PAK file header."""
        with open(self.file_path, 'rb') as file:
            # read header data
            header = file.read(0x28)
            header_data = struct.unpack('<8I4BI', header)

            self.header = {
                'full_header_size': header_data[0],
                'file_count': header_data[1],
                'id_start': header_data[2],
                'block_size': header_data[3],
                'unknown1': header_data[4],
                'unknown2': header_data[5],
                'unknown3': header_data[6],
                'unknown4': header_data[7],
                'flags': header_data[8:12],
                'file_names_offset': header_data[12]
            }

            # read file table
            for _ in range(self.header['file_count']):
                offset, size = struct.unpack('<II', file.read(8))
                self.files.append({
                    'offset': offset * self.header['block_size'],
                    'size': size
                })

            # read file names
            file.seek(self.header['file_names_offset'])
            for i in range(self.header['file_count']):
                self.files[i]['name'] = self._read_string(file)

    @staticmethod
    def _read_string(file) -> str:
        """Read a null-terminated ASCII string."""
        result = bytearray()
        while True:
            char = file.read(1)
            if char == b'\x00':
                return result.decode('ascii')
            result.extend(char)

    @property
    def file_list(self) -> List[str]:
        """Return a list of all file names in the PAK."""
        return [file_info['name'] for file_info in self.files]

    def extract(self, output_dir: str) -> None:
        """Extract all files from the archive."""
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        with open(self.file_path, 'rb') as pak_file:
            for file_info in self.files:
                pak_file.seek(file_info['offset'])
                data = pak_file.read(file_info['size'])

                file_path = f'{output_path}/{file_info['name']}'
                with open(file_path, 'wb') as out_file:
                    out_file.write(data)

        # write file names
        with open(f'{output_path}/file_list.txt', 'w', encoding='ascii') as names_file:
            names_file.write("\n".join(self.file_list))

    def modify_pak(self, output_path: str, input_dir: str):
        """Create a new PAK file from a directory of files."""
        input_path = Path(input_dir)

        with open(input_path.joinpath('file_list.txt'), 'r', encoding='ascii') as f:
            filenames = [line.strip().split("\t")[0] for line in f]

        input_path = Path(input_dir)

        # read header from the original PAK file
        with open(self.file_path, 'rb') as original_file:
            header = original_file.read(0x28)
            header_size = struct.unpack('<I', header[:4])[0]

        if len(filenames) != self.header['file_count']:
            raise ValueError(f'File count mismatch. Expected: {self.file_count}, got: {len(filenames)}')

        # calculate file sizes and offsets
        file_sizes = []
        file_offsets = []
        current_offset = header_size // self.header['block_size']

        for filename in filenames:
            file_path = input_path / f'{filename}'
            file_size = file_path.stat().st_size
            file_sizes.append(file_size)
            file_offsets.append(current_offset)
            current_offset += -(-file_size // self.header['block_size'])

        with open(output_path, "wb") as new_file:
            new_file.write(header)

            # write file table
            for offset, size in zip(file_offsets, file_sizes):
                new_file.write(struct.pack('<II', offset, size))

            # write filenames
            for filename in filenames:
                new_file.write(filename.encode('ascii') + b"\x00")

            # pad to header size
            new_file.write(b"\x00" * (header_size - new_file.tell()))

            # write file data
            for filename, size in zip(filenames, file_sizes):
                file_path = f'{input_path}/{filename}'
                with open(file_path, 'rb') as input_file:
                    data = input_file.read()
                new_file.write(data)
                padding = -size % self.header['block_size']
                new_file.write(b'\x00' * padding)

            # why is it not in the original script? it was in others...
            # final padding to multiple of 16
            # final_padding = -new_file.tell() % 16
            # new_file.write(b'\x00' * final_padding)


if __name__ == '__main__':
    pak = PAKArchive(original_file='SCRIPT_steam.PAK')
    pak.extract(output_dir='./unpacked')
    # pak.modify_pak(input_dir="./repacked", output_path="SCRIPT_repacked.PAK")
