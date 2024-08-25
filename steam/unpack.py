from utils.pak_archive import PAKArchive
from steam.core.disassembler import ScriptDisassembler
from steam.core import seen8500, seen8501


script_file = 'SCRIPT/SCRIPT_steam.PAK'
unpack_folder = './SCRIPT/unpacked'
disassembly_folder = './SCRIPT/disassembled'

# unpacking SCRIPT.PAK
pak = PAKArchive(original_pak=script_file)
pak.extract(output_dir=unpack_folder)

# disassembling scripts
disassembler = ScriptDisassembler(script_folder=unpack_folder)
disassembler.disassemble()
disassembler.save_disasm(result_folder=disassembly_folder)
# processing SEEN8500 and SEEN8501 files
seen8500.disassemble(seen8500_path=f'{unpack_folder}/SEEN8500', disasm_path=f'{disassembly_folder}/SEEN8500.json')
seen8501.disassemble(seen8501_path=f'{unpack_folder}/SEEN8501', disasm_path=f'{disassembly_folder}/SEEN8501.json')
