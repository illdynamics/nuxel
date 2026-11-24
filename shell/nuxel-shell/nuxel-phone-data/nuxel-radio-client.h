/* Native Radio1 client. Application capability checks precede private calls;
 * Radio1 independently checks the actual bus sender's EUID. */
#pragma once
#include <gio/gio.h>

typedef void (*NuxelRadioReply)(GVariant *reply, const GError *error, gpointer user);
typedef void (*NuxelRadioChanged)(gpointer user);
typedef struct {
    GDBusProxy *proxy;
    GDBusConnection *permissions;
    GCancellable *cancel;
    const char *app_id;
    NuxelRadioChanged changed;
    gpointer user;
} NuxelRadioClient;
void nuxel_radio_connect(NuxelRadioClient *client, const char *app_id,
                         NuxelRadioChanged changed, gpointer user);
void nuxel_radio_call(NuxelRadioClient *client, const char *method,
                     GVariant *args, const char *capability,
                     NuxelRadioReply callback, gpointer user);
gboolean nuxel_radio_available(NuxelRadioClient *client);
