# LB_repack
[Русский](README.md) | English

A project for working with scripts from the PC reissue of Little Busters! English Edition (Luca System, 2017).



## Project Status
The primary goal of enabling translation of the visual novel to a new language has been achieved. 
The assembler and disassembler functions properly, producing files that are identical to the originals ones.

- Full-featured assembler and disassembler for scripts
- Unpacker and packer .PAK archives

Please note that the project intentionally supports a limited range of opcodes related to the novel's text 
(MESSAGE, SELECT, BATTLE, TASK, SAYAVOICETEXT and VARSTR_SET). 
This range may expand in future versions.


## Usage
The repository contains the original SCRIPT.PAK file from the Steam version of the game (build 1.2.4.0).

1. Unpack `SCRIPT.PAK` and disassemble the scripts:
    
    `python3 unpack.py`

    This creates two folders: `unpacked` with assembled scripts and `disassembled` with disassembled scripts.

2. Modify scripts in the disassembled folder as needed.
3. Compile scripts and generate a new `SCRIPT.PAK`:

    `python3 repack.py`

For verification, use `test.py`, which reassembles all scripts and compares them with the originals.


## Known Issues
SEEN8500 and SEEN8501 files are not currently supported due to their non-standard structure.


## Future Plans
 - Add support for the Nintendo Switch version
 - Resolve issues with SEEN8500 and SEEN8501 files

## Acknowledgments
1. [LuckSystem](https://github.com/wetor/LuckSystem) от [wetor](https://github.com/wetor) for the general idea and some information about commands.
2. [NXGameScripts](https://github.com/masagrator/NXGameScripts/tree/f0c6f0d847ea3bf7ca6f6b5b43101cdb003d52ea/Summer%20Pockets%20REFLECTION%20BLUE) от [masagrator](https://github.com/masagrator). 

masagrator's code was initially used as the basis for the project, but very little of it remains in the current version.
