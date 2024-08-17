from pak_archive import PAKArchive
from disassembler import ScriptDisassembler


script_file = 'SCRIPT_steam.PAK'
unpack_folder = './unpacked'
disassembly_folder = './disassembled'

# unpacking SCRIPT.PAK
pak = PAKArchive(original_file=script_file)
pak.extract(output_dir=unpack_folder)

# disassembling scripts
disassembler = ScriptDisassembler(script_folder=unpack_folder)
disassembler.disassemble()
disassembler.save_disasm(result_folder=disassembly_folder)
