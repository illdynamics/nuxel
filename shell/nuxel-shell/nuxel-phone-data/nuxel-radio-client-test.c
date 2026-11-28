#include "nuxel-radio-client.h"
#include <string.h>
static const char xml[]=
"<node><interface name='org.nuxel.Bridge'><method name='CheckPermission'>"
"<arg type='s' direction='in'/><arg type='s' direction='in'/><arg type='s' direction='out'/>"
"</method></interface><interface name='nl.nuxel.Radio1'><method name='SendSms'>"
"<arg type='s' direction='in'/><arg type='s' direction='in'/><arg type='u' direction='out'/>"
"</method></interface></node>";
static GMainLoop *loop;
static unsigned submissions,checks,changes;
static const char *permission="{\"granted\":false}";
static gboolean expected_success,ready;
static void method(GDBusConnection *c,const char *sender,const char *path,const char *iface,
                   const char *name,GVariant *args,GDBusMethodInvocation *inv,gpointer user)
{
    (void)c;(void)sender;(void)path;(void)iface;(void)args;(void)user;
    if(!strcmp(name,"CheckPermission")) {
        checks++;g_dbus_method_invocation_return_value(inv,g_variant_new("(s)",permission));
    } else {
        submissions++;g_dbus_method_invocation_return_value(inv,g_variant_new("(u)",42));
    }
}
static void changed(gpointer user)
{
    changes++;if(!ready && nuxel_radio_available(user)) { ready=TRUE;g_main_loop_quit(loop); }
}
static void completed(GVariant *reply,const GError *error,gpointer user)
{
    (void)user;
    if(expected_success) { guint id;g_assert_null(error);g_assert_nonnull(reply);g_variant_get(reply,"(u)",&id);g_assert_cmpuint(id,==,42); }
    else { g_assert_null(reply);g_assert_error(error,G_IO_ERROR,G_IO_ERROR_PERMISSION_DENIED); }
    g_main_loop_quit(loop);
}
static gboolean deadline(gpointer unused)
{ (void)unused;g_error("Native client test timed out");return G_SOURCE_REMOVE; }
static void request_name(GDBusConnection *bus,const char *name)
{
    GError *error=NULL;GVariant *r=g_dbus_connection_call_sync(bus,"org.freedesktop.DBus",
        "/org/freedesktop/DBus","org.freedesktop.DBus","RequestName",g_variant_new("(su)",name,0),
        G_VARIANT_TYPE("(u)"),G_DBUS_CALL_FLAGS_NONE,2000,NULL,&error);
    g_assert_no_error(error);g_assert_nonnull(r);g_variant_unref(r);
}
int main(int argc,char **argv)
{
    g_test_init(&argc,&argv,NULL);
    GTestDBus *bus=g_test_dbus_new(G_TEST_DBUS_NONE);g_test_dbus_up(bus);
    g_setenv("DBUS_SYSTEM_BUS_ADDRESS",g_test_dbus_get_bus_address(bus),TRUE);
    GError *error=NULL;GDBusConnection *server=g_bus_get_sync(G_BUS_TYPE_SESSION,NULL,&error);g_assert_no_error(error);
    GDBusNodeInfo *info=g_dbus_node_info_new_for_xml(xml,&error);g_assert_no_error(error);
    const GDBusInterfaceVTable vtable={.method_call=method};
    g_assert_cmpuint(g_dbus_connection_register_object(server,"/org/nuxel/Bridge",info->interfaces[0],&vtable,NULL,NULL,&error),>,0);
    g_assert_no_error(error);
    g_assert_cmpuint(g_dbus_connection_register_object(server,"/nl/nuxel/Radio1",info->interfaces[1],&vtable,NULL,NULL,&error),>,0);
    g_assert_no_error(error);request_name(server,"org.nuxel.Bridge");request_name(server,"nl.nuxel.Radio1");
    loop=g_main_loop_new(NULL,FALSE);g_timeout_add_seconds(15,deadline,NULL);
    NuxelRadioClient client={0};nuxel_radio_connect(&client,"org.nuxel.Messages",changed,&client);
    g_main_loop_run(loop);g_assert_true(ready);
    const char *denials[]={"{\"granted\":false}","{}","invalid","{\"granted\":\"true\"}"};
    for(unsigned i=0;i<G_N_ELEMENTS(denials);i++) {
        permission=denials[i];expected_success=FALSE;
        nuxel_radio_call(&client,"SendSms",g_variant_new("(ss)","+12345678901","fixture"),"sms:send",completed,NULL);
        g_main_loop_run(loop);g_assert_cmpuint(submissions,==,0);
    }
    permission="{\"granted\":true}";expected_success=TRUE;
    nuxel_radio_call(&client,"SendSms",g_variant_new("(ss)","+12345678901","fixture"),"sms:send",completed,NULL);
    g_main_loop_run(loop);g_assert_cmpuint(submissions,==,1);g_assert_cmpuint(checks,==,5);
    g_assert_cmpuint(changes,>,0);
    g_print("Native client: 4 fail-closed permission cases; one authorized submission; PASS\n");
    g_object_unref(client.proxy);g_object_unref(client.permissions);g_object_unref(client.cancel);
    g_object_unref(server);g_dbus_node_info_unref(info);g_main_loop_unref(loop);
    g_test_dbus_down(bus);g_object_unref(bus);return 0;
}
