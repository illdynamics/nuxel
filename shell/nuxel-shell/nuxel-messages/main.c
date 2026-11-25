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
#include "nuxel-radio-client.h"

/* ============================================================
 * Data structures
 * ============================================================ */

typedef struct {
    gchar   *number;
    gchar   *text;
    gchar   *timestamp;
    gboolean incoming;
    guint native_id;
    gchar *state;
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
    
    NuxelRadioClient radio;
    GArray *native_ids;
    guint native_index;
    gboolean refreshing, refresh_again, sending;

    /* Data */
    GPtrArray *conversations;    /* Array of Conversation */
    Conversation *active_conversation;

    /* Shared phone data: threads are persisted through the same store the
     * dialer and contacts use, so a restart does not lose the message history. */
    NuxelPhoneStore store;
    NuxelPhoneCapabilities caps;
    gchar *store_path;
    GtkWidget *capability_label;

    /* SIM message mirror.  There is no ModemManager SIM SMS API on this
     * target, so this is explicit local storage that can be imported/synced
     * on demand and copied to a real SIM when the modem path exists. */
    NuxelPhoneStore sim_store;
    gchar *sim_path;
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
static void messages_import_sim(NuxelMessages *app, gboolean merge_only);

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
        g_free(msg->state);
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

/* Native IDs and status stay authoritative in Radio1's durable SQLite store.
 * They are rendered here, never copied into a second outgoing queue. */
static void native_refresh(gpointer user);
static void native_next(NuxelMessages *app);
static void native_message(GVariant *reply,const GError *error,gpointer user)
{
    NuxelMessages *app=user;
    guint id=g_array_index(app->native_ids,guint,app->native_index-1);
    if(reply && !error) {
        GVariant *dict=g_variant_get_child_value(reply,0);
        const char *peer="",*body="",*state="unknown",*direction="",*stamp="";
        g_variant_lookup(dict,"peer","&s",&peer);g_variant_lookup(dict,"text","&s",&body);
        g_variant_lookup(dict,"state","&s",&state);g_variant_lookup(dict,"direction","&s",&direction);
        g_variant_lookup(dict,"timestamp","&s",&stamp);
        Conversation *conv=find_or_create_conversation(app,peer);
        Message *msg=NULL;
        for(guint i=0;i<conv->messages->len;i++) {
            Message *candidate=g_ptr_array_index(conv->messages,i);
            if(candidate->native_id==id) { msg=candidate;break; }
        }
        if(!msg) {
            msg=message_new(peer,body,!strcmp(direction,"in"));msg->native_id=id;
            g_ptr_array_add(conv->messages,msg);
        }
        g_free(msg->text);
        msg->text = g_strdup(body);

        g_free(msg->state);
        msg->state = g_strdup(state);

        g_free(msg->timestamp);
        msg->timestamp = g_strdup(stamp);
        conv->last_message=msg;
        g_variant_unref(dict);
    } else if(error) gtk_label_set_text(GTK_LABEL(app->capability_label),error->message);
    native_next(app);
}
static void native_next(NuxelMessages *app)
{
    if(app->native_index<app->native_ids->len) {
        guint id=g_array_index(app->native_ids,guint,app->native_index++);
        nuxel_radio_call(&app->radio,"GetSms",g_variant_new("(u)",id),"sms:receive",native_message,app);
        return;
    }
    app->refreshing=FALSE;g_clear_pointer(&app->native_ids,g_array_unref);
    render_conversations(app);
    if(app->active_conversation)open_conversation(app,app->active_conversation);
    if(app->refresh_again) { app->refresh_again=FALSE;native_refresh(app); }
}
static void native_list(GVariant *reply,const GError *error,gpointer user)
{
    NuxelMessages *app=user;
    if(!reply || error) {
        app->refreshing=FALSE;
        gtk_label_set_text(GTK_LABEL(app->capability_label),error ? error->message : "Inbox unavailable");return;
    }
    GVariant *ids=g_variant_get_child_value(reply,0);
    app->native_ids=g_array_new(FALSE,FALSE,sizeof(guint));app->native_index=0;
    GVariantIter iter;guint id;g_variant_iter_init(&iter,ids);
    while(g_variant_iter_next(&iter,"u",&id))g_array_append_val(app->native_ids,id);
    g_variant_unref(ids);native_next(app);
}
static void native_status(GVariant *reply,const GError *error,gpointer user)
{
    NuxelMessages *app=user;
    if(!reply || error) {
        app->refreshing=FALSE;app->modem_ready=FALSE;
        gtk_label_set_text(GTK_LABEL(app->capability_label),"Native SMS unavailable");return;
    }
    GVariant *dict=g_variant_get_child_value(reply,0);
    const char *storage="unknown",*ready="unknown",*domain="unknown",*smsc="unknown";
    const char *pending="unknown",*blocked="unknown";
    g_variant_lookup(dict,"storage","&s",&storage);g_variant_lookup(dict,"device_ready","&s",&ready);
    g_variant_lookup(dict,"domain","&s",&domain);g_variant_lookup(dict,"smsc","&s",&smsc);
    g_variant_lookup(dict,"pending","&s",&pending);g_variant_lookup(dict,"blocked","&s",&blocked);
    /* Send readiness needs the whole transport, not just device-ready. */
    const gchar *reason="ready to send";
    gboolean storage_ok=!strcmp(storage,"available");
    gboolean ready_ok=!strcmp(ready,"accepted");
    gboolean smsc_ok=!strcmp(smsc,"received");
    gboolean pending_busy=!strcmp(pending,"true");
    gboolean blocked_unresolved=!strcmp(blocked,"true");
    app->modem_ready=storage_ok && ready_ok && smsc_ok && !pending_busy && !blocked_unresolved;
    if(!storage_ok) reason="storage unavailable";
    else if(!ready_ok) reason="device not ready";
    else if(!smsc_ok) reason="service center unavailable";
    else if(pending_busy) reason="a submission is in progress";
    else if(blocked_unresolved) reason="an unresolved submission must be reviewed first";
    gchar *label=g_strdup_printf("Native SMS · %s · storage %s · transport %s · SMSC %s · %s. Submission is not delivery.",
                                 domain,storage,ready,smsc,reason);
    gtk_label_set_text(GTK_LABEL(app->capability_label),label);g_free(label);g_variant_unref(dict);
    gtk_widget_set_sensitive(app->send_button,app->modem_ready && !app->sending);
    nuxel_radio_call(&app->radio,"ListSms",NULL,"sms:receive",native_list,app);
}
static void native_refresh(gpointer user)
{
    NuxelMessages *app=user;
    if(app->refreshing) { app->refresh_again=TRUE;return; }
    app->refreshing=TRUE;
    nuxel_radio_call(&app->radio,"GetSmsStatus",NULL,NULL,native_status,app);
}
static void native_sent(GVariant *reply,const GError *error,gpointer user)
{
    NuxelMessages *app=user;
    if(!reply || error) {
        /* A lost reply might follow a durable queue insertion. Do not retry. */
        gboolean denied=error && g_error_matches(error,G_IO_ERROR,G_IO_ERROR_PERMISSION_DENIED);
        app->sending=!denied;
        gtk_widget_set_sensitive(app->send_button,denied);
        gtk_label_set_text(GTK_LABEL(app->capability_label),denied ? error->message :
            "Submission outcome uncertain or rejected. Check the native outbox before another attempt.");
        return;
    }
    app->sending=FALSE;gtk_editable_set_text(GTK_EDITABLE(app->message_entry),"");
    native_refresh(app);
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
    
    if(app->sending || !nuxel_radio_available(&app->radio))return;
    app->sending=TRUE;gtk_widget_set_sensitive(app->send_button,FALSE);
    nuxel_radio_call(&app->radio,"SendSms",g_variant_new("(ss)",number,text),
                     "sms:send",native_sent,app);
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
    gtk_widget_set_margin_start(bubble, 8);
    gtk_widget_set_margin_end(bubble, 8);
    gtk_widget_set_margin_top(bubble, 8);
    gtk_widget_set_margin_bottom(bubble, 8);
    gtk_box_append(GTK_BOX(bubble), text);
    
    gchar *status_text=g_strdup_printf("%s · %s",msg->timestamp,msg->state ? msg->state : "local history");
    GtkWidget *time = gtk_label_new(status_text);
    g_free(status_text);
    gtk_widget_add_css_class(time, "caption");
    gtk_label_set_xalign(GTK_LABEL(time), 1.0);
    gtk_widget_set_margin_start(bubble, 8);
    gtk_widget_set_margin_end(bubble, 8);
    gtk_widget_set_margin_top(bubble, 8);
    gtk_widget_set_margin_bottom(bubble, 8);
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

    /* Preserve contacts and call history written by the other phone apps. */
    nuxel_phone_store_free(&app->store);
    nuxel_phone_store_init(&app->store);
    if(nuxel_phone_store_load(&app->store,app->store_path)<0)return;
    free(app->store.messages);app->store.messages=NULL;app->store.n_messages=0;app->store.cap_messages=0;

    for (guint i = 0; i < app->conversations->len; i++) {
        Conversation *conv = g_ptr_array_index(app->conversations, i);
        for (guint j = 0; j < conv->messages->len; j++) {
            Message *m = g_ptr_array_index(conv->messages, j);
            if(m->native_id)continue;
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

static void
messages_merge_store(NuxelMessages *app, NuxelPhoneStore *store, size_t *added)
{
    for (size_t i = 0; i < store->n_messages; i++) {
        NuxelMessage *stored = &store->messages[i];
        Conversation *conv = find_or_create_conversation(app, stored->peer);
        gboolean duplicate = FALSE;
        for (guint m = 0; m < conv->messages->len; m++) {
            Message *have = g_ptr_array_index(conv->messages, m);
            if (g_strcmp0(have->text, stored->body) == 0) {
                duplicate = TRUE;
                break;
            }
        }
        if (duplicate) continue;
        Message *msg = message_new(stored->peer, stored->body,
                                   g_strcmp0(stored->direction, "in") == 0);
        g_ptr_array_add(conv->messages, msg);
        conv->last_message = msg;
        (*added)++;
    }
}

static void
messages_import_sim(NuxelMessages *app, gboolean merge_only)
{
    nuxel_phone_store_free(&app->sim_store);
    nuxel_phone_store_init(&app->sim_store);
    int rc = app->sim_path ? nuxel_phone_store_load(&app->sim_store, app->sim_path) : -1;
    if (rc == -1 || app->sim_store.n_messages == 0) {
        gtk_label_set_text(GTK_LABEL(app->capability_label),
            "SIM message mirror is empty. Set messages are stored locally; "
            "physical SIM SMS access is unavailable on this build.");
        return;
    }
    size_t added = 0;
    messages_merge_store(app, &app->sim_store, &added);
    if (!merge_only) {
        /* Copy local messages into the SIM mirror for later export. */
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
    char msg[256];
    g_snprintf(msg, sizeof msg,
               "SIM mirror: loaded %zu message(s)%s. Physical SIM access is not available yet.",
               added, merge_only ? "" : ", synced local messages to mirror");
    gtk_label_set_text(GTK_LABEL(app->capability_label), msg);
    render_conversations(app);
}

static void
on_import_sim_clicked(GtkWidget *btn, gpointer user_data)
{
    (void)btn;
    messages_import_sim((NuxelMessages *)user_data, TRUE);
}

static void
on_sync_sim_clicked(GtkWidget *btn, gpointer user_data)
{
    (void)btn;
    messages_import_sim((NuxelMessages *)user_data, FALSE);
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
    gtk_widget_set_sensitive(app->send_button,FALSE);
    nuxel_radio_connect(&app->radio,"org.nuxel.Messages",native_refresh,app);
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
    AdwStyleManager *style = adw_style_manager_get_default();
    adw_style_manager_set_color_scheme(style, ADW_COLOR_SCHEME_FORCE_DARK);
    
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
        app->sim_path = g_build_filename(dir, "sim-messages.json", NULL);
        g_free(dir);
    }
    nuxel_phone_store_init(&app->store);
    nuxel_phone_store_init(&app->sim_store);
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
    gtk_widget_set_margin_start(list_title, 12);
    gtk_widget_set_margin_end(list_title, 12);
    gtk_widget_set_margin_top(list_title, 12);
    gtk_widget_set_margin_bottom(list_title, 12);
    gtk_box_append(GTK_BOX(list_header), list_title);
    GtkWidget *spacer = gtk_box_new(GTK_ORIENTATION_HORIZONTAL, 0);
    gtk_widget_set_hexpand(spacer, TRUE);
    gtk_box_append(GTK_BOX(list_header), spacer);
    GtkWidget *import_sim = gtk_button_new_with_label("Import SIM");
    gtk_widget_add_css_class(import_sim, "flat");
    g_signal_connect(import_sim, "clicked", G_CALLBACK(on_import_sim_clicked), app);
    gtk_box_append(GTK_BOX(list_header), import_sim);
    GtkWidget *sync_sim = gtk_button_new_with_label("Sync SIM");
    gtk_widget_add_css_class(sync_sim, "flat");
    g_signal_connect(sync_sim, "clicked", G_CALLBACK(on_sync_sim_clicked), app);
    gtk_box_append(GTK_BOX(list_header), sync_sim);
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
    gtk_widget_set_margin_start(thread_header_box, 8);
    gtk_widget_set_margin_end(thread_header_box, 8);
    gtk_widget_set_margin_top(thread_header_box, 8);
    gtk_widget_set_margin_bottom(thread_header_box, 8);
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
    gtk_widget_set_margin_start(input_box, 8);
    gtk_widget_set_margin_end(input_box, 8);
    gtk_widget_set_margin_top(input_box, 8);
    gtk_widget_set_margin_bottom(input_box, 8);
    
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
    /* "Ready to import from a SIM": when a SIM mirror exists, merge it
     * automatically on startup so a newly inserted/replaced SIM's stored
     * messages appear without a manual step. */
    messages_import_sim(app, TRUE);
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
