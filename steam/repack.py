import os
from utils.pak_archive import PAKArchive
from steam.core.assembler import ScriptAssembler
from steam.core import seen8500, seen8501


script_file = 'SCRIPT/SCRIPT_steam.PAK'
new_script_file = './SCRIPT/SCRIPT_repacked.PAK'

unpack_folder = './SCRIPT/unpacked'
disassembly_folder = './SCRIPT/disassembled'
assembly_folder = './SCRIPT/assembled'


# reassembling scripts
assembler = ScriptAssembler(disasm_folder=disassembly_folder)
assembler.assemble()
assembler.save_asm(result_folder=assembly_folder)
# processing SEEN8500 and SEEN8501 files
seen8500.assemble(disasm_path=f'{disassembly_folder}/SEEN8500.json', repack_path=f'{assembly_folder}/SEEN8500')
seen8501.assemble(disasm_path=f'{disassembly_folder}/SEEN8501.json', repack_path=f'{assembly_folder}/SEEN8501')

# copying remaining junk files
missing_files = list(set(os.listdir(unpack_folder)) - set(os.listdir(assembly_folder)))
for filename in missing_files:
    print(f"Missing file copied {filename}")
    source_path = os.path.join(unpack_folder, filename)
    target_path = os.path.join(assembly_folder, filename)
    with open(source_path, 'rb') as source_file:
        with open(target_path, 'wb') as target_file:
            target_file.write(source_file.read())

# building new SCRIPT.PAK
pak = PAKArchive(original_pak=script_file)
pak.modify_pak(output_path=new_script_file, input_dir=assembly_folder)
print(f'new file saved in {new_script_file}')
