#include "nuxel-radio-client.h"
#include <json-glib/json-glib.h>

typedef struct {
    NuxelRadioClient *client;
    char *method;
    GVariant *args;
    NuxelRadioReply callback;
    gpointer user;
    gboolean via_fallback;
} Request;

static void complete(Request *r, GVariant *reply, GError *error)
{
    r->callback(reply,error,r->user);
    g_clear_pointer(&reply,g_variant_unref);
    g_clear_error(&error);
    g_clear_pointer(&r->args,g_variant_unref);
    g_free(r->method);g_free(r);
}
/* True when the call provably never reached a peer (no name owner, no
 * service, no connection).  Only then is it safe to re-issue the same request
 * on the fallback bus; a timeout is ambiguous and is never retried. */
static gboolean is_unreachable(const GError *error)
{
    if (!error) return FALSE;
    if (error->domain == G_IO_ERROR)
        return error->code == G_IO_ERROR_NOT_CONNECTED ||
               error->code == G_IO_ERROR_CLOSED ||
               error->code == G_IO_ERROR_NOT_FOUND;
    /* GDBusProxy wraps "well-known name has no owner" as
     * org.freedesktop.DBus.Error.Unnamed (G_IO_ERROR domain in some glib
     * versions, the D-Bus name in others); both mean "never sent". */
    if (g_dbus_error_is_remote_error(error) &&
        (g_dbus_error_get_remote_error(error) &&
         (!strcmp(g_dbus_error_get_remote_error(error),
                  "org.freedesktop.DBus.Error.Unnamed") ||
          !strcmp(g_dbus_error_get_remote_error(error),
                  "org.freedesktop.DBus.Error.ServiceUnknown") ||
          !strcmp(g_dbus_error_get_remote_error(error),
                  "org.freedesktop.DBus.Error.NameHasNoOwner"))))
        return TRUE;
    if (error->domain == G_DBUS_ERROR)
        return g_error_matches(error, G_DBUS_ERROR, G_DBUS_ERROR_NO_REPLY) ||
               g_error_matches(error, G_DBUS_ERROR, G_DBUS_ERROR_UNKNOWN_METHOD) ||
               g_error_matches(error, G_DBUS_ERROR, G_DBUS_ERROR_SERVICE_UNKNOWN) ||
               g_error_matches(error, G_DBUS_ERROR, G_DBUS_ERROR_NAME_HAS_NO_OWNER) ||
               g_error_matches(error, G_DBUS_ERROR, G_DBUS_ERROR_DISCONNECTED);
    return FALSE;
}
static void send_request(Request *r, GDBusProxy *proxy, gboolean via_fallback);
static gboolean proxy_owned(GDBusProxy *p);
static void result_ready(GObject *object,GAsyncResult *result,gpointer user)
{
    Request *r=user;
    GError *error=NULL;
    GVariant *reply=g_dbus_proxy_call_finish(G_DBUS_PROXY(object),result,&error);
    /* The session-bus Radio1 may be unreachable for a uid-1000 app (it lives
     * on the root compositor bus).  Re-issue the SAME request on the
     * system-bus bridge only when the call provably never left: the session
     * name has no owner, or the error is an unreachable-bus error.  A timeout
     * after a submission is ambiguous and is never retried. */
    if(!reply && g_getenv("NUXEL_RADIO_TRACE") && error)
        g_message("radio call %s failed domain=%s code=%d msg=%s", r->method,
                  g_quark_to_string(error->domain), error->code, error->message);
    gboolean never_sent = !r->via_fallback && !proxy_owned(r->client->proxy);
    if(!reply && !r->via_fallback && r->client->fallback &&
       (never_sent || is_unreachable(error))) {
        g_clear_error(&error);
        if(g_getenv("NUXEL_RADIO_TRACE"))
            g_message("radio call %s retrying via system-bus Radio1Bridge",r->method);
        send_request(r,r->client->fallback,TRUE);
        return;
    }
    complete(r,reply,error);
}
static void send_request(Request *r, GDBusProxy *proxy, gboolean via_fallback)
{
    r->via_fallback=via_fallback;
    /* Opt-in trace (NUXEL_RADIO_TRACE=1): which bus actually answered.
     * Never logs message bodies. */
    if(g_getenv("NUXEL_RADIO_TRACE"))
        g_message("radio call %s via %s",r->method,
                  via_fallback ? "system-bus Radio1Bridge" : "session-bus Radio1");
    /* Never retry a submission after an ambiguous timeout. */
    g_dbus_proxy_call(proxy,r->method,r->args,
                     G_DBUS_CALL_FLAGS_NO_AUTO_START,10000,r->client->cancel,
                     result_ready,r);
}
static void invoke(Request *r)
{
    if(nuxel_radio_available(r->client))
        send_request(r,r->client->proxy,FALSE);
    else if(r->client->fallback)
        send_request(r,r->client->fallback,TRUE);
    else {
        complete(r,NULL,g_error_new_literal(G_IO_ERROR,G_IO_ERROR_NOT_CONNECTED,
                                            "Native radio unavailable"));
    }
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
static gboolean proxy_owned(GDBusProxy *p)
{
    char *owner = p ? g_dbus_proxy_get_name_owner(p) : NULL;
    gboolean ready = owner != NULL;
    g_free(owner);
    return ready;
}
gboolean nuxel_radio_available(NuxelRadioClient *c)
{
    return proxy_owned(c->proxy) || proxy_owned(c->fallback);
}
static void changed(GObject *object,GParamSpec *property,gpointer user)
{ (void)object;(void)property;NuxelRadioClient *c=user;c->changed(NULL,c->user); }
/* SmsReceived carries a hint string (the native id as text).  Relay it so the
 * app can fetch the row at once; other signals are generic "changed" events. */
static void signal_received(GDBusProxy *proxy,const char *sender,const char *signal,
                            GVariant *parameters,gpointer user)
{
    (void)proxy;(void)sender;
    NuxelRadioClient *c=user;
    if(!g_strcmp0(signal,"SmsReceived")) {
        /* radiod's signature is "(u)"; a bridge may relay it as text.  Only
         * the arrival matters here: the app fetches the row (and its text)
         * through GetSms, never from the signal. */
        const char *hint=NULL;
        if(parameters && g_variant_is_of_type(parameters,G_VARIANT_TYPE("(s)")))
            g_variant_get(parameters,"(&s)",&hint);
        c->changed(hint ? hint : "sms",c->user);
        return;
    }
    if(!g_strcmp0(signal,"SmsStateChanged")) {
        /* Incoming SMS transitions to "received"; re-read the store so a new
         * message appears even if SmsReceived was coalesced away. */
        c->changed("sms-state",c->user);
        return;
    }
    c->changed(NULL,c->user);
}
static void on_fallback_proxy(GObject *object,GAsyncResult *result,gpointer user)
{
    (void)object;NuxelRadioClient *c=user;GError *error=NULL;
    c->fallback=g_dbus_proxy_new_finish(result,&error);
    if(c->fallback) {
        g_signal_connect(c->fallback,"notify::g-name-owner",G_CALLBACK(changed),c);
        g_signal_connect(c->fallback,"g-signal",G_CALLBACK(signal_received),c);
        if(g_getenv("NUXEL_RADIO_TRACE"))
            g_message("radio fallback proxy ready (nl.nuxel.Radio1Bridge)");
    } else {
        g_warning("Radio1 system-bus bridge unavailable: %s",error ? error->message : "?");
    }
    g_clear_error(&error);
    c->changed(NULL,c->user);
}
static void proxy_ready(GObject *object,GAsyncResult *result,gpointer user)
{
    (void)object;NuxelRadioClient *c=user;
    c->proxy=g_dbus_proxy_new_for_bus_finish(result,NULL);
    if(c->proxy) {
        g_signal_connect(c->proxy,"notify::g-name-owner",G_CALLBACK(changed),c);
        g_signal_connect(c->proxy,"g-signal",G_CALLBACK(signal_received),c);
    }
    /* Second source: the Radio1 bridge on the system bus.  The app runs as
     * uid nuxel, which cannot join the root session bus; the bridge publishes
     * the full vtable as nl.nuxel.Radio1Bridge (radiod owns the short
     * nl.nuxel.Radio1 system-bus vtable). */
    g_dbus_proxy_new_for_bus(G_BUS_TYPE_SYSTEM,G_DBUS_PROXY_FLAGS_DO_NOT_AUTO_START,
        NULL,"nl.nuxel.Radio1Bridge","/nl/nuxel/Radio1","nl.nuxel.Radio1",
        c->cancel,on_fallback_proxy,c);
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
