import json
import os
import struct
from pathlib import Path
from typing import Dict
from utils import helpers
from utils.helpers import Charset
from collections import OrderedDict


class Script:
    def __init__(self):
        self.name: str = ''
        self.disasm: dict = {}
        self.asm: bytearray = bytearray()
        self.label_index: Dict[int, int] = {}  # original_label -> new_index in disasm


class ScriptAssembler:
    def __init__(self, disasm_folder: str):
        self.scripts = OrderedDict()
        self.current_script: str = ''  # name
        self.label_map: Dict[str, Dict[int, int]] = {}  # script_name -> {original_label: new_label}

        # load decompiled scripts
        for script_file in os.listdir(disasm_folder):
            lwr = script_file.lower()
            # fuck macOS .DS_Store
            if not (lwr.startswith('_') or lwr.startswith('seen')):
                continue
            # idk what the rest of the _-files are for
            if (lwr.startswith('_')) and (lwr not in ["_varstr.json", '_sayavoice.json', '_keyword.json']):
                continue
            # see explanation in repository description
            if 'seen8500' in lwr or 'seen8501' in lwr:
                continue

            script_path = os.path.join(disasm_folder, script_file)
            with open(script_path, 'r') as f:
                script = Script()
                script.name = script_file.replace('.json', '')
                script.disasm = json.loads(f.read())
                self.scripts[script.name] = script

        # load opcodes (line number in file = byte that encodes the opcode)
        self.opcodes = {}
        with open('./core/opcode_steam.txt') as file:
            self.opcodes = {opcode: i for i, opcode in enumerate(file.read().splitlines())}

        self.scripts = OrderedDict((key, self.scripts[key]) for key in sorted(self.scripts))

    def assemble(self):
        # first pass: calculating new offsets (labels) for goto/gosub/... instructions
        for script_name, script in self.scripts.items():
            print(f'calculate offsets for {script_name}')
            label = 0
            for cmd in script.disasm:
                new_label = label
                if script_name not in self.label_map:
                    self.label_map[script_name] = {}
                self.label_map[script_name][cmd['label']] = new_label
                command = self.make_command(data=cmd, calc_mode=True)
                label += len(command)

        # second pass: actual assembly
        for script_name, script in self.scripts.items():
            self.current_script = script.name  # for goto/gosub/... handlers
            print(f'assembling {self.current_script}')
            for cmd in script.disasm:
                command = self.make_command(data=cmd, calc_mode=False)
                script.asm += command

    def save_asm(self, result_folder: str) -> None:
        output_path = Path(result_folder)
        output_path.mkdir(parents=True, exist_ok=True)

        for script_name, script in self.scripts.items():
            file_path = os.path.join(output_path, script_name)
            with open(file_path, "wb") as new_file:
                new_file.write(script.asm)

    def make_command(self, data, calc_mode=False):
        handlers_table = {
            'MESSAGE': self.message_handler,
            'SELECT': self.select_handler,
            'BATTLE': self.battle_handler,
            'TASK': self.task_handler,
            'SAYAVOICETEXT': self.sayavoicetext_handler,
            'VARSTR_SET': self.varstr_set_handler,
            'GOTO': self.goto_handler,
            'GOSUB': self.gosub_handler,
            'JUMP': self.jump_handler,
            'FARCALL': self.farcall_handler,
            'IFN': self.ifn_ify_handler,
            'IFY': self.ifn_ify_handler,
            'RANDOM': self.random_handler,
            #'ADD': self.add_handler,
            'IMAGELOAD': self.imageload_handler
        }

        fixed_param = b''
        if data['flag'] == 1:
            fixed_param = struct.pack('<H', *data['fixed_param'])
        elif data['flag'] >= 2:
            fixed_param = struct.pack('<HH', *data['fixed_param'])

        command = struct.pack('<BB', self.opcodes[data['opcode']], data['flag'])
        command += fixed_param

        if 'raw_args' in data:
            command += bytes.fromhex(data['raw_args'])

        elif data['opcode'] in handlers_table:

            # not for first pass with calculation of new offsets
            if not calc_mode:
                if data.get('jump_pos') is not None:
                    filename = self.current_script
                    if 'filename' in data:
                        filename = data['filename'].upper()
                    data['jump_pos'] = self.label_map[filename][data['jump_pos']]

            command = handlers_table[data['opcode']](data, command)

        else:
            raise Exception(f'need handler for opcode: {data["opcode"]}')

        full_command = struct.pack('<H', len(command) + 2) + command
        if len(full_command) % 2 != 0:
            full_command += b'\x00'

        return full_command

    @staticmethod
    def message_handler(data: dict, command: bytes):
        command += helpers.pack_param(value=data['voice_id'], type='uint16')
        command += helpers.pack_param(value=data['msg_jp'], type='string', coding=Charset.Unicode)
        command += helpers.pack_param(value=data['msg_en'], type='string', coding=Charset.Unicode)
        if data['end'] is not None:
            command += bytes.fromhex(data['end'])
        return command

    @staticmethod
    def select_handler(data: dict, command: bytes):
        command += helpers.pack_param(value=data['var_id'], type='uint16')
        command += helpers.pack_param(value=data['var0'], type='uint16')
        command += helpers.pack_param(value=data['var1'], type='uint16')
        command += helpers.pack_param(value=data['var2'], type='uint16')
        command += helpers.pack_param(value=data['msg_jp'], type='string', coding=Charset.Unicode)
        command += helpers.pack_param(value=data['msg_en'], type='string', coding=Charset.Unicode)
        command += helpers.pack_param(value=data['var3'], type='uint16')
        command += helpers.pack_param(value=data['var4'], type='uint16')
        command += helpers.pack_param(value=data['var5'], type='uint16')
        return command

    @staticmethod
    def battle_handler(data: dict, command: bytes) -> bytes:
        command += helpers.pack_param(value=data['battle_type'], type='uint16')

        match data['battle_type']:
            case 101:
                command += helpers.pack_param(value=data['var1'], type='uint16')
                if (data['var2'] is not None) and (data['var2'] == 0):
                    command += helpers.pack_param(value=data['var2'], type='uint16')
                    command += helpers.pack_param(value=data['var3'], type='uint16')
                    command += helpers.pack_param(value=data['expr'], type='string', coding=Charset.ShiftJIS)
                    command += helpers.pack_param(value=data['msg_jp'], type='string', coding=Charset.Unicode)
                    command += helpers.pack_param(value=data['msg_en'], type='string', coding=Charset.Unicode)
                else:
                    command += helpers.pack_param(value=data['msg_jp'], type='string', coding=Charset.Unicode)
                    command += helpers.pack_param(value=data['msg_en'], type='string', coding=Charset.Unicode)

            case 102:
                if (data['var1'] is not None) and (data['var1'] == 0):
                    command += helpers.pack_param(value=data['var1'], type='uint16')
                    command += helpers.pack_param(value=data['var2'], type='uint16')
                    command += helpers.pack_param(value=data['expr'], type='string', coding=Charset.ShiftJIS)
                    command += helpers.pack_param(value=data['msg_jp'], type='string', coding=Charset.Unicode)
                    command += helpers.pack_param(value=data['msg_en'], type='string', coding=Charset.Unicode)
                    if data['expr2'] is not None:
                        command += helpers.pack_param(value=data['expr2'], type='string', coding=Charset.ShiftJIS)
                        command += helpers.pack_param(value=data['msg_jp2'], type='string', coding=Charset.Unicode)
                        command += helpers.pack_param(value=data['msg_en2'], type='string', coding=Charset.Unicode)
                        if data['expr3'] is not None:
                            command += helpers.pack_param(value=data['expr3'], type='string', coding=Charset.ShiftJIS)
                            command += helpers.pack_param(value=data['msg_jp3'], type='string', coding=Charset.Unicode)
                            command += helpers.pack_param(value=data['msg_en3'], type='string', coding=Charset.Unicode)
                else:
                    command += helpers.pack_param(value=data['msg_jp'], type='string', coding=Charset.Unicode)
                    command += helpers.pack_param(value=data['msg_en'], type='string', coding=Charset.Unicode)
                    if data['expr'] is not None:
                        command += helpers.pack_param(value=data['expr'], type='string', coding=Charset.ShiftJIS)
                        command += helpers.pack_param(value=data['msg_jp2'], type='string', coding=Charset.Unicode)
                        command += helpers.pack_param(value=data['msg_en2'], type='string', coding=Charset.Unicode)

            case 103:
                command += helpers.pack_param(value=data['msg_jp'], type='string', coding=Charset.Unicode)
                command += helpers.pack_param(value=data['msg_en'], type='string', coding=Charset.Unicode)
                command += helpers.pack_param(value=data['expr'], type='string', coding=Charset.ShiftJIS)
                command += helpers.pack_param(value=data['msg_jp2'], type='string', coding=Charset.Unicode)
                command += helpers.pack_param(value=data['msg_en2'], type='string', coding=Charset.Unicode)

            case 420:
                command += helpers.pack_param(value=data['expr'], type='string', coding=Charset.ShiftJIS)
                command += helpers.pack_param(value=data['expr2'], type='string', coding=Charset.ShiftJIS)

            case _:
                raise Exception(f'unhandled battle type {data["battle_type"]}')

        return command

    @staticmethod
    def task_handler(data: dict, command: bytes) -> bytes:
        command += helpers.pack_param(value=data['task_type'], type='uint16')

        match data['task_type']:
            case 4:
                command += helpers.pack_param(value=data['var1'], type='uint16')
                if data['var1'] in [0, 4, 5]:
                    command += helpers.pack_param(value=data['var2'], type='uint16')
                    command += helpers.pack_param(value=data['msg_jp1'], type='string', coding=Charset.Unicode)
                    command += helpers.pack_param(value=data['msg_en1'], type='string', coding=Charset.Unicode)
                elif data['var1'] == 1:
                    command += helpers.pack_param(value=data['var2'], type='uint16')
                    command += helpers.pack_param(value=data['var3'], type='uint16')
                    command += helpers.pack_param(value=data['var4'], type='uint16')
                    command += helpers.pack_param(value=data['msg_jp1'], type='string', coding=Charset.Unicode)
                    command += helpers.pack_param(value=data['msg_en1'], type='string', coding=Charset.Unicode)
                    command += helpers.pack_param(value=data['msg_jp2'], type='string', coding=Charset.Unicode)
                    command += helpers.pack_param(value=data['msg_en2'], type='string', coding=Charset.Unicode)
                elif data['var1'] == 6:
                    command += helpers.pack_param(value=data['var2'], type='uint16')
                    command += helpers.pack_param(value=data['var3'], type='uint16')
                    command += helpers.pack_param(value=data['msg_jp1'], type='string', coding=Charset.Unicode)
                    command += helpers.pack_param(value=data['msg_en1'], type='string', coding=Charset.Unicode)

            case 54:
                command += helpers.pack_param(value=data['msg_en1'], type='string', coding=Charset.Unicode)

            case 69:
                command += helpers.pack_param(value=data['var1'], type='uint16')
                command += helpers.pack_param(value=data['msg_jp1'], type='string', coding=Charset.Unicode)
                command += helpers.pack_param(value=data['msg_en1'], type='string', coding=Charset.Unicode)
                command += helpers.pack_param(value=data['msg_jp2'], type='string', coding=Charset.Unicode)
                command += helpers.pack_param(value=data['msg_en2'], type='string', coding=Charset.Unicode)

            case _:
                raise Exception(f'unhandled task type {data["task_type"]}')

        return command

    @staticmethod
    def sayavoicetext_handler(data: dict, command: bytes):
        command += helpers.pack_param(value=data['voice_id'], type='uint16')
        command += helpers.pack_param(value=data['msg_jp'], type='string', coding=Charset.Unicode)
        command += helpers.pack_param(value=data['msg_en'], type='string', coding=Charset.Unicode)
        return command

    @staticmethod
    def varstr_set_handler(data: dict, command: bytes):
        command += helpers.pack_param(value=data['varstr_id'], type='uint16')
        command += helpers.pack_param(value=data['varstr_str'], type='string', coding=Charset.Unicode)
        return command

    @staticmethod
    def farcall_handler(data: dict, command: bytes):
        command += helpers.pack_param(value=data['index'], type='uint16')
        command += helpers.pack_param(value=data['filename'], type='string', coding=Charset.ShiftJIS)
        command += helpers.pack_param(value=data['jump_pos'], type='uint32')
        if data['end'] is not None:
            command += bytes.fromhex(data['end'])
        return command

    @staticmethod
    def goto_handler(data: dict, command: bytes):
        command += helpers.pack_param(value=data['jump_pos'], type='uint32')
        return command

    @staticmethod
    def gosub_handler(data: dict, command: bytes):
        command += helpers.pack_param(value=data['arg1'], type='uint16')
        command += helpers.pack_param(value=data['jump_pos'], type='uint32')
        if data['end'] is not None:
            command += bytes.fromhex(data['end'])
        return command

    @staticmethod
    def jump_handler(data: dict, command: bytes):
        command += helpers.pack_param(value=data['filename'], type='string', coding=Charset.ShiftJIS)
        if data['jump_pos'] is not None:
            command += helpers.pack_param(value=data['jump_pos'], type='uint32')
        return command

    @staticmethod
    def ifn_ify_handler(data: dict, command: bytes):
        command += helpers.pack_param(value=data['condition'], type='string', coding=Charset.ShiftJIS)
        command += helpers.pack_param(value=data['jump_pos'], type='uint32')
        return command

    @staticmethod
    def random_handler(data: dict, command: bytes):
        command += helpers.pack_param(value=data['var1'], type='uint16')
        command += helpers.pack_param(value=data['rnd_from'], type='string', coding=Charset.ShiftJIS)
        command += helpers.pack_param(value=data['rnd_to'], type='string', coding=Charset.ShiftJIS)
        return command

    @staticmethod
    def add_handler(data: dict, command: bytes):
        command += helpers.pack_param(value=data['var1'], type='uint16')
        command += helpers.pack_param(value=data['expr'], type='string', coding=Charset.ShiftJIS)
        return command

    @staticmethod
    def imageload_handler(data: dict, command: bytes):
        command += helpers.pack_param(value=data['mode'], type='uint16')
        command += helpers.pack_param(value=data['image_id'], type='uint16')
        if data['var1'] is not None:
            command += helpers.pack_param(value=data['var1'], type='uint16')
            command += helpers.pack_param(value=data['pos_x'], type='uint16')
            command += helpers.pack_param(value=data['pos_y'], type='uint16')
        if data['end'] is not None:
            command += bytes.fromhex(data['end'])
        return command


if __name__ == "__main__":
    assembler = ScriptAssembler(disasm_folder='./disassembled')
    assembler.assemble()
    assembler.save_asm(result_folder='./assembled')
