# LB_repack
[Русский](README.md) | English

A project for working with scripts from [Little Busters! English Edition](https://vndb.org/v5 "リトルバスターズ！") (Luca System, 2017).
This tool supports both PC and Nintendo Switch versions of the game.


## Project Status
The primary goal of enabling translation of the visual novel to a new language has been achieved. 
The project includes:

- Full-featured assembler and disassembler for scripts
- An unpacker and packer for .PAK archives (script archives only)

The Nintendo Switch version, which is technically a completely different game running on a different engine version, is also supported.

It's important to note that the disassembler *intentionally* supports a minimal set of opcodes related to the novel's text: 
MESSAGE, SELECT, BATTLE, TASK, SAYAVOICETEXT, VARSTR_SET, and a few others.

If you believe an important opcode has been missed, please create an issue, and it will be addressed if necessary.



## Usage
The repository contains original script archives:
- SCRIPT.PAK from the Steam version of the game (build 1.2.4.0)
- SCRIPT.PAK from the Switch version of the game (title_id=0100943010310000, version=1.0.0)

1. Unpack `SCRIPT.PAK` and disassemble the scripts:
    
    `python3 unpack.py`

    This creates two folders: `unpacked` with original scripts from the archive and `disassembled` with disassembled scripts.

2. Modify scripts in the `disassembled` folder as needed.
3. Compile scripts and generate a new `SCRIPT.PAK`:

    `python3 repack.py`

For verification, use `test.py`, which reassembles all scripts and compares them with the originals. They should be identical.


## Notes
SEEN8500 and SEEN8501 files are not script files, although they look similar:

SEEN8500 contains accessory names used in character profiles and gift notifications to the protagonist.

SEEN8501 contains battle titles displayed in character profiles and at the end of each battle. 
Most titles are static, but some are generated on the fly from an adjective and a noun. 
This is partially documented in the [Japanese wiki](https://w.atwiki.jp/littlebus/pages/23.html) (see the bottom two tables).


## Acknowledgments
1. [LuckSystem](https://github.com/wetor/LuckSystem) от [wetor](https://github.com/wetor) for the general idea and some information about commands.
2. [NXGameScripts](https://github.com/masagrator/NXGameScripts/tree/f0c6f0d847ea3bf7ca6f6b5b43101cdb003d52ea/Summer%20Pockets%20REFLECTION%20BLUE) от [masagrator](https://github.com/masagrator). 

masagrator's code was initially used as the basis for the project, but very little of it remains in the current version.
