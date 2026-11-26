#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-only
"""Optional isolated vendor check; requires pyelftools and unicorn.
Run from repo root, or pass the matching libsec-ril.so path. Synthetic data
only; this script does not open a modem, contact a SIM, or use a network.
"""
import sys, struct, hashlib
from pathlib import Path
from elftools.elf.elffile import ELFFile
from unicorn import Uc, UC_ARCH_ARM64, UC_MODE_ARM, UC_HOOK_CODE
from unicorn.arm64_const import *

ELF=sys.argv[1] if len(sys.argv)>1 else '.vendor-ro/libsec-ril.so'
assert hashlib.sha256(Path(ELF).read_bytes()).hexdigest() == 'b02bd095ae44a991b3cb676e584b3209a947160c22e678578f8b0c877e282cb3'
OBJ, STR, STACK, STOP = 0x60000000, 0x60008000, 0x70000000, 0x50000000
with open(ELF,'rb') as f:
    e=ELFFile(f)
    segments=[(s['p_vaddr'],s.data()) for s in e.iter_segments() if s['p_type']=='PT_LOAD']
    dyn=list(e.get_section_by_name('.dynsym').iter_symbols())
    syms={s.name:s['st_value'] for s in dyn}
    relocs=list(e.get_section_by_name('.rela.dyn').iter_relocations())
    plt_base=e.get_section_by_name('.plt')['sh_addr']
    plts={plt_base+32+i*16: dyn[r['r_info_sym']].name for i,r in enumerate(e.get_section_by_name('.rela.plt').iter_relocations())}

def run(name,args):
    u=Uc(UC_ARCH_ARM64,UC_MODE_ARM)
    for base,size in [(0,0x500000),(OBJ,0x100000),(STACK,0x100000),(STOP,0x1000)]:u.mem_map(base,size)
    for base,data in segments:u.mem_write(base,data)
    for r in relocs:
        t=r['r_info_type']
        if t==1027: val=r['r_addend']
        elif t in [257,1025]: val=dyn[r['r_info_sym']]['st_value']+r['r_addend']
        else: continue
        u.mem_write(r['r_offset'],struct.pack('<Q',val))
    def q(a,v):u.mem_write(a,struct.pack('<Q',v))
    q(OBJ,syms['_ZTV13IpcProtocol41']+16)
    q(OBJ+16,OBJ+0x2000); q(OBJ+0x2000,OBJ+0x3000); q(OBJ+0x3030,STOP)
    q(OBJ+0x68,OBJ+0x5000)
    u.reg_write(UC_ARM64_REG_TPIDR_EL0,OBJ+0x4000)
    sp=STACK+0x80000
    u.reg_write(UC_ARM64_REG_SP,sp);u.reg_write(UC_ARM64_REG_LR,STOP+4)
    for i,arg in enumerate([OBJ]+args):
        if i<8:u.reg_write(UC_ARM64_REG_X0+i,arg)
        else:q(sp+8*(i-8),arg)
    u.mem_write(STR, bytes(range(16))); u.mem_write(STR+32, bytes(range(16,32)))
    captured=[]
    def hook(uc,addr,size,data):
        if addr==STOP:
            ptr=uc.reg_read(UC_ARM64_REG_X1);n=uc.reg_read(UC_ARM64_REG_X2)
            captured.append(bytes(uc.mem_read(ptr,n)));uc.emu_stop();return
        if addr==STOP+4:uc.emu_stop();return
        if addr not in plts:return
        symbol=plts[addr]
        if symbol=='strlen':
            ptr=uc.reg_read(UC_ARM64_REG_X0);ret=bytes(uc.mem_read(ptr,1024)).index(0)
        elif symbol=='_ZN6Region11GetInstanceEv':ret=OBJ+0x6000
        elif symbol=='_Z12ReadPropertyPKciPcS0_':
            dst=uc.reg_read(UC_ARM64_REG_X2);src=uc.reg_read(UC_ARM64_REG_X3)
            value=bytes(uc.mem_read(src,128)).split(b'\0')[0]+b'\0'
            uc.mem_write(dst,value);ret=len(value)-1
        elif symbol=='_Z14CompareStringsPKcz':ret=0
        elif symbol=='memset':
            dst=uc.reg_read(UC_ARM64_REG_X0);n=uc.reg_read(UC_ARM64_REG_X2)
            uc.mem_write(dst,bytes([uc.reg_read(UC_ARM64_REG_X1)&255])*n);ret=dst
        elif symbol in ('__memcpy_chk','memcpy'):
            dst=uc.reg_read(UC_ARM64_REG_X0);src=uc.reg_read(UC_ARM64_REG_X1)
            n=uc.reg_read(UC_ARM64_REG_X2);cap=uc.reg_read(UC_ARM64_REG_X3)
            if symbol=='__memcpy_chk' and n>cap:raise RuntimeError('copy overflow')
            if n:uc.mem_write(dst,bytes(uc.mem_read(src,n)))
            ret=dst
        elif symbol.startswith('_ZN6Region') or symbol=='__android_log_buf_print':ret=0
        elif syms.get(symbol):
            uc.reg_write(UC_ARM64_REG_PC,syms[symbol]);return
        else:raise RuntimeError(f'unhandled {symbol} at {addr:x}')
        uc.reg_write(UC_ARM64_REG_X0,ret);uc.reg_write(UC_ARM64_REG_PC,uc.reg_read(UC_ARM64_REG_LR))
    u.hook_add(UC_HOOK_CODE,hook)
    matches=[v for k,v in syms.items() if k.startswith(f'_ZN13IpcProtocol41{len(name)}{name}E')]
    if len(matches)!=1: raise RuntimeError(f'non-unique {name}: {matches}')
    addr=matches[0]
    u.emu_start(addr,STOP+8,count=200000)
    if not captured: raise RuntimeError(f'no tx for {name}; ret={u.reg_read(UC_ARM64_REG_X0):x}')
    return captured[0]


expected=bytes.fromhex('2a0000000509020210000102030405060708090a0b0c0d0e0f10101112131415161718191a1b1c1d1e1f')
assert run('IpcTxDoUiccAuth',[2,STR,16,STR+32,16])==expected
try:
    run('IpcTxImsAuthResp',[STR,16])
    raise AssertionError('CP auth response unexpectedly transmitted')
except RuntimeError as error:
    assert str(error)=='no tx for IpcTxImsAuthResp; ret=ffffffff',str(error)
vtable=syms['_ZTV10SmsManager']+16
slot=next(r for r in relocs if r['r_offset']==vtable+64)
assert dyn[slot['r_info_sym']].name=='_ZN10SmsManager9DoSendSmsEP7Requesti9ModemType'
print('Vendor USIM frame, unsupported CP auth relay, and SMS ModemType vtable: PASS')
