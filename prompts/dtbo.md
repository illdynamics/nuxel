total 1994293
-rw-r--r--  1 wicked  wheel  1994293 Nov 12 20:05 /tmp/dtbo-patched.img
entry9 181701 1812592 d00dfeed

codex
The dtbo patch is valid. Let me back up the dtbo partition, verify the image, then write it.
exec
/bin/zsh -lc "cd /tmp && python3 - <<'PY'
import struct
orig=open('/tmp/dtbo-live.img','rb').read()
new=open('/tmp/dtbo-patched.img','rb').read()
magic,total,hsize,esize,ecount,esize2,total2 = struct.unpack('>7I', new[:28])
assert magic==0xd7b7ab1e and ecount==10 and hsize==32 and esize==32, (hex(magic),ecount,hsize,esize)
# Every unchanged entry must be byte-identical to the original.
for i in range(ecount):
    h=hsize+i*esize
    sz,off=struct.unpack('>II', new[h:h+8])
    if i==9: continue
    osz,ooff=struct.unpack('>II', orig[h:h+8])
    assert new[off:off+sz]==orig[ooff:ooff+osz], i
print(\"unchanged entries identical; entry9 magic\", new[struct.unpack('>I',new[hsize+9*esize+4:hsize+9*esize+8])[0]:][:4])
PY
shasum -a 256 /tmp/dtbo-patched.img" in /Users/wicked/x/nuxel
 succeeded in 0ms:
unchanged entries identical; entry9 magic b'\xd0\r\xfe\xed'
7f03dea362e27be1af80b712a0e0070f8a60a086a43f4e2b13e9a812340802dc  /tmp/dtbo-patched.img

exec
/bin/zsh -lc 'mkdir -p /Users/wicked/x/nuxel/build/out/s10plus/debug-candidates/p109000-nfc-dtbo && D=/Users/wicked/x/nuxel/build/out/s10plus/debug-candidates/p109000-nfc-dtbo && cp /tmp/dtbo-live.img $D/dtbo-before.img && cp /tmp/dtbo-patched.img $D/dtbo-nfc-nci.img && cp /tmp/e9.dts $D/dtbo-entry9-stock.dts && cp /tmp/e9-patched.dts $D/dtbo-entry9-nfc-nci.dts && shasum -a 256 $D/*.img | tee $D/SHA256SUMS' in /Users/wicked/x/nuxel
 succeeded in 0ms:
2629e696aa47f141a9816b8530e57f66ad84765d9ebc9d4698ac91cddb0beb79  /Users/wicked/x/nuxel/build/out/s10plus/debug-candidates/p109000-nfc-dtbo/dtbo-before.img
7f03dea362e27be1af80b712a0e0070f8a60a086a43f4e2b13e9a812340802dc  /Users/wicked/x/nuxel/build/out/s10plus/debug-candidates/p109000-nfc-dtbo/dtbo-nfc-nci.img

exec
/bin/zsh -lc 'cd /Users/wicked/x/nuxel && D=build/out/s10plus/debug-candidates/p109000-nfc-dtbo && scp -q -i ~wicked/.ssh/wicked_wqn_id_rsa $D/dtbo-nfc-nci.img root@192.168.178.167:/tmp/dtbo-nfc-nci.img && ssh -i ~wicked/.ssh/wicked_wqn_id_rsa root@192.168.178.167 '"'sha256sum /tmp/dtbo-nfc-nci.img; dd if=/dev/sda13 of=/tmp/dtbo-safety-before.img bs=1M 2>/dev/null; sha256sum /tmp/dtbo-safety-before.img | cut -c1-64; cp /tmp/dtbo-safety-before.img /var/lib/nuxel/nfc/dtbo-before-v4.img 2>/dev/null; sync; dd if=/tmp/dtbo-nfc-nci.img of=/dev/sda13 bs=1048576 conv=fsync 2>&1 | tail -1; sync; dd if=/dev/sda13 of=/tmp/dtbo-readback.img bs=1M 2>/dev/null; head -c 1994293 /tmp/dtbo-readback.img | sha256sum' 2>&1 | tail -8" in /Users/wicked/x/nuxel  
 succeeded in 1244ms:
  /'\_   _/`\    ╚═╝  ╚═══╝ ╚═════╝ ╚═╝  ╚═╝╚══════╝╚══════╝
  \___)=(___/

                  Mobile Linux for Control Freaks
7f03dea362e27be1af80b712a0e0070f8a60a086a43f4e2b13e9a812340802dc  /tmp/dtbo-nfc-nci.img
2629e696aa47f141a9816b8530e57f66ad84765d9ebc9d4698ac91cddb0beb79
1994293 bytes (2.0 MB, 1.9 MiB) copied, 0.0179894 s, 111 MB/s
7f03dea362e27be1af80b712a0e0070f8a60a086a43f4e2b13e9a812340802dc  -

codex
dtbo written and read back identical. Rebooting to activate it.
exec
/bin/zsh -lc "ssh -i ~wicked/.ssh/wicked_wqn_id_rsa root@192.168.178.167 'sync; (sleep 1; systemctl reboot) >/dev/null 2>&1 & echo reboot-scheduled' 2>&1 | tail -1; sleep 50; for i in "'$(seq 1 40); do R=$(ssh -i ~wicked/.ssh/wicked_wqn_id_rsa -o ConnectTimeout=4 -o StrictHostKeyChecking=no root@192.168.178.167 '"'uptime' 2>/dev/null); if [ -n \""'$R" ]; then echo "UP try=$i"; break; fi; sleep 5; done' in /Users/wicked/x/nuxel
^Cturn interrupted
tokens used
194,940,268
[codeseeq] stopping owned bridge process (pid=25667)
[codeseeq] stopping owned bridge process (pid=25667)
(base) ╭─[ꝖꝖ]─wicked↯infranux in ~/x/nuxel
╰─❯❯❯ 

