"""Read PowerPC Mach-O metadata without executing target binaries."""
from pathlib import Path
import struct


def slices(data):
    if data[:4] == b'\xca\xfe\xba\xbe':
        count, = struct.unpack_from('>I', data, 4)
        if count > 32 or 8 + count * 20 > len(data):
            raise ValueError('invalid fat header')
        result = {}
        ranges = []
        for i in range(count):
            cpu, subtype, offset, size, alignment = struct.unpack_from('>5I', data, 8+i*20)
            if offset < 8+count*20 or offset+size > len(data) or cpu in result:
                raise ValueError('invalid fat slice')
            if any(offset < b and a < offset+size for a, b in ranges):
                raise ValueError('overlapping fat slices')
            ranges.append((offset, offset+size))
            result[cpu] = data[offset:offset+size]
        return result
    if data[:4] not in (b'\xfe\xed\xfa\xce', b'\xfe\xed\xfa\xcf'):
        raise ValueError('not a big-endian PowerPC Mach-O')
    return {struct.unpack_from('>I', data, 4)[0]: data}


def metadata(data):
    wide = data[:4] == b'\xfe\xed\xfa\xcf'
    header = 32 if wide else 28
    if len(data) < header or data[:4] not in (b'\xfe\xed\xfa\xce', b'\xfe\xed\xfa\xcf'):
        raise ValueError('invalid PowerPC header')
    _, cpu, subtype, kind, count, size, flags = struct.unpack_from('>7I', data)
    if cpu not in (18, 0x1000012) or header+size > len(data):
        raise ValueError('invalid architecture or commands')
    result = dict(cpu=cpu, subtype=subtype, kind=kind, flags=flags,
                  imports=[], exports=[], aliases={}, dependencies=[], rpaths=[], minimum_os=None)
    position = header
    for _ in range(count):
        if position+8 > header+size:
            raise ValueError('truncated command')
        command, length = struct.unpack_from('>II', data, position)
        if length < 8 or position+length > header+size:
            raise ValueError('invalid command length')
        block = data[position:position+length]
        def string_at(offset):
            if offset < 8 or offset >= len(block) or b'\0' not in block[offset:]:
                raise ValueError('invalid command string')
            return block[offset:block.index(b'\0', offset)].decode('utf-8')
        if command in (0xc, 0x80000018, 0x8000001f, 0x80000023):
            result['dependencies'].append(string_at(struct.unpack_from('>I', block, 8)[0]))
        elif command == 0x8000001c:
            result['rpaths'].append(string_at(struct.unpack_from('>I', block, 8)[0]))
        elif command == 0x24:
            value = struct.unpack_from('>I', block, 8)[0]
            result['minimum_os'] = [value >> 16, (value >> 8) & 255, value & 255]
        elif command == 2:
            symoff, nsyms, stroff, strsize = struct.unpack_from('>4I', block, 8)
            entry = 16 if wide else 12
            if symoff+nsyms*entry > len(data) or stroff+strsize > len(data):
                raise ValueError('invalid symbol table')
            strings = data[stroff:stroff+strsize]
            def symbol_string(index):
                if index >= len(strings) or b'\0' not in strings[index:]:
                    raise ValueError('invalid symbol string')
                return strings[index:strings.index(b'\0', index)].decode('utf-8')
            for i in range(nsyms):
                index, typ, sect, desc, value = struct.unpack_from('>IBBHQ' if wide else '>IBBHI', data, symoff+i*entry)
                if typ & 0xe0 or not typ & 1:
                    continue
                name = symbol_string(index)
                if typ & 0x0e == 0 and value == 0:
                    result['imports'].append(name)
                elif not typ & 0x10:
                    result['exports'].append(name)
                    if typ & 0x0e == 0xa:
                        result['aliases'][name] = symbol_string(value)
        position += length
    if position != header+size:
        raise ValueError('command size mismatch')
    result['imports'] = sorted(set(result['imports']))
    result['exports'] = sorted(set(result['exports']))
    return result


def read(path):
    return {cpu: metadata(data) for cpu, data in slices(Path(path).read_bytes()).items()
            if cpu in (18, 0x1000012)}
