import struct, sys
MAGIC=b"ANDROID!"
PAGE=2048
def rup(n,a=PAGE): return ((n+a-1)//a)*a
kernel=open(sys.argv[1],'rb').read()
ramdisk=open(sys.argv[2],'rb').read()
dtb=open(sys.argv[3],'rb').read()
cmdline=sys.argv[4].encode()
name=b"nuxel-g7power"
hdr=bytearray(1632)
hdr[0:8]=MAGIC
f=[len(kernel),0x80008000,len(ramdisk),0x81000000,0,0,0x80000100,PAGE,len(dtb),0]
struct.pack_into('<10I',hdr,8,*f)
hdr[48:48+16]=name.ljust(16,b'\0')
assert len(cmdline)<512
hdr[64:64+512]=cmdline.ljust(512,b'\0')
# id[32] and extra_cmdline[1024] left zero
out=bytearray()
out+=bytes(hdr).ljust(PAGE,b'\0')
out+=kernel.ljust(rup(len(kernel)),b'\0')
out+=ramdisk.ljust(rup(len(ramdisk)),b'\0')
out+=dtb.ljust(rup(len(dtb)),b'\0')
open(sys.argv[5],'wb').write(out)
print("wrote",sys.argv[5],len(out),"bytes; k=%d r=%d dt=%d"%(len(kernel),len(ramdisk),len(dtb)))
