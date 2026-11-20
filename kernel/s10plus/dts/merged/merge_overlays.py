#!/usr/bin/env python3
import re
from collections import OrderedDict

def read(f): return open(f).read()

vendor = read("vendor26.dts")
cam_raw = read("camera-fixed.dts")

vmax = max(int(m) for m in re.findall(r'(?m)^\s*fragment@(\d+)\s*\{', vendor))
cam_nums = sorted(set(int(m) for m in re.findall(r'(?m)^\s*fragment@(\d+)\s*\{', cam_raw)))
remap = {old: vmax+1+i for i, old in enumerate(cam_nums)}

def renumber(text, remap):
    for old,new in sorted(remap.items(), key=lambda kv:-kv[0]):
        text = re.sub(r'fragment@%d\b'%old, 'fragment@%d'%new, text)
    return text

cam = renumber(cam_raw, remap)

def split_dts(dts):
    m = re.search(r'(?m)^\s*fragment@', dts)
    ff = m.start()
    positions=[]
    for k in ['__symbols__','__fixups__','__local_fixups__']:
        for mm in re.finditer(rf'\n\t{re.escape(k)} \{{', dts):
            positions.append(mm.start()+1)
    ms = min(positions)
    return dts[:ff], dts[ff:ms], dts[ms:]

def map_raw(dts, name):
    start_m = re.search(rf'\n\t{re.escape(name)} \{{', dts)
    start = start_m.start()+1
    i = dts.index('{', start)
    depth = 0
    for j in range(i, len(dts)):
        c = dts[j]
        if c == '{': depth += 1
        elif c == '}':
            depth -= 1
            if depth == 0:
                return dts[start:j+1]
    raise RuntimeError('unclosed '+name)

# Parse __symbols__ into ordered key -> value
def parse_symbols(dts):
    m = re.search(r'(?m)\t__symbols__ \{(.*?)\n\t\};', dts, re.DOTALL)
    body = m.group(1)
    d = OrderedDict()
    for line in body.splitlines():
        line=line.strip()
        if not line or line.startswith('}'): continue
        mm = re.match(r'([A-Za-z0-9_]+)\s*=\s*(".*?");?$', line)
        if mm:
            d[mm.group(1)] = mm.group(2)
    return d

# Parse __fixups__ into ordered key -> list of quoted path strings
def parse_fixups(dts):
    m = re.search(r'(?m)\t__fixups__ \{(.*?)\n\t\};', dts, re.DOTALL)
    body = m.group(1)
    d = OrderedDict()
    for line in body.splitlines():
        line=line.strip()
        if not line: continue
        mm = re.match(r'([A-Za-z0-9_]+)\s*=\s*(.*?);?$', line)
        if mm:
            key=mm.group(1); val=mm.group(2)
            # split val by commas at top level (quoted paths)
            paths = re.findall(r'"[^"]*"', val)
            d[key] = paths
    return d

def merge_fixups(a, b):
    out = OrderedDict()
    for d in (a,b):
        for k, paths in d.items():
            out.setdefault(k, [])
            for p in paths:
                if p not in out[k]:
                    out[k].append(p)
    return out

vsym = parse_symbols(vendor); csym = parse_symbols(cam)
vfix = parse_fixups(vendor); cfix = parse_fixups(cam)

# Local fixups: need to merge node-by-node (fragment@N trees). We'll just concatenate
# the two map bodies for __local_fixups__ (node names are already disjoint after renumber).
def local_fixups_body(dts):
    m = re.search(r'(?m)\t__local_fixups__ \{(.*?)\n\t\};', dts, re.DOTALL)
    return m.group(1).strip('\n')

v_header, v_frags, v_maps = split_dts(vendor)
c_header, c_frags, c_maps = split_dts(cam)

out = v_header.rstrip() + '\n' + v_frags.rstrip() + '\n\n' + c_frags.strip('\n') + '\n'

# __symbols__ (dedupe; camera wins on conflict, but our keys are prefixed anyway)
out += '\t__symbols__ {\n'
for k,v in vsym.items():
    out += f'\t\t{k} = {v};\n'
for k,v in csym.items():
    if k in vsym:
        continue
    out += f'\t\t{k} = {v};\n'
out += '\t};\n'

# __fixups__ (merge, comma-join paths)
out += '\t__fixups__ {\n'
merged_fix = merge_fixups(vfix, cfix)
for k, paths in merged_fix.items():
    out += f'\t\t{k} = ' + ', '.join(paths) + ';\n'
out += '\t};\n'

# __local_fixups__ (concatenate disjoint fragment trees)
out += '\t__local_fixups__ {\n'
out += local_fixups_body(vendor) + '\n\n'
out += local_fixups_body(cam) + '\n'
out += '\t};\n'

out += '};\n'
open("merged-overlay.dts","w").write(out)
print("OK. vendor 0..%d, camera->%s" % (vmax, remap))
print("  symbols v/c=%d/%d  fixups v/c=%d/%d merged=%d" % (len(vsym),len(csym),len(vfix),len(cfix),len(merged_fix)))
