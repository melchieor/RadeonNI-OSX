"""Inspect PPC32 kernel C++ vtables without executing target code."""
from pathlib import Path
import struct
from leopard_macho import slices


def object_data(path):
    data = slices(Path(path).read_bytes())[18]
    sections = []
    position = 28
    for _ in range(struct.unpack_from('>I', data, 16)[0]):
        command, length = struct.unpack_from('>II', data, position)
        if command == 1:
            for index in range(struct.unpack_from('>I', data, position+48)[0]):
                offset = position+56+index*68
                sections.append(struct.unpack_from('>6I', data, offset+32))
        elif command == 2:
            symoff, count, stroff, _ = struct.unpack_from('>4I', data, position+8)
        position += length
    symbols = []
    for index in range(count):
        string, typ, section, _, value = struct.unpack_from('>IBBHI', data, symoff+index*12)
        name = data[stroff+string:data.index(b'\0', stroff+string)].decode()
        symbols.append((name, typ, section, value))
    return data, sections, symbols


def symbol_bytes(path, name, size):
    data, sections, symbols = object_data(path)
    symbol = next(s for s in symbols if s[0] == name and not s[1] & 0xe0)
    _, _, section, value = symbol
    address, length, offset, _, _, _ = sections[section-1]
    if value-address+size > length:
        raise ValueError('symbol extends beyond section')
    return data[offset+value-address:offset+value-address+size]


def vtables(path):
    data, sections, symbols = object_data(path)
    defined = {(section, value): name for name, typ, section, value in symbols
               if not typ & 0xe0 and typ & 0x0e == 0x0e}
    result = {}
    for name, typ, section, value in symbols:
        if not name.startswith('__ZTV') or typ & 0xe0 or typ & 0x0e != 0x0e:
            continue
        address, size, offset, _, reloff, nreloc = sections[section-1]
        limit = min([v-address for _, t, s, v in symbols
                     if not t & 0xe0 and t & 0x0e == 0x0e and s == section and v > value]
                    + [size])
        relocations = {}
        for index in range(nreloc):
            target, info = struct.unpack_from('>II', data, reloff+index*8)
            if target & 0x80000000 or info & 0x0f:
                continue
            if info & 0x10:
                symbol = symbols[info >> 8]
                relocations[target] = (symbol[0], symbol[1] & 0x0e != 0)
            else:
                pointer, = struct.unpack_from('>I', data, offset+target)
                relocations[target] = (defined.get((info >> 8, pointer), '<unknown>'), True)
        entries = []
        terminated = False
        cursor = value-address+8  # offset-to-top and RTTI precede function slots
        while cursor+4 <= limit:
            pointer, = struct.unpack_from('>I', data, offset+cursor)
            if cursor in relocations:
                entries.append(relocations[cursor])
            elif pointer == 0:
                terminated = True
                break
            else:
                entries.append(('<unrelocated>', False))
            cursor += 4
        result[name] = dict(entries=entries, terminated=terminated)
    return result


def compare(child, parent):
    """Mirror Leopard kld's reserved-slot mismatch rule; require termination.

    Local overrides are accepted by the loader. Imports at reserved superclass
    slots must retain exactly the same name. This does not prove full ABI safety.
    """
    errors = []
    if not child['terminated']:
        errors.append('missing kernel vtable zero terminator')
    if len(child['entries']) < len(parent['entries']):
        errors.append('vtable shorter than superclass')
    for index, ((name, local), (expected, _)) in enumerate(zip(child['entries'], parent['entries'])):
        if not local and '_RESERVED' in expected and name != expected:
            errors.append('slot %d: %s conflicts with superclass %s' % (index, name, expected))
    # PPC ABI1 has one deleting destructor, not the Itanium D1/D0 pair.
    if child['entries'] and 'D1Ev' in child['entries'][0][0]:
        errors.append('PPC kernel ABI requires a single D0 destructor slot')
    return errors
