#!/usr/bin/env python3
"""Offline synthetic execution of the pinned vendor RX decoder; never loads on device.
Requires pyelftools/unicorn. Pass path to independently supplied libsec-ril.so.
"""
import hashlib
import struct
import sys
from elftools.elf.elffile import ELFFile
from unicorn import Uc, UC_ARCH_ARM64, UC_MODE_ARM, UC_HOOK_CODE
from unicorn.arm64_const import UC_ARM64_REG_X0, UC_ARM64_REG_SP, UC_ARM64_REG_LR, UC_ARM64_REG_PC, UC_ARM64_REG_TPIDR_EL0
path = sys.argv[1]
assert hashlib.sha256(open(path, 'rb').read()).hexdigest() == 'b02bd095ae44a991b3cb676e584b3209a947160c22e678578f8b0c877e282cb3'
with open(path, 'rb') as f:
    elf = ELFFile(f)
    segments = [(s['p_vaddr'], s.data()) for s in elf.iter_segments() if s['p_type'] == 'PT_LOAD']
    dyn = list(elf.get_section_by_name('.dynsym').iter_symbols())
    syms = {s.name: s['st_value'] for s in dyn}
    relocs = list(elf.get_section_by_name('.rela.dyn').iter_relocations())
    base = elf.get_section_by_name('.plt')['sh_addr']
    plts = {base+32+i*16: dyn[r['r_info_sym']].name for i,r in enumerate(elf.get_section_by_name('.rela.plt').iter_relocations())}

def run(new):
    u = Uc(UC_ARCH_ARM64, UC_MODE_ARM)
    u.mem_map(0, 0x500000)
    u.mem_map(0x60000000, 0x200000)
    for addr,data in segments: u.mem_write(addr,data)
    def q(a,v): u.mem_write(a,struct.pack('<Q',v))
    for r in relocs:
        t=r['r_info_type']
        if t==1027: v=r['r_addend']
        elif t in (257,1025): v=dyn[r['r_info_sym']]['st_value']+r['r_addend']
        else: continue
        q(r['r_offset'],v)
    obj, data, result, cells, stop = (0x60000000,0x60010000,0x60020000,0x60030000,0x60100000)
    q(obj+0x68,obj+0x8000)
    u.reg_write(UC_ARM64_REG_SP,0x600f0000)
    u.reg_write(UC_ARM64_REG_TPIDR_EL0,obj+0x9000)
    u.reg_write(UC_ARM64_REG_LR,stop)
    rec = bytearray(31)
    rec[0]=1
    rec[1:7]=b'00101#'
    struct.pack_into('<IIHI',rec,7,0x1234567,301,0x3456,1300)
    counts = bytes([0,0,1,0]+([0] if new else []))
    frame = struct.pack('<HBBBBB',7+len(counts)+len(rec),0,0,8,17,2)+counts+rec
    u.mem_write(data,frame)
    for i,v in enumerate([obj,data,len(frame),obj+0xa000,obj+0xa004]):u.reg_write(UC_ARM64_REG_X0+i,v)
    def hook(uc,addr,size,_):
        if addr==stop: uc.emu_stop();return
        if addr not in plts:return
        s=plts[addr]
        reg=lambda i:uc.reg_read(UC_ARM64_REG_X0+i)
        if s=='_Znwm': ret=result
        elif s=='_ZN15CellInfoListV14C1Ei':
            q(result+24,cells);ret=result
        elif s=='__strncpy_chk2':
            b=bytes(uc.mem_read(reg(1),reg(2))).split(b'\0')[0]
            uc.mem_write(reg(0),b.ljust(reg(2),b'\0'));ret=reg(0)
        elif s=='__android_log_buf_print':ret=0
        else:raise RuntimeError('unexpected vendor dependency '+s)
        uc.reg_write(UC_ARM64_REG_X0,ret)
        uc.reg_write(UC_ARM64_REG_PC,uc.reg_read(UC_ARM64_REG_LR))
    u.hook_add(UC_HOOK_CODE,hook)
    u.emu_start(syms['_ZN13IpcProtocol4120IpcRxNetCellInfoListEPciRiR14RegistrantType'],stop+4,count=100000)
    assert u.reg_read(UC_ARM64_REG_PC)==stop
    assert u.reg_read(UC_ARM64_REG_X0)==result
    out=bytes(u.mem_read(cells,40))
    assert struct.unpack_from('<II',out)==(3,1)
    assert out[16:24]==b'001\x0001\x00\x00'
    assert struct.unpack_from('<IIII',out,24)==(0x1234567,301,0x3456,1300)
    print(('five-count' if new else 'four-count')+' vendor decoder: LTE, registered, MCC/MNC, CI/PCI/TAC/EARFCN PASS')
run(False)
run(True)
