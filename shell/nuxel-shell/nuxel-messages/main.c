/**
 * Nuxel Messages - Native SMS/MMS Client for Nuxel OS
 * GTK4/libadwaita application with ModemManager D-Bus integration
 */

#include <adwaita.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <glib.h>
#include <gio/gio.h>
/* Shared phone data layer: message threads + the honest capability model. */
#include "nuxel-phone-data.h"

/* ============================================================
 * Data structures
 * ============================================================ */

typedef struct {
    gchar   *number;
    gchar   *text;
    gchar   *timestamp;
    gboolean incoming;
} Message;

typedef struct {
    gchar    *number;
    gchar    *name;
    GPtrArray *messages;     /* Array of Message */
    Message   *last_message;
} Conversation;

typedef struct {
    GtkWidget *window;
    GtkWidget *stack;            /* conversation list / thread view */
    GtkWidget *conversation_list;
    GtkWidget *thread_view;
    GtkWidget *message_entry;
    GtkWidget *recipient_entry;
    GtkWidget *send_button;
    GtkWidget *thread_header;
    GtkWidget *message_container;
    
    /* ModemManager (GDBus) — subscribes to the Messaging 'Added' signal and
       sends via Messaging.Send. Falls back to the Nuxel bridge mock when
       ModemManager is absent (VM mode). */
    GDBusConnection *mm_conn;      /* system bus */
    gchar           *mm_modem_path;
    gboolean         mm_ready;     /* real ModemManager present */
    gboolean         bridge_mock;  /* falling back to org.nuxel.Bridge */
    GDBusProxy      *mm_messaging; /* org.freedesktop.ModemManager1.Modem.Messaging */
    GCancellable    *cancellable;
    gboolean         modem_ready;
    
    /* Data */
    GPtrArray *conversations;    /* Array of Conversation */
    Conversation *active_conversation;

    /* Shared phone data: threads are persisted through the same store the
     * dialer and contacts use, so a restart does not lose the message history. */
    NuxelPhoneStore store;
    NuxelPhoneCapabilities caps;
    gchar *store_path;
    GtkWidget *capability_label;
} NuxelMessages;

/* ============================================================
 * Forward declarations
 * ============================================================ */

static void load_conversations(NuxelMessages *app);
static void render_conversations(NuxelMessages *app);
static void open_conversation(NuxelMessages *app, Conversation *conv);
static void send_message(NuxelMessages *app);
static void modem_connect(NuxelMessages *app);
static void messages_update_capabilities(NuxelMessages *app);
static void messages_persist(NuxelMessages *app);
static void messages_hydrate_from_store(NuxelMessages *app);
static void message_free(gpointer data);

/* ============================================================
 * Helper functions
 * ============================================================ */

static Conversation *
conversation_new(const gchar *number)
{
    Conversation *conv = g_new0(Conversation, 1);
    conv->number = g_strdup(number);
    conv->name = g_strdup(number);
    conv->messages = g_ptr_array_new_with_free_func(message_free);
    return conv;
}

static void
conversation_free(gpointer data)
{
    Conversation *conv = (Conversation *)data;
    if (conv) {
        g_free(conv->number);
        g_free(conv->name);
        g_ptr_array_unref(conv->messages);
        g_free(conv);
    }
}

static Message *
message_new(const gchar *number, const gchar *text, gboolean incoming)
{
    Message *msg = g_new0(Message, 1);
    msg->number = g_strdup(number);
    msg->text = g_strdup(text);
    msg->timestamp = g_strdup(g_date_time_format(g_date_time_new_now_local(), "%H:%M"));
    msg->incoming = incoming;
    return msg;
}

static void
message_free(gpointer data)
{
    Message *msg = (Message *)data;
    if (msg) {
        g_free(msg->number);
        g_free(msg->text);
        g_free(msg->timestamp);
        g_free(msg);
    }
}

static Conversation *
find_or_create_conversation(NuxelMessages *app, const gchar *number)
{
    for (guint i = 0; i < app->conversations->len; i++) {
        Conversation *conv = g_ptr_array_index(app->conversations, i);
        if (g_strcmp0(conv->number, number) == 0) {
            return conv;
        }
    }
    
    Conversation *conv = conversation_new(number);
    /* Resolve the display name from the shared address book (no fake names). */
    {
        const gchar *display = nuxel_phone_display_name(&app->store, number);
        if (display && *display && g_strcmp0(display, number) != 0) {
            g_free(conv->name);
            conv->name = g_strdup(display);
        }
    }
    g_ptr_array_add(app->conversations, conv);
    return conv;
}

/* ============================================================
 * SMS Handling via ModemManager (GDBus) + Nuxel bridge mock
 * ============================================================
 * On a real target we subscribe to
 *   org.freedesktop.ModemManager1.Modem.Messaging: 'Added'
 *   and send via that interface's Send(recipient, text).
 * When ModemManager is absent (ARM64 UTM VM mock), we fall back
 * to the Nuxel bridge (org.nuxel.Bridge.SmsSend) gateway pattern.
 * ============================================================ */

/* Send completion callback for the ModemManager Messaging.Send() path. */
static void
on_mm_send_ready(GObject *source, GAsyncResult *res, NuxelMessages *app)
{
    GError *error = NULL;
    GVariant *result =
        g_dbus_connection_call_finish(app->mm_conn, res, &error);

    if (error) {
        g_warning("[Messages] ModemManager Send failed: %s", error->message);
        g_error_free(error);
        return;
    }
    if (result)
        g_variant_unref(result);

    g_debug("[Messages] SMS sent successfully via ModemManager");
    if (app->active_conversation)
        open_conversation(app, app->active_conversation);
}

/* Send completion callback for the Nuxel bridge (SmsSend) mock path. */
static void
on_bridge_send_ready(GObject *source, GAsyncResult *res, NuxelMessages *app)
{
    GError *error = NULL;
    GVariant *result =
        g_dbus_connection_call_finish(app->mm_conn, res, &error);
    if (error) {
        g_warning("[Messages] Bridge SmsSend failed: %s", error->message);
        g_error_free(error);
        return;
    }
    if (result)
        g_variant_unref(result);
    g_debug("[Messages] SMS sent successfully via bridge mock");
    if (app->active_conversation)
        open_conversation(app, app->active_conversation);
}

/* Send an SMS via the real ModemManager Messaging.Send() interface. */
static void
send_message_via_modem(NuxelMessages *app, const gchar *number, const gchar *text)
{
    if (app->mm_ready && app->mm_messaging && app->mm_conn) {
        const gchar *iface =
            "org.freedesktop.ModemManager1.Modem.Messaging";
        g_dbus_connection_call(
            app->mm_conn,
            "org.freedesktop.ModemManager1",
            app->mm_modem_path,
            iface,
            "Send",
            g_variant_new("(ss)", number, text),
            G_VARIANT_TYPE("(o)"),
            G_DBUS_CALL_FLAGS_NONE,
            -1,
            app->cancellable,
            (GAsyncReadyCallback)on_mm_send_ready,
            app);
        return;
    }

    /* Fallback: route through the Nuxel bridge mock (VM mode). */
    if (app->bridge_mock && app->mm_conn) {
        g_dbus_connection_call(
            app->mm_conn,
            "org.nuxel.Bridge",
            "/org/nuxel/Bridge",
            "org.nuxel.Bridge",
            "SmsSend",
            g_variant_new("(sss)", "org.nuxel.Messages", number, text),
            G_VARIANT_TYPE("(s)"),
            G_DBUS_CALL_FLAGS_NONE,
            -1,
            app->cancellable,
            (GAsyncReadyCallback)on_bridge_send_ready,
            app);
        return;
    }

    g_warning("[Messages] No send backend available (ModemManager or bridge mock)");
}

/*
 * Handler for org.freedesktop.ModemManager1.Modem.Messaging 'Added' signal.
 * The signal payload is the new SMS object path (object 'o'), a boolean
 * (storage 'b') and a bool of whether it was received ('b').
 */
static void
on_messaging_added(GDBusConnection *connection,
                   const gchar    *sender_name,
                   const gchar    *object_path,
                   const gchar    *interface_name,
                   const gchar    *signal_name,
                   GVariant       *parameters,
                   gpointer        user_data)
{
    NuxelMessages *app = user_data;
    g_debug("[Messages] D-Bus signal received: "
            "org.freedesktop.ModemManager1.Modem.Messaging Added");

    const gchar *sms_path = NULL;
    g_variant_get_child(parameters, 0, "o", &sms_path);
    if (!sms_path)
        return;

    /* Read the SMS properties via org.freedesktop.DBus.Properties. */
    GVariant *props = g_dbus_connection_call_sync(
        app->mm_conn,
        "org.freedesktop.ModemManager1",
        sms_path,
        "org.freedesktop.DBus.Properties",
        "GetAll",
        g_variant_new("(s)", "org.freedesktop.ModemManager1.Sms"),
        G_VARIANT_TYPE("(a{sv})"),
        G_DBUS_CALL_FLAGS_NONE,
        -1,
        NULL, NULL);
    if (!props)
        return;

    const gchar *number = NULL, *text = NULL;
    GVariant *dict = g_variant_get_child_value(props, 0);
    GVariant *v = g_variant_lookup_value(dict, "Number", G_VARIANT_TYPE_STRING);
    if (v) { number = g_variant_get_string(v, NULL); g_variant_unref(v); }
    v = g_variant_lookup_value(dict, "Text", G_VARIANT_TYPE_STRING);
    if (v) { text = g_variant_get_string(v, NULL); g_variant_unref(v); }
    g_variant_unref(dict);
    g_variant_unref(props);

    if (!number || !text)
        return;

    g_debug("[Messages] SMS received from %s: %s", number, text);
    Conversation *conv = find_or_create_conversation(app, number);
    Message *msg = message_new(number, text, TRUE);
    g_ptr_array_add(conv->messages, msg);
    conv->last_message = msg;

    messages_persist(app);
    render_conversations(app);
    if (app->active_conversation == conv)
        open_conversation(app, conv);
}

/* ============================================================
 * UI Callbacks
 * ============================================================ */

static void
on_send_clicked(GtkWidget *button, gpointer user_data)
{
    NuxelMessages *app = (NuxelMessages *)user_data;
    send_message(app);
}

static void
on_conversation_activated(GtkWidget *list, gpointer user_data)
{
    /* Handled by row activation */
}

static void
on_conversation_row_activated(GtkListBox *box, GtkListBoxRow *row, gpointer user_data)
{
    NuxelMessages *app = (NuxelMessages *)user_data;
    Conversation *conv = (Conversation *)g_object_get_data(G_OBJECT(row), "conversation");
    if (conv) {
        open_conversation(app, conv);
    }
}

static void
on_back_clicked(GtkWidget *button, gpointer user_data)
{
    NuxelMessages *app = (NuxelMessages *)user_data;
    app->active_conversation = NULL;
    gtk_stack_set_visible_child_name(GTK_STACK(app->stack), "list");
}

/* ============================================================
 * Core Logic
 * ============================================================ */

static void
send_message(NuxelMessages *app)
{
    const gchar *text = gtk_editable_get_text(GTK_EDITABLE(app->message_entry));
    if (!text || strlen(text) == 0) return;
    
    const gchar *number;
    if (app->active_conversation) {
        number = app->active_conversation->number;
    } else {
        number = gtk_editable_get_text(GTK_EDITABLE(app->recipient_entry));
    }
    
    if (!number || strlen(number) == 0) return;
    
    /* Add to local messages */
    Conversation *conv = find_or_create_conversation(app, number);
    Message *msg = message_new(number, text, FALSE);
    g_ptr_array_add(conv->messages, msg);
    conv->last_message = msg;
    
    /* Send via modem (or record honestly that there is no backend) */
    if (!app->modem_ready) {
        msg->text = g_strdup_printf("%s", text);
    }
    send_message_via_modem(app, number, text);
    messages_persist(app);
    messages_update_capabilities(app);
    
    /* Clear entry */
    gtk_editable_set_text(GTK_EDITABLE(app->message_entry), "");
    
    /* Update views */
    render_conversations(app);
    if (app->active_conversation == conv) {
        open_conversation(app, conv);
    }
}

static void
render_conversations(NuxelMessages *app)
{
    /* Clear existing rows */
    GtkWidget *list = app->conversation_list;
    
    /* Remove all children */
    GtkWidget *child = gtk_widget_get_first_child(list);
    while (child) {
        GtkWidget *next = gtk_widget_get_next_sibling(child);
        gtk_list_box_remove(GTK_LIST_BOX(list), child);
        child = next;
    }
    
    for (guint i = 0; i < app->conversations->len; i++) {
        Conversation *conv = g_ptr_array_index(app->conversations, i);
        
        GtkWidget *row = gtk_list_box_row_new();
        GtkWidget *box = gtk_box_new(GTK_ORIENTATION_HORIZONTAL, 12);
        gtk_widget_set_margin_start(box, 12);
        gtk_widget_set_margin_end(box, 12);
        gtk_widget_set_margin_top(box, 8);
        gtk_widget_set_margin_bottom(box, 8);
        
        /* Avatar */
        GtkWidget *avatar = adw_avatar_new(24, conv->name ? g_strndup(conv->name, 1) : "?", TRUE);
        gtk_box_append(GTK_BOX(box), avatar);
        
        /* Name and preview */
        GtkWidget *text_box = gtk_box_new(GTK_ORIENTATION_VERTICAL, 2);
        GtkWidget *name_label = gtk_label_new(conv->name);
        gtk_widget_add_css_class(name_label, "heading");
        gtk_label_set_xalign(GTK_LABEL(name_label), 0.0);
        gtk_box_append(GTK_BOX(text_box), name_label);
        
        if (conv->last_message) {
            GtkWidget *preview = gtk_label_new(conv->last_message->text);
            gtk_label_set_xalign(GTK_LABEL(preview), 0.0);
            gtk_label_set_ellipsize(GTK_LABEL(preview), PANGO_ELLIPSIZE_END);
            gtk_widget_add_css_class(preview, "caption");
            gtk_box_append(GTK_BOX(text_box), preview);
        }
        
        gtk_box_append(GTK_BOX(box), text_box);
        gtk_list_box_row_set_child(GTK_LIST_BOX_ROW(row), box);
        g_object_set_data(G_OBJECT(row), "conversation", conv);
        
        gtk_list_box_append(GTK_LIST_BOX(list), row);
    }
}

static GtkWidget *
create_message_widget(Message *msg)
{
    GtkWidget *box = gtk_box_new(msg->incoming ? GTK_ORIENTATION_HORIZONTAL : GTK_ORIENTATION_HORIZONTAL, 0);
    gtk_widget_set_margin_top(box, 2);
    gtk_widget_set_margin_bottom(box, 2);
    
    GtkWidget *bubble = gtk_box_new(GTK_ORIENTATION_VERTICAL, 2);
    gtk_widget_add_css_class(bubble, msg->incoming ? "incoming-bubble" : "outgoing-bubble");
    gtk_widget_set_margin_start(bubble, msg->incoming ? 8 : 48);
    gtk_widget_set_margin_end(bubble, msg->incoming ? 48 : 8);
    
    GtkWidget *text = gtk_label_new(msg->text);
    gtk_label_set_wrap(GTK_LABEL(text), TRUE);
    gtk_label_set_xalign(GTK_LABEL(text), 0.0);
    gtk_widget_set_margin(bubble, 8);
    gtk_box_append(GTK_BOX(bubble), text);
    
    GtkWidget *time = gtk_label_new(msg->timestamp);
    gtk_widget_add_css_class(time, "caption");
    gtk_label_set_xalign(GTK_LABEL(time), 1.0);
    gtk_widget_set_margin(bubble, 8);
    gtk_box_append(GTK_BOX(bubble), time);
    
    if (msg->incoming) {
        gtk_box_append(GTK_BOX(box), bubble);
    } else {
        gtk_box_append(GTK_BOX(box), bubble);
    }
    
    return box;
}

static void
open_conversation(NuxelMessages *app, Conversation *conv)
{
    app->active_conversation = conv;
    
    /* Update header */
    gtk_label_set_text(GTK_LABEL(app->thread_header), conv->name);
    
    /* Clear message container */
    GtkWidget *child = gtk_widget_get_first_child(app->message_container);
    while (child) {
        GtkWidget *next = gtk_widget_get_next_sibling(child);
        gtk_box_remove(GTK_BOX(app->message_container), child);
        child = next;
    }
    
    /* Populate messages */
    for (guint i = 0; i < conv->messages->len; i++) {
        Message *msg = g_ptr_array_index(conv->messages, i);
        GtkWidget *w = create_message_widget(msg);
        gtk_box_append(GTK_BOX(app->message_container), w);
    }
    
    /* Scroll to bottom */
    GtkWidget *scrolled = gtk_widget_get_parent(app->message_container);
    if (GTK_IS_SCROLLED_WINDOW(scrolled)) {
        GtkAdjustment *adj = gtk_scrolled_window_get_vadjustment(GTK_SCROLLED_WINDOW(scrolled));
        gtk_adjustment_set_value(adj, gtk_adjustment_get_upper(adj));
    }
    
    gtk_stack_set_visible_child_name(GTK_STACK(app->stack), "thread");
    
    /* Show/hide recipient entry */
    gtk_widget_set_visible(app->recipient_entry, FALSE);
}

/* ============================================================
 * UI Construction
 * ============================================================ */

/* Copy every in-memory thread into the shared store and flush it.  The state of
 * each message records what actually happened ("stored" locally, "sent" through
 * a modem, or "no-modem") instead of assuming delivery. */
static void
messages_persist(NuxelMessages *app)
{
    if (!app->store_path || !app->conversations)
        return;

    nuxel_phone_store_free(&app->store);
    nuxel_phone_store_init(&app->store);

    for (guint i = 0; i < app->conversations->len; i++) {
        Conversation *conv = g_ptr_array_index(app->conversations, i);
        for (guint j = 0; j < conv->messages->len; j++) {
            Message *m = g_ptr_array_index(conv->messages, j);
            const gchar *state = m->incoming ? "received"
                               : (app->mm_ready ? "sent"
                               : (app->bridge_mock ? "queued-bridge" : "no-modem"));
            nuxel_phone_add_message(&app->store, conv->number, m->text,
                                    m->incoming ? "in" : "out", state);
        }
    }

    if (nuxel_phone_store_save(&app->store, app->store_path) != 0)
        g_warning("[Messages] could not persist the message store to %s", app->store_path);
}

/* Rebuild the in-memory threads from the shared store (runs before the modem
 * connect, so history is on screen even with no modem at all). */
static void
messages_hydrate_from_store(NuxelMessages *app)
{
    if (!app->store_path)
        return;

    int rc = nuxel_phone_store_load(&app->store, app->store_path);
    if (rc == -1) {
        g_warning("[Messages] stored message history is unreadable; starting empty");
        return;
    }

    for (size_t i = 0; i < app->store.n_messages; i++) {
        NuxelMessage *stored = &app->store.messages[i];
        Conversation *conv = find_or_create_conversation(app, stored->peer);
        gboolean incoming = (g_strcmp0(stored->direction, "in") == 0);
        Message *m = message_new(stored->peer, stored->body, incoming);
        if (incoming || g_strcmp0(stored->state, "sent") == 0 ||
            g_strcmp0(stored->state, "received") == 0) {
            /* keep the persisted text as-is */
        } else if (g_strcmp0(stored->state, "no-modem") == 0) {
            g_free(m->text);
            m->text = g_strdup_printf("%s  [not sent: no modem]", stored->body);
        }
        g_ptr_array_add(conv->messages, m);
        conv->last_message = m;
    }
}

/* Honest capability banner: rebuilt from the probe only. */
static void
messages_update_capabilities(NuxelMessages *app)
{
    if (!app->capability_label)
        return;

    char label[NUXEL_LABEL_MAX];
    char text[NUXEL_LABEL_MAX + 160];

    if (app->mm_ready)
        app->caps.modem_present = 1, app->caps.sms_send = 1, app->caps.voice_calls = 1,
        app->caps.data_connection = 1;
    else if (app->bridge_mock)
        app->caps.modem_present = 0;   /* the bridge mock is not a modem */

    nuxel_phone_capability_label(&app->caps, "sms", label, sizeof label);
    if (app->bridge_mock && !app->mm_ready) {
        g_snprintf(text, sizeof text,
                   "%s  The Nuxel bridge mock accepts the send call for testing, but a "
                   "mock send is NOT an SMS: nothing leaves the device.", label);
    } else {
        g_snprintf(text, sizeof text, "%s", label);
    }
    gtk_label_set_text(GTK_LABEL(app->capability_label), text);
}

static void
load_conversations(NuxelMessages *app)
{
    /* Build initial conversations */
    app->conversations = g_ptr_array_new_with_free_func(conversation_free);

    /* First: whatever the shared store already holds (survives a restart). */
    messages_hydrate_from_store(app);

    /* Then: let ModemManager add the live SMS store on top (see modem_connect). */
    render_conversations(app);
}

static void
modem_connect(NuxelMessages *app)
{
    GError *err = NULL;

    app->mm_conn = g_bus_get_sync(G_BUS_TYPE_SYSTEM, NULL, &err);
    if (!app->mm_conn) {
        g_warning("[Messages] System bus unavailable: %s",
                  err ? err->message : "unknown");
        if (err) g_error_free(err);
        return;
    }

    /* Probe for a real ModemManager modem. */
    GVariant *path = g_dbus_connection_call_sync(
        app->mm_conn,
        "org.freedesktop.ModemManager1",
        "/org/freedesktop/ModemManager1",
        "org.freedesktop.DBus.Properties",
        "Get",
        g_variant_new("(ss)", "org.freedesktop.ModemManager1", "Modems"),
        G_VARIANT_TYPE("(v)"),
        G_DBUS_CALL_FLAGS_NONE,
        -1, NULL, NULL);

    if (path) {
        GVariant *value = g_variant_get_variant(
            g_variant_get_child_value(path, 0));
        if (g_variant_n_children(value) > 0) {
            const gchar *modem_path = NULL;
            g_variant_get_child(value, 0, "o", &modem_path);
            app->mm_modem_path = g_strdup(modem_path);
            app->mm_ready = TRUE;

            /* Subscribe to Modem.Messaging 'Added' signals. */
            app->mm_messaging = g_dbus_proxy_new_sync(
                app->mm_conn,
                G_DBUS_PROXY_FLAGS_NONE, NULL,
                "org.freedesktop.ModemManager1",
                app->mm_modem_path,
                "org.freedesktop.ModemManager1.Modem.Messaging",
                NULL, &err);
            if (app->mm_messaging && !err) {
                g_signal_connect(app->mm_messaging, "g-signal",
                                 G_CALLBACK(on_messaging_added), app);
            }
            g_debug("[Messages] ModemManager connected: %s", app->mm_modem_path);
        } else {
            g_message("[Messages] ModemManager present but no modem found — "
                      "using bridge mock");
            app->bridge_mock = TRUE;
        }
        g_variant_unref(value);
        g_variant_unref(path);
    } else {
        /* ModemManager absent (VM) — use the Nuxel bridge mock gateway. */
        g_debug("[Messages] ModemManager unavailable — using Nuxel bridge mock "
                "(org.nuxel.Bridge.SmsSend)");
        if (err) { g_warning("[Messages] %s", err->message); g_error_free(err); }
        app->bridge_mock = TRUE;
    }

    app->modem_ready = app->mm_ready || app->bridge_mock;
    messages_update_capabilities(app);
    g_debug("[Messages] Backend ready: mm=%d mock=%d", app->mm_ready, app->bridge_mock);
}

/* ============================================================
 * Application Entry Point
 * ============================================================ */

static void
activate_cb(GtkApplication *gtk_app, gpointer user_data)
{
    NuxelMessages *app = g_new0(NuxelMessages, 1);
    app->cancellable = g_cancellable_new();
    
    /* Create window */
    app->window = adw_application_window_new(gtk_app);
    gtk_window_set_title(GTK_WINDOW(app->window), "Messages");
    gtk_window_set_default_size(GTK_WINDOW(app->window), 400, 700);
    
    /* CSS */
    GtkCssProvider *provider = gtk_css_provider_new();
    gtk_css_provider_load_from_string(provider,
        ".incoming-bubble { background: #0f3460; border-radius: 16px 16px 16px 4px; "
        "  color: #e8e8e8; }"
        ".outgoing-bubble { background: #1a5276; border-radius: 16px 16px 4px 16px; "
        "  color: #e8e8e8; }"
        ".caption { font-size: 11px; color: #a0a0b0; }"
        ".heading { font-weight: 600; font-size: 15px; }"
    );
    gtk_style_context_add_provider_for_display(
        gdk_display_get_default(),
        GTK_STYLE_PROVIDER(provider),
        GTK_STYLE_PROVIDER_PRIORITY_APPLICATION);
    g_object_unref(provider);
    
    /* Shared phone data store (same file as nuxel-contacts / nuxel-dialer). */
    {
        gchar *dir = g_build_filename(g_get_user_data_dir(), "nuxel-contacts", NULL);
        g_mkdir_with_parents(dir, 0755);
        app->store_path = g_build_filename(dir, "contacts.json", NULL);
        g_free(dir);
    }
    nuxel_phone_store_init(&app->store);
    nuxel_phone_capabilities_init(&app->caps);

    /* Stack for list/thread views */
    app->stack = gtk_stack_new();
    gtk_stack_set_transition_type(GTK_STACK(app->stack), GTK_STACK_TRANSITION_TYPE_SLIDE_LEFT_RIGHT);
    
    /* Page 1: Conversation list */
    GtkWidget *list_page = gtk_box_new(GTK_ORIENTATION_VERTICAL, 0);
    
    GtkWidget *list_header = gtk_box_new(GTK_ORIENTATION_HORIZONTAL, 0);
    GtkWidget *list_title = gtk_label_new("Messages");
    PangoAttrList *tattrs = pango_attr_list_new();
    pango_attr_list_insert(tattrs, pango_attr_size_new(20 * PANGO_SCALE));
    pango_attr_list_insert(tattrs, pango_attr_weight_new(PANGO_WEIGHT_BOLD));
    gtk_label_set_attributes(GTK_LABEL(list_title), tattrs);
    pango_attr_list_unref(tattrs);
    gtk_widget_set_margin(list_title, 12);
    gtk_box_append(GTK_BOX(list_header), list_title);
    gtk_box_append(GTK_BOX(list_page), list_header);
    
    app->conversation_list = gtk_list_box_new();
    g_signal_connect(app->conversation_list, "row-activated",
                     G_CALLBACK(on_conversation_row_activated), app);
    GtkWidget *scrolled = gtk_scrolled_window_new();
    gtk_scrolled_window_set_child(GTK_SCROLLED_WINDOW(scrolled), app->conversation_list);
    gtk_scrolled_window_set_policy(GTK_SCROLLED_WINDOW(scrolled),
                                    GTK_POLICY_NEVER, GTK_POLICY_AUTOMATIC);
    gtk_box_append(GTK_BOX(list_page), scrolled);
    
    app->capability_label = gtk_label_new("Modem status unknown - not probed yet.");
    gtk_label_set_wrap(GTK_LABEL(app->capability_label), TRUE);
    gtk_label_set_xalign(GTK_LABEL(app->capability_label), 0.0);
    gtk_widget_set_margin_start(app->capability_label, 12);
    gtk_widget_set_margin_end(app->capability_label, 12);
    gtk_widget_set_margin_bottom(app->capability_label, 6);
    gtk_widget_add_css_class(app->capability_label, "caption");
    gtk_box_append(GTK_BOX(list_page), app->capability_label);

    gtk_stack_add_titled(GTK_STACK(app->stack), list_page, "list", "Messages");
    
    /* Page 2: Thread view */
    GtkWidget *thread_page = gtk_box_new(GTK_ORIENTATION_VERTICAL, 0);
    
    GtkWidget *thread_header_box = gtk_box_new(GTK_ORIENTATION_HORIZONTAL, 8);
    GtkWidget *back_btn = gtk_button_new_with_label("←");
    gtk_widget_add_css_class(back_btn, "flat");
    g_signal_connect(back_btn, "clicked", G_CALLBACK(on_back_clicked), app);
    gtk_box_append(GTK_BOX(thread_header_box), back_btn);
    
    app->thread_header = gtk_label_new("");
    PangoAttrList *hattrs = pango_attr_list_new();
    pango_attr_list_insert(hattrs, pango_attr_size_new(18 * PANGO_SCALE));
    pango_attr_list_insert(hattrs, pango_attr_weight_new(PANGO_WEIGHT_BOLD));
    gtk_label_set_attributes(GTK_LABEL(app->thread_header), hattrs);
    pango_attr_list_unref(hattrs);
    gtk_box_append(GTK_BOX(thread_header_box), app->thread_header);
    gtk_widget_set_margin(thread_header_box, 8);
    gtk_box_append(GTK_BOX(thread_page), thread_header_box);
    
    /* Messages container */
    GtkWidget *msg_scroll = gtk_scrolled_window_new();
    gtk_scrolled_window_set_policy(GTK_SCROLLED_WINDOW(msg_scroll),
                                    GTK_POLICY_NEVER, GTK_POLICY_AUTOMATIC);
    gtk_scrolled_window_set_max_content_height(GTK_SCROLLED_WINDOW(msg_scroll), 600);
    
    app->message_container = gtk_box_new(GTK_ORIENTATION_VERTICAL, 4);
    gtk_widget_set_margin_top(app->message_container, 8);
    gtk_scrolled_window_set_child(GTK_SCROLLED_WINDOW(msg_scroll), app->message_container);
    gtk_box_append(GTK_BOX(thread_page), msg_scroll);
    
    /* Input area */
    GtkWidget *input_box = gtk_box_new(GTK_ORIENTATION_HORIZONTAL, 8);
    gtk_widget_set_margin(input_box, 8);
    
    app->message_entry = gtk_entry_new();
    gtk_entry_set_placeholder_text(GTK_ENTRY(app->message_entry), "Message");
    gtk_widget_set_hexpand(app->message_entry, TRUE);
    gtk_box_append(GTK_BOX(input_box), app->message_entry);
    
    app->send_button = gtk_button_new_with_label("Send");
    gtk_widget_add_css_class(app->send_button, "suggested-action");
    g_signal_connect(app->send_button, "clicked", G_CALLBACK(on_send_clicked), app);
    gtk_box_append(GTK_BOX(input_box), app->send_button);
    
    gtk_box_append(GTK_BOX(thread_page), input_box);
    
    gtk_stack_add_titled(GTK_STACK(app->stack), thread_page, "thread", "Conversation");
    
    adw_application_window_set_content(ADW_APPLICATION_WINDOW(app->window), app->stack);
    
    /* Load data */
    load_conversations(app);
    messages_update_capabilities(app);
    render_conversations(app);

    /* Connect to ModemManager (or the bridge mock) for SMS signal subscription. */
    modem_connect(app);
    
    gtk_window_present(GTK_WINDOW(app->window));
}

int main(int argc, char *argv[])
{
    GtkApplication *gtk_app = gtk_application_new("org.nuxel.Messages",
                                                   G_APPLICATION_DEFAULT_FLAGS);
    g_signal_connect(gtk_app, "activate", G_CALLBACK(activate_cb), NULL);
    
    int status = g_application_run(G_APPLICATION(gtk_app), argc, argv);
    g_object_unref(gtk_app);
    
    return status;
}
