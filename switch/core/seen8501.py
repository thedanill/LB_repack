import json
from utils import helpers
from utils.helpers import Charset

first_title = '困りまくりグランプリ'.encode('utf-16le')


def disassemble(seen8501_path: str, disasm_path: str):
    with open(seen8501_path, 'rb') as f:
        data = f.read()
    result = []
    index = data.find(first_title) - 2  # header length
    result.append({
        'header': data[:index].hex()
    })

    data = data[index:]
    next = 0
    title_id = 0
    while len(data) - 8 > next:
        jp, next = helpers.get_param(params_bytes=data, type='string', start=next, coding=Charset.Unicode, switch=True)
        en, next = helpers.get_param(params_bytes=data, type='string', start=next, coding=Charset.UTF_8, switch=True)
        result.append({
            'title_id': title_id,
            'jp': jp,
            'en': en
        })
        title_id += 1

    result.append({
        'end': data[next:].hex()
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
    for title in data:
        result += helpers.pack_param(value=title['jp'], type='string', coding=Charset.Unicode, switch=True)
        result += helpers.pack_param(value=title['en'], type='string', coding=Charset.UTF_8, switch=True)
    result += end

    with open(repack_path, "wb") as new_file:
        new_file.write(result)


if __name__ == '__main__':
    disassemble('../SCRIPT/unpacked/SEEN8501', '8501switch.json')
    assemble('8501switch.json', 'SEEN8501')

