#include "nuxel-radio-client.h"
#include <json-glib/json-glib.h>

typedef struct {
    NuxelRadioClient *client;
    char *method;
    GVariant *args;
    NuxelRadioReply callback;
    gpointer user;
} Request;

static void complete(Request *r, GVariant *reply, GError *error)
{
    r->callback(reply,error,r->user);
    g_clear_pointer(&reply,g_variant_unref);
    g_clear_error(&error);
    g_clear_pointer(&r->args,g_variant_unref);
    g_free(r->method);g_free(r);
}
static void result_ready(GObject *object,GAsyncResult *result,gpointer user)
{
    GError *error=NULL;
    GVariant *reply=g_dbus_proxy_call_finish(G_DBUS_PROXY(object),result,&error);
    complete(user,reply,error);
}
static void invoke(Request *r)
{
    if(!nuxel_radio_available(r->client)) {
        complete(r,NULL,g_error_new_literal(G_IO_ERROR,G_IO_ERROR_NOT_CONNECTED,
                                            "Native radio unavailable"));return;
    }
    /* Never retry a command: a timeout after submission is uncertain. */
    g_dbus_proxy_call(r->client->proxy,r->method,r->args,
                     G_DBUS_CALL_FLAGS_NO_AUTO_START,10000,r->client->cancel,
                     result_ready,r);
}
static void permission_ready(GObject *object,GAsyncResult *result,gpointer user)
{
    Request *r=user;GError *error=NULL;
    GVariant *reply=g_dbus_connection_call_finish(G_DBUS_CONNECTION(object),result,&error);
    gboolean granted=FALSE;
    if(reply) {
        const char *json=NULL;g_variant_get(reply,"(&s)",&json);
        JsonParser *parser=json_parser_new();
        if(json_parser_load_from_data(parser,json,-1,NULL)) {
            JsonNode *root=json_parser_get_root(parser);
            if(JSON_NODE_HOLDS_OBJECT(root)) {
                JsonNode *value=json_object_get_member(json_node_get_object(root),"granted");
                granted=value && JSON_NODE_HOLDS_VALUE(value) &&
                        json_node_get_value_type(value)==G_TYPE_BOOLEAN &&
                        json_node_get_boolean(value);
            }
        }
        g_object_unref(parser);g_variant_unref(reply);
    }
    g_clear_error(&error);
    if(!granted) {
        complete(r,NULL,g_error_new_literal(G_IO_ERROR,G_IO_ERROR_PERMISSION_DENIED,
                     "Phone permission not granted; review application permissions"));return;
    }
    invoke(r);
}
void nuxel_radio_call(NuxelRadioClient *c,const char *method,GVariant *args,
                     const char *capability,NuxelRadioReply callback,gpointer user)
{
    Request *r=g_new0(Request,1);r->client=c;r->method=g_strdup(method);
    r->args=args ? g_variant_ref_sink(args) : NULL;r->callback=callback;r->user=user;
    if(capability) {
        if(!c->permissions) {
            complete(r,NULL,g_error_new_literal(G_IO_ERROR,G_IO_ERROR_PERMISSION_DENIED,
                                                "Permission service unavailable"));return;
        }
        g_dbus_connection_call(c->permissions,"org.nuxel.Bridge","/org/nuxel/Bridge",
            "org.nuxel.Bridge","CheckPermission",g_variant_new("(ss)",c->app_id,capability),
            G_VARIANT_TYPE("(s)"),G_DBUS_CALL_FLAGS_NO_AUTO_START,3000,c->cancel,
            permission_ready,r);
    } else invoke(r);
}
gboolean nuxel_radio_available(NuxelRadioClient *c)
{
    char *owner=c->proxy ? g_dbus_proxy_get_name_owner(c->proxy) : NULL;
    gboolean ready=owner!=NULL;g_free(owner);return ready;
}
static void changed(GObject *object,GParamSpec *property,gpointer user)
{ (void)object;(void)property;NuxelRadioClient *c=user;c->changed(c->user); }
static void signal_received(GDBusProxy *proxy,const char *sender,const char *signal,
                            GVariant *parameters,gpointer user)
{
    (void)proxy;(void)sender;(void)signal;(void)parameters;
    NuxelRadioClient *c=user;c->changed(c->user);
}
static void proxy_ready(GObject *object,GAsyncResult *result,gpointer user)
{
    (void)object;NuxelRadioClient *c=user;
    c->proxy=g_dbus_proxy_new_for_bus_finish(result,NULL);
    if(c->proxy) {
        g_signal_connect(c->proxy,"notify::g-name-owner",G_CALLBACK(changed),c);
        g_signal_connect(c->proxy,"g-signal",G_CALLBACK(signal_received),c);
    }
    c->changed(c->user);
}
static void permissions_ready(GObject *object,GAsyncResult *result,gpointer user)
{
    (void)object;NuxelRadioClient *c=user;c->permissions=g_bus_get_finish(result,NULL);
    g_dbus_proxy_new_for_bus(G_BUS_TYPE_SESSION,G_DBUS_PROXY_FLAGS_DO_NOT_AUTO_START,NULL,
        "nl.nuxel.Radio1","/nl/nuxel/Radio1","nl.nuxel.Radio1",c->cancel,proxy_ready,c);
}
void nuxel_radio_connect(NuxelRadioClient *c,const char *app_id,
                         NuxelRadioChanged callback,gpointer user)
{
    c->app_id=app_id;c->changed=callback;c->user=user;c->cancel=g_cancellable_new();
    g_bus_get(G_BUS_TYPE_SYSTEM,c->cancel,permissions_ready,c);
}
