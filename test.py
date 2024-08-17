import filecmp
import os
from pak_archive import PAKArchive
from disassembler import ScriptDisassembler
from assembler import ScriptAssembler


script_file = 'SCRIPT_steam.PAK'
new_script_file = 'SCRIPT_repacked.PAK'
unpack_folder = './unpacked'
disassembly_folder = './disassembled'
assembly_folder = './assembled'


print('===Unpacking SCRIPT.PAK===')
pak = PAKArchive(original_file=script_file)
pak.extract(output_dir=unpack_folder)


print('\n===Disassembling scripts===')
disassembler = ScriptDisassembler(script_folder=unpack_folder)
disassembler.disassemble()
disassembler.save_disasm(result_folder=disassembly_folder)


print('\n===Reassembling scripts===')
assembler = ScriptAssembler(disasm_folder=disassembly_folder)
assembler.assemble()
assembler.save_asm(result_folder=assembly_folder)


print('\n===Comparison of repacked scripts===')
files = sorted(os.listdir(assembly_folder))
different_files = []

for file in sorted(os.listdir(assembly_folder)):
    original = os.path.join(unpack_folder, file)
    repacked = os.path.join(assembly_folder, file)

    if os.path.isfile(original) and os.path.isfile(repacked):
        if filecmp.cmp(original, repacked, shallow=False):
            print(f"{file} matches the original")
        else:
            different_files += file
            print(f"{file} differs from the original")

if different_files:
    print(f"\nAttention: {len(different_files)} out of {len(files)} files are different. "
          f"The following files do not match their originals:")
    for file in different_files:
        print(f"    — {file}")
else:
    print(f"\nAll {len(files)} files match their originals.")


print('\n===Copying remaining junk files===')
missing_files = list(set(os.listdir(unpack_folder)) - set(os.listdir(assembly_folder)))
for filename in missing_files:
    print(f"    — {filename}")
    source_path = os.path.join(unpack_folder, filename)
    target_path = os.path.join(assembly_folder, filename)
    with open(source_path, 'rb') as source_file:
        with open(target_path, 'wb') as target_file:
            target_file.write(source_file.read())


print('\n===Building new SCRIPT.PAK ===')
pak.modify_pak(output_path=new_script_file, input_dir=assembly_folder)
if filecmp.cmp(script_file, new_script_file, shallow=False):
    print(f"{new_script_file} matches the original {script_file}")
else:
    print(f"{new_script_file} differs from the original {script_file}")
