#!/usr/bin/env python3
"""Strict read-only, dependency-free flattened-device-tree decoder.

FDT layout v16/v17+ is checked before parsing. This parser deliberately rejects
truncated, overlapping, duplicate or malformed structures rather than attempting
best-effort recovery. No candidate should be cleared by a permissive parser.
"""
import struct

MAGIC = 0xD00DFEED
BEGIN_NODE, END_NODE, PROP, NOP, END = 1, 2, 3, 4, 9


def be32(data, off):
    if off < 0 or off + 4 > len(data):
        raise ValueError('FDT truncated 32-bit field at %d' % off)
    return struct.unpack_from('>I', data, off)[0]


def align4(n):
    return (n + 3) & ~3


def inspect(data):
    if len(data) < 40 or be32(data, 0) != MAGIC:
        raise ValueError('bad FDT magic or short header')
    total, st, strings, reserve, ver, last = struct.unpack_from('>6I', data, 4)
    if ver < 16 or ver > 17 or last > ver:
        raise ValueError('unsupported FDT version %d (last compatible %d)' % (ver, last))
    if total < 40 or total > len(data):
        raise ValueError('FDT totalsize exceeds input or shorter than header')
    size_strings = be32(data, 32)
    size_struct = be32(data, 36)
    if not size_struct or not size_strings:
        raise ValueError('missing FDT structure or strings block')
    if st % 4 or strings % 4 or reserve % 8:
        raise ValueError('FDT offset alignment invalid')
    ranges = [(0, 40, 'header'), (st, st + size_struct, 'struct'),
              (strings, strings + size_strings, 'strings')]
    if reserve < 40 or reserve + 16 > total:
        raise ValueError('reserve map missing or outside totalsize')
    endreserve = reserve
    while True:
        if endreserve + 16 > total:
            raise ValueError('unterminated reserve map')
        addr, size = struct.unpack_from('>QQ', data, endreserve)
        endreserve += 16
        if addr == 0 and size == 0:
            break
    ranges.append((reserve, endreserve, 'reserve'))
    for start, end, name in ranges:
        if start < 0 or end > total or start >= end:
            raise ValueError('%s section outside FDT totalsize' % name)
    for i, a in enumerate(ranges):
        for b in ranges[i + 1:]:
            if max(a[0], b[0]) < min(a[1], b[1]):
                raise ValueError('overlapping FDT %s and %s sections' % (a[2], b[2]))
    return {'totalsize': total, 'struct_offset': st, 'struct_size': size_struct,
            'strings_offset': strings, 'strings_size': size_strings, 'version': ver}


def parse(data, classes):
    """classes=(DtTree, DtNode, DtProperty) from dt_graph; avoids circular import."""
    Tree, Node, Property = classes
    h = inspect(data)
    st, end = h['struct_offset'], h['struct_offset'] + h['struct_size']
    strings = data[h['strings_offset']:h['strings_offset'] + h['strings_size']]
    tree = Tree.__new__(Tree)
    tree.root = None
    tree.nodes, tree.phandle_map, tree.symbols = {}, {}, {}
    stack, p, finished, root_seen = [], st, False, False
    while p + 4 <= end:
        token = be32(data, p)
        p += 4
        if token == BEGIN_NODE:
            nul = data.find(b'\0', p, end)
            if nul < 0:
                raise ValueError('unterminated FDT node name')
            name = data[p:nul].decode('utf-8', 'strict')
            p = align4(nul + 1)
            if p > end:
                raise ValueError('node name extends past struct block')
            if not stack:
                if root_seen or name:
                    raise ValueError('invalid or duplicate FDT root node')
                path = '/'
                node = Node('/', '/', None)
                tree.root, root_seen = node, True
            else:
                parent = stack[-1]
                if not name or '/' in name:
                    raise ValueError('invalid node name %r' % name)
                path = ('/' if parent.path == '/' else parent.path + '/') + name
                if path in tree.nodes:
                    raise ValueError('duplicate FDT node %s' % path)
                node = Node(name, path, parent)
                parent.children[name] = node
            tree.nodes[path] = node
            stack.append(node)
        elif token == END_NODE:
            if not stack:
                raise ValueError('FDT END_NODE without BEGIN_NODE')
            stack.pop()
        elif token == PROP:
            if not stack or p + 8 > end:
                raise ValueError('FDT property outside node or truncated')
            length, noff = struct.unpack_from('>II', data, p)
            p += 8
            if noff >= len(strings):
                raise ValueError('FDT property name offset outside string table')
            nul = strings.find(b'\0', noff)
            if nul < 0:
                raise ValueError('unterminated FDT property name')
            name = strings[noff:nul].decode('utf-8', 'strict')
            if not name or '/' in name or name in stack[-1].props:
                raise ValueError('empty/duplicate/invalid FDT property %r' % name)
            if length > end - p:
                raise ValueError('truncated FDT property %s' % name)
            value = data[p:p + length]
            p += align4(length)
            if p > end:
                raise ValueError('FDT property alignment beyond block')
            prop = Property(name, '')
            prop.data = value
            # NUL-terminated list of printable UTF8 strings; no arbitrary binary
            if value and value[-1] == 0:
                segments = value[:-1].split(b'\0')
                try:
                    dec = [x.decode('utf-8', 'strict') for x in segments]
                    if all(x and all((ord(c) >= 32 or c in '\t\n') for c in x) for x in dec):
                        prop.strings = dec
                except UnicodeDecodeError:
                    pass
            if length % 4 == 0:
                prop.cells = list(struct.unpack('>%dI' % (length // 4), value)) if length else []
            stack[-1].props[name] = prop
        elif token == NOP:
            continue
        elif token == END:
            if stack or not root_seen:
                raise ValueError('FDT END before balanced tree')
            finished = True
            if any(data[p:end]):
                raise ValueError('nonzero bytes after FDT_END in struct block')
            break
        else:
            raise ValueError('unrecognized FDT token 0x%x' % token)
    if not finished:
        raise ValueError('FDT_END missing from structure')
    for path, node in tree.nodes.items():
        for field in ('phandle', 'linux,phandle'):
            v = node.props.get(field)
            if v:
                if len(v.data) != 4 or v.cells[0] in (0, 0xffffffff):
                    raise ValueError('invalid phandle at %s' % path)
                old = tree.phandle_map.get(v.cells[0])
                if old is not None and old != path:
                    raise ValueError('duplicate phandle 0x%x: %s %s' % (v.cells[0], old, path))
                tree.phandle_map[v.cells[0]] = path
                node.phandle = v.cells[0]
    symbols = tree.nodes.get('/__symbols__')
    if symbols:
        for name, prop in symbols.props.items():
            if prop.strings and prop.strings[0] in tree.nodes:
                tree.symbols[name] = prop.strings[0]
    return tree
