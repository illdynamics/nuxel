#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-only
"""Execute vendor serializers in an isolated emulator; never open a modem."""
import argparse
import hashlib
import json
import struct
from pathlib import Path
from elftools.elf.elffile import ELFFile
from unicorn import Uc, UC_ARCH_ARM64, UC_MODE_ARM, UC_HOOK_CODE
from unicorn.arm64_const import *

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("elf", help="DTK9 vendor/lib64/libsec-ril.so (not distributed)")
parser.add_argument("--header", action="store_true", help="emit normalized C golden vectors")
parser.add_argument("--rx-header", action="store_true", help="emit receive-conversion C golden vectors")
parser.add_argument("--sms-header", action="store_true", help="emit SMS transport golden vectors")
parser.add_argument("--call-header", action="store_true", help="emit call control golden vectors")
options = parser.parse_args()
ELF = options.elf
EXPECTED_SHA256 = "b02bd095ae44a991b3cb676e584b3209a947160c22e678578f8b0c877e282cb3"
if hashlib.sha256(Path(ELF).read_bytes()).hexdigest() != EXPECTED_SHA256:
    raise SystemExit("wrong vendor ELF; refusing to regenerate protocol fixtures")
OBJ, STR, STACK, STOP = 0x60000000, 0x60008000, 0x70000000, 0x50000000
with open(ELF, 'rb') as f:
    e = ELFFile(f)
    segments = [(s['p_vaddr'], s.data()) for s in e.iter_segments() if s['p_type'] == 'PT_LOAD']
    dyn = list(e.get_section_by_name('.dynsym').iter_symbols())
    syms = {s.name: s['st_value'] for s in dyn}
    relocs = list(e.get_section_by_name('.rela.dyn').iter_relocations())
    plt_base = e.get_section_by_name('.plt')['sh_addr']
    plts = {plt_base + 32 + i*16: dyn[r['r_info_sym']].name for i, r in enumerate(e.get_section_by_name('.rela.plt').iter_relocations())}

def run(name, args, strings=None):
    u = Uc(UC_ARCH_ARM64, UC_MODE_ARM)
    for base, size in [(0,0x500000),(OBJ,0x100000),(STACK,0x100000),(STOP,0x1000)]: u.mem_map(base,size)
    for base, data in segments: u.mem_write(base,data)
    for r in relocs:
        if r['r_info_type'] == 1027: val = r['r_addend']
        elif r['r_info_type'] in [257,1025]: val = dyn[r['r_info_sym']]['st_value'] + r['r_addend']
        else: continue
        u.mem_write(r['r_offset'],struct.pack('<Q',val))
    def q(a,v):u.mem_write(a,struct.pack('<Q',v))
    q(OBJ,syms['_ZTV13IpcProtocol41']+16)
    q(OBJ+16,OBJ+0x2000); q(OBJ+0x2000,OBJ+0x3000);q(OBJ+0x3030,STOP)
    q(OBJ+0x68,OBJ+0x5000)
    if strings:
        for off,s in strings.items():u.mem_write(STR+off,s.encode()+b'\0' if isinstance(s,str) else bytes(s))
    u.reg_write(UC_ARM64_REG_TPIDR_EL0,OBJ+0x4000)
    sp=STACK+0x80000
    u.reg_write(UC_ARM64_REG_SP,sp);u.reg_write(UC_ARM64_REG_LR,STOP+4)
    for i,arg in enumerate([OBJ]+args):
        if i<8:u.reg_write(UC_ARM64_REG_X0+i,arg)
        else:q(sp+8*(i-8),arg)
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
            # Explicit normal/default property context, no Android runtime.
            dst=uc.reg_read(UC_ARM64_REG_X2); src=uc.reg_read(UC_ARM64_REG_X3)
            value=bytes(uc.mem_read(src,128)).split(b'\0')[0]+b'\0'
            uc.mem_write(dst,value);ret=len(value)-1
        elif symbol=='_Z14CompareStringsPKcz':ret=0
        elif symbol=='memset':
            dst=uc.reg_read(UC_ARM64_REG_X0);n=uc.reg_read(UC_ARM64_REG_X2)
            uc.mem_write(dst,bytes([uc.reg_read(UC_ARM64_REG_X1)&255])*n);ret=dst
        elif symbol=='__memcpy_chk':
            dst=uc.reg_read(UC_ARM64_REG_X0);src=uc.reg_read(UC_ARM64_REG_X1)
            n=uc.reg_read(UC_ARM64_REG_X2);cap=uc.reg_read(UC_ARM64_REG_X3)
            if n>cap:raise RuntimeError('vendor copy exceeds destination')
            if n:uc.mem_write(dst,bytes(uc.mem_read(src,n)))
            ret=dst
        elif symbol.startswith('_ZN6Region') or symbol=='__android_log_buf_print':ret=0
        elif syms.get(symbol):
            uc.reg_write(UC_ARM64_REG_PC,syms[symbol]);return
        else:raise RuntimeError(f'unhandled import {symbol} at {addr:x}')
        uc.reg_write(UC_ARM64_REG_X0,ret);uc.reg_write(UC_ARM64_REG_PC,uc.reg_read(UC_ARM64_REG_LR))
    u.hook_add(UC_HOOK_CODE,hook)
    # Match the complete Itanium method name. A substring would accidentally
    # select IpcTxDeliveryReportWithPdu for IpcTxDeliveryReport.
    prefix=f'_ZN13IpcProtocol41{len(name)}{name}E'
    matches=[v for k,v in syms.items() if k.startswith(prefix)]
    if len(matches)!=1:raise RuntimeError(f'non-unique serializer {name}: {matches}')
    addr=matches[0]
    try:u.emu_start(addr,STOP+8,count=100000)
    except Exception:
        print('failed PC',hex(u.reg_read(UC_ARM64_REG_PC)));raise
    if not captured:raise RuntimeError(f'no transmit for {name}; return {u.reg_read(UC_ARM64_REG_X0):x}')
    return captured[0]

def registration_states():
    """Execute the receiver's conversion block, with EPDG/policy overrides off."""
    result=[]
    for wire in range(256):
        u=Uc(UC_ARCH_ARM64,UC_MODE_ARM)
        u.mem_map(0,0x500000);u.mem_map(OBJ,0x10000)
        for base,data in segments:u.mem_write(base,data)
        u.mem_write(OBJ+9,bytes([wire]));u.mem_write(OBJ+7,bytes([33]))
        u.reg_write(UC_ARM64_REG_X19,OBJ)
        def hook(uc,addr,size,data):
            if addr==0x339c04:uc.emu_stop()
            elif addr==0x339aec:
                # IsDomesticRoaming-style virtual policy override is false.
                uc.reg_write(UC_ARM64_REG_PC,0x339bf8)
            elif addr==0x38d650:
                uc.reg_write(UC_ARM64_REG_X0,0)
                uc.reg_write(UC_ARM64_REG_PC,uc.reg_read(UC_ARM64_REG_LR))
        u.hook_add(UC_HOOK_CODE,hook)
        u.emu_start(0x3399cc,0x339c08,count=1000)
        if u.reg_read(UC_ARM64_REG_PC)!=0x339c04:raise RuntimeError('conversion did not finish')
        result.append(u.reg_read(UC_ARM64_REG_W26))
    return bytes(result)

if __name__=='__main__':
    results={}
    for enabled in [0,1]:
        results[f'profile_enabled_{enabled}']=run('IpcTxSetDataProfile',[STR,STR+128,STR+256,0,4,0,enabled,0,0,0,0],{0:'internet'}).hex()
    for apply in [0,1]:
        results[f'attach_bool_{apply}']=run('IpcTxSetLteAttachProfile',[1,STR,STR+128,STR+256,0,4,4,0,0,0,apply],{0:'internet'}).hex()
    results['define_pdp']=run('IpcTxDefinePdpContext',[STR,1,4,0,0,0],{0:'internet'}).hex()
    results['define_pdp_ipv4']=run('IpcTxDefinePdpContext',[STR,1,2,0,0,0],{0:'internet'}).hex()
    results['release_pdp']=run('IpcTxSetPdpContext',[1,0,STR,STR+128,0,0],{0:''}).hex()
    results['activate_pdp']=run('IpcTxSetPdpContext',[1,1,STR,STR+128,0,0],{0:''}).hex()
    results['preferred_lte_auto']=run('IpcTxNetSetPreferredNetType',[9]).hex()
    results['preferred_lte_only']=run('IpcTxNetSetPreferredNetType',[11]).hex()
    results['get_preferred_network']=run('IpcTxNetGetPreferredNetType',[]).hex()
    results['domain_cs_ps']=run('IpcTxNetSetServiceDomain',[0]).hex()
    results['domain_ps_only']=run('IpcTxNetSetServiceDomain',[1]).hex()
    results['domain_cs_only']=run('IpcTxNetSetServiceDomain',[2]).hex()
    results['get_service_domain']=run('IpcTxNetGetServiceDomain',[]).hex()
    results['get_pin_status']=run('IpcTxGetPinStatus',[]).hex()
    results['get_sim_network']=run('IpcTxGetImsi',[]).hex()
    results['get_baseband']=run('IpcTxBaseBandVersion',[]).hex()
    results['radio_on']=run('IpcTxRadioPower',[2]).hex()
    results['radio_off']=run('IpcTxRadioPower',[1]).hex()
    results['select_auto']=run('IpcTxNetSetNetSelectionAuto',[2]).hex()
    results['oes_confirm']=run('IpcTxCfrmOesDrkCpInfo',[]).hex()
    results['oes_certificate']=run('IpcTxEventDrkCpInfo',[0,1,5,STR],{0:'DER01'}).hex()
    results['oes_missing']=run('IpcTxEventDrkCpInfo',[1,0,0,STR]).hex()
    results['detach_initial_apn']=run('IpcTxPsAttach',[1,0,0,4]).hex()
    results['ps_attach']=run('IpcTxPsAttach',[1,1,0,0]).hex()
    results['sync_profile']=run('IpcTxSyncProfileInfo',[0,14,STR,STR+128,STR+256,0,4,4,0,0,1],{0:'internet'}).hex()
    results['pap_profile']=run('IpcTxSetDataProfile',[STR,STR+128,STR+256,1,4,0,1,0,0,0,0],{0:'internet'}).hex()
    results['chap_attach']=run('IpcTxSetLteAttachProfile',[5,STR,STR+128,STR+256,2,2,2,0,0,0,0],{0:'internet'}).hex()
    results['pap_activate']=run('IpcTxSetPdpContext',[1,1,STR,STR+128,1,0],{0:''}).hex()
    results['registration_states']=registration_states().hex()
    sms_pdu=bytes.fromhex('00212a0b912143658709f1000005e8329bfd06')
    for domain in range(4):
        results[f'sms_send_domain_{domain}']=run('IpcTxSendSms',[2,1,1,1,domain,STR,len(sms_pdu)],{0:sms_pdu}).hex()
    results['sms_send_more']=run('IpcTxSendSms',[2,1,2,2,2,STR,len(sms_pdu)],{0:sms_pdu}).hex()
    results['sms_ack_ok']=run('IpcTxDeliveryReport',[2,0x42,1,0]).hex()
    results['sms_ack_memory_full']=run('IpcTxDeliveryReport',[2,0x42,0,0x16]).hex()
    results['sms_get_smsc']=run('IpcTxGetSmscAddress',[]).hex()
    results['sms_device_ready']=run('IpcTxSetDeviceReady',[]).hex()
    results['call_dial_international']=run('IpcTxCallOriginate',[STR,0,1,0],{0:'+12345678901'}).hex()
    results['call_dial_national']=run('IpcTxCallOriginate',[STR,0,1,0],{0:'0123456789'}).hex()
    results['call_answer']=run('IpcTxCallAnswer',[1]).hex()
    results['call_release']=run('IpcTxCallRelease',[]).hex()
    results['call_get_list']=run('IpcTxCallGetCallList',[]).hex()
    results['call_get_voice_registration']=run('IpcTxNetGetVoiceRegState',[]).hex()
    if not options.header and not options.rx_header and not options.sms_header and not options.call_header:
        print(json.dumps(results,indent=2))
    else:
        print("/* Golden vectors from isolated execution of DTK9 libsec-ril.so.\n"
              f" * SHA256 {EXPECTED_SHA256}.\n"
              " * Only bytes after the profile-label NUL are normalized to zero: the vendor\n"
              " * over-copies adjacent literal PB_CMD; the CP ignores this string padding.\n"
              " * See scripts/recover_vendor_vectors.py. No hardware access. */")
        for name, raw in results.items():
            if name.startswith('sms_') != options.sms_header:continue
            if name.startswith('call_') != options.call_header:continue
            if (name == 'registration_states') != options.rx_header:continue
            frame = bytearray.fromhex(raw)
            if frame[4:7] == bytes([13,27,3]):
                frame[20:28] = bytes(8)
            print(f"static const uint8_t golden_{name}[] = {{")
            for i in range(0,len(frame),16):
                print("    " + ", ".join(f"0x{x:02x}" for x in frame[i:i+16]) + ",")
            print("};")
