import codecs
import struct
from typing import List, Tuple, Union
from enum import Enum


class Charset(Enum):
    UTF_8 = 1
    ShiftJIS = 2
    Unicode = 3


def all_to_uint16(data: bytes) -> Tuple[List[int], int]:
    data_len = len(data)
    uint16_list = struct.unpack(f'<{data_len // 2}H', data[:data_len - (data_len % 2)])
    last_byte_pos = -1 if data_len % 2 == 0 else data_len - 1

    return list(uint16_list), last_byte_pos


def decode_string(data: bytes, strlen: None | int, start: int, coding: Charset, switch_mode: bool) -> Tuple[str, int]:
    end = start

    eof_len = 0
    char_len = 0
    decoder = None
    match coding:
        case Charset.ShiftJIS:
            eof_len = 1
            char_len = 1
            decoder = codecs.getdecoder('shift_jis')
        case Charset.UTF_8:
            eof_len = 1
            char_len = 1
            decoder = codecs.getdecoder('utf-8')
        case Charset.Unicode:
            eof_len = 2
            char_len = 2
            decoder = codecs.getdecoder('utf-16le')

    if not strlen or strlen == 0:
        if switch_mode:
            start += 2  # string length
        match coding:
            case Charset.ShiftJIS | Charset.UTF_8:
                while (end < len(data)) and (data[end] != 0):
                    end += char_len
            case Charset.Unicode:
                while (end + 1 < len(data)) and not ((data[end] == 0) and (data[end + 1] == 0)):
                    end += char_len

    else:
        end = start + strlen

    str_data, _ = decoder(data[start:end])
    return str_data, end + eof_len


def encode_string(data: str, coding: Charset, switch_mode: bool = False) -> bytes:
    encoder = None
    terminator = encoded_data = b''

    match coding:
        case Charset.ShiftJIS:
            encoder = codecs.getencoder('shift_jis')
            terminator = b'\x00'
        case Charset.UTF_8:
            encoder = codecs.getencoder('utf-8')
            terminator = b'\x00'
        case Charset.Unicode:
            encoder = codecs.getencoder('utf-16le')
            terminator = b'\x00\x00'

    if switch_mode and not data:
        return b'\x00'
    str_bytes, consumed = encoder(data)

    if switch_mode:
        match coding:
            case Charset.Unicode:
                data_len = consumed
            case Charset.ShiftJIS:
                data_len = min((0xFFFF - consumed + 1), 0xFFFF)
            case Charset.UTF_8:
                data_len = min((0xFFFF - len(encode_string(data=data, coding=Charset.UTF_8)) + 2), 0xFFFF)
        encoded_data += pack_param(value=data_len, type='uint16')

    encoded_data += str_bytes
    encoded_data += terminator

    return encoded_data


def get_param(
        params_bytes: bytes,
        type: str,
        start: None | int = None,
        size: None | int = None,
        coding: Charset = Charset.Unicode,
        switch: bool = False
):
    if not start:
        start = 0

    match type:
        case 'uint8':
            end = start + 1
            return struct.unpack('<B', params_bytes[start:end])[0], end
        case 'uint16':
            end = start + 2
            return struct.unpack('<H', params_bytes[start:end])[0], end
        case 'uint32':
            end = start + 4
            return struct.unpack('<I', params_bytes[start:end])[0], end
        case 'string':
            string, next_arg_pos = decode_string(data=params_bytes, strlen=size, start=start, coding=coding, switch_mode=switch)
            return string, next_arg_pos
        case _:
            raise ValueError(f"Unsupported type: {type}")


def pack_param(
    value: Union[int, str],
    type: str,
    coding: Charset = Charset.Unicode,
    switch: bool = False
) -> bytes:
    match type:
        case 'uint8':
            packed = struct.pack('<B', value)
            return packed
        case 'uint16':
            packed = struct.pack('<H', value)
            return packed
        case 'uint32':
            packed = struct.pack('<I', value)
            return packed
        case 'string':
            encoded = encode_string(data=value, coding=coding, switch_mode=switch)
            return encoded
        case _:
            raise ValueError(f"Unsupported type: {type}")
