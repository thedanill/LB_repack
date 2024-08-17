import os
from pak_archive import PAKArchive
from assembler import ScriptAssembler


script_file = 'SCRIPT_steam.PAK'
new_script_file = 'SCRIPT_repacked.PAK'
unpack_folder = './unpacked'
disassembly_folder = './disassembled'
assembly_folder = './assembled'


# reassembling scripts
assembler = ScriptAssembler(disasm_folder=disassembly_folder)
assembler.assemble()
assembler.save_asm(result_folder=assembly_folder)

# Copying remaining junk files
missing_files = list(set(os.listdir(unpack_folder)) - set(os.listdir(assembly_folder)))
for filename in missing_files:
    print(f"Missing file copied {filename}")
    source_path = os.path.join(unpack_folder, filename)
    target_path = os.path.join(assembly_folder, filename)
    with open(source_path, 'rb') as source_file:
        with open(target_path, 'wb') as target_file:
            target_file.write(source_file.read())

# building new SCRIPT.PAK
pak = PAKArchive(original_file=script_file)
pak.modify_pak(output_path=new_script_file, input_dir=assembly_folder)
print(f'new file saved in {new_script_file}')
