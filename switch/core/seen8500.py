import json
from utils import helpers
from utils.helpers import Charset

first_accessory = 'カップゼリー'.encode('utf-16le')


def disassemble(seen8500_path: str, disasm_path: str):
    with open(seen8500_path, 'rb') as f:
        data = f.read()
    result = []
    index = data.find(first_accessory) - 2   # header length
    result.append({
        'header': data[:index].hex()
    })

    data = data[index:]
    start = 0
    accessory_id = 0
    while len(data) - 10 > start:
        jp, start = helpers.get_param(params_bytes=data, type='string', start=start, coding=Charset.Unicode, switch=True)
        en, start = helpers.get_param(params_bytes=data, type='string', start=start, coding=Charset.UTF_8, switch=True)
        var1, start = helpers.get_param(params_bytes=data, type='uint8', start=start)
        var2, start = helpers.get_param(params_bytes=data, type='uint16', start=start)
        result.append({
            'accessory_id': accessory_id,
            'jp': jp,
            'en': en,
            'var1': var1,
            'var2': var2
        })
        accessory_id += 1

    result.append({
        'end': data[start:].hex()
    })
    with open(disasm_path, "w", encoding="UTF-8") as new_file:
        json.dump(result, new_file, indent="\t", ensure_ascii=False)


def assemble(disasm_path: str, repack_path: str):
    result = bytes()
    with open(disasm_path, 'r') as f:
        data = json.loads(f.read())
    header = bytes.fromhex(data.pop(0)['header'])
    end = bytes.fromhex(data.pop(-1)['end'])

    result += header
    for accessory in data:
        result += helpers.pack_param(value=accessory['jp'], type='string', coding=Charset.Unicode, switch=True)
        result += helpers.pack_param(value=accessory['en'], type='string', coding=Charset.UTF_8, switch=True)
        result += helpers.pack_param(value=accessory['var1'], type='uint8')
        result += helpers.pack_param(value=accessory['var2'], type='uint16')
    result += end

    with open(repack_path, "wb") as new_file:
        new_file.write(result)


if __name__ == '__main__':
    disassemble('../SCRIPT/unpacked/SEEN8500', '8500switch.json')
    assemble('8500switch.json', 'SEEN8500')

    #disassemble('/Users/danil/Downloads/littlebusturs/switch/unpacked/seen8500', '8500switch.json')
