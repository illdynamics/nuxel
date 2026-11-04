/* Read-only reproduction of WebKitGTK 2.54.1's drmMainDevice() enumeration.
 *
 * It calls drmGetDevices2(0, ...) exactly like
 * Source/WebKit/UIProcess/glib/DRMMainDevice.cpp and reports whether a real
 * DRM device with a render node exists.  It never creates /dev/dri nodes,
 * never opens /dev/mali0 and never stubs a DRM ioctl.
 *
 * Build: gcc -O2 -o nuxel-drm-main-device-probe nuxel-drm-main-device-probe.c -ldrm
 */
#include <stdio.h>
#include <stdlib.h>
#include <xf86drm.h>

int main(void) {
    drmDevicePtr devices[64] = {0};
    int n = drmGetDevices2(0, devices, 64);
    if (n < 0) {
        printf("drm_devices=error errno=%d\n", -n);
        printf("render_nodes=0 webkit_drmMainDevice_is_null=true\n");
        return 1;
    }
    printf("drm_devices=%d\n", n);
    int render_nodes = 0;
    for (int i = 0; i < n; i++) {
        drmDevicePtr d = devices[i];
        const char *primary = (d->available_nodes & (1 << DRM_NODE_PRIMARY))
                              ? d->nodes[DRM_NODE_PRIMARY] : "-";
        const char *render = (d->available_nodes & (1 << DRM_NODE_RENDER))
                             ? d->nodes[DRM_NODE_RENDER] : "-";
        if (d->available_nodes & (1 << DRM_NODE_RENDER)) render_nodes++;
        printf("device[%d] primary=%s render=%s\n", i, primary, render);
    }
    drmFreeDevices(devices, n);
    printf("render_nodes=%d webkit_drmMainDevice_is_null=%s\n",
           render_nodes, render_nodes ? "false" : "true");
    return render_nodes ? 0 : 1;
}
