/* ABI probe: the numbers the S10+ UI hard-codes, checked against the ARM64
   kernel UAPI headers (compile-time only - a mismatch fails the build). */
#include <linux/input.h>
#include <stddef.h>
_Static_assert(EVIOCGBIT(EV_ABS, 32)==0x80204523u, "EVIOCGBIT(EV_ABS,32)");
_Static_assert(EVIOCGABS(ABS_MT_POSITION_X)==0x80184575u, "EVIOCGABS(MT_X)");
_Static_assert(EVIOCGABS(ABS_MT_POSITION_Y)==0x80184576u, "EVIOCGABS(MT_Y)");
_Static_assert(EVIOCGABS(ABS_X)==0x80184540u, "EVIOCGABS(ABS_X)");
_Static_assert(EVIOCGABS(ABS_Y)==0x80184541u, "EVIOCGABS(ABS_Y)");
_Static_assert(EVIOCGPROP(8)==0x80084509u, "EVIOCGPROP(8)");
_Static_assert(sizeof(struct input_event)==24, "input_event is 24 bytes on arm64");
_Static_assert(sizeof(struct input_absinfo)==24, "input_absinfo is 24 bytes");
_Static_assert(ABS_MT_SLOT==0x2f && ABS_MT_POSITION_X==0x35 && ABS_MT_POSITION_Y==0x36, "MT codes");
_Static_assert(ABS_MT_TRACKING_ID==0x39 && BTN_TOUCH==0x14a, "MT tracking/BTN_TOUCH");
_Static_assert(INPUT_PROP_DIRECT==0x01, "INPUT_PROP_DIRECT");
int main(void){ return 0; }
