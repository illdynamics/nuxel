/*
 * nuxel-radio-bridge — expose nl.nuxel.Radio1 on the per-user session bus.
 *
 * Why this exists
 * ---------------
 * nuxel-radiod owns nl.nuxel.Radio1 on the ROOT session bus
 * (unix:path=/run/nuxel-wayland/bus).  The Home launcher starts the native
 * session-user apps (nuxel-messages, nuxel-dialer, nuxel-contacts) on the
 * REAL per-user bus (unix:path=/run/user/1000/bus), because that is where
 * dconf, xdg-desktop-portal and the desktop notifier live.  A uid-1000 app
 * therefore could not see the radio at all: Messages showed
 * "Native SMS unavailable" and an empty inbox even though Radio1 held the
 * SMS store and could submit.
 *
 * This bridge is a small, explicit D-Bus forwarder:
 *   - it connects to the root session bus and the SYSTEM bus;
 *   - it owns nl.nuxel.Radio1Bridge on the system bus (radiod already owns
 *     nl.nuxel.Radio1 there with a small mobile-only vtable);
 *   - every method call it receives is checked against the allow-list below
 *     and answered from the root bus;
 *   - Radio1 signals (SmsReceived/SmsStateChanged/...) are re-emitted on the
 *     system bus.
 *
 * Rationale: the two session buses authenticate with EXTERNAL (peer UID), so
 * root cannot join /run/user/1000/bus and uid nuxel cannot join the root
 * compositor bus.  The system bus is the only bus both identities can join;
 * its policy files restrict nl.nuxel.Radio1 to root (own the bridge) and
 * nuxel-bridge (the HTTP bridge) so ordinary apps cannot call it.
 *
 * It never re-implements radio logic and does not cache state.  It only
 * forwards the read/SMS/call methods listed below; data-session, network
 * selection and NV writes stay on the root bus.  Dictionary payloads (GetSms,
 * GetSmsStatus, GetImsStatus, ...) are forwarded byte-for-byte, so new keys
 * such as GetSms "created" need no bridge change.
 *
 * Build: gcc -O2 -Wall -Wextra -Werror $(pkg-config --cflags gio-2.0) \
 *            -o nuxel-radio-bridge nuxel-radio-bridge.c \
 *            $(pkg-config --libs gio-2.0)
 */
#include <gio/gio.h>
#include <string.h>

#define UPSTREAM_BUS "nl.nuxel.Radio1"      /* radiod on the root session bus */
#define BUS_NAME     "nl.nuxel.Radio1Bridge" /* what this bridge owns */
#define OBJ_PATH     "/nl/nuxel/Radio1"
#define IFACE        "nl.nuxel.Radio1"

static const char *const IFACE_XML =
    "<node>"
    "  <interface name='nl.nuxel.Radio1'>"
    "    <method name='SendSms'><arg name='peer' type='s' direction='in'/>"
    "      <arg name='text' type='s' direction='in'/><arg name='id' type='u' direction='out'/></method>"
    "    <method name='ResolveSms'><arg name='id' type='u' direction='in'/>"
    "      <arg name='state' type='s' direction='in'/><arg name='ok' type='b' direction='out'/></method>"
    "    <method name='ListSms'><arg name='ids' type='au' direction='out'/></method>"
    "    <method name='GetSms'><arg name='id' type='u' direction='in'/>"
    "      <arg name='sms' type='a{ss}' direction='out'/></method>"
    "    <method name='GetSmsStatus'><arg name='status' type='a{ss}' direction='out'/></method>"
    "    <method name='GetImsStatus'><arg name='status' type='a{ss}' direction='out'/></method>"
    "    <method name='GetSignalInfo'><arg name='rsrp' type='i' direction='out'/>"
    "      <arg name='rsrq' type='i' direction='out'/><arg name='sinr' type='i' direction='out'/>"
    "      <arg name='valid' type='b' direction='out'/></method>"
    "    <method name='GetSimState'><arg name='state' type='s' direction='out'/></method>"
    "    <method name='GetIpInfo'><arg name='info' type='a{ss}' direction='out'/></method>"
    "    <method name='GetVoiceStatus'><arg name='status' type='a{ss}' direction='out'/></method>"
    "    <method name='HangupCall'><arg name='ok' type='b' direction='out'/></method>"
    "    <method name='GetDiagnostics'><arg name='diag' type='a{st}' direction='out'/></method>"
    "    <method name='GetPacketStats'><arg name='rx_bytes' type='t' direction='out'/>"
    "      <arg name='tx_bytes' type='t' direction='out'/><arg name='valid' type='b' direction='out'/></method>"
    "    <method name='GetPdpProfiles'><arg name='profiles' type='a(yysyy)' direction='out'/></method>"
    "    <method name='RefreshStatus'><arg name='ok' type='b' direction='out'/></method>"
    "    <property name='CpState' type='s' access='read'/>"
    "    <property name='DaemonState' type='s' access='read'/>"
    "    <property name='DevicePresent' type='b' access='read'/>"
    "    <property name='RadioState' type='s' access='read'/>"
    "    <property name='Registered' type='b' access='read'/>"
    "    <property name='SimPinRequired' type='b' access='read'/>"
    "    <property name='SimPresent' type='b' access='read'/>"
    "    <property name='Version' type='u' access='read'/>"
    "    <property name='ApiRevision' type='s' access='read'/>"
    "    <signal name='SmsReceived'><arg name='id' type='u'/></signal>"
    "    <signal name='SmsStateChanged'><arg name='id' type='u'/><arg name='state' type='s'/></signal>"
    "    <signal name='CallStateChanged'><arg name='peer' type='s'/><arg name='state' type='s'/></signal>"
    "    <signal name='CpReset'/>"
    "  </interface>"
    "</node>";

/* Methods the SMS app and the dialer use.  Anything else (data sessions,
 * network selection, NV writes) stays on the root bus only. */
static const char *const ALLOWED_METHODS[] = {
    "SendSms", "ResolveSms", "ListSms", "GetSms", "GetSmsStatus",
    "GetImsStatus", "GetSignalInfo", "GetSimState", "GetIpInfo",
    "GetVoiceStatus", "HangupCall", "GetDiagnostics", "GetPacketStats",
    "GetPdpProfiles", "RefreshStatus",
    NULL,
};

typedef struct {
    GDBusConnection *upstream;   /* root session bus: radiod lives here */
    GDBusConnection *local;      /* system bus: the bridge is published here */
    GMainLoop *loop;
} Bridge;

/* Methods that change state or disclose subscriber content.  The bridge
 * forwards them as root, so nuxel-radiod's own EUID check cannot see the real
 * caller.  The bridge therefore re-checks the caller identity itself. */
static gboolean
method_is_sensitive(const char *method)
{
    return !strcmp(method, "SendSms") || !strcmp(method, "ResolveSms") ||
           !strcmp(method, "Dial") || !strcmp(method, "HangupCall") ||
           !strcmp(method, "AnswerCall");
}

/* Allowed caller identities (EUID).  This is the real kernel-verified bus
 * credential, not a caller-supplied app id. */
static gboolean
caller_privileged(GDBusConnection *system_bus, const char *sender,
                  GDBusMethodInvocation *invocation)
{
    GError *error = NULL;
    GVariant *reply = g_dbus_connection_call_sync(system_bus,
        "org.freedesktop.DBus", "/org/freedesktop/DBus",
        "org.freedesktop.DBus", "GetConnectionUnixUser",
        g_variant_new("(s)", sender), G_VARIANT_TYPE("(u)"),
        G_DBUS_CALL_FLAGS_NONE, 3000, NULL, &error);
    if (!reply) {
        g_dbus_method_invocation_return_dbus_error(invocation,
            "nl.nuxel.Radio1.Error.AccessDenied", "caller identity unavailable");
        if (error) { g_warning("GetConnectionUnixUser: %s", error->message); g_clear_error(&error); }
        return FALSE;
    }
    guint32 uid = 0;
    g_variant_get(reply, "(u)", &uid);
    g_variant_unref(reply);
    if (uid == 0 || uid == 1000)
        return TRUE;
    g_dbus_method_invocation_return_dbus_error(invocation,
        "nl.nuxel.Radio1.Error.AccessDenied",
        "only the Nuxel session owner may submit SMS or control calls");
    return FALSE;
}

static gboolean
method_allowed(const char *method)
{
    for (const char *const *m = ALLOWED_METHODS; *m; m++)
        if (strcmp(*m, method) == 0)
            return TRUE;
    return FALSE;
}

static void
upstream_done(GObject *source, GAsyncResult *result, gpointer user)
{
    GDBusMethodInvocation *invocation = user;
    GError *error = NULL;
    GVariant *reply = g_dbus_connection_call_finish(G_DBUS_CONNECTION(source),
                                                    result, &error);
    if (reply) {
        g_dbus_method_invocation_return_value(invocation, reply);
        g_variant_unref(reply);
    } else {
        g_dbus_method_invocation_return_gerror(invocation, error);
        g_clear_error(&error);
    }
    g_object_unref(invocation);
}

static void
handle_method_call(GDBusConnection *connection, const char *sender,
                   const char *object_path, const char *interface_name,
                   const char *method_name, GVariant *parameters,
                   GDBusMethodInvocation *invocation, gpointer user_data)
{
    Bridge *b = user_data;
    (void)object_path; (void)interface_name;
    if (!b->upstream) {
        g_dbus_method_invocation_return_dbus_error(invocation,
            "nl.nuxel.Radio1.Error.UpstreamDown",
            "The root session bus is not connected");
        return;
    }
    if (!method_allowed(method_name)) {
        g_dbus_method_invocation_return_dbus_error(invocation,
            "nl.nuxel.Radio1.Error.NotAllowed",
            "This method is not forwarded by the per-user radio bridge");
        return;
    }
    if (method_is_sensitive(method_name) &&
        !caller_privileged(connection, sender, invocation))
        return;
    g_dbus_connection_call(b->upstream, UPSTREAM_BUS, OBJ_PATH, IFACE, method_name,
                           parameters, NULL, G_DBUS_CALL_FLAGS_NO_AUTO_START,
                           -1, NULL, upstream_done,
                           g_object_ref(invocation));
}

static GVariant *
handle_get_property(GDBusConnection *connection, const char *sender,
                    const char *object_path, const char *interface_name,
                    const char *property_name, GError **error,
                    gpointer user_data)
{
    Bridge *b = user_data;
    (void)connection; (void)sender; (void)object_path;
    GVariant *v;
    if (!b->upstream) {
        g_set_error(error, G_IO_ERROR, G_IO_ERROR_NOT_CONNECTED,
                    "root session bus not connected");
        return NULL;
    }
    v = g_dbus_connection_call_sync(b->upstream, UPSTREAM_BUS, OBJ_PATH,
            "org.freedesktop.DBus.Properties", "Get",
            g_variant_new("(ss)", interface_name, property_name),
            G_VARIANT_TYPE("(v)"), G_DBUS_CALL_FLAGS_NO_AUTO_START,
            -1, NULL, error);
    if (!v) return NULL;
    GVariant *out = g_variant_get_child_value(v, 0);
    g_variant_unref(v);
    return out;
}

static const GDBusInterfaceVTable VTABLE = {
    handle_method_call, handle_get_property, NULL, { 0 }
};

static void
upstream_signal(GDBusConnection *connection, const char *sender,
                const char *object_path, const char *interface_name,
                const char *signal_name, GVariant *parameters, gpointer user_data)
{
    Bridge *b = user_data;
    (void)connection; (void)sender;
    if (strcmp(interface_name, IFACE) != 0) return;
    if (strcmp(object_path, OBJ_PATH) != 0) return;
    if (!b->local) return;
    /* Emit from the bridge's own name, not a NULL sender: GDBusProxy's
     * g-signal handler drops senderless signals, and apps match on the
     * well-known name anyway. */
    g_dbus_connection_emit_signal(b->local, BUS_NAME, OBJ_PATH, IFACE,
                                  signal_name, parameters, NULL);
}

static void
on_name_acquired(GDBusConnection *connection, const char *name, gpointer user)
{
    (void)connection; (void)user;
    g_message("radio bridge owns %s on the system bus", name);
}

static void
on_bus_ready(GObject *source, GAsyncResult *result, gpointer user)
{
    (void)source;
    Bridge *b = user;
    GError *error = NULL;
    b->local = g_dbus_connection_new_for_address_finish(result, &error);
    if (!b->local) {
        g_critical("system bus unavailable: %s", error->message);
        g_clear_error(&error);
        g_main_loop_quit(b->loop);
        return;
    }
    g_dbus_connection_set_exit_on_close(b->local, FALSE);

    GDBusNodeInfo *node = g_dbus_node_info_new_for_xml(IFACE_XML, &error);
    if (!node) {
        g_critical("interface XML invalid: %s", error->message);
        g_clear_error(&error);
        g_main_loop_quit(b->loop);
        return;
    }
    GDBusInterfaceInfo *iface = g_dbus_node_info_lookup_interface(node, IFACE);
    if (!g_dbus_connection_register_object(b->local, OBJ_PATH, iface, &VTABLE,
                                           b, NULL, &error)) {
        g_critical("cannot register %s: %s", OBJ_PATH, error->message);
        g_clear_error(&error);
        g_dbus_node_info_unref(node);
        g_main_loop_quit(b->loop);
        return;
    }
    g_dbus_node_info_unref(node);

    g_bus_own_name_on_connection(b->local, BUS_NAME,
        G_BUS_NAME_OWNER_FLAGS_NONE, on_name_acquired, NULL, NULL, NULL);
}

static void
connect_upstream(Bridge *b)
{
    const char *root_addr = g_getenv("NUXEL_ROOT_BUS");
    if (!root_addr || !*root_addr) root_addr = "unix:path=/run/nuxel-wayland/bus";
    GError *error = NULL;
    b->upstream = g_dbus_connection_new_for_address_sync(root_addr,
        G_DBUS_CONNECTION_FLAGS_AUTHENTICATION_CLIENT |
        G_DBUS_CONNECTION_FLAGS_MESSAGE_BUS_CONNECTION,
        NULL, NULL, &error);
    if (!b->upstream) {
        /* radiod/session may not be up yet; calls report UpstreamDown. */
        g_warning("root session bus %s not reachable: %s", root_addr, error->message);
        g_clear_error(&error);
        return;
    }
    g_dbus_connection_set_exit_on_close(b->upstream, FALSE);
    g_dbus_connection_signal_subscribe(b->upstream, UPSTREAM_BUS, IFACE, NULL, OBJ_PATH,
        NULL, G_DBUS_SIGNAL_FLAGS_NONE, upstream_signal, b, NULL);
}

int
main(void)
{
    Bridge bridge = { 0 };
    connect_upstream(&bridge);

    bridge.loop = g_main_loop_new(NULL, FALSE);
    g_dbus_connection_new_for_address("unix:path=/run/dbus/system_bus_socket",
        G_DBUS_CONNECTION_FLAGS_AUTHENTICATION_CLIENT |
        G_DBUS_CONNECTION_FLAGS_MESSAGE_BUS_CONNECTION,
        NULL, NULL, on_bus_ready, &bridge);
    g_main_loop_run(bridge.loop);
    g_main_loop_unref(bridge.loop);
    if (bridge.local) g_object_unref(bridge.local);
    if (bridge.upstream) g_object_unref(bridge.upstream);
    return 0;
}
