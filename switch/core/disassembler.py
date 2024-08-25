import json
import os
import struct
from collections import OrderedDict
from pathlib import Path
from typing import List
from utils import helpers
from utils.helpers import Charset


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
            lwr = script_file.lower()
            # fuck macOS .DS_Store
            if not (lwr.startswith('_') or lwr.startswith('seen') or lwr.startswith('ミニゲ')):
                continue
            # idk what the rest of the _-files are for
            if (lwr.startswith('_')) and (lwr not in ["_varstr", '_sayavoice', '_keyword']):
                continue
            # see explanation in repository description
            if 'seen8500' in lwr or 'seen8501' in lwr:
                continue

            script_path = os.path.join(script_folder, script_file)
            with open(script_path, 'rb') as f:
                script = Script()
                script.name = script_file.replace('.json', '')
                script.asm = f.read()
                self.scripts[script.name] = script

        # load opcodes (line number in file = byte that encodes the opcode)
        self.opcodes = {}
        with open('core/opcode_switch.txt') as file:
            self.opcodes = {i: opcode for i, opcode in enumerate(file.read().splitlines())}

        self.current_script = None
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
            'CSAYAVOICETEXT': self.csayavoicetext_handler,
            'VARSTR_SET': self.varstr_set_handler,
            'GOTO': self.goto_handler,
            'GOSUB': self.gosub_handler,
            'JUMP': self.jump_handler,
            'FARCALL': self.farcall_handler,
            'IFN': self.ifn_ify_handler,
            'IFY': self.ifn_ify_handler,
            'RANDOM': self.random_handler,
            # 'ADD': self.add_handler,  # for some reason it breaks some scripts
            'IMAGELOAD': self.imageload_handler,
        }

        for script_name, script in self.scripts.items():
            self.current_script = script_name
            print(f'disassembling {self.current_script}')
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

    def message_handler(self, param_bytes: bytes, result: dict) -> dict:
        en_coding = Charset.UTF_8 if not self.current_script.startswith('ミニゲ') else Charset.Unicode
        voice_id, start = helpers.get_param(params_bytes=param_bytes, type='uint16')
        msg_jp, start = helpers.get_param(params_bytes=param_bytes, type='string', start=start, coding=Charset.Unicode, switch=True)
        msg_en = None
        if msg_jp != '':
            msg_en, start = helpers.get_param(params_bytes=param_bytes, type='string', start=start, coding=en_coding, switch=True)
        end = None
        if len(param_bytes) > start:
            end = param_bytes[start:].hex()
        result.update({
            'voice_id': voice_id,
            'msg_jp': msg_jp,
            'msg_en': msg_en,
            'end': end
        })
        return result

    @staticmethod
    def select_handler(param_bytes: bytes, result: dict) -> dict:
        var_id, start = helpers.get_param(params_bytes=param_bytes, type='uint16')
        var0, start = helpers.get_param(params_bytes=param_bytes, type='uint16', start=start)
        var1, start = helpers.get_param(params_bytes=param_bytes, type='uint16', start=start)
        var2, start = helpers.get_param(params_bytes=param_bytes, type='uint16', start=start)
        msg_jp, start = helpers.get_param(params_bytes=param_bytes, type='string', start=start, coding=Charset.Unicode, switch=True)
        msg_en, start = helpers.get_param(params_bytes=param_bytes, type='string', start=start, coding=Charset.Unicode, switch=True)
        var3, start = helpers.get_param(params_bytes=param_bytes, type='uint16', start=start)
        var4, start = helpers.get_param(params_bytes=param_bytes, type='uint16', start=start)
        result.update({
            'var_id': var_id,
            'msg_jp': msg_jp,
            'msg_en': msg_en,
            'var0': var0,
            'var1': var1,
            'var2': var2,
            'var3': var3,
            'var4': var4,
        })
        return result

    @staticmethod
    def battle_handler(param_bytes: bytes, result: dict) -> dict:
        battle_type, start = helpers.get_param(params_bytes=param_bytes, type='uint16')
        result['battle_type'] = battle_type
        if len(param_bytes) <= start:
            result.update({'raw_args': param_bytes.hex()})
            return result

        var1 = var2 = var3 = expr = msg_jp = msg_en = expr2 = msg_jp2 = msg_en2 = expr3 = msg_jp3 = msg_en3 = None
        match battle_type:

            case 101:
                var1, start = helpers.get_param(params_bytes=param_bytes, type='uint16', start=start)
                var2, start = helpers.get_param(params_bytes=param_bytes, type='uint16', start=start)
                if var2 == 0:
                    var3, start = helpers.get_param(params_bytes=param_bytes, type='uint16', start=start)
                    expr, start = helpers.get_param(params_bytes=param_bytes, type='string', start=start, coding=Charset.ShiftJIS, switch=True)
                    msg_jp, start = helpers.get_param(params_bytes=param_bytes, type='string', start=start, coding=Charset.Unicode, switch=True)
                    msg_en, start = helpers.get_param(params_bytes=param_bytes, type='string', start=start, coding=Charset.UTF_8, switch=True)
                else:
                    var1 = var2 = var3 = expr = msg_jp = msg_en = expr2 = msg_jp2 = msg_en2 = expr3 = msg_jp3 = msg_en3 = None
                    battle_type, start = helpers.get_param(params_bytes=param_bytes, type='uint16')
                    var1, start = helpers.get_param(params_bytes=param_bytes, type='uint16', start=start)
                    msg_jp, start = helpers.get_param(params_bytes=param_bytes, type='string', start=start, coding=Charset.Unicode, switch=True)
                    msg_en, start = helpers.get_param(params_bytes=param_bytes, type='string', start=start, coding=Charset.UTF_8, switch=True)

            case 102:
                var1, start = helpers.get_param(params_bytes=param_bytes, type='uint16', start=start)
                if var1 == 0:
                    var2, start = helpers.get_param(params_bytes=param_bytes, type='uint16', start=start)
                    expr, start = helpers.get_param(params_bytes=param_bytes, type='string', start=start, coding=Charset.ShiftJIS, switch=True)
                    msg_jp, start = helpers.get_param(params_bytes=param_bytes, type='string', start=start, coding=Charset.Unicode, switch=True)
                    msg_en, start = helpers.get_param(params_bytes=param_bytes, type='string', start=start, coding=Charset.UTF_8, switch=True)
                    if len(param_bytes) > start:
                        expr2, start = helpers.get_param(params_bytes=param_bytes, type='string', start=start, coding=Charset.ShiftJIS, switch=True)
                        msg_jp2, start = helpers.get_param(params_bytes=param_bytes, type='string', start=start, coding=Charset.Unicode, switch=True)
                        msg_en2, start = helpers.get_param(params_bytes=param_bytes, type='string', start=start, coding=Charset.UTF_8, switch=True)
                        if len(param_bytes) > start:
                            expr3, start = helpers.get_param(params_bytes=param_bytes, type='string', start=start, coding=Charset.ShiftJIS, switch=True)
                            msg_jp3, start = helpers.get_param(params_bytes=param_bytes, type='string', start=start, coding=Charset.Unicode, switch=True)
                            msg_en3, start = helpers.get_param(params_bytes=param_bytes, type='string', start=start, coding=Charset.UTF_8, switch=True)
                else:
                    var1 = var2 = var3 = expr = msg_jp = msg_en = expr2 = msg_jp2 = msg_en2 = expr3 = msg_jp3 = msg_en3 = None
                    battle_type, start = helpers.get_param(params_bytes=param_bytes, type='uint16')
                    msg_jp, start = helpers.get_param(params_bytes=param_bytes, type='string', start=start, coding=Charset.Unicode, switch=True)
                    msg_en, start = helpers.get_param(params_bytes=param_bytes, type='string', start=start, coding=Charset.UTF_8, switch=True)
                    if len(param_bytes) > start:
                        expr, start = helpers.get_param(params_bytes=param_bytes, type='string', start=start, coding=Charset.ShiftJIS, switch=True)
                        msg_jp2, start = helpers.get_param(params_bytes=param_bytes, type='string', start=start, coding=Charset.Unicode, switch=True)
                        msg_en2, start = helpers.get_param(params_bytes=param_bytes, type='string', start=start, coding=Charset.UTF_8, switch=True)

            case 103:
                msg_jp, start = helpers.get_param(params_bytes=param_bytes, type='string', start=start, coding=Charset.Unicode, switch=True)
                msg_en, start = helpers.get_param(params_bytes=param_bytes, type='string', start=start, coding=Charset.UTF_8, switch=True)
                expr, start = helpers.get_param(params_bytes=param_bytes, type='string', start=start, coding=Charset.ShiftJIS, switch=True)
                msg_jp2, start = helpers.get_param(params_bytes=param_bytes, type='string', start=start, coding=Charset.Unicode, switch=True)
                msg_en2, start = helpers.get_param(params_bytes=param_bytes, type='string', start=start, coding=Charset.UTF_8, switch=True)

            case 420:
                expr, start = helpers.get_param(params_bytes=param_bytes, type='string', start=start, coding=Charset.ShiftJIS, switch=True)
                expr2, start = helpers.get_param(params_bytes=param_bytes, type='string', start=start, coding=Charset.ShiftJIS, switch=True)

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
        task_type, start = helpers.get_param(params_bytes=param_bytes, type='uint16')
        result['task_type'] = task_type
        if len(param_bytes) <= start:
            result.update({'raw_args': param_bytes.hex()})
            return result

        var1 = var2 = var3 = var4 = var5 = msg_jp1 = msg_en1 = msg_jp2 = msg_en2 = None
        match task_type:

            case 4:
                var1, start = helpers.get_param(params_bytes=param_bytes, type='uint16', start=start)
                if len(param_bytes) <= start:
                    result.update({'raw_args': param_bytes.hex()})
                    return result
                if var1 == 0:
                    var2, start = helpers.get_param(params_bytes=param_bytes, type='uint16', start=start)
                    msg_jp1, start = helpers.get_param(params_bytes=param_bytes, type='string', start=start, coding=Charset.Unicode, switch=True)
                    msg_en1, start = helpers.get_param(params_bytes=param_bytes, type='string', start=start, coding=Charset.UTF_8, switch=True)
                elif var1 == 1:
                    var2, start = helpers.get_param(params_bytes=param_bytes, type='uint16', start=start)
                    var3, start = helpers.get_param(params_bytes=param_bytes, type='uint16', start=start)
                    var4, start = helpers.get_param(params_bytes=param_bytes, type='uint16', start=start)
                    msg_jp1, start = helpers.get_param(params_bytes=param_bytes, type='string', start=start, coding=Charset.Unicode, switch=True)
                    msg_en1, start = helpers.get_param(params_bytes=param_bytes, type='string', start=start, coding=Charset.Unicode, switch=True)
                    msg_jp2, start = helpers.get_param(params_bytes=param_bytes, type='string', start=start, coding=Charset.Unicode, switch=True)
                    msg_en2, start = helpers.get_param(params_bytes=param_bytes, type='string', start=start, coding=Charset.Unicode, switch=True)
                elif var1 in [4, 5]:
                    var2, start = helpers.get_param(params_bytes=param_bytes, type='uint16', start=start)
                    msg_jp1, start = helpers.get_param(params_bytes=param_bytes, type='string', start=start, coding=Charset.Unicode, switch=True)
                    msg_en1, start = helpers.get_param(params_bytes=param_bytes, type='string', start=start, coding=Charset.Unicode, switch=True)
                elif var1 == 6:
                    var2, start = helpers.get_param(params_bytes=param_bytes, type='uint16', start=start)
                    var3, start = helpers.get_param(params_bytes=param_bytes, type='uint16', start=start)
                    msg_jp1, start = helpers.get_param(params_bytes=param_bytes, type='string', start=start, coding=Charset.Unicode, switch=True)
                    msg_en1, start = helpers.get_param(params_bytes=param_bytes, type='string', start=start, coding=Charset.UTF_8, switch=True)
                else:
                    result.update({'raw_args': param_bytes.hex()})
                    return result

            case 54:
                msg_en1, start = helpers.get_param(params_bytes=param_bytes, type='string', start=start, coding=Charset.UTF_8, switch=True)

            case 69:
                var1, start = helpers.get_param(params_bytes=param_bytes, type='uint16', start=start)
                msg_jp1, start = helpers.get_param(params_bytes=param_bytes, type='string', start=start, coding=Charset.Unicode, switch=True)
                msg_en1, start = helpers.get_param(params_bytes=param_bytes, type='string', start=start, coding=Charset.Unicode, switch=True)
                msg_jp2, start = helpers.get_param(params_bytes=param_bytes, type='string', start=start, coding=Charset.Unicode, switch=True)
                msg_en2, start = helpers.get_param(params_bytes=param_bytes, type='string', start=start, coding=Charset.Unicode, switch=True)

            case _:
                result.update({'raw_args': param_bytes.hex()})
                return result


        result.update({
            'msg_jp': msg_jp1,
            'msg_en': msg_en1,
            'msg_jp2': msg_jp2,
            'msg_en2': msg_en2,
            'var1': var1,
            'var2': var2,
            'var3': var3,
            'var4': var4,
            'var5': var5
        })
        return result

    @staticmethod
    def csayavoicetext_handler(param_bytes: bytes, result: dict) -> dict:
        voice_id, start = helpers.get_param(params_bytes=param_bytes, type='uint16')
        msg_jp, start = helpers.get_param(params_bytes=param_bytes, type='string', start=start, coding=Charset.Unicode, switch=True)
        msg_en, start = helpers.get_param(params_bytes=param_bytes, type='string', start=start, coding=Charset.Unicode, switch=True)
        result.update({
            'voice_id': voice_id,
            'msg_jp': msg_jp,
            'msg_en': msg_en
        })
        return result

    @staticmethod
    def varstr_set_handler(param_bytes: bytes, result: dict) -> dict:
        varstr_id, start = helpers.get_param(params_bytes=param_bytes, type='uint16')
        varstr_str, start = helpers.get_param(params_bytes=param_bytes, type='string', start=start, coding=Charset.Unicode, switch=True)
        result.update({
            'varstr_id': varstr_id,
            'varstr_str': varstr_str
        })
        return result

    @staticmethod
    def farcall_handler(param_bytes: bytes, result: dict) -> dict:
        index, start = helpers.get_param(params_bytes=param_bytes, type='uint16')
        filename, start = helpers.get_param(params_bytes=param_bytes, start=start, type='string', coding=Charset.ShiftJIS, switch=True)
        jump_pos, start = helpers.get_param(params_bytes=param_bytes, type='uint32', start=start)
        end = None
        if len(param_bytes) > start:
            end = param_bytes[start:].hex()  # 1-5 expressions

        result.update({
            'index': index,
            'filename': filename,
            'jump_pos': jump_pos,
            'end': end
        })
        return result

    @staticmethod
    def goto_handler(param_bytes: bytes, result: dict) -> dict:
        jump_pos, start = helpers.get_param(params_bytes=param_bytes, type='uint32')
        result.update({
            'jump_pos': jump_pos
        })
        return result

    @staticmethod
    def gosub_handler(param_bytes: bytes, result: dict) -> dict:
        arg1, start = helpers.get_param(params_bytes=param_bytes, type='uint16')
        jump_pos, start = helpers.get_param(params_bytes=param_bytes, type='uint32', start=start)
        end = None
        if len(param_bytes) > start:
            end = param_bytes[start:].hex()
        result.update({
            'arg1': arg1,
            'jump_pos': jump_pos,
            'end': end
        })
        return result

    @staticmethod
    def jump_handler(param_bytes: bytes, result: dict) -> dict:
        filename, start = helpers.get_param(params_bytes=param_bytes, type='string', coding=Charset.ShiftJIS, switch=True)
        jump_pos = None
        if len(param_bytes) > start:
            jump_pos, start = helpers.get_param(params_bytes=param_bytes, type='uint32', start=start)
        result.update({
            'filename': filename,
            'jump_pos': jump_pos
        })
        return result

    @staticmethod
    def ifn_ify_handler(param_bytes: bytes, result: dict) -> dict:
        condition, start = helpers.get_param(params_bytes=param_bytes, type='string', coding=Charset.ShiftJIS, switch=True)
        jump_pos, start = helpers.get_param(params_bytes=param_bytes, type='uint32', start=start)
        result.update({
            'condition': condition,
            'jump_pos': jump_pos
        })
        return result

    @staticmethod
    def random_handler(param_bytes: bytes, result: dict) -> dict:
        var1, start = helpers.get_param(params_bytes=param_bytes, type='uint16')
        rnd_from, start = helpers.get_param(params_bytes=param_bytes, type='string', start=start, coding=Charset.ShiftJIS, switch=True)
        rnd_to, start = helpers.get_param(params_bytes=param_bytes, type='string', start=start, coding=Charset.ShiftJIS, switch=True)
        result.update({
            'var1': var1,
            'rnd_from': rnd_from,
            'rnd_to': rnd_to
        })
        return result

    @staticmethod
    def add_handler(param_bytes: bytes, result: dict) -> dict:
        var1, start = helpers.get_param(params_bytes=param_bytes, type='uint16')
        expr, start = helpers.get_param(params_bytes=param_bytes, type='string', start=start, coding=Charset.ShiftJIS, switch=True)
        result.update({
            'var1': var1,
            'expr': expr
        })
        return result

    @staticmethod
    def imageload_handler(param_bytes: bytes, result: dict) -> dict:
        mode, start = helpers.get_param(params_bytes=param_bytes, type='uint16')
        image_id, start = helpers.get_param(params_bytes=param_bytes, type='uint16', start=start)

        var1 = var2 = pos_x = pos_y = end = None
        # mode 0 - background
        if mode != 0:
            if len(param_bytes) > start:
                var1, start = helpers.get_param(params_bytes=param_bytes, type='uint32', start=start)
                pos_x, start = helpers.get_param(params_bytes=param_bytes, type='uint16', start=start)
                var2, start = helpers.get_param(params_bytes=param_bytes, type='uint16', start=start)
                pos_y, start = helpers.get_param(params_bytes=param_bytes, type='uint16', start=start)

        if len(param_bytes) != start:
            end = param_bytes[start:].hex()

        result.update({
            'mode': mode,
            'image_id': image_id,
            'pos_x': pos_x,
            'pos_y': pos_y,
            'var1': var1,
            'var2': var2,
            'end': end
        })
        return result


if __name__ == "__main__":
    disassembler = ScriptDisassembler(script_folder='../SCRIPT/unpacked')
    disassembler.disassemble()
    disassembler.save_disasm(result_folder='../SCRIPT/disassembled')
