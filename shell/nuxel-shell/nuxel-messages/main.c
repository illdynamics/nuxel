/**
 * Nuxel Messages — Native SMS client for Nuxel OS
 * GTK4/libadwaita, native Radio1/Radio1Bridge D-Bus integration.
 *
 * Model: every stored logical SMS is rebuilt from the authoritative
 * ListSms+GetSms snapshot on each refresh (one Message per native id). The
 * legacy ModemManager/thread-file path this file replaced appended a new
 * object per refresh and persisted its own copy, which duplicated history and
 * made "one message" show up on screen; it is gone. The native SMS store is
 * the single source of truth, and SIM-mirror imports are additive.
 *
 * Notifications/sounds: the Radiod service owns the one-and-only inbound SMS
 * announcement (nuxel-radiod -> notification hub -> POW cue). This app never
 * calls Notify and never plays a sound, so history load, refresh, restart or a
 * bridge reconnect can never replay a notification.
 *
 * SIM: "Import SIM" copies SIM-mirror messages + phonebook names into the
 * local store/address book (additive, idempotent, never writes the SIM).
 * "Sync" repeats that and also copies local messages the mirror lacks. Both
 * preserve every existing record.
 *
 * Visual language follows the Nuxel reference apps (Maps / Snekbyte /
 * Firewall): deep navy ground, rounded panel cards, cyan accent, muted dim
 * text, flat touch targets.
 */

#include <adwaita.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdbool.h>
#include <glib.h>
#include <gio/gio.h>
#include "nuxel-phone-data.h"
#include "nuxel-radio-client.h"

/* ============================================================
 * Data structures
 * ============================================================ */

typedef struct {
    gchar   *timestamp;
    gboolean incoming;
    guint   native_id;         /* 0 for SIM-mirror rows */
    gchar   *state;
    gchar   *mirror_body;      /* SIM-mirror rows only */
    gchar   *preview;          /* body/state text for conversation rows */
    gint64   at;               /* unix seconds for ordering */
} Message;

typedef struct {
    gchar    *number;
    gchar    *name;
    GPtrArray *messages;
    Message   *last_message;
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
    GtkWidget *contact_entry;
    GtkWidget *contact_popover;
    GtkWidget *send_button;
    GtkWidget *thread_header;
    GtkWidget *thread_subtitle;
    GtkWidget *message_scroll;
    GtkWidget *message_container;
    GtkWidget *capability_label;

    guint poll_source;
    gboolean modem_ready;

    NuxelRadioClient radio;
    GArray *native_ids;
    guint native_index;
    gboolean refreshing, refresh_again, sending;

    gchar *status_detail;
    gchar *list_detail;
    gchar *ims_state;
    gchar *sms_transport;
    gchar *sync_detail;

    GHashTable *native;          /* id -> GVariant a{ss} snapshot */
    guint native_count;

    GPtrArray *conversations;
    Conversation *active_conversation;
    gchar *keep_active_key;

    NuxelPhoneStore store;
    NuxelPhoneCapabilities caps;
    gchar *store_path;

    NuxelPhoneStore sim_store;
    gchar *sim_path;
    gchar *sim_contact_path;     /* the SIM phonebook mirror Contacts writes */
} NuxelMessages;

/* ============================================================
 * Forward declarations
 * ============================================================ */

static void load_conversations(NuxelMessages *app);
static void render_conversations(NuxelMessages *app);
static GtkWidget *render_all_messages(NuxelMessages *app);
static void place_all_messages(NuxelMessages *app, gboolean in_thread);
static void open_conversation(NuxelMessages *app, Conversation *conv);
static void send_message(NuxelMessages *app);
static void modem_connect(NuxelMessages *app);
static void messages_update_capabilities(NuxelMessages *app);
static gint conversation_cmp(const Conversation *a, const Conversation *b);
static void message_free(gpointer data);
static void messages_import_sim(NuxelMessages *app, gboolean merge_only);
static void messages_merge_store(NuxelMessages *app, NuxelPhoneStore *store, size_t *added);
static void on_import_sim_clicked(GtkWidget *btn, gpointer user_data);
static void on_sync_sim_clicked(GtkWidget *btn, gpointer user_data);
static void on_contact_search_changed(GtkEditable *editable, gpointer user_data);
static void on_contact_row_picked(GtkListBox *box, GtkListBoxRow *row, gpointer user_data);
static void native_refresh(gpointer user);
static gboolean messages_poll_tick(gpointer user);
static void messages_refresh_banner(NuxelMessages *app);
static void messages_probe_ims(NuxelMessages *app);
static void refresh_thread_if_open(NuxelMessages *app);
static void messages_sort_thread(GPtrArray *msgs);
static void build_model(NuxelMessages *app);
static const gchar *conversation_title(NuxelMessages *app, Conversation *conv);
static gchar *conversation_preview(NuxelMessages *app, Conversation *conv);

/* ============================================================
 * Helpers
 * ============================================================ */

/* Opt-in trace (NUXEL_MESSAGES_TRACE=1): names only, no message bodies. */
static gboolean
messages_trace_enabled(void)
{
    return g_getenv("NUXEL_MESSAGES_TRACE") != NULL;
}


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
    const gchar *name = nuxel_phone_contact_name(&app->store, number);
    if (name && *name) {
        g_free(conv->name);
        conv->name = g_strdup(name);
    }
    g_ptr_array_add(app->conversations, conv);
    return conv;
}

static void
canonical_peer(char *out, size_t cap, const char *peer)
{
    char norm[NUXEL_NUMBER_MAX];
    if (peer && *peer && nuxel_phone_normalize_number(norm, sizeof norm, peer) == 0 && norm[0])
        g_strlcpy(out, norm, cap);
    else
        g_strlcpy(out, peer ? peer : "", cap);
}

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
    return NULL;
}

static gint
conversation_cmp(const Conversation *a, const Conversation *b)
{
    guint ao = a->last_message ? a->last_message->native_id : 0;
    guint bo = b->last_message ? b->last_message->native_id : 0;
    if (ao != bo) return (ao > bo) ? -1 : 1;
    gint64 at = a->last_message ? a->last_message->at : 0;
    gint64 bt = b->last_message ? b->last_message->at : 0;
    if (at != bt) return (at > bt) ? -1 : 1;
    return g_strcmp0(a->number, b->number);
}

static const char *
state_label(const char *state)
{
    if (!state || !*state) return "";
    return state;
}

static void
messages_reset_conversations(NuxelMessages *app)
{
    g_free(app->keep_active_key);
    app->keep_active_key = app->active_conversation
                         ? g_strdup(app->active_conversation->number) : NULL;
    app->active_conversation = NULL;
    if (app->conversations) g_ptr_array_unref(app->conversations);
    app->conversations = g_ptr_array_new_with_free_func(conversation_free);
}

/* Contacts used later as labels are resolved lazily from app->store, so
 * conversation->name is only the number fallback.  Keep it in sync. */
static gchar *variant_str(GVariant *dict, const char *key)
{
    const char *v = "";
    return g_variant_lookup(dict, key, "&s", &v) ? g_strdup(v) : g_strdup("");
}

/* ============================================================
 * Native path (Radio1 snapshots) — no notification code in this app
 * ============================================================ */

static void
native_list_done(NuxelMessages *app)
{
    app->refreshing = FALSE;
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
messages_update_capabilities(NuxelMessages *app)
{
    nuxel_phone_capabilities_init(&app->caps);
    app->caps.modem_present = app->modem_ready ? 1 : 0;
    app->caps.sms_send = app->modem_ready ? 1 : 0;
    app->caps.data_connection = app->modem_ready ? 1 : 0;
    app->caps.voice_calls = 0;   /* native VoLTE is not implemented yet */
    g_strlcpy(app->caps.modem_name, "Samsung S5000AP (native Radio1)",
              sizeof app->caps.modem_name);
    g_strlcpy(app->caps.detail, app->modem_ready
             ? "Native SMS over IMS is available; voice (VoLTE) is pending."
             : "Radio1 reports the SMS transport as not ready.",
             sizeof app->caps.detail);
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
    const char *storage = "unknown", *ready = "unknown", *smsc = "unknown";
    const char *pending = "unknown", *blocked = "unknown", *native_ready = "false",
               *registration = "unavailable";
    g_variant_lookup(dict, "storage", "&s", &storage);
    g_variant_lookup(dict, "smsc", "&s", &smsc);
    g_variant_lookup(dict, "pending", "&s", &pending);
    g_variant_lookup(dict, "blocked", "&s", &blocked);
    g_variant_lookup(dict, "ready", "&s", &native_ready);
    g_variant_lookup(dict, "registration", "&s", &registration);
    g_free(app->sms_transport);
    app->sms_transport = g_strdup(ready);
    gboolean registered = !strcmp(registration, "registered");
    app->modem_ready = !strcmp(native_ready, "true") && !strcmp(storage, "available") &&
                       !strcmp(smsc, "received") && !strcmp(pending, "false") &&
                       !strcmp(blocked, "false") && registered;
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
    if (app->native) {
        g_hash_table_remove_all(app->native);
        app->native_count = 0;
    }
    /* load_conversations() re-reads the address book; do it again here so a
     * 20 s refresh after a contact edit resolves the new name, and so the
     * clear->GetSmsStatus->ListSms sequence below never leaves the store
     * momentarily empty while the model is being rebuilt. */
    load_conversations(app);
    messages_probe_ims(app);
    nuxel_radio_call(&app->radio, "GetSmsStatus", NULL, NULL, native_status, app);
}

static void
native_sent(GVariant *reply, const GError *error, gpointer user)
{
    NuxelMessages *app = user;
    app->sending = FALSE;
    gtk_widget_set_sensitive(app->send_button, app->modem_ready);
    if (!reply || error) {
        gboolean denied = error && g_error_matches(error, G_IO_ERROR, G_IO_ERROR_PERMISSION_DENIED);
        g_free(app->status_detail);
        app->status_detail = g_strdup(denied
            ? (error ? error->message : "Sending SMS was denied.")
            : "Submission outcome uncertain or rejected. Check the outbox before another attempt; nothing was retried.");
        messages_refresh_banner(app);
        native_refresh(app);
        return;
    }
    gtk_editable_set_text(GTK_EDITABLE(app->message_entry), "");
    if (!app->active_conversation && app->recipient_entry) {
        const gchar *peer = gtk_editable_get_text(GTK_EDITABLE(app->recipient_entry));
        if (peer && *peer) {
            char key[NUXEL_NUMBER_MAX];
            canonical_peer(key, sizeof key, peer);
            app->active_conversation = find_or_create_conversation(app, key);
        }
    }
    native_refresh(app);
}

static void
messages_refresh_banner(NuxelMessages *app)
{
    if (!app->capability_label) return;
    gboolean ims_ok = app->ims_state && !strcmp(app->ims_state, "registered") &&
                      !(app->sms_transport && !strcmp(app->sms_transport, "unavailable"));
    const gchar *ims = app->ims_state ? app->ims_state : "status pending";
    gchar *banner;
    if (app->sync_detail && *app->sync_detail)
        banner = g_strdup(app->sync_detail);
    else if (app->list_detail && *app->list_detail)
        banner = g_strdup_printf("SMS store unavailable (%s)", app->list_detail);
    else if (app->status_detail && *app->status_detail)
        banner = g_strdup_printf("SMS unavailable (%s)", app->status_detail);
    else if (ims_ok)
        banner = g_strdup_printf("Native SMS ready over IMS (%s) · a submission is not yet delivery", ims);
    else
        banner = g_strdup_printf("Native SMS starting · IMS %s", ims);
    gtk_label_set_text(GTK_LABEL(app->capability_label), banner);
    g_free(banner);
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

static void
sms_received_hint(const gchar *hint, gpointer user)
{
    (void)hint;
    native_refresh(user);
}

/* ============================================================
 * Store / SIM mirror / contact-name resolution
 * ============================================================ */

static void
messages_merge_store(NuxelMessages *app, NuxelPhoneStore *store, size_t *added)
{
    for (size_t i = 0; i < store->n_messages; i++) {
        NuxelMessage *stored = &store->messages[i];
        char key[NUXEL_NUMBER_MAX];
        canonical_peer(key, sizeof key, stored->peer);
        if (!key[0]) continue;
        gboolean exists = FALSE;
        if (app->native) {
            GHashTableIter it; gpointer k, v;
            g_hash_table_iter_init(&it, app->native);
            while (g_hash_table_iter_next(&it, &k, &v)) {
                gchar *np = variant_str(v, "peer");
                gchar *nb = variant_str(v, "text");
                gchar *nd = variant_str(v, "direction");
                char nk[NUXEL_NUMBER_MAX]; canonical_peer(nk, sizeof nk, np);
                if (g_strcmp0(nk, key) == 0 && g_strcmp0(nb, stored->body) == 0 &&
                    g_strcmp0(nd, stored->direction) == 0) exists = TRUE;
                g_free(np); g_free(nb); g_free(nd);
                if (exists) break;
            }
        }
        if (!exists) {
            for (guint c = 0; c < app->conversations->len && !exists; c++) {
                Conversation *conv = g_ptr_array_index(app->conversations, c);
                if (g_strcmp0(conv->number, key) != 0) continue;
                for (guint j = 0; j < conv->messages->len; j++) {
                    Message *m = g_ptr_array_index(conv->messages, j);
                    if (m->native_id == 0 && m->incoming == (g_strcmp0(stored->direction, "in") == 0) &&
                        g_strcmp0(m->mirror_body, stored->body) == 0) { exists = TRUE; break; }
                }
            }
        }
        if (exists) continue;
        /* A mirror record whose peer is an alpha name (a SIM storage name
         * without a number) is not a conversation: it is only reachable once
         * the name has been mapped to a number, which the address-book merge
         * does.  Showing it as a thread would create a nameless #-row. */
        if (!nuxel_phone_is_number(key) && !nuxel_phone_contact_name(&app->store, key))
            continue;
        Conversation *conv = find_or_create_conversation(app, key);
        Message *m = message_new_at(NULL, g_strcmp0(stored->direction, "in") == 0, 0,
                                    stored->state, stored->at);
        if (stored->at > 0) {
            GDateTime *dt = g_date_time_new_from_unix_local(stored->at);
            m->timestamp = dt ? g_date_time_format(dt, "%H:%M") : NULL;
            if (dt) g_date_time_unref(dt);
        }
        m->mirror_body = g_strdup(stored->body);
        m->preview = g_strdup(stored->body);
        g_ptr_array_add(conv->messages, m);
        if (conv->last_message) {
            if (!stored->at || stored->at >= conv->last_message->at) conv->last_message = m;
        } else conv->last_message = m;
        (*added)++;
    }
}

static bool
messages_sync_contacts(NuxelMessages *app, size_t *added)
{
    if (added) *added = 0;
    if (!app->sim_contact_path) return false;
    NuxelPhoneStore simbook;
    nuxel_phone_store_init(&simbook);
    int rc = nuxel_phone_store_load(&simbook, app->sim_contact_path);
    if (rc == 0 && simbook.n_contacts) {
        size_t n = nuxel_phone_merge_contacts(&app->store, &simbook);
        if (n) nuxel_phone_store_save(&app->store, app->store_path);
        if (added) *added = n;
    }
    nuxel_phone_store_free(&simbook);
    return rc == 0;
}

static void
messages_import_sim(NuxelMessages *app, gboolean merge_only)
{
    nuxel_phone_store_free(&app->sim_store);
    nuxel_phone_store_init(&app->sim_store);
    int rc = app->sim_path ? nuxel_phone_store_load(&app->sim_store, app->sim_path) : 1;
    if (rc == -1 || app->sim_store.n_messages == 0) {
        if (!merge_only) {
            g_free(app->sync_detail);
            app->sync_detail = g_strdup(rc == -1
                ? "The SIM mirror could not be read; nothing was changed."
                : "The SIM mirror is empty — nothing to import. The SIM itself was not modified.");
        }
        return;
    }
    if (merge_only) {
        size_t added = 0;
        messages_merge_store(app, &app->sim_store, &added);
        if (added) g_message("[Messages] SIM mirror: loaded %zu message(s).", added);
        return;
    }
    size_t added = 0, added_contacts = 0;
    added = (size_t)nuxel_phone_import_sim_messages(&app->store, &app->sim_store, 1,
                                                    NULL, &added_contacts);
    if (added || added_contacts)
        nuxel_phone_store_save(&app->store, app->store_path);
    g_free(app->sync_detail);
    app->sync_detail = g_strdup_printf(
        "Imported %zu message(s) and %zu contact(s) from the SIM mirror; already-present "
        "records were kept once. Nothing was deleted and the SIM itself was not written.",
        added, added_contacts);
}

static void
on_import_sim_clicked(GtkWidget *btn, gpointer user_data)
{
    (void)btn;
    NuxelMessages *app = user_data;
    messages_import_sim(app, FALSE);
    build_model(app);
    render_conversations(app);
    render_all_messages(app);
    refresh_thread_if_open(app);
    messages_refresh_banner(app);
}

static void
on_sync_sim_clicked(GtkWidget *btn, gpointer user_data)
{
    (void)btn;
    NuxelMessages *app = user_data;
    size_t from_sim = 0, to_sim = 0, contacts = 0;
    if (app->store_path) {
        nuxel_phone_store_free(&app->store);
        nuxel_phone_store_init(&app->store);
        nuxel_phone_store_load(&app->store, app->store_path);
    }
    messages_sync_contacts(app, &contacts);
    nuxel_phone_store_free(&app->sim_store);
    nuxel_phone_store_init(&app->sim_store);
    int rc = app->sim_path ? nuxel_phone_store_load(&app->sim_store, app->sim_path) : 1;
    if (rc == 0 && app->sim_store.n_messages)
        from_sim = (size_t)nuxel_phone_import_sim_messages(&app->store, &app->sim_store, 1,
                                                           NULL, &contacts);
    if (app->sim_path && rc == 0) {
        for (size_t i = 0; i < app->store.n_messages; i++) {
            NuxelMessage *m = &app->store.messages[i];
            gboolean exists = FALSE;
            for (size_t j = 0; j < app->sim_store.n_messages; j++) {
                NuxelMessage *s = &app->sim_store.messages[j];
                if (g_strcmp0(s->direction, m->direction) == 0 &&
                    g_strcmp0(s->body, m->body) == 0 &&
                    nuxel_phone_number_match(s->peer, m->peer)) { exists = TRUE; break; }
            }
            if (!exists && nuxel_phone_add_message(&app->sim_store, m->peer, m->body,
                                                   m->direction, m->state))
                to_sim++;
        }
        if (to_sim) nuxel_phone_store_save(&app->sim_store, app->sim_path);
    }
    nuxel_phone_store_free(&app->store);
    nuxel_phone_store_init(&app->store);
    if (app->store_path) nuxel_phone_store_load(&app->store, app->store_path);
    g_free(app->sync_detail);
    app->sync_detail = rc == -1
        ? g_strdup("The SIM mirror could not be read; nothing was changed.")
        : g_strdup_printf("Sync complete: %zu message(s) from the SIM, %zu local message(s) "
                          "added to the mirror, %zu contact(s) imported. Additive only — "
                          "nothing was deleted and the SIM itself was not written.",
                          from_sim, to_sim, contacts);
    build_model(app);
    render_conversations(app);
    render_all_messages(app);
    refresh_thread_if_open(app);
    messages_refresh_banner(app);
}

static void
load_conversations(NuxelMessages *app)
{
    messages_reset_conversations(app);
    if (app->store_path) {
        nuxel_phone_store_free(&app->store);
        nuxel_phone_store_init(&app->store);
        nuxel_phone_store_load(&app->store, app->store_path);
    }
    render_conversations(app);
}

/* ============================================================
 * Model → UI
 * ============================================================ */

static void messages_sort_thread(GPtrArray *msgs);

static void
build_model(NuxelMessages *app)
{
    messages_reset_conversations(app);
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
            if (keybuf[0]) {
                Conversation *conv = find_or_create_conversation(app, keybuf);
                gint64 at = created && *created ? g_ascii_strtoll(created, NULL, 10) : 0;
                Message *msg = message_new_at(message_time_label(stamp, created), incoming,
                                              id, state_label(state), at);
                msg->preview = g_strdup(body && *body ? body : state_label(state));
                g_ptr_array_add(conv->messages, msg);
                conv->last_message = msg;
            }
            g_free(peer); g_free(body); g_free(state); g_free(dir); g_free(stamp); g_free(created);
        }
    }
    /* SIM-mirror rows that are not already in the native snapshot. */
    if (app->sim_store.n_messages) {
        size_t added = 0;
        messages_merge_store(app, &app->sim_store, &added);
    }
    for (guint c = 0; c < app->conversations->len; c++) {
        Conversation *conv = g_ptr_array_index(app->conversations, c);
        messages_sort_thread(conv->messages);
        if (conv->messages->len)
            conv->last_message = g_ptr_array_index(conv->messages, conv->messages->len - 1);
        if (messages_trace_enabled())
            g_message("[Messages] thread %s resolved name=%s contacts=%zu",
                      conv->number, conversation_title(app, conv), app->store.n_contacts);
    }
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

/* ============================================================
 * Rendering
 * ============================================================ */

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
create_avatar(const gchar *name, gboolean incoming)
{
    gchar *initial = name && *name ? g_utf8_substring(name, 0, 1) : g_strdup("?");
    GtkWidget *avatar = gtk_label_new(initial);
    g_free(initial);
    gtk_widget_add_css_class(avatar, "nuxel-avatar");
    if (incoming) gtk_widget_add_css_class(avatar, "nuxel-avatar-in");
    gtk_widget_set_valign(avatar, GTK_ALIGN_CENTER);
    return avatar;
}

static const gchar *
conversation_title(NuxelMessages *app, Conversation *conv)
{
    const gchar *name = nuxel_phone_contact_name(&app->store, conv->number);
    if (name && *name) return name;
    if (conv->name && *conv->name && g_strcmp0(conv->name, conv->number) != 0) return conv->name;
    return conv->number && *conv->number ? conv->number : "Unknown";
}

static gchar *
conversation_preview(NuxelMessages *app, Conversation *conv)
{
    if (!conv->last_message) return g_strdup("");
    const gchar *pv = conv->last_message->preview;
    if (pv) return g_strdup(*pv ? pv : "(no text)");
    if (conv->last_message->native_id) {
        gchar *body = NULL;
        if (native_lookup(app, conv->last_message->native_id, &body, NULL)) {
            gchar *out = g_strdup(body && *body ? body : "(no text)");
            g_free(body);
            return out;
        }
    }
    return g_strdup("(no text)");
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
        const gchar *title = conversation_title(app, conv);
        GtkWidget *row = gtk_list_box_row_new();
        GtkWidget *card = gtk_box_new(GTK_ORIENTATION_HORIZONTAL, 12);
        gtk_widget_add_css_class(card, "nuxel-row");
        gtk_box_append(GTK_BOX(card), create_avatar(title,
            conv->last_message ? conv->last_message->incoming : FALSE));
        GtkWidget *text_box = gtk_box_new(GTK_ORIENTATION_VERTICAL, 3);
        gtk_widget_set_hexpand(text_box, TRUE);
        GtkWidget *name_label = gtk_label_new(title);
        gtk_widget_add_css_class(name_label, "nuxel-row-title");
        gtk_label_set_xalign(GTK_LABEL(name_label), 0.0);
        gtk_label_set_ellipsize(GTK_LABEL(name_label), PANGO_ELLIPSIZE_END);
        gtk_box_append(GTK_BOX(text_box), name_label);
        if (g_strcmp0(title, conv->number) != 0) {
            GtkWidget *num = gtk_label_new(conv->number);
            gtk_widget_add_css_class(num, "dim");
            gtk_label_set_xalign(GTK_LABEL(num), 0.0);
            gtk_box_append(GTK_BOX(text_box), num);
        }
        if (conv->last_message) {
            gchar *pv = conversation_preview(app, conv);
            GtkWidget *preview = gtk_label_new(pv);
            g_free(pv);
            gtk_label_set_xalign(GTK_LABEL(preview), 0.0);
            gtk_label_set_ellipsize(GTK_LABEL(preview), PANGO_ELLIPSIZE_END);
            gtk_widget_add_css_class(preview, "dim");
            gtk_box_append(GTK_BOX(text_box), preview);
        }
        gtk_box_append(GTK_BOX(card), text_box);
        if (conv->last_message && conv->last_message->timestamp) {
            GtkWidget *ts = gtk_label_new(conv->last_message->timestamp);
            gtk_widget_add_css_class(ts, "dim");
            gtk_widget_set_valign(ts, GTK_ALIGN_START);
            gtk_box_append(GTK_BOX(card), ts);
        }
        gtk_list_box_row_set_child(GTK_LIST_BOX_ROW(row), card);
        g_object_set_data(G_OBJECT(row), "conversation", conv);
        gtk_list_box_append(GTK_LIST_BOX(list), row);
    }
    if (app->list_empty)
        gtk_widget_set_visible(app->list_empty, ordered->len == 0);
    g_ptr_array_unref(ordered);
}

/* Builds the complete logical-message list and returns it.  All rows are real
 * stored logical messages (native ids, plus SIM-mirror rows), oldest→newest;
 * the list is used directly by the All messages tab and shown inside the
 * conversation screen under the newest messages. */
static GtkWidget *
render_all_messages(NuxelMessages *app)
{
    GtkWidget *list = app->all_messages_list;
    if (!list) return NULL;
    GtkWidget *child = gtk_widget_get_first_child(list);
    while (child) {
        GtkWidget *next = gtk_widget_get_next_sibling(child);
        gtk_list_box_remove(GTK_LIST_BOX(list), child);
        child = next;
    }
    /* Assemble every logical row (native + SIM mirror) in one chronological
     * list; each native id appears exactly once. */
    GPtrArray *rows = g_ptr_array_new();   /* of Message, borrowed from convs */
    for (guint c = 0; c < app->conversations->len; c++) {
        Conversation *conv = g_ptr_array_index(app->conversations, c);
        for (guint j = 0; j < conv->messages->len; j++)
            g_ptr_array_add(rows, g_ptr_array_index(conv->messages, j));
    }
    for (guint i = 1; i < rows->len; i++) {
        Message *key = g_ptr_array_index(rows, i);
        guint j = i;
        while (j > 0 && message_cmp(key, g_ptr_array_index(rows, j - 1)) < 0) {
            rows->pdata[j] = rows->pdata[j - 1];
            j--;
        }
        rows->pdata[j] = key;
    }
    guint shown = 0;
    for (guint i = 0; i < rows->len; i++) {
        Message *msg = g_ptr_array_index(rows, i);
        gchar *peer = NULL;
        if (msg->native_id) {
            if (!app->native) continue;
            GVariant *dict = g_hash_table_lookup(app->native, GUINT_TO_POINTER(msg->native_id));
            if (!dict) continue;
            peer = variant_str(dict, "peer");
        } else {
            continue;
        }
        char keybuf[NUXEL_NUMBER_MAX]; canonical_peer(keybuf, sizeof keybuf, peer);
        if (!keybuf[0]) { g_free(peer); continue; }
        const gchar *cname = nuxel_phone_contact_name(&app->store, keybuf);
        const gchar *shown_name = cname && *cname ? cname : keybuf;

        GtkWidget *row = gtk_list_box_row_new();
        GtkWidget *card = gtk_box_new(GTK_ORIENTATION_VERTICAL, 4);
        gtk_widget_add_css_class(card, "nuxel-row");
        GtkWidget *top = gtk_box_new(GTK_ORIENTATION_HORIZONTAL, 8);
        gchar *who = g_strdup_printf("%s  %s  #%u", msg->incoming ? "↓" : "↑", shown_name, msg->native_id);
        GtkWidget *who_label = gtk_label_new(who);
        g_free(who);
        gtk_widget_add_css_class(who_label, "nuxel-row-title");
        gtk_label_set_xalign(GTK_LABEL(who_label), 0.0);
        gtk_widget_set_hexpand(who_label, TRUE);
        gtk_label_set_ellipsize(GTK_LABEL(who_label), PANGO_ELLIPSIZE_END);
        gtk_box_append(GTK_BOX(top), who_label);
        if (msg->timestamp) {
            GtkWidget *ts = gtk_label_new(msg->timestamp);
            gtk_widget_add_css_class(ts, "dim");
            gtk_box_append(GTK_BOX(top), ts);
        }
        gtk_box_append(GTK_BOX(card), top);
        gchar *body = NULL;
        if (!native_lookup(app, msg->native_id, &body, NULL)) body = g_strdup("");
        GtkWidget *body_label = gtk_label_new(body && *body ? body : "(no text)");
        g_free(body);
        gtk_label_set_wrap(GTK_LABEL(body_label), TRUE);
        gtk_label_set_xalign(GTK_LABEL(body_label), 0.0);
        gtk_widget_add_css_class(body_label, "nuxel-row-body");
        gtk_box_append(GTK_BOX(card), body_label);
        gchar *meta = g_strdup_printf("%s · %s", msg->incoming ? "incoming" : "outgoing",
                                      state_label(msg->state));
        GtkWidget *state_w = gtk_label_new(meta);
        g_free(meta);
        gtk_widget_add_css_class(state_w, "dim");
        gtk_label_set_xalign(GTK_LABEL(state_w), 0.0);
        gtk_box_append(GTK_BOX(card), state_w);
        gtk_list_box_row_set_child(GTK_LIST_BOX_ROW(row), card);
        g_object_set_data(G_OBJECT(row), "conversation", NULL);
        gtk_list_box_append(GTK_LIST_BOX(list), row);
        g_free(peer);
        shown++;
    }
    g_ptr_array_unref(rows);
    if (app->all_empty) gtk_widget_set_visible(app->all_empty, shown == 0);
    return list;
}

/* The "All messages" list is reparented (one widget, two placements) rather
 * than duplicated: the All messages tab owns it until a conversation is
 * opened, and the conversation screen shows the same list. */
static void
place_all_messages(NuxelMessages *app, gboolean in_thread)
{
    GtkWidget *list = render_all_messages(app);
    if (!list) return;
    GtkWidget *wrapper_thread = g_object_get_data(G_OBJECT(app->list_page), "all_thread_slot");
    GtkWidget *wrapper_tab = g_object_get_data(G_OBJECT(app->list_page), "all_tab_slot");
    if (!wrapper_thread || !wrapper_tab) return;
    GtkWidget *parent = gtk_widget_get_parent(list);
    GtkWidget *target = in_thread ? wrapper_thread : wrapper_tab;
    if (parent == target) return;
    /* Setting the child on the other scroller re-parents the list inside the
     * toolkit; no widget is created or destroyed here. */
    if (parent) gtk_scrolled_window_set_child(GTK_SCROLLED_WINDOW(parent), NULL);
    gtk_scrolled_window_set_child(GTK_SCROLLED_WINDOW(target), list);
    if (app->all_empty) {
        GtkWidget *parent_box = gtk_widget_get_parent(target);
        if (parent_box) gtk_widget_set_visible(app->all_empty, FALSE);
    }
}

static GtkWidget *
create_message_widget(NuxelMessages *app, Message *msg, const gchar *body)
{
    (void)app;
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
    const char *st = state_label(msg->state);
    gchar *status_text;
    if (msg->timestamp && *msg->timestamp)
        status_text = *st ? g_strdup_printf("%s · %s", msg->timestamp, st) : g_strdup(msg->timestamp);
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
open_conversation(NuxelMessages *app, Conversation *conv)
{
    app->active_conversation = conv;
    gtk_label_set_text(GTK_LABEL(app->thread_header), conversation_title(app, conv));
    if (app->thread_subtitle) {
        const gchar *title = conversation_title(app, conv);
        gchar *sub = g_strcmp0(title, conv->number) == 0
            ? g_strdup_printf("%u message(s)", conv->messages->len)
            : g_strdup_printf("%s · %u message(s)", conv->number, conv->messages->len);
        gtk_label_set_text(GTK_LABEL(app->thread_subtitle), sub);
        g_free(sub);
    }
    place_all_messages(app, TRUE);
    gtk_stack_set_visible_child_name(GTK_STACK(app->stack), "thread");
    gtk_widget_set_visible(app->recipient_entry, FALSE);
    if (app->contact_entry) gtk_widget_set_visible(app->contact_entry, FALSE);
    refresh_thread_if_open(app);
    gtk_widget_grab_focus(app->message_entry);
}

static void
refresh_thread_if_open(NuxelMessages *app)
{
    Conversation *conv = app->active_conversation;
    if (!conv || !app->message_container) return;
    if (!app->refreshing) {
        gtk_label_set_text(GTK_LABEL(app->thread_header), conversation_title(app, conv));
        if (app->thread_subtitle)
            gtk_label_set_text(GTK_LABEL(app->thread_subtitle), conv->number);
    }
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
            w = create_message_widget(app, msg, body);
            g_free(body);
        } else {
            w = create_message_widget(app, msg, msg->mirror_body ? msg->mirror_body : "(mirror)");
        }
        gtk_box_append(GTK_BOX(app->message_container), w);
    }
    if (GTK_IS_SCROLLED_WINDOW(app->message_scroll)) {
        GtkAdjustment *adj = gtk_scrolled_window_get_vadjustment(GTK_SCROLLED_WINDOW(app->message_scroll));
        gtk_adjustment_set_value(adj, gtk_adjustment_get_upper(adj) - gtk_adjustment_get_page_size(adj));
    }
}

/* ============================================================
 * Core logic
 * ============================================================ */

/* Typing a bare number into the recipient field is validated before send:
 * digits/leading '+'/separators only, at least three digits. */
static gboolean
recipient_is_valid(const gchar *peer)
{
    if (!peer) return FALSE;
    char norm[NUXEL_NUMBER_MAX];
    if (nuxel_phone_normalize_number(norm, sizeof norm, peer) != 0) return FALSE;
    size_t digits = 0;
    for (const gchar *p = norm; *p; p++) {
        if (g_ascii_isdigit(*p)) digits++;
        else if (*p != '+') return FALSE;
    }
    return digits >= 3;
}

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
    g_free(app->status_detail);
    app->status_detail = NULL;
    if (!normalized || !recipient_is_valid(normalized)) {
        g_free(normalized);
        app->status_detail = g_strdup("Enter a valid recipient number (digits, optional leading +). Nothing was sent.");
        messages_refresh_banner(app);
        return;
    }
    if (app->sending) {
        g_free(normalized);
        app->status_detail = g_strdup("A message is already being submitted; this one was not sent.");
        messages_refresh_banner(app);
        return;
    }
    if (!app->modem_ready || !nuxel_radio_available(&app->radio)) {
        g_free(normalized);
        app->status_detail = g_strdup("The SMS transport is not ready; nothing was sent.");
        messages_refresh_banner(app);
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
    if (signal && g_str_has_prefix(signal, "SmsReceived")) sms_received_hint(signal, app);
    else native_refresh(app);
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
    if (app->contact_entry) gtk_widget_set_visible(app->contact_entry, FALSE);
    if (app->contact_popover) gtk_popover_popdown(GTK_POPOVER(app->contact_popover));
    place_all_messages(app, FALSE);
    render_conversations(app);
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
    if (app->contact_entry) {
        gtk_editable_set_text(GTK_EDITABLE(app->contact_entry), "");
        gtk_widget_set_visible(app->contact_entry, TRUE);
    }
    gtk_stack_set_visible_child_name(GTK_STACK(app->stack), "thread");
    gtk_widget_grab_focus(app->recipient_entry);
}

static void
on_stack_page_changed(GtkStack *stack, GParamSpec *pspec, gpointer user_data)
{
    (void)pspec;
    NuxelMessages *app = user_data;
    if (g_strcmp0(gtk_stack_get_visible_child_name(stack), "list") == 0) {
        gtk_widget_set_visible(app->recipient_entry, FALSE);
        if (app->contact_entry) gtk_widget_set_visible(app->contact_entry, FALSE);
        if (app->contact_popover) gtk_popover_popdown(GTK_POPOVER(app->contact_popover));
    }
}

static void
on_contact_row_picked(GtkListBox *box, GtkListBoxRow *row, gpointer user_data)
{
    (void)box;
    NuxelMessages *app = user_data;
    const gchar *number = g_object_get_data(G_OBJECT(row), "number");
    if (!number || !app->recipient_entry) return;
    gtk_editable_set_text(GTK_EDITABLE(app->recipient_entry), number);
    gtk_widget_set_visible(app->recipient_entry, TRUE);
    if (app->contact_popover) gtk_popover_popdown(GTK_POPOVER(app->contact_popover));
    if (app->contact_entry) gtk_editable_set_text(GTK_EDITABLE(app->contact_entry), "");
    gtk_widget_grab_focus(app->message_entry);
}

static void
on_contact_search_changed(GtkEditable *editable, gpointer user_data)
{
    NuxelMessages *app = user_data;
    if (!app->contact_popover || !app->contact_entry) return;
    const gchar *query = gtk_editable_get_text(editable);
    GtkWidget *list = g_object_get_data(G_OBJECT(app->contact_popover), "list");
    if (!list) return;
    GtkWidget *child = gtk_widget_get_first_child(list);
    while (child) {
        GtkWidget *next = gtk_widget_get_next_sibling(child);
        gtk_list_box_remove(GTK_LIST_BOX(list), child);
        child = next;
    }
    if (!query || !*query) {
        gtk_popover_popdown(GTK_POPOVER(app->contact_popover));
        return;
    }
    NuxelContact *hits[8];
    size_t n = nuxel_phone_search_contacts(&app->store, query, hits, G_N_ELEMENTS(hits));
    for (size_t i = 0; i < n && i < G_N_ELEMENTS(hits); i++) {
        NuxelContact *ct = hits[i];
        if (!ct->phone[0]) continue;
        char ignore[NUXEL_NUMBER_MAX];
        if (nuxel_phone_normalize_number(ignore, sizeof ignore, ct->phone) != 0) continue;
        GtkWidget *row = gtk_list_box_row_new();
        GtkWidget *box = gtk_box_new(GTK_ORIENTATION_VERTICAL, 2);
        gtk_widget_set_margin_start(box, 12);
        gtk_widget_set_margin_end(box, 12);
        gtk_widget_set_margin_top(box, 8);
        gtk_widget_set_margin_bottom(box, 8);
        GtkWidget *nm = gtk_label_new(ct->name);
        gtk_widget_add_css_class(nm, "nuxel-row-title");
        gtk_label_set_xalign(GTK_LABEL(nm), 0.0);
        GtkWidget *ph = gtk_label_new(ct->phone);
        gtk_widget_add_css_class(ph, "dim");
        gtk_label_set_xalign(GTK_LABEL(ph), 0.0);
        gtk_box_append(GTK_BOX(box), nm);
        gtk_box_append(GTK_BOX(box), ph);
        gtk_list_box_row_set_child(GTK_LIST_BOX_ROW(row), box);
        g_object_set_data_full(G_OBJECT(row), "number", g_strdup(ct->phone), g_free);
        gtk_list_box_append(GTK_LIST_BOX(list), row);
    }
    if (gtk_widget_get_first_child(list))
        gtk_popover_popup(GTK_POPOVER(app->contact_popover));
    else
        gtk_popover_popdown(GTK_POPOVER(app->contact_popover));
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
 * UI construction
 * ============================================================ */

static const char *MESSAGES_CSS =
    "window, .nuxel-root, .nuxel-page { background: #0a1628; background-color: #0a1628; }"
    ".nuxel-head { padding: 14px 16px 10px; border-bottom: 1px solid rgba(255,255,255,0.08); }"
    ".nuxel-title { font-size: 19px; font-weight: 700; color: #e6f0ff; }"
    ".nuxel-tabs { padding: 10px 12px 10px 12px; }"
    ".nuxel-panel { background: #12233c; border-radius: 14px; margin: 0 12px 12px 12px; padding: 4px; }"
    ".nuxel-row { background: #12233c; border-radius: 14px; padding: 12px; margin: 4px 8px; }"
    ".nuxel-row-title { font-weight: 700; font-size: 15px; color: #e6f0ff; }"
    ".nuxel-row-body { font-size: 14px; color: #e6f0ff; }"
    ".dim { color: #8aa3c7; font-size: 12px; }"
    ".nuxel-avatar { background: rgba(62,166,255,0.18); color: #3ea6ff; border-radius: 18px;"
    "  min-width: 36px; min-height: 36px; font-weight: 700; }"
    ".nuxel-avatar-in { background: rgba(70,209,140,0.16); color: #46d18c; }"
    ".nuxel-badge { background: #3ea6ff; color: #06121f; border-radius: 10px; padding: 1px 7px;"
    "  font-size: 11px; font-weight: 700; }"
    "scrolledwindow, scrolledwindow > viewport, scrolledwindow undershoot,"
    "  .nuxel-list-scroll { background: #0a1628; }"
    ".nuxel-empty { padding: 24px; }"
    ".nuxel-empty-title { font-size: 16px; font-weight: 700; color: #e6f0ff; }"
    ".incoming-bubble { background: #12233c; border-radius: 14px 14px 14px 4px;"
    "  color: #e6f0ff; padding: 9px 12px; margin: 3px 44px 3px 10px; }"
    ".outgoing-bubble { background: rgba(62,166,255,0.22); border-radius: 14px 14px 4px 14px;"
    "  color: #e6f0ff; padding: 9px 12px; margin: 3px 10px 3px 44px; }"
    ".nuxel-composer { background: #12233c; border-radius: 14px; margin: 6px 12px 12px 12px; padding: 8px; }"
    ".nuxel-composer entry { background: #0a1628; color: #e6f0ff; border-radius: 10px; min-height: 40px; }"
    ".nuxel-composer button { min-height: 40px; }"
    "listbox { background: transparent; }"
    "listbox row { background: transparent; }"
    "listbox row:selected { background: transparent; }"
    "popover > contents { background: #12233c; border-radius: 12px; }";

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
    /* The Nuxel reference apps paint their own opaque navy ground.  libadwaita
     * gives the window a default (near-black) background, and a page box only
     * paints behind its children, so set the page's own background too. */
    gtk_widget_set_hexpand(page, TRUE);
    gtk_widget_set_vexpand(page, TRUE);
    return page;
}

static GtkWidget *
build_list_page(NuxelMessages *app)
{
    GtkWidget *page = nuxel_page("Messages");
    GtkWidget *head = gtk_widget_get_first_child(page);
    GtkWidget *import_sim = gtk_button_new_with_label("Import SIM");
    gtk_widget_add_css_class(import_sim, "flat");
    gtk_widget_set_tooltip_text(import_sim,
        "Copy messages and contact names from the SIM mirror (nothing is deleted)");
    g_signal_connect(import_sim, "clicked", G_CALLBACK(on_import_sim_clicked), app);
    gtk_box_append(GTK_BOX(head), import_sim);
    GtkWidget *sync_sim = gtk_button_new_with_label("Sync");
    gtk_widget_add_css_class(sync_sim, "flat");
    gtk_widget_set_tooltip_text(sync_sim,
        "Re-sync: import new SIM messages and contacts, copy local messages to the mirror");
    g_signal_connect(sync_sim, "clicked", G_CALLBACK(on_sync_sim_clicked), app);
    gtk_box_append(GTK_BOX(head), sync_sim);
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

    GtkWidget *conv_box = gtk_box_new(GTK_ORIENTATION_VERTICAL, 0);
    app->conversation_list = gtk_list_box_new();
    gtk_list_box_set_selection_mode(GTK_LIST_BOX(app->conversation_list), GTK_SELECTION_NONE);
    g_signal_connect(app->conversation_list, "row-activated",
                     G_CALLBACK(on_conversation_row_activated), app);
    GtkWidget *conv_scroll = gtk_scrolled_window_new();
    gtk_widget_add_css_class(conv_scroll, "nuxel-list-scroll");
    gtk_scrolled_window_set_policy(GTK_SCROLLED_WINDOW(conv_scroll), GTK_POLICY_NEVER, GTK_POLICY_AUTOMATIC);
    gtk_scrolled_window_set_child(GTK_SCROLLED_WINDOW(conv_scroll), app->conversation_list);
    gtk_widget_set_vexpand(conv_scroll, TRUE);
    gtk_box_append(GTK_BOX(conv_box), conv_scroll);
    app->list_empty = create_empty_state("No messages yet",
        "Received and sent SMS appear here. Use Import SIM to bring across stored SIM messages, or New to write one.");
    gtk_box_append(GTK_BOX(conv_box), app->list_empty);
    gtk_stack_add_named(GTK_STACK(inner_stack), conv_box, "conversations");

    GtkWidget *all_box = gtk_box_new(GTK_ORIENTATION_VERTICAL, 0);
    app->all_messages_list = gtk_list_box_new();
    gtk_list_box_set_selection_mode(GTK_LIST_BOX(app->all_messages_list), GTK_SELECTION_NONE);
    GtkWidget *all_scroll = gtk_scrolled_window_new();
    gtk_widget_add_css_class(all_scroll, "nuxel-list-scroll");
    gtk_scrolled_window_set_policy(GTK_SCROLLED_WINDOW(all_scroll), GTK_POLICY_NEVER, GTK_POLICY_AUTOMATIC);
    gtk_scrolled_window_set_child(GTK_SCROLLED_WINDOW(all_scroll), app->all_messages_list);
    gtk_widget_set_vexpand(all_scroll, TRUE);
    g_object_set_data(G_OBJECT(page), "all_tab_slot", all_scroll);
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
    /* Complete history: the same All messages list, scrolled independently
     * under the newest exchange, so every stored logical SMS is reachable
     * inside the conversation as well as from the All messages tab. */
    {
        GtkWidget *all_head = gtk_label_new("All stored messages");
        gtk_widget_add_css_class(all_head, "dim");
        gtk_widget_set_margin_start(all_head, 14);
        gtk_widget_set_margin_top(all_head, 6);
        gtk_box_append(GTK_BOX(page), all_head);
        GtkWidget *all_slot = gtk_scrolled_window_new();
        gtk_widget_add_css_class(all_slot, "nuxel-list-scroll");
        gtk_scrolled_window_set_policy(GTK_SCROLLED_WINDOW(all_slot), GTK_POLICY_NEVER, GTK_POLICY_AUTOMATIC);
        gtk_widget_set_size_request(all_slot, -1, 230);
        g_object_set_data(G_OBJECT(app->list_page), "all_thread_slot", all_slot);
        gtk_box_append(GTK_BOX(page), all_slot);
    }

    GtkWidget *compose_box = gtk_box_new(GTK_ORIENTATION_VERTICAL, 6);
    gtk_widget_add_css_class(compose_box, "nuxel-composer");
    app->recipient_entry = gtk_entry_new();
    gtk_entry_set_placeholder_text(GTK_ENTRY(app->recipient_entry),
                                   "Recipient number (e.g. +31612345678)");
    gtk_entry_set_input_purpose(GTK_ENTRY(app->recipient_entry), GTK_INPUT_PURPOSE_PHONE);
    gtk_widget_set_visible(app->recipient_entry, FALSE);
    gtk_box_append(GTK_BOX(compose_box), app->recipient_entry);
    app->contact_entry = gtk_entry_new();
    gtk_entry_set_placeholder_text(GTK_ENTRY(app->contact_entry), "Contact name or number");
    gtk_widget_set_visible(app->contact_entry, FALSE);
    gtk_box_append(GTK_BOX(compose_box), app->contact_entry);
    {
        app->contact_popover = gtk_popover_new();
        GtkWidget *pick_list = gtk_list_box_new();
        gtk_list_box_set_selection_mode(GTK_LIST_BOX(pick_list), GTK_SELECTION_NONE);
        g_object_set_data(G_OBJECT(app->contact_popover), "list", pick_list);
        gtk_popover_set_child(GTK_POPOVER(app->contact_popover), pick_list);
        gtk_widget_set_parent(GTK_WIDGET(app->contact_popover), compose_box);
        g_signal_connect(app->contact_entry, "changed", G_CALLBACK(on_contact_search_changed), app);
        g_signal_connect(pick_list, "row-activated", G_CALLBACK(on_contact_row_picked), app);
    }
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
modem_connect(NuxelMessages *app)
{
    gtk_widget_set_sensitive(app->send_button, FALSE);
    nuxel_radio_connect(&app->radio, "org.nuxel.Messages", native_changed, app);
    app->poll_source = g_timeout_add_seconds(20, messages_poll_tick, app);
    native_refresh(app);
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
        app->sim_contact_path = g_build_filename(dir, "sim-contacts.json", NULL);
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

    gtk_widget_add_css_class(app->stack, "nuxel-root");
    adw_application_window_set_content(ADW_APPLICATION_WINDOW(app->window), app->stack);

    /* The shared address book is the name source for every thread; the SIM
     * phonebook mirror is merged in (additive) before the first render. */
    load_conversations(app);
    messages_sync_contacts(app, NULL);
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
