/**
 * Nuxel Messages — Native SMS client for Nuxel OS
 * GTK4/libadwaita, native Radio1/Radio1Bridge D-Bus integration.
 *
 * Round 34.5 model rewrite.  The previous model appended a new Message object
 * for every inbound row on every refresh (inbound rows carry no GetSms id, so
 * the "(direction, peer, text)" match never succeeded) and never removed stale
 * objects.  Over repeated 20 s refreshes the thread accumulated unbounded
 * duplicates and out-of-order rows — the owner saw "only one message" while the
 * database held seventeen.  This version replaces the whole model from the
 * authoritative ListSms snapshot on every refresh, so one native id yields
 * exactly one Message and the count on screen equals the count in Radio1.
 *
 * Visual language follows the Nuxel reference apps (Maps / Snekbyte /
 * Firewall): deep navy ground, rounded panel cards, cyan accent, muted dim
 * text, 14-16 px radii, flat touch targets, safe-area padding.
 *
 * Notifications for inbound SMS are owned by the notification hub (announced
 * by nuxel-radiod exactly once per new logical SMS); this app never plays a
 * sound and never announces historical rows.
 */

#include <adwaita.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <glib.h>
#include <gio/gio.h>
/* Shared phone data layer: message threads + the honest capability model. */
#include "nuxel-phone-data.h"
#include "nuxel-radio-client.h"

/* ============================================================
 * Data structures
 * ============================================================ */

typedef struct {
    gchar   *timestamp;
    gboolean incoming;
    guint   native_id;
    gchar  *state;
    gchar  *mirror_body;   /* SIM-mirror rows only; native rows read the snapshot */
    gchar  *preview;       /* body/state text for conversation rows */
    gint64   at;           /* unix seconds for mirror rows (ordering) */
} Message;

typedef struct {
    gchar    *number;
    gchar    *name;
    GPtrArray *messages;     /* Array of Message, lowest native id first */
    Message   *last_message;
    guint     unread;
} Conversation;

typedef struct {
    GtkWidget *window;
    GtkWidget *stack;            /* list / thread */
    GtkWidget *list_page;
    GtkWidget *conversation_list;
    GtkWidget *list_empty;
    GtkWidget *all_messages_list;
    GtkWidget *all_empty;
    GtkWidget *message_entry;
    GtkWidget *recipient_entry;
    GtkWidget *send_button;
    GtkWidget *thread_header;
    GtkWidget *thread_subtitle;
    GtkWidget *thread_status;
    GtkWidget *message_scroll;
    GtkWidget *scroll_bottom;
    GtkWidget *message_container;

    GDBusConnection *notify_conn;
    GDBusProxy *notify_proxy;
    guint poll_source;
    gboolean modem_ready;

    NuxelRadioClient radio;
    GArray *native_ids;
    guint native_index;
    gboolean refreshing, refresh_again, sending;

    gchar *status_detail;      /* last GetSmsStatus failure, if any */
    gchar *list_detail;        /* last ListSms failure, if any */
    gchar *ims_state;
    gchar *sms_transport;

    /* Native rows from the last completed ListSms snapshot, keyed by id. */
    GHashTable *native;
    guint native_count;

    GPtrArray *conversations;    /* Array of Conversation */
    Conversation *active_conversation;
    gchar *keep_active_key;

    NuxelPhoneStore store;
    NuxelPhoneCapabilities caps;
    gchar *store_path;
    GtkWidget *capability_label;

    NuxelPhoneStore sim_store;
    gchar *sim_path;
} NuxelMessages;

/* ============================================================
 * Forward declarations
 * ============================================================ */

static void load_conversations(NuxelMessages *app);
static void render_conversations(NuxelMessages *app);
static void render_all_messages(NuxelMessages *app);
static void open_conversation(NuxelMessages *app, Conversation *conv);
static void send_message(NuxelMessages *app);
static void modem_connect(NuxelMessages *app);
static void messages_update_capabilities(NuxelMessages *app);
static void messages_hydrate_from_store(NuxelMessages *app);
static gint conversation_cmp(const Conversation *a, const Conversation *b);
static void message_free(gpointer data);
static void messages_import_sim(NuxelMessages *app, gboolean merge_only);
static void native_refresh(gpointer user);
static gboolean messages_poll_tick(gpointer user);
static void messages_refresh_banner(NuxelMessages *app);
static void messages_probe_ims(NuxelMessages *app);
static void refresh_thread_if_open(NuxelMessages *app);
static void messages_sort_thread(GPtrArray *msgs);
static void build_model(NuxelMessages *app);

/* ============================================================
 * Helpers
 * ============================================================ */

static gint
message_cmp(const Message *a, const Message *b)
{
    if (a->native_id && b->native_id && a->native_id != b->native_id)
        return (a->native_id < b->native_id) ? -1 : 1;
    if (a->at != b->at) return (a->at < b->at) ? -1 : 1;
    if (a->native_id != b->native_id) return (a->native_id < b->native_id) ? -1 : 1;
    return 0;
}

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
message_new_at(const gchar *timestamp, gboolean incoming, guint native_id,
               const gchar *state, gint64 at)
{
    Message *msg = g_new0(Message, 1);
    msg->timestamp = g_strdup(timestamp);
    msg->incoming = incoming;
    msg->native_id = native_id;
    msg->state = g_strdup(state);
    msg->at = at;
    msg->preview = NULL;   /* filled by the model layer */
    return msg;
}

static void
message_free(gpointer data)
{
    Message *msg = (Message *)data;
    if (msg) {
        g_free(msg->timestamp);
        g_free(msg->state);
        g_free(msg->mirror_body);
        g_free(msg->preview);
        g_free(msg);
    }
}

static Conversation *
find_or_create_conversation(NuxelMessages *app, const gchar *number)
{
    for (guint i = 0; i < app->conversations->len; i++) {
        Conversation *conv = g_ptr_array_index(app->conversations, i);
        if (g_strcmp0(conv->number, number) == 0)
            return conv;
    }
    Conversation *conv = conversation_new(number);
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

/* Collapse a peer to one canonical thread key so +31 6.. / 06.. merge. */
static void
canonical_peer(char *out, size_t cap, const char *peer)
{
    char norm[NUXEL_NUMBER_MAX];
    if (peer && *peer && nuxel_phone_normalize_number(norm, sizeof norm, peer) == 0 && norm[0])
        g_strlcpy(out, norm, cap);
    else
        g_strlcpy(out, peer ? peer : "", cap);
}

/* Carrier/host timestamps: show HH:MM when they carry a usable time. */
static gchar *
message_time_label(const gchar *stamp, const char *created)
{
    if (stamp && strlen(stamp) >= 16 && stamp[4] == '-' && stamp[10] == 'T')
        return g_strndup(stamp + 11, 5);
    if (stamp && *stamp && !g_ascii_isdigit(stamp[0]))
        return g_strdup(stamp);
    if (created && *created) {
        gint64 sec = g_ascii_strtoll(created, NULL, 10);
        if (sec > 0) {
            GDateTime *dt = g_date_time_new_from_unix_local(sec);
            gchar *out = dt ? g_date_time_format(dt, "%H:%M") : g_strdup("");
            if (dt) g_date_time_unref(dt);
            return out;
        }
    }
    return NULL;   /* genuinely unknown; caller shows the date, never "now" */
}

static gint
conversation_cmp(const Conversation *a, const Conversation *b)
{
    guint ao = a->last_message ? a->last_message->native_id : 0;
    guint bo = b->last_message ? b->last_message->native_id : 0;
    if (ao != bo) return (ao > bo) ? -1 : 1;   /* newest thread first */
    return g_strcmp0(a->number, b->number);
}

static void
messages_reset_conversations(NuxelMessages *app)
{
    /* Preserve the open thread across a refresh by remembering its key; the
     * new model object is re-bound in build_model. */
    g_free(app->keep_active_key);
    app->keep_active_key = app->active_conversation
                         ? g_strdup(app->active_conversation->number) : NULL;
    app->active_conversation = NULL;
    if (app->conversations) g_ptr_array_unref(app->conversations);
    app->conversations = g_ptr_array_new_with_free_func(conversation_free);
}

/* ============================================================
 * Native path (Radio1 snapshots)
 * ============================================================ */

static gchar *variant_str(GVariant *dict, const char *key)
{
    const char *v = "";
    return g_variant_lookup(dict, key, "&s", &v) ? g_strdup(v) : g_strdup("");
}

static void
native_list_done(NuxelMessages *app)
{
    app->refreshing = FALSE;
    /* build_model reads the just-completed snapshot; the table is reused as
     * the loading buffer for the next refresh and cleared when that load
     * starts (get_sms_status), never before the model consumes it. */
    build_model(app);
    render_conversations(app);
    render_all_messages(app);
    refresh_thread_if_open(app);
    messages_refresh_banner(app);
    if (app->refresh_again) { app->refresh_again = FALSE; native_refresh(app); }
}

static void native_next(NuxelMessages *app);

static void
native_message(GVariant *reply, const GError *error, gpointer user)
{
    NuxelMessages *app = user;
    guint id = 0;
    if (app->native_ids && app->native_index > 0 && app->native_index <= app->native_ids->len)
        id = g_array_index(app->native_ids, guint, app->native_index - 1);
    if (reply && !error && id) {
        GVariant *dict = g_variant_get_child_value(reply, 0);
        if (!app->native)
            app->native = g_hash_table_new_full(g_direct_hash, g_direct_equal, NULL,
                                               (GDestroyNotify)g_variant_unref);
        g_hash_table_replace(app->native, GUINT_TO_POINTER(id), g_variant_ref(dict));
        app->native_count++;
        g_variant_unref(dict);
    } else if (error) {
        g_free(app->list_detail);
        app->list_detail = g_strdup(error->message);
    }
    native_next(app);
}

static void
native_next(NuxelMessages *app)
{
    if (app->native_ids && app->native_index < app->native_ids->len) {
        guint id = g_array_index(app->native_ids, guint, app->native_index++);
        nuxel_radio_call(&app->radio, "GetSms", g_variant_new("(u)", id),
                         "sms:receive", native_message, app);
        return;
    }
    native_list_done(app);
}

static void
native_list(GVariant *reply, const GError *error, gpointer user)
{
    NuxelMessages *app = user;
    g_free(app->list_detail);
    app->list_detail = NULL;
    if (!reply || error) {
        app->list_detail = g_strdup(error ? error->message : "Inbox unavailable");
        native_list_done(app);
        return;
    }
    GVariant *ids = g_variant_get_child_value(reply, 0);
    g_clear_pointer(&app->native_ids, g_array_unref);
    app->native_ids = g_array_new(FALSE, FALSE, sizeof(guint));
    app->native_index = 0;
    GVariantIter iter;
    guint id;
    g_variant_iter_init(&iter, ids);
    while (g_variant_iter_next(&iter, "u", &id))
        g_array_append_val(app->native_ids, id);
    g_variant_unref(ids);
    if (app->native_ids->len == 0) { native_list_done(app); return; }
    native_next(app);
}

static void
native_status(GVariant *reply, const GError *error, gpointer user)
{
    NuxelMessages *app = user;
    g_free(app->status_detail);
    app->status_detail = NULL;
    if (!reply || error) {
        app->modem_ready = FALSE;
        app->status_detail = g_strdup(error ? error->message : "no status reply");
        messages_update_capabilities(app);
        messages_refresh_banner(app);
        gtk_widget_set_sensitive(app->send_button, FALSE);
        nuxel_radio_call(&app->radio, "ListSms", NULL, "sms:receive", native_list, app);
        return;
    }
    GVariant *dict = g_variant_get_child_value(reply, 0);
    const char *storage = "unknown", *ready = "unknown", *domain = "unknown", *smsc = "unknown";
    const char *pending = "unknown", *blocked = "unknown", *native_ready = "false",
               *registration = "unavailable";
    g_variant_lookup(dict, "storage", "&s", &storage);
    g_variant_lookup(dict, "device_ready", "&s", &ready);
    g_variant_lookup(dict, "domain", "&s", &domain);
    g_variant_lookup(dict, "smsc", "&s", &smsc);
    g_variant_lookup(dict, "pending", "&s", &pending);
    g_variant_lookup(dict, "blocked", "&s", &blocked);
    g_variant_lookup(dict, "ready", "&s", &native_ready);
    g_variant_lookup(dict, "registration", "&s", &registration);
    g_free(app->sms_transport);
    app->sms_transport = g_strdup(ready);
    gboolean storage_ok = !strcmp(storage, "available");
    gboolean ready_ok = !strcmp(ready, "accepted");
    gboolean smsc_ok = !strcmp(smsc, "received");
    gboolean pending_busy = !strcmp(pending, "true");
    gboolean blocked_unresolved = !strcmp(blocked, "true");
    gboolean registered = !strcmp(registration, "registered");
    app->modem_ready = !strcmp(native_ready, "true") && storage_ok && ready_ok && smsc_ok &&
                       !pending_busy && !blocked_unresolved && registered;
    g_variant_unref(dict);
    messages_update_capabilities(app);
    messages_refresh_banner(app);
    gtk_widget_set_sensitive(app->send_button, app->modem_ready && !app->sending);
    nuxel_radio_call(&app->radio, "ListSms", NULL, "sms:receive", native_list, app);
}

static void
native_refresh(gpointer user)
{
    NuxelMessages *app = user;
    if (app->refreshing) { app->refresh_again = TRUE; return; }
    app->refreshing = TRUE;
    /* New snapshot load: drop the previous ids so stale rows can never be
     * rendered while the list+GetSms sequence is in flight. */
    if (app->native) {
        g_hash_table_remove_all(app->native);
        app->native_count = 0;
    }
    messages_probe_ims(app);
    nuxel_radio_call(&app->radio, "GetSmsStatus", NULL, NULL, native_status, app);
}

static void
native_sent(GVariant *reply, const GError *error, gpointer user)
{
    NuxelMessages *app = user;
    if (!reply || error) {
        /* A lost reply might follow a durable queue insertion. Do not retry. */
        gboolean denied = error && g_error_matches(error, G_IO_ERROR, G_IO_ERROR_PERMISSION_DENIED);
        app->sending = FALSE;
        gtk_widget_set_sensitive(app->send_button, app->modem_ready);
        g_free(app->status_detail);
        app->status_detail = g_strdup(denied ? error->message :
            "Submission outcome uncertain or rejected. Check the native outbox before another attempt.");
        messages_refresh_banner(app);
        return;
    }
    app->sending = FALSE;
    gtk_editable_set_text(GTK_EDITABLE(app->message_entry), "");
    gtk_widget_set_sensitive(app->send_button, app->modem_ready);
    if (!app->active_conversation && app->recipient_entry) {
        const gchar *peer = gtk_editable_get_text(GTK_EDITABLE(app->recipient_entry));
        if (peer && *peer) {
            char key[NUXEL_NUMBER_MAX];
            canonical_peer(key, sizeof key, peer);
            app->active_conversation = find_or_create_conversation(app, key);
            gtk_label_set_text(GTK_LABEL(app->thread_header), app->active_conversation->name);
            gtk_widget_set_visible(app->recipient_entry, FALSE);
        }
    }
    native_refresh(app);
}

/* Banner text from what Radio1 actually reports.  The CS fields describe the
 * circuit-switched path (DENIED on LTE-only); when IMS carries SMS, say so. */
static void
messages_refresh_banner(NuxelMessages *app)
{
    if (!app->capability_label) return;
    gboolean ims_ok = app->ims_state && !strcmp(app->ims_state, "registered") &&
                      !(app->sms_transport && !strcmp(app->sms_transport, "unavailable"));
    gchar *ims = g_strdup_printf("IMS %s", app->ims_state ? app->ims_state : "status pending");
    gchar *banner;
    if (app->list_detail && *app->list_detail)
        banner = g_strdup_printf("SMS store unavailable (%s)", app->list_detail);
    else if (app->status_detail && *app->status_detail)
        banner = g_strdup_printf("SMS unavailable (%s)", app->status_detail);
    else if (ims_ok)
        banner = g_strdup_printf("Native SMS ready over IMS (%s; CS path not registered) · "
                                 "submission is not delivery", ims);
    else
        banner = g_strdup_printf("Native SMS starting · %s", ims);
    gtk_label_set_text(GTK_LABEL(app->capability_label), banner);
    g_free(banner);
    g_free(ims);
}

static void
ims_status(GVariant *reply, const GError *error, gpointer user)
{
    NuxelMessages *app = user;
    g_free(app->ims_state); app->ims_state = NULL;
    if (reply && !error) {
        GVariant *dict = g_variant_get_child_value(reply, 0);
        const char *state = "", *transport = "";
        g_variant_lookup(dict, "registered", "&s", &state);
        g_variant_lookup(dict, "sms_transport", "&s", &transport);
        if (!strcmp(state, "true")) app->ims_state = g_strdup("registered");
        else {
            const char *raw = "";
            g_variant_lookup(dict, "state", "&s", &raw);
            app->ims_state = g_strdup(*raw ? raw : "not registered");
        }
        if (*transport) {
            g_free(app->sms_transport);
            app->sms_transport = g_strdup(transport);
        }
        g_variant_unref(dict);
    }
    messages_refresh_banner(app);
}

static void
messages_probe_ims(NuxelMessages *app)
{
    nuxel_radio_call(&app->radio, "GetImsStatus", NULL, NULL, ims_status, app);
}

/* SmsReceived(u) is Radio1's hint that a new inbound SMS was stored.  No sound
 * or notification is created here — nuxel-radiod owns that exactly once. */
static void
sms_received_hint(const gchar *hint, gpointer user)
{
    (void)hint;
    native_refresh(user);
}

/* Local contact-derived threads (address book + call log) are loaded first so
 * a contact is visible even before Radio1 answers; native rows then dominate
 * because they are rebuilt from the store snapshot.  SMS bodies are NOT copied
 * from the legacy contact file except for SIM-mirror rows, which have no
 * native id and are clearly separate. */
static void
messages_hydrate_from_store(NuxelMessages *app)
{
    if (!app->store_path || !app->store.messages) return;
    if (nuxel_phone_store_load(&app->store, app->store_path) == -1) {
        g_warning("[Messages] stored phone data is unreadable; continuing with native rows");
        return;
    }
    for (size_t i = 0; i < app->store.n_messages; i++) {
        NuxelMessage *stored = &app->store.messages[i];
        char key[NUXEL_NUMBER_MAX];
        canonical_peer(key, sizeof key, stored->peer);
        Conversation *conv = find_or_create_conversation(app, key);
        gboolean incoming = (g_strcmp0(stored->direction, "in") == 0);
        gint64 when = stored->at > 0 ? stored->at : 0;
        gchar *label = NULL;
        if (when > 0) {
            GDateTime *dt = g_date_time_new_from_unix_local(when);
            label = dt ? g_date_time_format(dt, "%H:%M") : NULL;
            if (dt) g_date_time_unref(dt);
        }
        Message *m = message_new_at(label, incoming, 0, stored->state, when);
        m->mirror_body = g_strdup(stored->body);
        m->preview = g_strdup(stored->body);
        g_free(label);
        g_ptr_array_add(conv->messages, m);
        conv->last_message = m;   /* hydration is chronological */
    }
}

/* Merge the SIM mirror additively.  Mirror rows carry their body; they are
 * identified by (peer, body) against the mirror and against native rows so a
 * message that also arrived over IMS does not appear twice. */
static void
messages_merge_store(NuxelMessages *app, NuxelPhoneStore *store, size_t *added)
{
    for (size_t i = 0; i < store->n_messages; i++) {
        NuxelMessage *stored = &store->messages[i];
        char key[NUXEL_NUMBER_MAX];
        canonical_peer(key, sizeof key, stored->peer);
        gboolean exists = FALSE;
        if (app->native) {
            GHashTableIter it; gpointer k, v;
            g_hash_table_iter_init(&it, app->native);
            while (g_hash_table_iter_next(&it, &k, &v)) {
                gchar *np = variant_str(v, "peer");
                gchar *nb = variant_str(v, "text");
                char nk[NUXEL_NUMBER_MAX]; canonical_peer(nk, sizeof nk, np);
                if (g_strcmp0(nk, key) == 0 && g_strcmp0(nb, stored->body) == 0) exists = TRUE;
                g_free(np); g_free(nb);
                if (exists) break;
            }
        }
        if (exists) continue;
        Conversation *conv = find_or_create_conversation(app, key);
        gchar *label = NULL;
        if (stored->at > 0) {
            GDateTime *dt = g_date_time_new_from_unix_local(stored->at);
            label = dt ? g_date_time_format(dt, "%H:%M") : NULL;
            if (dt) g_date_time_unref(dt);
        }
        Message *m = message_new_at(label, g_strcmp0(stored->direction, "in") == 0, 0,
                                    stored->state, stored->at);
        g_free(label);
        m->mirror_body = g_strdup(stored->body);
        m->preview = g_strdup(stored->body);
        g_ptr_array_add(conv->messages, m);
        if (conv->last_message) {
            if (!stored->at || stored->at >= conv->last_message->at) conv->last_message = m;
        } else conv->last_message = m;
        (*added)++;
    }
}

static void
messages_import_sim(NuxelMessages *app, gboolean merge_only)
{
    nuxel_phone_store_free(&app->sim_store);
    nuxel_phone_store_init(&app->sim_store);
    int rc = app->sim_path ? nuxel_phone_store_load(&app->sim_store, app->sim_path) : -1;
    /* An empty mirror is the normal state; never shown as fake history. */
    if (rc == -1 || app->sim_store.n_messages == 0)
        return;
    size_t added = 0;
    messages_merge_store(app, &app->sim_store, &added);
    if (!merge_only) {
        for (size_t i = 0; i < app->store.n_messages; i++) {
            NuxelMessage *m = &app->store.messages[i];
            gboolean exists = FALSE;
            for (size_t j = 0; j < app->sim_store.n_messages; j++) {
                NuxelMessage *s = &app->sim_store.messages[j];
                if (g_strcmp0(s->peer, m->peer) == 0 && g_strcmp0(s->body, m->body) == 0) {
                    exists = TRUE; break;
                }
            }
            if (!exists) nuxel_phone_add_message(&app->sim_store, m->peer, m->body,
                                                 m->direction, m->state);
        }
        if (app->sim_path) nuxel_phone_store_save(&app->sim_store, app->sim_path);
    }
    if (added) {
        g_message("[Messages] SIM mirror: loaded %zu message(s)%s.", added,
                  merge_only ? "" : "; synced local messages to mirror");
    }
}

static void
on_import_sim_clicked(GtkWidget *btn, gpointer user_data)
{
    (void)btn;
    NuxelMessages *app = user_data;
    messages_import_sim(app, TRUE);
    render_conversations(app);
}

static void
load_conversations(NuxelMessages *app)
{
    messages_reset_conversations(app);
    messages_hydrate_from_store(app);
    render_conversations(app);
}
/* ============================================================
 * Model → UI (one object per native id, authoritative snapshot)
 * ============================================================ */

static const char *
state_label(const char *state)
{
    if (!state || !*state) return "";
    if (!strcmp(state, "received")) return "received";
    if (!strcmp(state, "queued")) return "queued";
    if (!strcmp(state, "sending")) return "sending";
    if (!strcmp(state, "submitted")) return "submitted";
    if (!strcmp(state, "delivered")) return "delivered";
    if (!strcmp(state, "failed")) return "failed";
    if (!strcmp(state, "unknown")) return "unknown";
    return state;
}

static void messages_sort_thread(GPtrArray *msgs);

static void
build_model(NuxelMessages *app)
{
    messages_reset_conversations(app);
    messages_hydrate_from_store(app);
    if (app->native) {
        GHashTableIter it;
        gpointer key, val;
        g_hash_table_iter_init(&it, app->native);
        while (g_hash_table_iter_next(&it, &key, &val)) {
            guint id = GPOINTER_TO_UINT(key);
            GVariant *dict = val;
            gchar *peer = variant_str(dict, "peer");
            gchar *state = variant_str(dict, "state");
            gchar *dir = variant_str(dict, "direction");
            gchar *stamp = variant_str(dict, "timestamp");
            gchar *created = variant_str(dict, "created");
            gchar *body = variant_str(dict, "text");
            gboolean incoming = !strcmp(dir, "in");
            char keybuf[NUXEL_NUMBER_MAX];
            canonical_peer(keybuf, sizeof keybuf, peer);
            Conversation *conv = find_or_create_conversation(app, keybuf);
            gint64 at = created && *created ? g_ascii_strtoll(created, NULL, 10) : 0;
            Message *msg = message_new_at(message_time_label(stamp, created), incoming,
                                          id, state_label(state), at);
            msg->preview = g_strdup(body && *body ? body : state_label(state));
            g_ptr_array_add(conv->messages, msg);
            conv->last_message = msg;
            /* Native store has no per-message read flag; unread is not
             * fabricated.  A conversation badge therefore stays absent
             * rather than showing a stale count. */
            (void)incoming;
            g_free(peer); g_free(body); g_free(state); g_free(dir); g_free(stamp); g_free(created);
        }
    }
    for (guint c = 0; c < app->conversations->len; c++) {
        Conversation *conv = g_ptr_array_index(app->conversations, c);
        messages_sort_thread(conv->messages);
        if (conv->messages->len)
            conv->last_message = g_ptr_array_index(conv->messages, conv->messages->len - 1);
    }
    /* Rebind the open conversation after a refresh. */
    if (app->keep_active_key) {
        for (guint c = 0; c < app->conversations->len; c++) {
            Conversation *conv = g_ptr_array_index(app->conversations, c);
            if (g_strcmp0(conv->number, app->keep_active_key) == 0) {
                app->active_conversation = conv;
                break;
            }
        }
        g_clear_pointer(&app->keep_active_key, g_free);
    }
}

/* Text, direction and state for one native id, straight from the snapshot. */
static gboolean
native_lookup(NuxelMessages *app, guint id, gchar **body, gboolean *incoming)
{
    if (!app->native) return FALSE;
    GVariant *dict = g_hash_table_lookup(app->native, GUINT_TO_POINTER(id));
    if (!dict) return FALSE;
    if (body) *body = variant_str(dict, "text");
    if (incoming) {
        gchar *dir = variant_str(dict, "direction");
        *incoming = !strcmp(dir, "in");
        g_free(dir);
    }
    return TRUE;
}

static GtkWidget *
create_empty_state(const char *title, const char *detail)
{
    GtkWidget *box = gtk_box_new(GTK_ORIENTATION_VERTICAL, 6);
    gtk_widget_add_css_class(box, "nuxel-empty");
    gtk_widget_set_valign(box, GTK_ALIGN_CENTER);
    gtk_widget_set_margin_top(box, 32);
    gtk_widget_set_margin_bottom(box, 32);
    GtkWidget *t = gtk_label_new(title);
    gtk_widget_add_css_class(t, "nuxel-empty-title");
    GtkWidget *d = gtk_label_new(detail);
    gtk_widget_add_css_class(d, "dim");
    gtk_label_set_wrap(GTK_LABEL(d), TRUE);
    gtk_label_set_justify(GTK_LABEL(d), GTK_JUSTIFY_CENTER);
    gtk_box_append(GTK_BOX(box), t);
    gtk_box_append(GTK_BOX(box), d);
    return box;
}

static GtkWidget *
create_avatar(const gchar *name)
{
    gchar *initial = name && *name ? g_utf8_substring(name, 0, 1) : g_strdup("?");
    GtkWidget *avatar = gtk_label_new(initial);
    g_free(initial);
    gtk_widget_add_css_class(avatar, "nuxel-avatar");
    gtk_widget_set_valign(avatar, GTK_ALIGN_CENTER);
    return avatar;
}

static void
render_conversations(NuxelMessages *app)
{
    GtkWidget *list = app->conversation_list;
    if (!list) return;
    GtkWidget *child = gtk_widget_get_first_child(list);
    while (child) {
        GtkWidget *next = gtk_widget_get_next_sibling(child);
        gtk_list_box_remove(GTK_LIST_BOX(list), child);
        child = next;
    }
    GPtrArray *ordered = g_ptr_array_new();
    for (guint i = 0; i < app->conversations->len; i++)
        g_ptr_array_add(ordered, g_ptr_array_index(app->conversations, i));
    for (guint i = 1; i < ordered->len; i++) {
        Conversation *key = g_ptr_array_index(ordered, i);
        guint j = i;
        while (j > 0 && conversation_cmp(key, g_ptr_array_index(ordered, j - 1)) < 0) {
            ordered->pdata[j] = ordered->pdata[j - 1];
            j--;
        }
        ordered->pdata[j] = key;
    }
    for (guint i = 0; i < ordered->len; i++) {
        Conversation *conv = g_ptr_array_index(ordered, i);
        GtkWidget *row = gtk_list_box_row_new();
        GtkWidget *card = gtk_box_new(GTK_ORIENTATION_HORIZONTAL, 12);
        gtk_widget_add_css_class(card, "nuxel-row");
        gtk_box_append(GTK_BOX(card), create_avatar(conv->name));
        GtkWidget *text_box = gtk_box_new(GTK_ORIENTATION_VERTICAL, 3);
        gtk_widget_set_hexpand(text_box, TRUE);
        GtkWidget *name_label = gtk_label_new(conv->name);
        gtk_widget_add_css_class(name_label, "nuxel-row-title");
        gtk_label_set_xalign(GTK_LABEL(name_label), 0.0);
        gtk_label_set_ellipsize(GTK_LABEL(name_label), PANGO_ELLIPSIZE_END);
        gtk_box_append(GTK_BOX(text_box), name_label);
        if (conv->last_message) {
            const gchar *pv = conv->last_message->preview;
            if (!pv && conv->last_message->native_id) {
                gchar *body = NULL;
                if (native_lookup(app, conv->last_message->native_id, &body, NULL)) {
                    GtkWidget *preview = gtk_label_new(body && *body ? body : "(no text)");
                    gtk_label_set_xalign(GTK_LABEL(preview), 0.0);
                    gtk_label_set_ellipsize(GTK_LABEL(preview), PANGO_ELLIPSIZE_END);
                    gtk_widget_add_css_class(preview, "dim");
                    gtk_box_append(GTK_BOX(text_box), preview);
                    g_free(body);
                }
            } else if (pv) {
                GtkWidget *preview = gtk_label_new(*pv ? pv : "(no text)");
                gtk_label_set_xalign(GTK_LABEL(preview), 0.0);
                gtk_label_set_ellipsize(GTK_LABEL(preview), PANGO_ELLIPSIZE_END);
                gtk_widget_add_css_class(preview, "dim");
                gtk_box_append(GTK_BOX(text_box), preview);
            }
        }
        gtk_box_append(GTK_BOX(card), text_box);
        if (conv->last_message && conv->last_message->timestamp) {
            GtkWidget *ts = gtk_label_new(conv->last_message->timestamp);
            gtk_widget_add_css_class(ts, "dim");
            gtk_widget_set_valign(ts, GTK_ALIGN_START);
            gtk_box_append(GTK_BOX(card), ts);
        }
        if (conv->unread) {
            gchar *n = g_strdup_printf("%u", conv->unread);
            GtkWidget *badge = gtk_label_new(n);
            g_free(n);
            gtk_widget_add_css_class(badge, "nuxel-badge");
            gtk_widget_set_valign(badge, GTK_ALIGN_CENTER);
            gtk_box_append(GTK_BOX(card), badge);
        }
        gtk_list_box_row_set_child(GTK_LIST_BOX_ROW(row), card);
        g_object_set_data(G_OBJECT(row), "conversation", conv);
        gtk_list_box_append(GTK_LIST_BOX(list), row);
    }
    g_ptr_array_unref(ordered);
    if (app->list_empty)
        gtk_widget_set_visible(app->list_empty, ordered->len == 0);
}

static void
render_all_messages(NuxelMessages *app)
{
    GtkWidget *list = app->all_messages_list;
    if (!list) return;
    GtkWidget *child = gtk_widget_get_first_child(list);
    while (child) {
        GtkWidget *next = gtk_widget_get_next_sibling(child);
        gtk_list_box_remove(GTK_LIST_BOX(list), child);
        child = next;
    }
    if (!app->native) {
        if (app->all_empty) gtk_widget_set_visible(app->all_empty, TRUE);
        return;
    }
    guint n = g_hash_table_size(app->native);
    /* Chronological, oldest → newest, one row per stored logical SMS. */
    GArray *ids = g_array_new(FALSE, FALSE, sizeof(guint));
    GHashTableIter it; gpointer key, val;
    g_hash_table_iter_init(&it, app->native);
    while (g_hash_table_iter_next(&it, &key, &val)) {
        guint gid = GPOINTER_TO_UINT(key);
        g_array_append_val(ids, gid);
    }
    for (guint i = 1; i < ids->len; i++) {
        guint k = g_array_index(ids, guint, i); guint j = i;
        while (j > 0 && g_array_index(ids, guint, j - 1) > k) {
            g_array_index(ids, guint, j) = g_array_index(ids, guint, j - 1); j--;
        }
        g_array_index(ids, guint, j) = k;
    }
    for (guint i = 0; i < ids->len; i++) {
        guint id = g_array_index(ids, guint, i);
        GVariant *dict = g_hash_table_lookup(app->native, GUINT_TO_POINTER(id));
        if (!dict) continue;
        gchar *peer = variant_str(dict, "peer");
        gchar *body = variant_str(dict, "text");
        gchar *state = variant_str(dict, "state");
        gchar *dir = variant_str(dict, "direction");
        gchar *stamp = variant_str(dict, "timestamp");
        gchar *created = variant_str(dict, "created");
        char keybuf[NUXEL_NUMBER_MAX]; canonical_peer(keybuf, sizeof keybuf, peer);
        gchar *name = g_strdup(nuxel_phone_display_name(&app->store, keybuf));
        gboolean incoming = !strcmp(dir, "in");
        gchar *when = message_time_label(stamp, created);

        GtkWidget *row = gtk_list_box_row_new();
        GtkWidget *card = gtk_box_new(GTK_ORIENTATION_VERTICAL, 4);
        gtk_widget_add_css_class(card, "nuxel-row");
        GtkWidget *top = gtk_box_new(GTK_ORIENTATION_HORIZONTAL, 8);
        gchar *who = g_strdup_printf("%s  %s  #%u", incoming ? "↓" : "↑",
                                     name && *name ? name : keybuf, id);
        GtkWidget *who_label = gtk_label_new(who);
        g_free(who);
        gtk_widget_add_css_class(who_label, "nuxel-row-title");
        gtk_label_set_xalign(GTK_LABEL(who_label), 0.0);
        gtk_widget_set_hexpand(who_label, TRUE);
        gtk_label_set_ellipsize(GTK_LABEL(who_label), PANGO_ELLIPSIZE_END);
        gtk_box_append(GTK_BOX(top), who_label);
        if (when) {
            GtkWidget *ts = gtk_label_new(when);
            gtk_widget_add_css_class(ts, "dim");
            gtk_box_append(GTK_BOX(top), ts);
        }
        gtk_box_append(GTK_BOX(card), top);
        GtkWidget *body_label = gtk_label_new(body && *body ? body : "(no text)");
        gtk_label_set_wrap(GTK_LABEL(body_label), TRUE);
        gtk_label_set_xalign(GTK_LABEL(body_label), 0.0);
        gtk_widget_add_css_class(body_label, "nuxel-row-body");
        gtk_box_append(GTK_BOX(card), body_label);
        gchar *meta = g_strdup_printf("%s · %s", incoming ? "incoming" : "outgoing", state_label(state));
        GtkWidget *state_label_w = gtk_label_new(meta);
        g_free(meta);
        gtk_widget_add_css_class(state_label_w, "dim");
        gtk_label_set_xalign(GTK_LABEL(state_label_w), 0.0);
        gtk_box_append(GTK_BOX(card), state_label_w);
        gtk_list_box_row_set_child(GTK_LIST_BOX_ROW(row), card);
        g_object_set_data(G_OBJECT(row), "conversation", NULL);
        gtk_list_box_append(GTK_LIST_BOX(list), row);

        g_free(peer); g_free(body); g_free(state); g_free(dir); g_free(stamp);
        g_free(created); g_free(name); g_free(when);
    }
    g_array_unref(ids);
    if (app->all_empty) gtk_widget_set_visible(app->all_empty, n == 0);
}

static GtkWidget *
create_message_widget(Message *msg, const gchar *body)
{
    GtkWidget *outer = gtk_box_new(GTK_ORIENTATION_HORIZONTAL, 0);
    gtk_widget_set_margin_top(outer, 2);
    gtk_widget_set_margin_bottom(outer, 2);
    GtkWidget *bubble = gtk_box_new(GTK_ORIENTATION_VERTICAL, 2);
    gtk_widget_add_css_class(bubble, msg->incoming ? "incoming-bubble" : "outgoing-bubble");
    gtk_widget_set_halign(bubble, msg->incoming ? GTK_ALIGN_START : GTK_ALIGN_END);
    gtk_widget_set_hexpand(outer, TRUE);
    GtkWidget *text = gtk_label_new(body && *body ? body : "(no text)");
    gtk_label_set_wrap(GTK_LABEL(text), TRUE);
    gtk_label_set_selectable(GTK_LABEL(text), TRUE);
    gtk_label_set_xalign(GTK_LABEL(text), 0.0);
    gtk_box_append(GTK_BOX(bubble), text);
    gchar *status_text;
    const char *st = state_label(msg->state);
    if (msg->timestamp && *msg->timestamp)
        status_text = *st ? g_strdup_printf("%s · %s", msg->timestamp, st)
                          : g_strdup(msg->timestamp);
    else
        status_text = g_strdup(*st ? st : "time unknown");
    GtkWidget *time = gtk_label_new(status_text);
    g_free(status_text);
    gtk_widget_add_css_class(time, "dim");
    gtk_label_set_xalign(GTK_LABEL(time), 1.0);
    gtk_box_append(GTK_BOX(bubble), time);
    gtk_box_append(GTK_BOX(outer), bubble);
    return outer;
}

static void
messages_sort_thread(GPtrArray *msgs)
{
    for (guint i = 1; i < msgs->len; i++) {
        gpointer key = msgs->pdata[i];
        guint j = i;
        while (j > 0 && message_cmp(key, msgs->pdata[j - 1]) < 0) {
            msgs->pdata[j] = msgs->pdata[j - 1];
            j--;
        }
        msgs->pdata[j] = key;
    }
}

static void
open_conversation(NuxelMessages *app, Conversation *conv)
{
    app->active_conversation = conv;
    gtk_label_set_text(GTK_LABEL(app->thread_header), conv->name);
    if (app->thread_subtitle)
        gtk_label_set_text(GTK_LABEL(app->thread_subtitle), conv->number);
    gtk_stack_set_visible_child_name(GTK_STACK(app->stack), "thread");
    gtk_widget_set_visible(app->recipient_entry, FALSE);
    refresh_thread_if_open(app);
    gtk_widget_grab_focus(app->message_entry);
}

static void
refresh_thread_if_open(NuxelMessages *app)
{
    Conversation *conv = app->active_conversation;
    if (!conv || !app->message_container) return;
    GtkWidget *child = gtk_widget_get_first_child(app->message_container);
    while (child) {
        GtkWidget *next = gtk_widget_get_next_sibling(child);
        gtk_box_remove(GTK_BOX(app->message_container), child);
        child = next;
    }
    for (guint i = 0; i < conv->messages->len; i++) {
        Message *msg = g_ptr_array_index(conv->messages, i);
        gchar *body = NULL;
        GtkWidget *w;
        if (msg->native_id) {
            if (!native_lookup(app, msg->native_id, &body, NULL)) continue;
            w = create_message_widget(msg, body);
            g_free(body);
        } else {
            w = create_message_widget(msg, msg->mirror_body ? msg->mirror_body : "(mirror)");
        }
        gtk_box_append(GTK_BOX(app->message_container), w);
    }
    /* Keep the newest message in view without hiding the composer. */
    if (GTK_IS_SCROLLED_WINDOW(app->message_scroll)) {
        GtkAdjustment *adj = gtk_scrolled_window_get_vadjustment(GTK_SCROLLED_WINDOW(app->message_scroll));
        gtk_adjustment_set_value(adj, gtk_adjustment_get_upper(adj) - gtk_adjustment_get_page_size(adj));
    }
}

/* ============================================================
 * UI callbacks
 * ============================================================ */

static void
on_send_clicked(GtkWidget *button, gpointer user_data)
{
    (void)button;
    send_message((NuxelMessages *)user_data);
}

static void
on_conversation_row_activated(GtkListBox *box, GtkListBoxRow *row, gpointer user_data)
{
    (void)box;
    NuxelMessages *app = user_data;
    Conversation *conv = g_object_get_data(G_OBJECT(row), "conversation");
    if (conv) open_conversation(app, conv);
}

static void
on_back_clicked(GtkWidget *button, gpointer user_data)
{
    (void)button;
    NuxelMessages *app = user_data;
    app->active_conversation = NULL;
    gtk_stack_set_visible_child_name(GTK_STACK(app->stack), "list");
    gtk_widget_set_visible(app->recipient_entry, FALSE);
    render_conversations(app);
    render_all_messages(app);
}

static void
on_new_message_clicked(GtkWidget *button, gpointer user_data)
{
    (void)button;
    NuxelMessages *app = user_data;
    app->active_conversation = NULL;
    gtk_label_set_text(GTK_LABEL(app->thread_header), "New message");
    if (app->thread_subtitle) gtk_label_set_text(GTK_LABEL(app->thread_subtitle), "Enter a recipient");
    gtk_editable_set_text(GTK_EDITABLE(app->message_entry), "");
    GtkWidget *child = gtk_widget_get_first_child(app->message_container);
    while (child) {
        GtkWidget *next = gtk_widget_get_next_sibling(child);
        gtk_box_remove(GTK_BOX(app->message_container), child);
        child = next;
    }
    gtk_widget_set_visible(app->recipient_entry, TRUE);
    gtk_editable_set_text(GTK_EDITABLE(app->recipient_entry), "");
    gtk_stack_set_visible_child_name(GTK_STACK(app->stack), "thread");
    gtk_widget_grab_focus(app->recipient_entry);
}

static void
on_stack_page_changed(GtkStack *stack, GParamSpec *pspec, gpointer user_data)
{
    (void)pspec;
    NuxelMessages *app = user_data;
    if (g_strcmp0(gtk_stack_get_visible_child_name(stack), "list") == 0)
        gtk_widget_set_visible(app->recipient_entry, FALSE);
}

static void
on_recipient_activate(GtkWidget *entry, gpointer user_data)
{
    (void)entry;
    NuxelMessages *app = user_data;
    if (app->recipient_entry && gtk_editable_get_text(GTK_EDITABLE(app->recipient_entry))[0])
        gtk_widget_grab_focus(app->message_entry);
}

static void on_tab_messages(GtkWidget *b, gpointer u)
{
    (void)b;
    NuxelMessages *app = u;
    GtkWidget *inner = g_object_get_data(G_OBJECT(app->list_page), "inner_stack");
    if (inner) gtk_stack_set_visible_child_name(GTK_STACK(inner), "conversations");
}
static void on_tab_all(GtkWidget *b, gpointer u)
{
    (void)b;
    NuxelMessages *app = u;
    GtkWidget *inner = g_object_get_data(G_OBJECT(app->list_page), "inner_stack");
    render_all_messages(app);
    if (inner) gtk_stack_set_visible_child_name(GTK_STACK(inner), "all");
}

/* ============================================================
 * Core logic
 * ============================================================ */

static void
send_message(NuxelMessages *app)
{
    const gchar *text = gtk_editable_get_text(GTK_EDITABLE(app->message_entry));
    if (!text || strlen(text) == 0) return;
    const gchar *number;
    if (app->active_conversation)
        number = app->active_conversation->number;
    else
        number = gtk_editable_get_text(GTK_EDITABLE(app->recipient_entry));
    gchar *normalized = NULL;
    if (number && *number) {
        char buf[NUXEL_NUMBER_MAX];
        if (nuxel_phone_normalize_number(buf, sizeof buf, number) == 0 && buf[0])
            normalized = g_strdup(buf);
    }
    if (!normalized) {
        if (!number || !*number) return;
        normalized = g_strdup(number);
    }
    if (app->sending || !app->modem_ready || !nuxel_radio_available(&app->radio)) {
        g_free(normalized);
        return;
    }
    app->sending = TRUE;
    gtk_widget_set_sensitive(app->send_button, FALSE);
    nuxel_radio_call(&app->radio, "SendSms", g_variant_new("(ss)", normalized, text),
                     "sms:send", native_sent, app);
    g_free(normalized);
}

static gboolean
messages_poll_tick(gpointer user)
{
    NuxelMessages *app = user;
    if (!app->sending) native_refresh(app);
    return G_SOURCE_CONTINUE;
}

static void
native_changed(const char *signal, gpointer user)
{
    NuxelMessages *app = user;
    if (signal) sms_received_hint(signal, app);
    else native_refresh(app);
}

static void
messages_update_capabilities(NuxelMessages *app)
{
    g_strlcpy(app->caps.modem_name, "Shannon 5000AP (Radio1 over IMS)",
              sizeof app->caps.modem_name);
    app->caps.modem_present = app->modem_ready ? 1 : 0;
    app->caps.sms_send = app->modem_ready ? 1 : 0;
}

/* ============================================================
 * UI construction
 * ============================================================ */

static GtkWidget *
nuxel_page(const char *title)
{
    GtkWidget *page = gtk_box_new(GTK_ORIENTATION_VERTICAL, 0);
    gtk_widget_add_css_class(page, "nuxel-page");
    GtkWidget *head = gtk_box_new(GTK_ORIENTATION_HORIZONTAL, 8);
    gtk_widget_add_css_class(head, "nuxel-head");
    GtkWidget *label = gtk_label_new(title);
    gtk_widget_add_css_class(label, "nuxel-title");
    gtk_label_set_xalign(GTK_LABEL(label), 0.0);
    gtk_widget_set_hexpand(label, TRUE);
    gtk_box_append(GTK_BOX(head), label);
    gtk_box_append(GTK_BOX(page), head);
    return page;
}

static const char *MESSAGES_CSS =
    ".nuxel-page { background: #0a1628; }"
    ".nuxel-head { padding: 14px 16px 10px; }"
    ".nuxel-title { font-size: 19px; font-weight: 700; color: #e6f0ff; }"
    ".nuxel-tabs { padding: 0 12px 10px 12px; }"
    ".nuxel-panel { background: #12233c; border-radius: 14px; margin: 0 12px 12px 12px; padding: 4px; }"
    ".nuxel-row { background: #1a3050; border-radius: 12px; padding: 12px; margin: 4px; }"
    ".nuxel-row-title { font-weight: 700; font-size: 15px; color: #e6f0ff; }"
    ".nuxel-row-body { font-size: 14px; color: #e6f0ff; }"
    ".dim { color: #8aa3c7; font-size: 12px; }"
    ".nuxel-avatar { background: rgba(62,166,255,0.18); color: #3ea6ff; border-radius: 18px;"
    "  min-width: 36px; min-height: 36px; font-weight: 700; }"
    ".nuxel-badge { background: #3ea6ff; color: #06121f; border-radius: 10px; padding: 1px 7px;"
    "  font-size: 11px; font-weight: 700; }"
    ".nuxel-empty { padding: 24px; }"
    ".nuxel-empty-title { font-size: 16px; font-weight: 700; color: #e6f0ff; }"
    ".incoming-bubble { background: #1a3050; border-radius: 14px 14px 14px 4px;"
    "  color: #e6f0ff; padding: 9px 12px; margin: 3px 44px 3px 10px; }"
    ".outgoing-bubble { background: rgba(62,166,255,0.22); border-radius: 14px 14px 4px 14px;"
    "  color: #e6f0ff; padding: 9px 12px; margin: 3px 10px 3px 44px; }"
    ".nuxel-composer { background: #12233c; border-radius: 14px; margin: 6px 12px 12px 12px; padding: 8px; }"
    ".nuxel-composer entry { background: #0a1628; color: #e6f0ff; border-radius: 10px; }"
    "listbox { background: transparent; }"
    "listbox row { background: transparent; }"
    "listbox row:selected { background: transparent; }";

static GtkWidget *
build_list_page(NuxelMessages *app)
{
    GtkWidget *page = nuxel_page("Messages");
    GtkWidget *head = gtk_widget_get_first_child(page);
    gtk_widget_set_margin_start(head, 4);
    gtk_widget_set_margin_end(head, 8);
    GtkWidget *import_sim = gtk_button_new_with_label("⇤");
    gtk_widget_add_css_class(import_sim, "flat");
    gtk_widget_set_tooltip_text(import_sim, "Import messages from the SIM mirror");
    g_signal_connect(import_sim, "clicked", G_CALLBACK(on_import_sim_clicked), app);
    gtk_box_append(GTK_BOX(head), import_sim);
    GtkWidget *new_message = gtk_button_new_with_label("New");
    gtk_widget_add_css_class(new_message, "suggested-action");
    gtk_widget_set_tooltip_text(new_message, "Write a new SMS");
    g_signal_connect(new_message, "clicked", G_CALLBACK(on_new_message_clicked), app);
    gtk_box_append(GTK_BOX(head), new_message);

    GtkWidget *tabs = gtk_box_new(GTK_ORIENTATION_HORIZONTAL, 6);
    gtk_widget_add_css_class(tabs, "nuxel-tabs");
    GtkWidget *tab_conv = gtk_toggle_button_new_with_label("Conversations");
    GtkWidget *tab_all = gtk_toggle_button_new_with_label("All messages");
    gtk_toggle_button_set_group(GTK_TOGGLE_BUTTON(tab_all), GTK_TOGGLE_BUTTON(tab_conv));
    gtk_toggle_button_set_active(GTK_TOGGLE_BUTTON(tab_conv), TRUE);
    gtk_widget_set_hexpand(tab_conv, TRUE);
    gtk_widget_set_hexpand(tab_all, TRUE);
    g_signal_connect(tab_conv, "toggled", G_CALLBACK(on_tab_messages), app);
    g_signal_connect(tab_all, "toggled", G_CALLBACK(on_tab_all), app);
    gtk_box_append(GTK_BOX(tabs), tab_conv);
    gtk_box_append(GTK_BOX(tabs), tab_all);
    gtk_box_append(GTK_BOX(page), tabs);

    GtkWidget *inner_stack = gtk_stack_new();
    gtk_widget_set_vexpand(inner_stack, TRUE);

    /* Conversations view */
    GtkWidget *conv_box = gtk_box_new(GTK_ORIENTATION_VERTICAL, 0);
    app->conversation_list = gtk_list_box_new();
    gtk_list_box_set_selection_mode(GTK_LIST_BOX(app->conversation_list), GTK_SELECTION_NONE);
    g_signal_connect(app->conversation_list, "row-activated",
                     G_CALLBACK(on_conversation_row_activated), app);
    GtkWidget *conv_scroll = gtk_scrolled_window_new();
    gtk_scrolled_window_set_policy(GTK_SCROLLED_WINDOW(conv_scroll), GTK_POLICY_NEVER, GTK_POLICY_AUTOMATIC);
    gtk_scrolled_window_set_child(GTK_SCROLLED_WINDOW(conv_scroll), app->conversation_list);
    gtk_widget_set_vexpand(conv_scroll, TRUE);
    gtk_box_append(GTK_BOX(conv_box), conv_scroll);
    app->list_empty = create_empty_state("No messages yet", "Received and sent SMS appear here. Use New to write one.");
    gtk_box_append(GTK_BOX(conv_box), app->list_empty);
    gtk_stack_add_named(GTK_STACK(inner_stack), conv_box, "conversations");

    /* All Messages view — every stored logical SMS, one row each. */
    GtkWidget *all_box = gtk_box_new(GTK_ORIENTATION_VERTICAL, 0);
    app->all_messages_list = gtk_list_box_new();
    gtk_list_box_set_selection_mode(GTK_LIST_BOX(app->all_messages_list), GTK_SELECTION_NONE);
    GtkWidget *all_scroll = gtk_scrolled_window_new();
    gtk_scrolled_window_set_policy(GTK_SCROLLED_WINDOW(all_scroll), GTK_POLICY_NEVER, GTK_POLICY_AUTOMATIC);
    gtk_scrolled_window_set_child(GTK_SCROLLED_WINDOW(all_scroll), app->all_messages_list);
    gtk_widget_set_vexpand(all_scroll, TRUE);
    gtk_box_append(GTK_BOX(all_box), all_scroll);
    app->all_empty = create_empty_state("No stored SMS", "The native SMS store is empty.");
    gtk_box_append(GTK_BOX(all_box), app->all_empty);
    gtk_stack_add_named(GTK_STACK(inner_stack), all_box, "all");

    g_object_set_data(G_OBJECT(page), "inner_stack", inner_stack);
    gtk_box_append(GTK_BOX(page), inner_stack);

    app->capability_label = gtk_label_new("Native SMS · status pending");
    gtk_label_set_wrap(GTK_LABEL(app->capability_label), TRUE);
    gtk_label_set_xalign(GTK_LABEL(app->capability_label), 0.0);
    gtk_widget_set_margin_start(app->capability_label, 14);
    gtk_widget_set_margin_end(app->capability_label, 14);
    gtk_widget_set_margin_bottom(app->capability_label, 10);
    gtk_widget_add_css_class(app->capability_label, "dim");
    gtk_box_append(GTK_BOX(page), app->capability_label);
    app->list_page = page;
    return page;
}

static GtkWidget *
build_thread_page(NuxelMessages *app)
{
    GtkWidget *page = gtk_box_new(GTK_ORIENTATION_VERTICAL, 0);
    gtk_widget_add_css_class(page, "nuxel-page");

    GtkWidget *head = gtk_box_new(GTK_ORIENTATION_HORIZONTAL, 8);
    gtk_widget_add_css_class(head, "nuxel-head");
    GtkWidget *back_btn = gtk_button_new_with_label("←");
    gtk_widget_add_css_class(back_btn, "flat");
    gtk_widget_set_tooltip_text(back_btn, "Back to conversations");
    g_signal_connect(back_btn, "clicked", G_CALLBACK(on_back_clicked), app);
    gtk_box_append(GTK_BOX(head), back_btn);
    GtkWidget *titles = gtk_box_new(GTK_ORIENTATION_VERTICAL, 0);
    gtk_widget_set_hexpand(titles, TRUE);
    app->thread_header = gtk_label_new("");
    gtk_widget_add_css_class(app->thread_header, "nuxel-title");
    gtk_label_set_xalign(GTK_LABEL(app->thread_header), 0.0);
    gtk_label_set_ellipsize(GTK_LABEL(app->thread_header), PANGO_ELLIPSIZE_END);
    app->thread_subtitle = gtk_label_new("");
    gtk_widget_add_css_class(app->thread_subtitle, "dim");
    gtk_label_set_xalign(GTK_LABEL(app->thread_subtitle), 0.0);
    gtk_box_append(GTK_BOX(titles), app->thread_header);
    gtk_box_append(GTK_BOX(titles), app->thread_subtitle);
    gtk_box_append(GTK_BOX(head), titles);
    gtk_box_append(GTK_BOX(page), head);

    app->message_scroll = gtk_scrolled_window_new();
    gtk_scrolled_window_set_policy(GTK_SCROLLED_WINDOW(app->message_scroll), GTK_POLICY_NEVER, GTK_POLICY_AUTOMATIC);
    gtk_widget_set_vexpand(app->message_scroll, TRUE);
    app->message_container = gtk_box_new(GTK_ORIENTATION_VERTICAL, 2);
    gtk_widget_set_margin_top(app->message_container, 4);
    gtk_widget_set_margin_bottom(app->message_container, 4);
    gtk_scrolled_window_set_child(GTK_SCROLLED_WINDOW(app->message_scroll), app->message_container);
    gtk_box_append(GTK_BOX(page), app->message_scroll);

    GtkWidget *compose_box = gtk_box_new(GTK_ORIENTATION_VERTICAL, 6);
    gtk_widget_add_css_class(compose_box, "nuxel-composer");
    app->recipient_entry = gtk_entry_new();
    gtk_entry_set_placeholder_text(GTK_ENTRY(app->recipient_entry),
                                   "Recipient number (e.g. +31612345678)");
    gtk_entry_set_input_purpose(GTK_ENTRY(app->recipient_entry), GTK_INPUT_PURPOSE_PHONE);
    gtk_widget_set_visible(app->recipient_entry, FALSE);
    gtk_box_append(GTK_BOX(compose_box), app->recipient_entry);
    GtkWidget *input_box = gtk_box_new(GTK_ORIENTATION_HORIZONTAL, 8);
    app->message_entry = gtk_entry_new();
    gtk_entry_set_placeholder_text(GTK_ENTRY(app->message_entry), "Message");
    gtk_widget_set_hexpand(app->message_entry, TRUE);
    gtk_box_append(GTK_BOX(input_box), app->message_entry);
    app->send_button = gtk_button_new_with_label("Send");
    gtk_widget_add_css_class(app->send_button, "suggested-action");
    g_signal_connect(app->send_button, "clicked", G_CALLBACK(on_send_clicked), app);
    gtk_box_append(GTK_BOX(input_box), app->send_button);
    gtk_box_append(GTK_BOX(compose_box), input_box);
    gtk_box_append(GTK_BOX(page), compose_box);
    g_signal_connect(app->message_entry, "activate", G_CALLBACK(on_send_clicked), app);
    g_signal_connect(app->recipient_entry, "activate", G_CALLBACK(on_recipient_activate), app);
    return page;
}

/* ============================================================
 * Application entry point
 * ============================================================ */

static void
notify_proxy_ready(GObject *source, GAsyncResult *result, gpointer user)
{
    (void)source;
    NuxelMessages *app = user;
    GError *error = NULL;
    app->notify_proxy = g_dbus_proxy_new_for_bus_finish(result, &error);
    if (error) g_clear_error(&error);
}

static void
modem_connect(NuxelMessages *app)
{
    gtk_widget_set_sensitive(app->send_button, FALSE);
    nuxel_radio_connect(&app->radio, "org.nuxel.Messages", native_changed, app);
    /* Kept for completeness; inbound SMS announcements are owned by radiod. */
    g_dbus_proxy_new_for_bus(G_BUS_TYPE_SESSION, G_DBUS_PROXY_FLAGS_DO_NOT_AUTO_START,
                             NULL, "org.freedesktop.Notifications",
                             "/org/freedesktop/Notifications",
                             "org.freedesktop.Notifications", NULL,
                             notify_proxy_ready, app);
    app->poll_source = g_timeout_add_seconds(20, messages_poll_tick, app);
}

static void
activate_cb(GtkApplication *gtk_app, gpointer user_data)
{
    (void)user_data;
    NuxelMessages *app = g_new0(NuxelMessages, 1);
    GtkCssProvider *provider = gtk_css_provider_new();
    gtk_css_provider_load_from_string(provider, MESSAGES_CSS);
    gtk_style_context_add_provider_for_display(gdk_display_get_default(),
        GTK_STYLE_PROVIDER(provider), GTK_STYLE_PROVIDER_PRIORITY_APPLICATION);
    g_object_unref(provider);

    app->window = adw_application_window_new(gtk_app);
    gtk_window_set_title(GTK_WINDOW(app->window), "Messages");
    gtk_window_set_default_size(GTK_WINDOW(app->window), 400, 700);
    AdwStyleManager *style = adw_style_manager_get_default();
    adw_style_manager_set_color_scheme(style, ADW_COLOR_SCHEME_FORCE_DARK);

    {
        gchar *dir = g_build_filename(g_get_user_data_dir(), "nuxel-contacts", NULL);
        g_mkdir_with_parents(dir, 0755);
        app->store_path = g_build_filename(dir, "contacts.json", NULL);
        app->sim_path = g_build_filename(dir, "sim-messages.json", NULL);
        g_free(dir);
    }
    nuxel_phone_store_init(&app->store);
    nuxel_phone_store_init(&app->sim_store);
    nuxel_phone_capabilities_init(&app->caps);

    app->stack = gtk_stack_new();
    gtk_stack_set_transition_type(GTK_STACK(app->stack), GTK_STACK_TRANSITION_TYPE_SLIDE_LEFT_RIGHT);
    gtk_widget_set_vexpand(app->stack, TRUE);

    GtkWidget *list_page = build_list_page(app);
    GtkWidget *thread_page = build_thread_page(app);
    gtk_stack_add_named(GTK_STACK(app->stack), list_page, "list");
    gtk_stack_add_named(GTK_STACK(app->stack), thread_page, "thread");
    g_signal_connect(app->stack, "notify::visible-child-name", G_CALLBACK(on_stack_page_changed), app);

    adw_application_window_set_content(ADW_APPLICATION_WINDOW(app->window), app->stack);

    load_conversations(app);
    messages_import_sim(app, TRUE);
    render_conversations(app);
    render_all_messages(app);

    modem_connect(app);

    gtk_window_present(GTK_WINDOW(app->window));
}

int
main(int argc, char *argv[])
{
    GtkApplication *gtk_app = gtk_application_new("org.nuxel.Messages",
                                                   G_APPLICATION_DEFAULT_FLAGS);
    g_signal_connect(gtk_app, "activate", G_CALLBACK(activate_cb), NULL);
    int status = g_application_run(G_APPLICATION(gtk_app), argc, argv);
    g_object_unref(gtk_app);
    return status;
}
