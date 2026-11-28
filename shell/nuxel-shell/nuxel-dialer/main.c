/**
 * Nuxel Phone (Dialer) — native GTK4/libadwaita dialer.
 *
 * Round 34.5: restyled to the Nuxel reference language (Maps / Snekbyte /
 * Firewall: deep navy ground, rounded panel cards, cyan accent, muted dim text,
 * large safe touch targets) and made honest about voice:
 *
 *   - The keypad, backspace/clear, call action and call log remain.
 *   - Native VoLTE signalling is not implemented, and LTE has no CS fallback,
 *     so a dial attempt reports "VoLTE pending" and never creates a fake or
 *     connected call.  Radio1 itself returns NOT_SUPPORTED for Dial.
 *   - Current calls are rendered only from Radio1 GetCalls; nothing is
 *     manufactured locally.
 *
 * No ModemManager dependency and no Android runtime: Radio1 (via the bridge)
 * is the only telephony authority.
 */

#include <adwaita.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <glib.h>
#include <gio/gio.h>
#include "nuxel-phone-data.h"
#include "nuxel-radio-client.h"

typedef struct {
    GtkWidget *window;
    GtkWidget *stack;
    GtkWidget *display_label;
    GtkWidget *call_button;
    GtkWidget *end_button;
    GtkWidget *call_status;
    GtkWidget *network_label;
    GtkWidget *call_log_list;
    GtkWidget *call_log_empty;
    GtkWidget *voicemail_row;
    GtkWidget *capability_label;

    NuxelRadioClient radio;
    gboolean modem_ready;
    gboolean incoming, command_pending, refreshing, refresh_again;
    guint call_id;
    gchar *native_state;
    gchar *current_number;
    gboolean in_call;

    GPtrArray *contacts;
    NuxelPhoneStore store;
    NuxelPhoneCapabilities caps;
    gchar *store_path;
} NuxelDialer;

static void dialer_append_digit(NuxelDialer *dialer, const gchar *digit);
static void dialer_clear(NuxelDialer *dialer);
static void dialer_backspace(NuxelDialer *dialer);
static void dialer_initiate_call(NuxelDialer *dialer);
static void dialer_update_ui(NuxelDialer *dialer);
static void modem_connect(NuxelDialer *dialer);
static void dialer_update_capabilities(NuxelDialer *dialer);
static void dialer_log_call(NuxelDialer *dialer, const gchar *number, const gchar *state);
static void native_refresh(gpointer user);
static void dialer_render_log(NuxelDialer *dialer);

/* ============================================================
 * Shared data / honest capability
 * ============================================================ */

static void
dialer_update_capabilities(NuxelDialer *dialer)
{
    if (!dialer->capability_label) return;
    if (!nuxel_radio_available(&dialer->radio)) {
        gtk_label_set_text(GTK_LABEL(dialer->capability_label),
                           "Native call service unavailable");
        return;
    }
    if (!dialer->modem_ready) {
        gtk_label_set_text(GTK_LABEL(dialer->capability_label),
                           "No voice network · calls cannot be placed");
        return;
    }
    gtk_label_set_text(GTK_LABEL(dialer->capability_label),
        "VoLTE voice is pending · native SMS and data are ready");
}

static void
dialer_log_call(NuxelDialer *dialer, const gchar *number, const gchar *state)
{
    if (!number || !*number || !dialer->store_path) return;
    nuxel_phone_store_free(&dialer->store);
    nuxel_phone_store_init(&dialer->store);
    if (nuxel_phone_store_load(&dialer->store, dialer->store_path) < 0) return;
    nuxel_phone_add_call(&dialer->store, number, dialer->incoming ? "in" : "out",
                         state, nuxel_phone_now(), 0);
    nuxel_phone_store_save(&dialer->store, dialer->store_path);
    dialer_render_log(dialer);
}

/* ============================================================
 * Native path (Radio1)
 * ============================================================ */

static void
native_calls(GVariant *reply, const GError *error, gpointer user)
{
    NuxelDialer *dialer = user;
    dialer->refreshing = FALSE;
    if (!reply || error) {
        dialer->in_call = FALSE; dialer->incoming = FALSE;
        gtk_label_set_text(GTK_LABEL(dialer->call_status), error ? error->message : "Call state unknown");
    } else {
        GVariant *list = g_variant_get_child_value(reply, 0);
        gboolean was_call = dialer->in_call;
        if (g_variant_n_children(list)) {
            guint id; const char *state, *number; gboolean incoming;
            g_variant_get_child(list, 0, "(u&s&sb)", &id, &state, &number, &incoming);
            dialer->in_call = TRUE;
            dialer->incoming = !strcmp(state, "incoming") || !strcmp(state, "waiting");
            if (dialer->call_id != id || g_strcmp0(dialer->native_state, state)) {
                dialer_log_call(dialer, number, state);
                dialer->call_id = id;
                g_free(dialer->native_state);
                dialer->native_state = g_strdup(state);
            }
            g_free(dialer->current_number);
            dialer->current_number = g_strdup(number);
            gtk_label_set_text(GTK_LABEL(dialer->display_label), number);
            gtk_label_set_text(GTK_LABEL(dialer->call_status), state);
        } else {
            if (was_call && dialer->current_number)
                dialer_log_call(dialer, dialer->current_number, "ended");
            dialer->in_call = FALSE; dialer->incoming = FALSE; dialer->call_id = 0;
            g_clear_pointer(&dialer->native_state, g_free);
            if (!dialer->command_pending)
                gtk_label_set_text(GTK_LABEL(dialer->call_status), "No active call");
        }
        g_variant_unref(list);
    }
    dialer_update_ui(dialer);
    if (dialer->refresh_again) { dialer->refresh_again = FALSE; native_refresh(dialer); }
}

static void
native_status(GVariant *reply, const GError *error, gpointer user)
{
    NuxelDialer *dialer = user;
    if (!reply || error) {
        dialer->refreshing = FALSE; dialer->modem_ready = FALSE;
        dialer->in_call = FALSE; dialer->incoming = FALSE;
        gtk_label_set_text(GTK_LABEL(dialer->call_status),
                           "Call state unknown; native service unavailable");
        if (dialer->network_label)
            gtk_label_set_text(GTK_LABEL(dialer->network_label), "Radio1 unavailable");
        dialer_update_ui(dialer);
        return;
    }
    GVariant *dict = g_variant_get_child_value(reply, 0);
    const char *registration = "unknown", *audio = "unknown", *list = "unknown";
    g_variant_lookup(dict, "registration", "&s", &registration);
    g_variant_lookup(dict, "audio_route", "&s", &audio);
    g_variant_lookup(dict, "call_list", "&s", &list);
    dialer->modem_ready = !strcmp(registration, "REGISTERED_HOME") ||
                          !strcmp(registration, "REGISTERED_ROAMING");
    if (dialer->network_label) {
        gchar *label = g_strdup_printf("Network · %s · call audio %s", registration, audio);
        gtk_label_set_text(GTK_LABEL(dialer->network_label), label);
        g_free(label);
    }
    dialer_update_capabilities(dialer);
    gboolean valid = !strcmp(list, "received");
    g_variant_unref(dict);
    if (!valid) {
        dialer->refreshing = FALSE; dialer->in_call = FALSE; dialer->incoming = FALSE;
        gtk_label_set_text(GTK_LABEL(dialer->call_status), "Call list unavailable");
        dialer_update_ui(dialer);
        return;
    }
    nuxel_radio_call(&dialer->radio, "GetCalls", NULL, "call:status", native_calls, dialer);
}

static void
native_refresh(gpointer user)
{
    NuxelDialer *dialer = user;
    if (dialer->refreshing) { dialer->refresh_again = TRUE; return; }
    dialer->refreshing = TRUE;
    nuxel_radio_call(&dialer->radio, "GetVoiceStatus", NULL, NULL, native_status, dialer);
}

static gboolean
native_poll(gpointer user)
{ native_refresh(user); return G_SOURCE_CONTINUE; }

static void
dialer_radio_changed(const char *signal, gpointer user)
{
    (void)signal;
    native_refresh(user);
}

static void
modem_connect(NuxelDialer *dialer)
{
    nuxel_radio_connect(&dialer->radio, "org.nuxel.Dialer", dialer_radio_changed, dialer);
    g_timeout_add_seconds(3, native_poll, dialer);
}

static void
native_command_done(GVariant *reply, const GError *error, gpointer user)
{
    NuxelDialer *dialer = user;
    dialer->command_pending = FALSE;
    gboolean accepted = FALSE;
    if (reply) g_variant_get(reply, "(b)", &accepted);
    if (error) {
        /* Radio1 returns NOT_SUPPORTED for Dial because native VoLTE is pending:
         * say exactly that, never a fake "calling". */
        const gchar *msg = error->message;
        if (g_dbus_error_is_remote_error(error) &&
            (strstr(msg, "NOT_SUPPORTED") || strstr(msg, "not supported") ||
             strstr(msg, "VoLTE") || strstr(msg, "Emergency"))) {
            gtk_label_set_text(GTK_LABEL(dialer->call_status), msg);
        } else {
            gtk_label_set_text(GTK_LABEL(dialer->call_status), msg);
        }
    } else {
        gtk_label_set_text(GTK_LABEL(dialer->call_status),
                           accepted ? "Command accepted; waiting for call state" : "Command rejected");
    }
    dialer_update_ui(dialer);
    native_refresh(dialer);
}

static void
native_command(NuxelDialer *dialer, const char *method, GVariant *args, const char *capability)
{
    if (dialer->command_pending) return;
    dialer->command_pending = TRUE;
    dialer_update_ui(dialer);
    nuxel_radio_call(&dialer->radio, method, args, capability, native_command_done, dialer);
}

static void
native_answer(GtkWidget *button, gpointer user)
{
    (void)button;
    NuxelDialer *dialer = user;
    if (dialer->incoming) native_command(dialer, "AnswerCall", NULL, "call:initiate");
}

/* ============================================================
 * Dialer logic
 * ============================================================ */

static void
dialer_append_digit(NuxelDialer *dialer, const gchar *digit)
{
    gchar *current = g_strdup(gtk_label_get_text(GTK_LABEL(dialer->display_label)));
    if (strlen(current) >= 20) { g_free(current); return; }
    gchar *new_text = g_strconcat(current, digit, NULL);
    gtk_label_set_text(GTK_LABEL(dialer->display_label), new_text);
    g_free(current); g_free(new_text);
    dialer_update_ui(dialer);
}

static void
dialer_clear(NuxelDialer *dialer)
{
    gtk_label_set_text(GTK_LABEL(dialer->display_label), "");
    dialer_update_ui(dialer);
}

static void
dialer_backspace(NuxelDialer *dialer)
{
    const gchar *current = gtk_label_get_text(GTK_LABEL(dialer->display_label));
    gint len = strlen(current);
    if (len > 0) {
        gchar *new_text = g_strndup(current, len - 1);
        gtk_label_set_text(GTK_LABEL(dialer->display_label), new_text);
        g_free(new_text);
    }
    dialer_update_ui(dialer);
}

static void
on_call_button(GtkWidget *button, gpointer user)
{
    (void)button;
    NuxelDialer *dialer = user;
    if (dialer->in_call) native_command(dialer, "HangupCall", NULL, "call:end");
    else dialer_initiate_call(dialer);
}

static void
dialer_initiate_call(NuxelDialer *dialer)
{
    const char *number = gtk_label_get_text(GTK_LABEL(dialer->display_label));
    if (!number || !*number) return;
    if (!nuxel_radio_available(&dialer->radio)) {
        gtk_label_set_text(GTK_LABEL(dialer->call_status), "Native call service unavailable");
        return;
    }
    if (!dialer->modem_ready) {
        gtk_label_set_text(GTK_LABEL(dialer->call_status), "No voice network registered");
        return;
    }
    native_command(dialer, "Dial", g_variant_new("(s)", number), "call:initiate");
}


static void
dialer_update_ui(NuxelDialer *dialer)
{
    const gchar *number = gtk_label_get_text(GTK_LABEL(dialer->display_label));
    gboolean has_number = (number && strlen(number) > 0);
    if (dialer->in_call) {
        gtk_button_set_label(GTK_BUTTON(dialer->call_button), "■");
        gtk_widget_remove_css_class(dialer->call_button, "nuxel-call");
        gtk_widget_add_css_class(dialer->call_button, "nuxel-end");
    } else {
        gtk_button_set_label(GTK_BUTTON(dialer->call_button), "📞");
        gtk_widget_remove_css_class(dialer->call_button, "nuxel-end");
        gtk_widget_add_css_class(dialer->call_button, "nuxel-call");
    }
    gtk_widget_set_sensitive(dialer->call_button,
                             !dialer->command_pending && (has_number || dialer->in_call));
    if (dialer->end_button) {
        gtk_widget_set_visible(dialer->end_button, dialer->incoming);
        gtk_widget_set_sensitive(dialer->end_button, !dialer->command_pending);
    }
    dialer_update_capabilities(dialer);
}

/* ============================================================
 * UI
 * ============================================================ */

static const char *DIALER_CSS =
    ".nuxel-page { background: #0a1628; }"
    ".nuxel-head { padding: 14px 16px 10px; }"
    ".nuxel-title { font-size: 19px; font-weight: 700; color: #e6f0ff; }"
    ".nuxel-panel { background: #12233c; border-radius: 14px; margin: 0 12px 12px 12px; padding: 12px; }"
    ".nuxel-row { background: #1a3050; border-radius: 12px; padding: 12px; margin: 4px; }"
    ".nuxel-row-title { font-weight: 700; font-size: 15px; color: #e6f0ff; }"
    ".dim { color: #8aa3c7; font-size: 12px; }"
    ".nuxel-display { font-size: 34px; font-weight: 700; color: #e6f0ff; padding: 12px 0 4px 0; }"
    ".nuxel-digit { background: #1a3050; color: #e6f0ff; border-radius: 32px;"
    "  min-width: 64px; min-height: 58px; font-size: 22px; font-weight: 600; }"
    ".nuxel-digit:hover { background: #23446b; }"
    ".nuxel-action { background: #12233c; color: #8aa3c7; border-radius: 22px;"
    "  min-width: 56px; min-height: 44px; font-size: 16px; }"
    ".nuxel-call { background: #46d18c; color: #06121f; border-radius: 34px;"
    "  min-width: 68px; min-height: 68px; font-size: 26px; }"
    ".nuxel-end { background: #ff5b5b; color: #2a0505; border-radius: 34px;"
    "  min-width: 68px; min-height: 68px; font-size: 24px; }"
    ".nuxel-tabs { padding: 0 0 4px 0; }"
    ".nuxel-badge { background: rgba(255,184,77,0.15); color: #ffb84d;"
    "  border-radius: 10px; padding: 2px 9px; font-size: 11px; font-weight: 700; }"
    "listbox { background: transparent; } listbox row { background: transparent; }";

static GtkWidget *
create_digit_button(NuxelDialer *dialer, const gchar *digit, const gchar *subtitle)
{
    GtkWidget *button = gtk_button_new();
    GtkWidget *box = gtk_box_new(GTK_ORIENTATION_VERTICAL, 0);
    GtkWidget *label = gtk_label_new(digit);
    gtk_widget_set_size_request(button, 80, 76);
    gtk_widget_add_css_class(button, "nuxel-digit");
    gtk_box_append(GTK_BOX(box), label);
    if (subtitle && *subtitle) {
        GtkWidget *sub = gtk_label_new(subtitle);
        gtk_widget_add_css_class(sub, "dim");
        gtk_box_append(GTK_BOX(box), sub);
    }
    gtk_button_set_child(GTK_BUTTON(button), box);
    g_object_set_data_full(G_OBJECT(button), "digit", g_strdup(digit), g_free);
    g_signal_connect(button, "clicked", G_CALLBACK(dialer_append_digit), dialer);
    return button;
}

static void
dialer_render_log(NuxelDialer *dialer)
{
    GtkWidget *list = dialer->call_log_list;
    if (!list) return;
    GtkWidget *child = gtk_widget_get_first_child(list);
    while (child) {
        GtkWidget *next = gtk_widget_get_next_sibling(child);
        gtk_list_box_remove(GTK_LIST_BOX(list), child);
        child = next;
    }
    if (nuxel_phone_store_load(&dialer->store, dialer->store_path) < 0) return;
    size_t shown = 0;
    for (size_t i = dialer->store.n_calls; i > 0 && shown < 50; i--, shown++) {
        NuxelCall *call = &dialer->store.calls[i - 1];
        GtkWidget *row = gtk_box_new(GTK_ORIENTATION_HORIZONTAL, 10);
        gtk_widget_add_css_class(row, "nuxel-row");
        const gchar *arrow = !strcmp(call->direction, "in") ? "↓" : "↑";
        gchar *title = g_strdup_printf("%s  %s", arrow,
            call->name[0] ? call->name : call->number);
        GtkWidget *name = gtk_label_new(title);
        g_free(title);
        gtk_widget_add_css_class(name, "nuxel-row-title");
        gtk_label_set_xalign(GTK_LABEL(name), 0.0);
        gtk_widget_set_hexpand(name, TRUE);
        gtk_label_set_ellipsize(GTK_LABEL(name), PANGO_ELLIPSIZE_END);
        gtk_box_append(GTK_BOX(row), name);
        gchar *when = NULL;
        if (call->started_at > 0) {
            GDateTime *dt = g_date_time_new_from_unix_local(call->started_at);
            when = dt ? g_date_time_format(dt, "%H:%M") : NULL;
            if (dt) g_date_time_unref(dt);
        }
        GtkWidget *state = gtk_label_new(when ? when : call->state);
        gtk_widget_add_css_class(state, "dim");
        gtk_box_append(GTK_BOX(row), state);
        g_free(when);
        gtk_list_box_append(GTK_LIST_BOX(list), row);
    }
    if (dialer->call_log_empty)
        gtk_widget_set_visible(dialer->call_log_empty, shown == 0);
}

static GtkWidget *
build_dialer_page(NuxelDialer *dialer)
{
    GtkWidget *page = gtk_box_new(GTK_ORIENTATION_VERTICAL, 0);
    gtk_widget_add_css_class(page, "nuxel-page");

    GtkWidget *head = gtk_box_new(GTK_ORIENTATION_HORIZONTAL, 8);
    gtk_widget_add_css_class(head, "nuxel-head");
    GtkWidget *title = gtk_label_new("Phone");
    gtk_widget_add_css_class(title, "nuxel-title");
    gtk_label_set_xalign(GTK_LABEL(title), 0.0);
    gtk_widget_set_hexpand(title, TRUE);
    gtk_box_append(GTK_BOX(head), title);
    GtkWidget *voicemail = gtk_label_new("Voicemail");
    gtk_widget_add_css_class(voicemail, "dim");
    gtk_box_append(GTK_BOX(head), voicemail);
    gtk_box_append(GTK_BOX(page), head);

    /* Keypad card */
    GtkWidget *panel = gtk_box_new(GTK_ORIENTATION_VERTICAL, 0);
    gtk_widget_add_css_class(panel, "nuxel-panel");

    dialer->display_label = gtk_label_new("");
    gtk_label_set_selectable(GTK_LABEL(dialer->display_label), TRUE);
    gtk_widget_add_css_class(dialer->display_label, "nuxel-display");
    gtk_widget_set_halign(dialer->display_label, GTK_ALIGN_CENTER);
    gtk_label_set_ellipsize(GTK_LABEL(dialer->display_label), PANGO_ELLIPSIZE_END);
    gtk_label_set_max_width_chars(GTK_LABEL(dialer->display_label), 16);
    gtk_box_append(GTK_BOX(panel), dialer->display_label);

    dialer->call_status = gtk_label_new("No active call");
    gtk_widget_add_css_class(dialer->call_status, "dim");
    gtk_widget_set_halign(dialer->call_status, GTK_ALIGN_CENTER);
    gtk_label_set_wrap(GTK_LABEL(dialer->call_status), TRUE);
    gtk_label_set_justify(GTK_LABEL(dialer->call_status), GTK_JUSTIFY_CENTER);
    gtk_box_append(GTK_BOX(panel), dialer->call_status);
    gtk_box_append(GTK_BOX(page), panel);

    GtkWidget *grid = gtk_grid_new();
    gtk_grid_set_row_spacing(GTK_GRID(grid), 8);
    gtk_grid_set_column_spacing(GTK_GRID(grid), 8);
    gtk_widget_set_halign(grid, GTK_ALIGN_CENTER);
    gtk_widget_set_margin_top(grid, 4);
    const gchar *keys[] = {
        "1", "", "2", "ABC", "3", "DEF",
        "4", "GHI", "5", "JKL", "6", "MNO",
        "7", "PQRS", "8", "TUV", "9", "WXYZ",
        "*", "", "0", "+", "#", "",
    };
    int n_keys = sizeof(keys) / sizeof(keys[0]);
    for (int i = 0; i < n_keys; i += 2) {
        int row = (i / 2) / 3;
        int col = (i / 2) % 3;
        GtkWidget *btn = create_digit_button(dialer, keys[i], keys[i + 1]);
        gtk_grid_attach(GTK_GRID(grid), btn, col, row, 1, 1);
    }
    gtk_box_append(GTK_BOX(page), grid);

    /* Call actions */
    GtkWidget *call_box = gtk_box_new(GTK_ORIENTATION_HORIZONTAL, 18);
    gtk_widget_set_halign(call_box, GTK_ALIGN_CENTER);
    gtk_widget_set_margin_top(call_box, 12);
    gtk_widget_set_margin_bottom(call_box, 8);
    GtkWidget *clear_btn = gtk_button_new_with_label("C");
    gtk_widget_add_css_class(clear_btn, "nuxel-action");
    g_signal_connect(clear_btn, "clicked", G_CALLBACK(dialer_clear), dialer);
    gtk_box_append(GTK_BOX(call_box), clear_btn);
    dialer->call_button = gtk_button_new_with_label("📞");
    gtk_widget_add_css_class(dialer->call_button, "nuxel-call");
    gtk_widget_set_size_request(dialer->call_button, 72, 72);
    gtk_widget_set_tooltip_text(dialer->call_button, "Call (VoLTE voice pending)");
    g_signal_connect(dialer->call_button, "clicked", G_CALLBACK(on_call_button), dialer);
    gtk_box_append(GTK_BOX(call_box), dialer->call_button);
    GtkWidget *backspace_btn = gtk_button_new_with_label("⌫");
    gtk_widget_add_css_class(backspace_btn, "nuxel-action");
    g_signal_connect(backspace_btn, "clicked", G_CALLBACK(dialer_backspace), dialer);
    gtk_box_append(GTK_BOX(call_box), backspace_btn);
    gtk_box_append(GTK_BOX(page), call_box);

    dialer->end_button = gtk_button_new_with_label("Answer");
    gtk_widget_add_css_class(dialer->end_button, "nuxel-call");
    g_signal_connect(dialer->end_button, "clicked", G_CALLBACK(native_answer), dialer);
    gtk_widget_set_visible(dialer->end_button, FALSE);
    gtk_widget_set_halign(dialer->end_button, GTK_ALIGN_CENTER);
    gtk_box_append(GTK_BOX(page), dialer->end_button);

    dialer->capability_label = gtk_label_new("Modem status unknown - not probed yet.");
    gtk_label_set_wrap(GTK_LABEL(dialer->capability_label), TRUE);
    gtk_label_set_justify(GTK_LABEL(dialer->capability_label), GTK_JUSTIFY_CENTER);
    gtk_widget_set_margin_start(dialer->capability_label, 16);
    gtk_widget_set_margin_end(dialer->capability_label, 16);
    gtk_widget_add_css_class(dialer->capability_label, "dim");
    gtk_box_append(GTK_BOX(page), dialer->capability_label);

    dialer->network_label = gtk_label_new("Network · status pending");
    gtk_widget_add_css_class(dialer->network_label, "dim");
    gtk_widget_set_halign(dialer->network_label, GTK_ALIGN_CENTER);
    gtk_widget_set_margin_bottom(dialer->network_label, 6);
    gtk_box_append(GTK_BOX(page), dialer->network_label);
    return page;
}

static GtkWidget *
build_recents_page(NuxelDialer *dialer)
{
    GtkWidget *page = gtk_box_new(GTK_ORIENTATION_VERTICAL, 0);
    gtk_widget_add_css_class(page, "nuxel-page");
    GtkWidget *head = gtk_box_new(GTK_ORIENTATION_HORIZONTAL, 8);
    gtk_widget_add_css_class(head, "nuxel-head");
    GtkWidget *title = gtk_label_new("Recents");
    gtk_widget_add_css_class(title, "nuxel-title");
    gtk_label_set_xalign(GTK_LABEL(title), 0.0);
    gtk_widget_set_hexpand(title, TRUE);
    gtk_box_append(GTK_BOX(head), title);
    gtk_box_append(GTK_BOX(page), head);

    dialer->call_log_list = gtk_list_box_new();
    gtk_list_box_set_selection_mode(GTK_LIST_BOX(dialer->call_log_list), GTK_SELECTION_NONE);
    GtkWidget *scroll = gtk_scrolled_window_new();
    gtk_scrolled_window_set_policy(GTK_SCROLLED_WINDOW(scroll), GTK_POLICY_NEVER, GTK_POLICY_AUTOMATIC);
    gtk_scrolled_window_set_child(GTK_SCROLLED_WINDOW(scroll), dialer->call_log_list);
    gtk_widget_set_vexpand(scroll, TRUE);
    gtk_box_append(GTK_BOX(page), scroll);
    dialer->call_log_empty = gtk_label_new("No recent calls");
    gtk_widget_add_css_class(dialer->call_log_empty, "dim");
    gtk_widget_set_margin_top(dialer->call_log_empty, 24);
    gtk_box_append(GTK_BOX(page), dialer->call_log_empty);
    return page;
}

static void
on_tab_keypad(GtkToggleButton *b, gpointer user)
{
    NuxelDialer *dialer = user;
    if (gtk_toggle_button_get_active(b))
        gtk_stack_set_visible_child_name(GTK_STACK(dialer->stack), "keypad");
}

static void
on_tab_recents(GtkToggleButton *b, gpointer user)
{
    NuxelDialer *dialer = user;
    if (gtk_toggle_button_get_active(b)) {
        dialer_render_log(dialer);
        gtk_stack_set_visible_child_name(GTK_STACK(dialer->stack), "recents");
    }
}

/* ============================================================
 * Entry point
 * ============================================================ */

static void
activate_cb(GtkApplication *app, gpointer user_data)
{
    (void)user_data;
    NuxelDialer *dialer = g_new0(NuxelDialer, 1);

    GtkCssProvider *provider = gtk_css_provider_new();
    gtk_css_provider_load_from_string(provider, DIALER_CSS);
    gtk_style_context_add_provider_for_display(gdk_display_get_default(),
        GTK_STYLE_PROVIDER(provider), GTK_STYLE_PROVIDER_PRIORITY_APPLICATION);
    g_object_unref(provider);

    dialer->window = adw_application_window_new(GTK_APPLICATION(app));
    gtk_window_set_title(GTK_WINDOW(dialer->window), "Phone");
    gtk_window_set_default_size(GTK_WINDOW(dialer->window), 400, 700);
    gtk_window_set_resizable(GTK_WINDOW(dialer->window), TRUE);
    AdwStyleManager *style = adw_style_manager_get_default();
    adw_style_manager_set_color_scheme(style, ADW_COLOR_SCHEME_FORCE_DARK);

    dialer->stack = gtk_stack_new();
    GtkWidget *keypad = build_dialer_page(dialer);
    GtkWidget *recents = build_recents_page(dialer);
    gtk_stack_add_named(GTK_STACK(dialer->stack), keypad, "keypad");
    gtk_stack_add_named(GTK_STACK(dialer->stack), recents, "recents");
    gtk_stack_set_visible_child_name(GTK_STACK(dialer->stack), "keypad");

    GtkWidget *switcher = gtk_box_new(GTK_ORIENTATION_HORIZONTAL, 6);
    gtk_widget_add_css_class(switcher, "nuxel-tabs");
    gtk_widget_set_margin_start(switcher, 12);
    gtk_widget_set_margin_end(switcher, 12);
    gtk_widget_set_margin_bottom(switcher, 6);
    GtkWidget *tab_keypad = gtk_toggle_button_new_with_label("Keypad");
    GtkWidget *tab_recents = gtk_toggle_button_new_with_label("Recents");
    gtk_toggle_button_set_group(GTK_TOGGLE_BUTTON(tab_recents), GTK_TOGGLE_BUTTON(tab_keypad));
    gtk_toggle_button_set_active(GTK_TOGGLE_BUTTON(tab_keypad), TRUE);
    gtk_widget_set_hexpand(tab_keypad, TRUE);
    gtk_widget_set_hexpand(tab_recents, TRUE);
    g_signal_connect(tab_keypad, "toggled", G_CALLBACK(on_tab_keypad), dialer);
    g_signal_connect(tab_recents, "toggled", G_CALLBACK(on_tab_recents), dialer);
    gtk_box_append(GTK_BOX(switcher), tab_keypad);
    gtk_box_append(GTK_BOX(switcher), tab_recents);

    GtkWidget *root = gtk_box_new(GTK_ORIENTATION_VERTICAL, 0);
    gtk_box_append(GTK_BOX(root), switcher);
    gtk_widget_set_vexpand(dialer->stack, TRUE);
    gtk_box_append(GTK_BOX(root), dialer->stack);
    adw_application_window_set_content(ADW_APPLICATION_WINDOW(dialer->window), root);

    dialer->in_call = FALSE;
    dialer->modem_ready = FALSE;
    dialer->contacts = g_ptr_array_new_with_free_func(g_free);
    {
        gchar *dir = g_build_filename(g_get_user_data_dir(), "nuxel-contacts", NULL);
        g_mkdir_with_parents(dir, 0755);
        dialer->store_path = g_build_filename(dir, "contacts.json", NULL);
        g_free(dir);
    }
    nuxel_phone_store_init(&dialer->store);
    nuxel_phone_capabilities_init(&dialer->caps);
    if (dialer->store_path) {
        if (nuxel_phone_store_load(&dialer->store, dialer->store_path) == -1)
            g_warning("[Dialer] stored phone data is unreadable; call log starts empty");
    }
    dialer_update_capabilities(dialer);
    dialer_update_ui(dialer);
    dialer_render_log(dialer);

    modem_connect(dialer);
    gtk_window_present(GTK_WINDOW(dialer->window));
}

int
main(int argc, char *argv[])
{
    GtkApplication *app = gtk_application_new("org.nuxel.Dialer",
                                              G_APPLICATION_DEFAULT_FLAGS);
    g_signal_connect(app, "activate", G_CALLBACK(activate_cb), NULL);
    int status = g_application_run(G_APPLICATION(app), argc, argv);
    g_object_unref(app);
    return status;
}
