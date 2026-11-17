"""Execute capture payload boundaries without accessing any device."""
import pathlib
import subprocess
import tempfile

ROOT = pathlib.Path(__file__).resolve().parents[2]

def test_payload_bounds_under_sanitizers():
    source = ROOT / 'tools/s10plus/fimc-capture/nuxel-fimc-capture.c'
    with tempfile.TemporaryDirectory() as d:
        p = pathlib.Path(d)
        (p / 'test.c').write_text('''
#define main capture_main
#include "''' + str(source) + '''"
#undef main
#include <assert.h>
int main(void) {
    struct v4l2_buffer b = {0};
    struct v4l2_plane p = {0};
    size_t n = 999;
    unsigned char constant[] = {0,0,0,0}, varied[] = {0,1,2,3};
    b.length = 1;
    assert(payload_length(&b, &p, 64, &n) == -1);
    p.bytesused = 65;
    assert(payload_length(&b, &p, 64, &n) == -1);
    p.bytesused = 64; p.data_offset = 64;
    assert(payload_length(&b, &p, 64, &n) == -1);
    p.data_offset = 4;
    assert(payload_length(&b, &p, 64, &n) == 0 && n == 60);
    b.flags = V4L2_BUF_FLAG_ERROR;
    assert(payload_length(&b, &p, 64, &n) == -1);
    b.flags = 0; b.length = 2;
    assert(payload_length(&b, &p, 64, &n) == -1);
    assert(!varied_payload(constant, sizeof(constant)));
    assert(!varied_payload(constant, 0));
    assert(varied_payload(varied, sizeof(varied)));
    return 0;
}
''')
        subprocess.run(['cc','-Wall','-Wextra','-Werror','-fsanitize=address,undefined',
                        '-I'+str(ROOT/'tools/s10plus/v4l2-uapi'),str(p/'test.c'),
                        '-o',str(p/'test')],check=True)
        subprocess.run([str(p/'test')],check=True)

def test_group_input_rejects_legacy_enum_before_device_access():
    with tempfile.TemporaryDirectory() as d:
        binary = pathlib.Path(d)/'capture'
        subprocess.run(['cc','-Wall','-Wextra','-Werror',
                        '-I'+str(ROOT/'tools/s10plus/v4l2-uapi'),
                        str(ROOT/'tools/s10plus/fimc-capture/nuxel-fimc-capture.c'),
                        '-o',str(binary)],check=True)
        for args in [ ['--sensor-id','37','--sensor-probe','--allow-sensor-init'],
                      ['--sensor-position','1','--sensor-probe','--allow-sensor-init'],
                      ['--sensor-position','0','--sensor-probe'],
                      ['--probe-only'] ]:
            result = subprocess.run([str(binary),'--node','/dev/nonexistent']+args,
                                    capture_output=True,text=True)
            assert result.returncode == 2
            assert not result.stdout  # rejected before stat/open/ioctls
