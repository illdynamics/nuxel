#!/usr/bin/env python3
"""Safe, read-only sanity check of `heimdall print-pit` output.

PIT does not contain a device-tree revision or reliable logical block byte
size. Do NOT treat this script as permission to flash an unproven board DTB.
"""
import argparse
import pathlib
import re
import sys

FIELDS=('Partition Name','Partition Block Count','Partition Block Size/Offset','Device Type','Identifier')

def entries_from_text(data):
    header=re.search(r'CPU/bootloader tag:\s*(\S+)',data)
    if not header:raise ValueError('missing CPU/bootloader tag')
    all_entries=[]
    for raw in re.split(r'^--- Entry #\d+ ---\s*$',data,flags=re.M)[1:]:
        row={}
        for field in FIELDS:
            m=re.search(r'^'+re.escape(field)+r':\s*(\S+)',raw,re.M)
            if m:row[field]=m.group(1)
        if 'Partition Name' in row:all_entries.append(row)
    return header.group(1),all_entries

def main():
    p=argparse.ArgumentParser()
    p.add_argument('pit',type=pathlib.Path,help='text from heimdall print-pit')
    p.add_argument('--boot',type=pathlib.Path,help='optional boot image to check')
    p.add_argument('--rootfs',type=pathlib.Path,help='optional rootfs image to check')
    p.add_argument('--verified-block-bytes',type=int,choices=[512,4096,8192],
                  help='ONLY if independently verified for device; never infer from PIT')
    args=p.parse_args()
    try:
        cpu,rows=entries_from_text(args.pit.read_text(errors='replace'))
        if cpu!='LSI9820':raise ValueError('expected Exynos LSI9820, found '+cpu)
        names={r.get('Partition Name'):r for r in rows}
        for part in ('DTB','DTBO','BOOT','USERDATA','SYSTEM'):
            if part not in names:raise ValueError('required entry missing: '+part)
        if len(rows)!=41:raise ValueError('expected 41 PIT entries from attached reference; found '+str(len(rows)))
        for key in ('BOOT','USERDATA'):
            if names[key].get('Device Type')!='8':raise ValueError('unexpected non-UFS partition '+key)
        print('PASS: LSI9820 PIT with 41 entries, separate DTB/DTBO/BOOT/SYSTEM/USERDATA')
        for key,p in [('BOOT',args.boot),('USERDATA',args.rootfs)]:
            row=names[key]
            count=int(row['Partition Block Count'])
            print(f'{key}: PIT block-count={count}, identifier={row.get("Identifier")}, logical unit={row.get("Partition Block Size/Offset")}')
            if p is not None:
                size=p.stat().st_size
                print(f'  supplied image bytes={size}')
                if count==0:
                    print('  CAPACITY UNKNOWN: count=0 (extends to disk end); require actual capacity check')
                elif args.verified_block_bytes:
                    cap=count*args.verified_block_bytes
                    if size>cap:raise ValueError(f'{key} image {size} exceeds verified {cap}-byte capacity')
                    print('  PASS: image <= independently-verified capacity',cap)
                else:print('  CAPACITY NOT VERIFIED: PIT does not state verified block size in bytes')
        print('NOT DETERMINABLE FROM PIT: board hardware revision, DTB overlay rev, bootloader apply behavior, physical boot')
        return 0
    except (OSError,ValueError) as e:
        print('PIT CHECK FAILED: '+str(e),file=sys.stderr)
        return 1
if __name__=='__main__':sys.exit(main())
