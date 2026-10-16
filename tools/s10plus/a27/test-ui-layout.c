/* ============================================================================
 * test-ui-layout.c — offline layout harness for the A27 Nuxel phone UI.
 *
 * Compiles the SAME renderer the handset runs (tools/s10plus/nuxel-ui.c with the
 * NUXEL_UI_HOST syscall shim) and renders every page at every phone scale with
 * injected extreme-value fixtures, then asserts that layout_check() finds
 * NOTHING wrong:
 *
 *   * no two content elements overlap;
 *   * no element leaves the status-bar/dock safe area;
 *   * no status-bar element sits in the camera cutout.
 *
 * Scales 1..4 correspond to the mission's four panel widths (360x760,
 * 720x1520, 1080x2280, 1440x3040): the design space is 360x760 and SC is the
 * integer scale, so these are the real devices this interface must survive.
 *
 *   cc -O1 -w -o test-ui-layout tools/s10plus/a27/test-ui-layout.c
 *   ./test-ui-layout build/out/s10plus/a27/layout
 *
 * Exit: 0 all pages clean, 1 layout violation found, 2 usage/host error.
 * ==========================================================================*/
#define NUXEL_UI_HOST 1
#include "../nuxel-ui.c"
#include <sys/stat.h>

int main(int argc,char **argv){
  const char *dir = (argc>1)?argv[1]:"/tmp/nuxel-ui-layout";
  mkdir(dir,0755);
  int bad=0, pages=0;
  for(int sc=1;sc<=4;sc++){
    for(int fix=0;fix<4;fix++){
      int w=360*sc, h=760*sc;
      char sub[256]; snprintf(sub,sizeof sub,"%s/s%d-f%d",dir,sc,fix);
      mkdir(sub,0755);
      printf("--- scale=%d (%dx%d) fixture=%d\n",sc,w,h,fix);
      int rc=selftest(sub,w,h,fix);
      if(rc){ printf("FAIL scale=%d fixture=%d rc=%d\n",sc,fix,rc); bad++; }
      else pages+=PAGE_MAX;
    }
  }
  printf("HOST_UI_LAYOUT %s: %d page renders, %d failing configurations\n",
         bad?"FAIL":"OK",pages,bad);
  if(bad) return 1;
  printf("A27_UI_LAYOUT_TESTS_OK\n");
  return 0;
}
