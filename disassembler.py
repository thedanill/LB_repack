import json
import os
import struct
from collections import OrderedDict
from pathlib import Path
from typing import List
import utils
from utils import Charset


class Opcode:
    def __init__(self):
        self.index: int = 0
        self.pos: int = 0
        self.len: int = 0
        self.opcode: int = 0
        self.flag: int = 0
        self.raw_bytes: bytes = b''
        self.align: bytes = b''
        self.fixed_param: List[int] = []
        self.param_bytes: bytes = b''
        self.opstr: str = ''


class Script:
    def __init__(self):
        self.name: str = ''
        self.asm: bytearray = bytearray()
        self.disasm: List[dict] = []
        self.opcodes: List[Opcode] = []
        self.code_num: int = 0


class ScriptDisassembler:
    """
    Сlass is used to parse Luca System Engine game scripts.
    Each script consists of a series of commands (CodeLine objects) with the following structure:

    1. Command structure:
       - length (2 bytes): total length of the command
       - opcode (1 byte): identifies the command type
       - flag (1 byte): indicates the presence and type of params
       - raw bytes: variable length data specific to the command

    2. Fixed parameters (optional):
       - present if flag > 0
       - for flag >= 2: two 2-byte parameters
       - for flag == 1: one 2-byte parameter

    3. Parameter bytes:
       - remaining bytes after fixed parameters
       - interpreted based on the specific command

    4. Alignment:
       - if command length is odd, an extra byte is added for 2-byte alignment
    """
    def __init__(self, script_folder):
        self.scripts = OrderedDict()

        # load scripts
        for script_file in os.listdir(script_folder):
            # fuck macOS .DS_Store
            if not (script_file.startswith('_') or script_file.startswith('SEEN')):
                continue
            # idk what the rest of the _-files are for
            if (script_file.startswith('_')) and (script_file not in ["_VARSTR", '_SAYAVOICE', '_KEYWORD']):
                continue
            # see explanation in repository description
            if script_file == 'SEEN8500' or script_file == 'SEEN8501':
                continue

            script_path = os.path.join(script_folder, script_file)
            with open(script_path, 'rb') as f:
                script = Script()
                script.name = script_file.replace('.json', '')
                script.asm = f.read()
                self.scripts[script.name] = script

        # load opcodes (line number in file = byte that encodes the opcode)
        self.opcodes = {}
        with open('opcode.txt') as file:
            self.opcodes = {i: opcode for i, opcode in enumerate(file.read().splitlines())}

        self.scripts = OrderedDict((key, self.scripts[key]) for key in sorted(self.scripts))
        self.parse_scripts()

    def parse_scripts(self):
        for script_name, script in self.scripts.items():
            print(f'parse {script_name}')
            offset = 0
            while offset < len(script.asm):
                code = Opcode()

                # read length, opcode byte and flag (number of params depends on it)
                code.len, code.opcode, code.flag = struct.unpack_from('<HBB', script.asm, offset)
                code.opstr = self.opcodes[code.opcode]
                offset += 4

                # read the rest of the command
                raw_bytes_len = code.len - 4
                code.raw_bytes = script.asm[offset:offset + raw_bytes_len]
                offset += raw_bytes_len

                # read align (if any)
                if code.len % 2 != 0:
                    code.align = script.asm[offset:offset + 1]
                    offset += 1

                # parse opcode params
                if code.flag > 0:
                    if code.flag >= 2:
                        code.fixed_param = list(struct.unpack_from('<HH', code.raw_bytes))
                        code.param_bytes = code.raw_bytes[4:]
                    else:
                        code.fixed_param = [struct.unpack_from('<H', code.raw_bytes)[0]]
                        code.param_bytes = code.raw_bytes[2:]
                else:
                    code.param_bytes = code.raw_bytes

                script.opcodes.append(code)

            script.code_num = len(script.opcodes)

            pos = 0
            for i, code in enumerate(script.opcodes):
                code.index = i
                code.pos = pos
                pos += (code.len + 1) & ~1  # align to 2 bytes


    def save_disasm(self, result_folder: str) -> None:
        output_path = Path(result_folder)
        output_path.mkdir(parents=True, exist_ok=True)

        for script_name, script in self.scripts.items():
            file_path = os.path.join(output_path, f"{script_name}.json")
            with open(file_path, "w", encoding="UTF-8") as new_file:
                json.dump(script.disasm, new_file, indent="\t", ensure_ascii=False)


    def disassemble(self):
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
        }

        for script_name, script in self.scripts.items():
            print(f'disassembling {script_name}')
            for code in script.opcodes:
                result = {
                    'label': code.pos,
                    'opcode': code.opstr,
                    'flag': code.flag,
                    'fixed_param': code.fixed_param
                }
                if code.opstr in handlers_table:
                    result = handlers_table[code.opstr](code.param_bytes, result)
                else:
                    result['raw_args'] = code.param_bytes.hex()
                # print(f'{code.opstr} {result}')
                script.disasm.append(result)


    @staticmethod
    def message_handler(param_bytes: bytes, result: dict) -> dict:
        voice_id, next = utils.get_param(params_bytes=param_bytes, type='uint16')
        msg_jp, next = utils.get_param(params_bytes=param_bytes, type='string', start=next, coding=Charset.Unicode)
        msg_en, next = utils.get_param(params_bytes=param_bytes, type='string', start=next, coding=Charset.Unicode)
        end = None
        if len(param_bytes) > next:
            end = param_bytes[next:].hex()
        result.update({
            'voice_id': voice_id,
            'msg_jp': msg_jp,
            'msg_en': msg_en,
            'end': end
        })
        return result

    @staticmethod
    def select_handler(param_bytes: bytes, result: dict) -> dict:
        var_id, next = utils.get_param(params_bytes=param_bytes, type='uint16')
        var0, next = utils.get_param(params_bytes=param_bytes, type='uint16', start=next)
        var1, next = utils.get_param(params_bytes=param_bytes, type='uint16', start=next)
        var2, next = utils.get_param(params_bytes=param_bytes, type='uint16', start=next)
        msg_jp, next = utils.get_param(params_bytes=param_bytes, type='string', start=next, coding=Charset.Unicode)
        msg_en, next = utils.get_param(params_bytes=param_bytes, type='string', start=next, coding=Charset.Unicode)
        var3, next = utils.get_param(params_bytes=param_bytes, type='uint16', start=next)
        var4, next = utils.get_param(params_bytes=param_bytes, type='uint16', start=next)
        var5, next = utils.get_param(params_bytes=param_bytes, type='uint16', start=next)
        result.update({
            'var_id': var_id,
            'var0': var0,
            'var1': var1,
            'var2': var2,
            'msg_jp': msg_jp,
            'msg_en': msg_en,
            'var3': var3,
            'var4': var4,
            'var5': var5,
        })
        return result

    @staticmethod
    def battle_handler(param_bytes: bytes, result: dict) -> dict:
        battle_type, next = utils.get_param(params_bytes=param_bytes, type='uint16')
        result['battle_type'] = battle_type
        if len(param_bytes) <= next:
            result.update({'raw_args': param_bytes.hex()})
            return result

        var1 = var2 = var3 = expr = msg_jp = msg_en = expr2 = msg_jp2 = msg_en2 = expr3 = msg_jp3 = msg_en3 = None
        match battle_type:

            case 101:
                var1, next = utils.get_param(params_bytes=param_bytes, type='uint16', start=next)
                var2, next = utils.get_param(params_bytes=param_bytes, type='uint16', start=next)
                if var2 == 0:
                    var3, next = utils.get_param(params_bytes=param_bytes, type='uint16', start=next)
                    expr, next = utils.get_param(params_bytes=param_bytes, type='string', start=next, coding=Charset.ShiftJIS)
                    msg_jp, next = utils.get_param(params_bytes=param_bytes, type='string', start=next, coding=Charset.Unicode)
                    msg_en, next = utils.get_param(params_bytes=param_bytes, type='string', start=next, coding=Charset.Unicode)
                else:
                    var1 = var2 = var3 = expr = msg_jp = msg_en = expr2 = msg_jp2 = msg_en2 = expr3 = msg_jp3 = msg_en3 = None
                    battle_type, next = utils.get_param(params_bytes=param_bytes, type='uint16')
                    var1, next = utils.get_param(params_bytes=param_bytes, type='uint16', start=next)
                    msg_jp, next = utils.get_param(params_bytes=param_bytes, type='string', start=next, coding=Charset.Unicode)
                    msg_en, next = utils.get_param(params_bytes=param_bytes, type='string', start=next, coding=Charset.Unicode)

            case 102:
                var1, next = utils.get_param(params_bytes=param_bytes, type='uint16', start=next)
                if var1 == 0:
                    var2, next = utils.get_param(params_bytes=param_bytes, type='uint16', start=next)
                    expr, next = utils.get_param(params_bytes=param_bytes, type='string', start=next, coding=Charset.ShiftJIS)
                    msg_jp, next = utils.get_param(params_bytes=param_bytes, type='string', start=next, coding=Charset.Unicode)
                    msg_en, next = utils.get_param(params_bytes=param_bytes, type='string', start=next, coding=Charset.Unicode)
                    if len(param_bytes) > next:
                        expr2, next = utils.get_param(params_bytes=param_bytes, type='string', start=next, coding=Charset.ShiftJIS)
                        msg_jp2, next = utils.get_param(params_bytes=param_bytes, type='string', start=next, coding=Charset.Unicode)
                        msg_en2, next = utils.get_param(params_bytes=param_bytes, type='string', start=next, coding=Charset.Unicode)
                        if len(param_bytes) > next:
                            expr3, next = utils.get_param(params_bytes=param_bytes, type='string', start=next, coding=Charset.ShiftJIS)
                            msg_jp3, next = utils.get_param(params_bytes=param_bytes, type='string', start=next, coding=Charset.Unicode)
                            msg_en3, next = utils.get_param(params_bytes=param_bytes, type='string', start=next, coding=Charset.Unicode)
                else:
                    var1 = var2 = var3 = expr = msg_jp = msg_en = expr2 = msg_jp2 = msg_en2 = expr3 = msg_jp3 = msg_en3 = None
                    battle_type, next = utils.get_param(params_bytes=param_bytes, type='uint16')
                    msg_jp, next = utils.get_param(params_bytes=param_bytes, type='string', start=next, coding=Charset.Unicode)
                    msg_en, next = utils.get_param(params_bytes=param_bytes, type='string', start=next, coding=Charset.Unicode)
                    if len(param_bytes) > next:
                        expr, next = utils.get_param(params_bytes=param_bytes, type='string', start=next, coding=Charset.ShiftJIS)
                        msg_jp2, next = utils.get_param(params_bytes=param_bytes, type='string', start=next, coding=Charset.Unicode)
                        msg_en2, next = utils.get_param(params_bytes=param_bytes, type='string', start=next, coding=Charset.Unicode)

            case _:
                result.update({'raw_args': param_bytes.hex()})
                return result

        result.update({
            'var1': var1,
            'var2': var2,
            'var3': var3,
            'expr': expr,
            'msg_jp': msg_jp,
            'msg_en': msg_en,
            'expr2': expr2,
            'msg_jp2': msg_jp2,
            'msg_en2': msg_en2,
            'expr3': expr3,
            'msg_jp3': msg_jp3,
            'msg_en3': msg_en3
        })
        return result

    @staticmethod
    def task_handler(param_bytes: bytes, result: dict) -> dict:
        task_type, next = utils.get_param(params_bytes=param_bytes, type='uint16')
        result['task_type'] = task_type
        if len(param_bytes) <= next:
            result.update({'raw_args': param_bytes.hex()})
            return result

        var1 = var2 = var3 = var4 = msg_jp1 = msg_en1 = msg_jp2 = msg_en2 = None
        match task_type:

            case 4:
                var1, next = utils.get_param(params_bytes=param_bytes, type='uint16', start=next)
                if len(param_bytes) <= next:
                    result.update({'raw_args': param_bytes.hex()})
                    return result
                if var1 in [0, 4, 5]:
                    var2, next = utils.get_param(params_bytes=param_bytes, type='uint16', start=next)
                    msg_jp1, next = utils.get_param(params_bytes=param_bytes, type='string', start=next, coding=Charset.Unicode)
                    msg_en1, next = utils.get_param(params_bytes=param_bytes, type='string', start=next, coding=Charset.Unicode)
                elif var1 == 1:
                    var2, next = utils.get_param(params_bytes=param_bytes, type='uint16', start=next)
                    var3, next = utils.get_param(params_bytes=param_bytes, type='uint16', start=next)
                    var4, next = utils.get_param(params_bytes=param_bytes, type='uint16', start=next)
                    msg_jp1, next = utils.get_param(params_bytes=param_bytes, type='string', start=next, coding=Charset.Unicode)
                    msg_en1, next = utils.get_param(params_bytes=param_bytes, type='string', start=next, coding=Charset.Unicode)
                    msg_jp2, next = utils.get_param(params_bytes=param_bytes, type='string', start=next, coding=Charset.Unicode)
                    msg_en2, next = utils.get_param(params_bytes=param_bytes, type='string', start=next, coding=Charset.Unicode)
                elif var1 == 6:
                    var2, next = utils.get_param(params_bytes=param_bytes, type='uint16', start=next)
                    var3, next = utils.get_param(params_bytes=param_bytes, type='uint16', start=next)
                    msg_jp1, next = utils.get_param(params_bytes=param_bytes, type='string', start=next, coding=Charset.Unicode)
                    msg_en1, next = utils.get_param(params_bytes=param_bytes, type='string', start=next, coding=Charset.Unicode)
                else:
                    result.update({'raw_args': param_bytes.hex()})
                    return result

            case 54:
                msg_en1, next = utils.get_param(params_bytes=param_bytes, type='string', start=next, coding=Charset.Unicode)

            case 69:
                var1, next = utils.get_param(params_bytes=param_bytes, type='uint16', start=next)
                msg_jp1, next = utils.get_param(params_bytes=param_bytes, type='string', start=next, coding=Charset.Unicode)
                msg_en1, next = utils.get_param(params_bytes=param_bytes, type='string', start=next, coding=Charset.Unicode)
                msg_jp2, next = utils.get_param(params_bytes=param_bytes, type='string', start=next, coding=Charset.Unicode)
                msg_en2, next = utils.get_param(params_bytes=param_bytes, type='string', start=next, coding=Charset.Unicode)

            case _:
                result.update({'raw_args': param_bytes.hex()})
                return result

        result.update({
            'var1': var1,
            'var2': var2,
            'var3': var3,
            'var4': var4,
            'msg_jp1': msg_jp1,
            'msg_en1': msg_en1,
            'msg_jp2': msg_jp2,
            'msg_en2': msg_en2
        })
        return result

    @staticmethod
    def sayavoicetext_handler(param_bytes: bytes, result: dict) -> dict:
        voice_id, next = utils.get_param(params_bytes=param_bytes, type='uint16')
        msg_jp, next = utils.get_param(params_bytes=param_bytes, type='string', start=next, coding=utils.Charset.Unicode)
        msg_en, next = utils.get_param(params_bytes=param_bytes, type='string', start=next, coding=utils.Charset.Unicode)
        result.update({
            'voice_id': voice_id,
            'msg_jp': msg_jp,
            'msg_en': msg_en
        })
        return result

    @staticmethod
    def varstr_set_handler(param_bytes: bytes, result: dict) -> dict:
        varstr_id, next = utils.get_param(params_bytes=param_bytes, type='uint16')
        varstr_str, next = utils.get_param(params_bytes=param_bytes, type='string', start=next, coding=Charset.Unicode)
        result.update({
            'varstr_id': varstr_id,
            'varstr_str': varstr_str
        })
        return result

    @staticmethod
    def farcall_handler(param_bytes: bytes, result: dict) -> dict:
        index, next = utils.get_param(params_bytes=param_bytes, type='uint16')
        filename, next = utils.get_param(params_bytes=param_bytes, start=next, type='string', coding=Charset.ShiftJIS)
        jump_pos, next = utils.get_param(params_bytes=param_bytes, type='uint32', start=next)
        end = None
        if len(param_bytes) > next:
            end = param_bytes[next:].hex()

        result.update({
            'index': index,
            'filename': filename,
            'jump_pos': jump_pos,
            'end': end
        })
        return result

    @staticmethod
    def goto_handler(param_bytes: bytes, result: dict) -> dict:
        jump_pos, next = utils.get_param(params_bytes=param_bytes, type='uint32')
        result.update({
            'jump_pos': jump_pos
        })
        return result

    @staticmethod
    def gosub_handler(param_bytes: bytes, result: dict) -> dict:
        arg1, next = utils.get_param(params_bytes=param_bytes, type='uint16')
        jump_pos, next = utils.get_param(params_bytes=param_bytes, type='uint32', start=next)
        end = None
        if len(param_bytes) > next:
            end = param_bytes[next:].hex()
        result.update({
            'arg1': arg1,
            'jump_pos': jump_pos,
            'end': end
        })
        return result

    @staticmethod
    def jump_handler(param_bytes: bytes, result: dict) -> dict:
        filename, next = utils.get_param(params_bytes=param_bytes, type='string', coding=Charset.ShiftJIS)
        jump_pos = None
        if len(param_bytes) > next:
            jump_pos, next = utils.get_param(params_bytes=param_bytes, type='uint32', start=next)
        result.update({
            'filename': filename,
            'jump_pos': jump_pos
        })
        return result

    @staticmethod
    def ifn_ify_handler(param_bytes: bytes, result: dict) -> dict:
        condition, next = utils.get_param(params_bytes=param_bytes, type='string', coding=Charset.ShiftJIS)
        jump_pos, next = utils.get_param(params_bytes=param_bytes, type='uint32', start=next)
        result.update({
            'condition': condition,
            'jump_pos': jump_pos
        })
        return result


if __name__ == "__main__":
    disassembler = ScriptDisassembler(script_folder='./unpacked')
    disassembler.disassemble()
    disassembler.save_disasm(result_folder='./disassembled')
