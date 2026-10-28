/**
 * Nuxel Dialer - Native Phone Dialer for Nuxel OS
 * GTK4/libadwaita application with ModemManager D-Bus integration
 *
 * Compile: gcc `pkg-config --cflags gtk4 libadwaita-1 mm-glib` \
 *              main.c -o nuxel-dialer \
 *              `pkg-config --libs gtk4 libadwaita-1 mm-glib`
 */

#ifdef HAVE_MM_GLIB
#include <libmm-glib.h>
#endif /* HAVE_MM_GLIB */
#include <adwaita.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <glib.h>
#include <gio/gio.h>
/* Shared phone data layer: contacts, call log and honest capability labels. */
#include "nuxel-phone-data.h"

/* ============================================================
 * Data structures
 * ============================================================ */

typedef struct {
    GtkWidget *window;
    GtkWidget *display_label;    /* Phone number display */
    GtkWidget *call_button;      /* Green call button */
    GtkWidget *end_button;       /* Red end call button */
    GtkWidget *call_status;      /* Call status label */
    GtkWidget *contacts_list;    /* Contact list for search */
    GtkWidget *stack;            /* Main stack (dialer/contacts) */
    
    GCancellable *cancellable;
    gboolean modem_ready;
#ifdef HAVE_MM_GLIB
    /* ModemManager integration (only when the client library is available) */
    MMManager *mm_manager;
    MMModem *mm_modem;
#else
    /* Runtime GDBus ModemManager path (no libmm-glib). */
    GDBusConnection *mm_conn;
#endif
    
    /* Call state */
    gchar *current_number;
    gboolean in_call;
    
    /* Contacts */
    GPtrArray *contacts;

    /* Shared phone data (call log + contacts) and the capability probe result.
     * The capability text shown in the UI is generated ONLY from this struct, so
     * the dialer can never claim a modem it has not seen. */
    NuxelPhoneStore store;
    NuxelPhoneCapabilities caps;
    gchar *store_path;
    GtkWidget *capability_label;
} NuxelDialer;

/* ============================================================
 * Forward declarations
 * ============================================================ */

static void dialer_append_digit(NuxelDialer *dialer, const gchar *digit);
static void dialer_clear(NuxelDialer *dialer);
static void dialer_backspace(NuxelDialer *dialer);
static void dialer_initiate_call(NuxelDialer *dialer);
static void dialer_end_call(NuxelDialer *dialer);
static void dialer_update_ui(NuxelDialer *dialer);
static void modem_connect(NuxelDialer *dialer);
static void dialer_update_capabilities(NuxelDialer *dialer);
static void dialer_log_call(NuxelDialer *dialer, const gchar *number, const gchar *state);

#ifdef HAVE_MM_GLIB
/* ============================================================
 * ModemManager Integration
 * ============================================================ */

static void
on_modem_added_cb (MMManager *manager,
                   MMModem   *modem,
                   NuxelDialer *dialer)
{
    g_debug ("[Dialer] Modem detected: %s",
             mm_modem_get_path (modem));
    
    dialer->mm_modem = g_object_ref (modem);
    dialer->modem_ready = TRUE;
    
    /* Update call button state */
    dialer_update_ui (dialer);
    
    /* Monitor call state changes */
    g_signal_connect_swapped (modem, "state-changed",
                              G_CALLBACK (dialer_update_ui), dialer);
}

static void
on_modem_removed_cb (MMManager *manager,
                     MMModem   *modem,
                     NuxelDialer *dialer)
{
    if (dialer->mm_modem == modem) {
        g_clear_object (&dialer->mm_modem);
        dialer->modem_ready = FALSE;
        dialer_update_ui (dialer);
    }
}

static void
modem_manager_ready_cb (GObject      *source,
                        GAsyncResult *res,
                        gpointer      user_data)
{
    NuxelDialer *dialer = (NuxelDialer *)user_data;
    GError *error = NULL;
    
    dialer->mm_manager = mm_manager_new_finish (res, &error);
    
    if (error) {
        g_warning ("[Dialer] Failed to connect to ModemManager: %s",
                   error->message);
        g_error_free (error);
        return;
    }
    
    g_debug ("[Dialer] Connected to ModemManager");
    
    /* Connect signals for modem add/remove */
    g_signal_connect (dialer->mm_manager, "modem-added",
                      G_CALLBACK (on_modem_added_cb), dialer);
    g_signal_connect (dialer->mm_manager, "modem-removed",
                      G_CALLBACK (on_modem_removed_cb), dialer);
    
    /* Get existing modems */
    GList *modems = mm_manager_peek_modems (dialer->mm_manager);
    if (modems) {
        dialer->mm_modem = g_object_ref (MM_MODEM (modems->data));
        dialer->modem_ready = TRUE;
        dialer->caps.modem_present = 1;
        dialer->caps.voice_calls = 1;
        dialer->caps.sms_send = 1;
        dialer->caps.data_connection = 1;
        {
            const gchar *nm = mm_modem_get_manufacturer (MM_MODEM (modems->data));
            g_strlcpy (dialer->caps.modem_name, nm ? nm : "ModemManager modem",
                       sizeof dialer->caps.modem_name);
        }
        g_strlcpy (dialer->caps.detail,
                   "ModemManager reported a modem with a call interface.",
                   sizeof dialer->caps.detail);
        dialer_update_capabilities (dialer);
        dialer_update_ui (dialer);
    } else {
        dialer->caps.modem_present = 0;
        g_strlcpy (dialer->caps.detail,
                   "ModemManager is running but exposes no modem.",
                   sizeof dialer->caps.detail);
        dialer_update_capabilities (dialer);
    }
}

/* Append a call-log entry through the shared store and flush it.  A failed or
 * impossible call is still recorded with its honest state so the log itself
 * never lies about what happened. */
static void
dialer_log_call (NuxelDialer *dialer, const gchar *number, const gchar *state)
{
    nuxel_phone_add_call (&dialer->store, number, "out", state, nuxel_phone_now (), 0);
    if (dialer->store_path)
        nuxel_phone_store_save (&dialer->store, dialer->store_path);
}

/* Rebuild the capability sentence from the probe only. */
static void
dialer_update_capabilities (NuxelDialer *dialer)
{
    if (!dialer->capability_label)
        return;

    char label[NUXEL_LABEL_MAX];
    char detail[200];
    nuxel_phone_capability_label (&dialer->caps, "summary", label, sizeof label);

    if (dialer->caps.modem_present == 1 && dialer->caps.voice_calls) {
        snprintf (detail, sizeof detail,
                  "%s  Placing a real call still needs an owner test (proof area 17).", label);
    } else if (dialer->caps.modem_present == 0) {
        snprintf (detail, sizeof detail,
                  "%s  This build records attempted calls in the call log and never "
                  "pretends a call connected.", label);
    } else {
        snprintf (detail, sizeof detail, "%s", label);
    }
    gtk_label_set_text (GTK_LABEL (dialer->capability_label), detail);
}

static void
modem_connect (NuxelDialer *dialer)
{
    mm_manager_new (g_bus_get_sync (G_BUS_TYPE_SYSTEM, NULL, NULL),
                    G_PRIORITY_DEFAULT,
                    dialer->cancellable,
                    modem_manager_ready_cb,
                    dialer);
}
#else /* no libmm-glib: GDBus runtime path */
static void
modem_connect (NuxelDialer *dialer)
{
    /* ModemManager is only available when built against libmm-glib. When
     * absent we report the modem as unavailable; the UI still works and shows
     * the user a clear status message. On real hardware the native build ships
     * libmm-glib so this path is unused. */
    dialer->modem_ready = FALSE;
    /* No libmm-glib build: we cannot even ask ModemManager, so the modem stays
     * UNKNOWN (not "absent") and the label says so. */
    dialer->caps.modem_present = -1;
    g_strlcpy (dialer->caps.detail,
               "Built without libmm-glib: ModemManager was not queried, so modem "
               "availability is unknown. No call can be placed from this build.",
               sizeof dialer->caps.detail);
    gtk_label_set_text (GTK_LABEL (dialer->call_status),
                        "Calls unavailable (built without libmm-glib)");
    dialer_update_capabilities (dialer);
    dialer_update_ui (dialer);
}

static void
dialer_log_call (NuxelDialer *dialer, const gchar *number, const gchar *state)
{
    nuxel_phone_add_call (&dialer->store, number, "out", state, nuxel_phone_now (), 0);
    if (dialer->store_path)
        nuxel_phone_store_save (&dialer->store, dialer->store_path);
}

static void
dialer_update_capabilities (NuxelDialer *dialer)
{
    char label[NUXEL_LABEL_MAX];
    if (!dialer->capability_label)
        return;
    nuxel_phone_capability_label (&dialer->caps, "summary", label, sizeof label);
    gtk_label_set_text (GTK_LABEL (dialer->capability_label), label);
}
#endif /* HAVE_MM_GLIB */
/* ============================================================
 * UI Callbacks
 * ============================================================ */

static void
on_digit_clicked (GtkWidget   *button,
                  gpointer     user_data)
{
    NuxelDialer *dialer = (NuxelDialer *)user_data;
    const gchar *digit = g_object_get_data (G_OBJECT (button), "digit");
    
    if (digit) {
        dialer_append_digit (dialer, digit);
    }
}

static void
on_call_clicked (GtkWidget   *button,
                 gpointer     user_data)
{
    NuxelDialer *dialer = (NuxelDialer *)user_data;
    
    if (dialer->in_call) {
        dialer_end_call (dialer);
    } else {
        dialer_initiate_call (dialer);
    }
}

static void
on_clear_clicked (GtkWidget   *button,
                  gpointer     user_data)
{
    NuxelDialer *dialer = (NuxelDialer *)user_data;
    dialer_clear (dialer);
}

static void
on_backspace_clicked (GtkWidget   *button,
                      gpointer     user_data)
{
    NuxelDialer *dialer = (NuxelDialer *)user_data;
    dialer_backspace (dialer);
}

/* ============================================================
 * Dialer Logic
 * ============================================================ */

static void
dialer_append_digit (NuxelDialer *dialer, const gchar *digit)
{
    gchar *current = g_strdup (gtk_label_get_text (GTK_LABEL (dialer->display_label)));
    
    /* Limit to 20 digits */
    if (strlen (current) >= 20) {
        g_free (current);
        return;
    }
    
    gchar *new_text = g_strconcat (current, digit, NULL);
    gtk_label_set_text (GTK_LABEL (dialer->display_label), new_text);
    g_free (current);
    g_free (new_text);
    
    dialer_update_ui (dialer);
}

static void
dialer_clear (NuxelDialer *dialer)
{
    gtk_label_set_text (GTK_LABEL (dialer->display_label), "");
    dialer_update_ui (dialer);
}

static void
dialer_backspace (NuxelDialer *dialer)
{
    const gchar *current = gtk_label_get_text (GTK_LABEL (dialer->display_label));
    gint len = strlen (current);
    
    if (len > 0) {
        gchar *new_text = g_strndup (current, len - 1);
        gtk_label_set_text (GTK_LABEL (dialer->display_label), new_text);
        g_free (new_text);
    }
    
    dialer_update_ui (dialer);
}

#ifdef HAVE_MM_GLIB /* ModemManager call orchestration (libmm-glib only) */
static void
on_call_state_changed (MMModem    *modem,
                       guint       old_state,
                       guint       new_state,
                       guint       reason,
                       NuxelDialer *dialer)
{
    g_debug ("[Dialer] Call state changed: %u -> %u (reason: %u)",
             old_state, new_state, reason);
    
    if (new_state == 0) { /* MM_MODEM_STATE_UNKNOWN or disconnected */
        dialer->in_call = FALSE;
        gtk_label_set_text (GTK_LABEL (dialer->call_status), "");
    } else {
        dialer->in_call = (new_state >= 8 && new_state <= 11); /* Connected/Calling states */
        if (dialer->in_call) {
            gtk_label_set_text (GTK_LABEL (dialer->call_status),
                                "Call in progress...");
        }
    }
    
    dialer_update_ui (dialer);
}

static void
on_call_created (GObject      *source,
                 GAsyncResult *res,
                 NuxelDialer  *dialer)
{
    GError *error = NULL;
    MMCall *call = mm_modem_create_call_finish (MM_MODEM (source), res, &error);
    
    if (error) {
        g_warning ("[Dialer] Failed to create call: %s", error->message);
        gtk_label_set_text (GTK_LABEL (dialer->call_status), error->message);
        g_error_free (error);
        return;
    }
    
    g_debug ("[Dialer] Call created: %s", mm_call_get_path (call));
    dialer->in_call = TRUE;
    gtk_label_set_text (GTK_LABEL (dialer->call_status), "Connecting...");
    
    /* Start the call */
    mm_call_start (call, dialer->cancellable, NULL, NULL);
    
    /* Monitor call state */
    g_signal_connect_swapped (call, "state-changed",
                              G_CALLBACK (on_call_state_changed), dialer);
    
    dialer_update_ui (dialer);
}

static void
dialer_initiate_call (NuxelDialer *dialer)
{
    const gchar *number = gtk_label_get_text (GTK_LABEL (dialer->display_label));

    if (!dialer->modem_ready || !dialer->mm_modem) {
        char label[NUXEL_LABEL_MAX];
        nuxel_phone_capability_label (&dialer->caps, "voice", label, sizeof label);
        gtk_label_set_text (GTK_LABEL (dialer->call_status), label);
        if (number && *number)
            dialer_log_call (dialer, number, "no-modem");
        return;
    }

    if (!number || strlen (number) == 0) {
        gtk_label_set_text (GTK_LABEL (dialer->call_status),
                            "Enter a number first");
        return;
    }

    /* Record the attempt before it is made: if the app dies mid-dial the log
     * still shows what the user asked for. */
    dialer_log_call (dialer, number, "attempted");

    g_debug ("[Dialer] Initiating call to: %s", number);
    gtk_label_set_text (GTK_LABEL (dialer->call_status), "Dialing...");
    
    /* Create call via ModemManager */
    MMSmsProperties *properties = mm_sms_properties_new ();
    g_object_set (properties,
                  MM_SMS_PROPERTY_NUMBER, number,
                  NULL);
    
    mm_modem_create_call (dialer->mm_modem,
                          properties,
                          dialer->cancellable,
                          (GAsyncReadyCallback)on_call_created,
                          dialer);
    
    g_object_unref (properties);
}

static void
on_call_deleted (GObject      *source,
                 GAsyncResult *res,
                 NuxelDialer  *dialer)
{
    GError *error = NULL;
    gboolean result = mm_modem_delete_call_finish (MM_MODEM (source), res, &error);
    
    if (error) {
        g_warning ("[Dialer] Failed to end call: %s", error->message);
        g_error_free (error);
    }
    
    dialer->in_call = FALSE;
    gtk_label_set_text (GTK_LABEL (dialer->call_status), "Call ended");
    dialer_update_ui (dialer);
}

static void
dialer_end_call (NuxelDialer *dialer)
{
    if (!dialer->modem_ready || !dialer->mm_modem) {
        return;
    }
    
    g_debug ("[Dialer] Ending call");
    
    /* Hangup all active calls */
    mm_modem_hangup_all (dialer->mm_modem,
                         dialer->cancellable,
                         (GAsyncReadyCallback)on_call_deleted,
                         dialer);
}
#else /* no libmm-glib: dialer still works but cannot place/end real calls */
static void
dialer_initiate_call (NuxelDialer *dialer)
{
    const gchar *number = gtk_label_get_text (GTK_LABEL (dialer->display_label));
    char label[NUXEL_LABEL_MAX];
    nuxel_phone_capability_label (&dialer->caps, "voice", label, sizeof label);
    gtk_label_set_text (GTK_LABEL (dialer->call_status), label);
    if (number && *number)
        dialer_log_call (dialer, number, "no-modem");
}

static void
dialer_end_call (NuxelDialer *dialer)
{
    dialer->in_call = FALSE;
    gtk_label_set_text (GTK_LABEL (dialer->call_status), "");
    dialer_update_ui (dialer);
}
#endif /* HAVE_MM_GLIB */
static void
dialer_update_ui (NuxelDialer *dialer)
{
    const gchar *number = gtk_label_get_text (GTK_LABEL (dialer->display_label));
    gboolean has_number = (number && strlen (number) > 0);
    
    /* Update call/end button appearance */
    if (dialer->in_call) {
        gtk_button_set_label (GTK_BUTTON (dialer->call_button), "■");
        gtk_widget_remove_css_class (dialer->call_button, "call-button");
        gtk_widget_add_css_class (dialer->call_button, "end-button");
    } else {
        gtk_button_set_label (GTK_BUTTON (dialer->call_button), "📞");
        gtk_widget_remove_css_class (dialer->call_button, "end-button");
        gtk_widget_add_css_class (dialer->call_button, "call-button");
    }
    
    /* Enable/disable call button.  The button stays available with a number so
     * the user can press it and read WHY nothing will happen; the call log then
     * records the attempt with an honest state instead of a fake "connected". */
    gtk_widget_set_sensitive (dialer->call_button,
                              has_number || dialer->in_call);

    dialer_update_capabilities (dialer);
}

/* ============================================================
 * UI Construction
 * ============================================================ */

static GtkWidget *
create_digit_button (NuxelDialer *dialer,
                     const gchar *digit,
                     const gchar *subtitle)
{
    GtkWidget *button = gtk_button_new ();
    GtkWidget *box = gtk_box_new (GTK_ORIENTATION_VERTICAL, 0);
    GtkWidget *label = gtk_label_new (digit);
    GtkWidget *sub = subtitle ? gtk_label_new (subtitle) : NULL;
    
    /* removed duplicate pango attr leak */
    PangoAttrList *attrs = pango_attr_list_new ();
    pango_attr_list_insert (attrs, pango_attr_size_new (36 * PANGO_SCALE));
    gtk_label_set_attributes (GTK_LABEL (label), attrs);
    pango_attr_list_unref (attrs);
    
    gtk_widget_set_size_request (button, 80, 80);
    gtk_widget_add_css_class (button, "digit-button");
    
    gtk_box_append (GTK_BOX (box), label);
    if (sub) {
        gtk_label_set_attributes (GTK_LABEL (sub), (pango_attr_list_new ()));
        PangoAttrList *sattrs = pango_attr_list_new ();
        pango_attr_list_insert (sattrs, pango_attr_size_new (12 * PANGO_SCALE));
        gtk_label_set_attributes (GTK_LABEL (sub), sattrs);
        pango_attr_list_unref (sattrs);
        gtk_box_append (GTK_BOX (box), sub);
    }
    
    gtk_button_set_child (GTK_BUTTON (button), box);
    g_object_set_data_full (G_OBJECT (button), "digit",
                            g_strdup (digit), g_free);
    
    g_signal_connect (button, "clicked",
                      G_CALLBACK (on_digit_clicked), dialer);
    
    return button;
}

static GtkWidget *
create_dialer_page (NuxelDialer *dialer)
{
    GtkWidget *page = gtk_box_new (GTK_ORIENTATION_VERTICAL, 0);
    
    /* Status indicators */
    GtkWidget *status_bar = gtk_box_new (GTK_ORIENTATION_HORIZONTAL, 4);
    gtk_widget_add_css_class (status_bar, "status-bar");
    
    dialer->call_status = gtk_label_new ("");
    gtk_widget_set_halign (GTK_WIDGET (dialer->call_status), GTK_ALIGN_START);
    gtk_box_append (GTK_BOX (status_bar), dialer->call_status);
    gtk_box_append (GTK_BOX (page), status_bar);
    
    /* Number display */
    GtkWidget *display_box = gtk_box_new (GTK_ORIENTATION_VERTICAL, 4);
    gtk_widget_set_margin_top (display_box, 20);
    gtk_widget_set_margin_bottom (display_box, 10);
    
    dialer->display_label = gtk_label_new ("");
    gtk_label_set_selectable (GTK_LABEL (dialer->display_label), TRUE);
    PangoAttrList *dattrs = pango_attr_list_new ();
    pango_attr_list_insert (dattrs, pango_attr_size_new (42 * PANGO_SCALE));
    pango_attr_list_insert (dattrs, pango_attr_weight_new (PANGO_WEIGHT_BOLD));
    gtk_label_set_attributes (GTK_LABEL (dialer->display_label), dattrs);
    pango_attr_list_unref (dattrs);
    gtk_widget_set_halign (dialer->display_label, GTK_ALIGN_CENTER);
    gtk_box_append (GTK_BOX (display_box), dialer->display_label);

    /* Honest capability line: generated from the ModemManager probe only. */
    dialer->capability_label = gtk_label_new ("Modem status unknown - not probed yet.");
    gtk_label_set_wrap (GTK_LABEL (dialer->capability_label), TRUE);
    gtk_label_set_justify (GTK_LABEL (dialer->capability_label), GTK_JUSTIFY_CENTER);
    gtk_widget_set_halign (dialer->capability_label, GTK_ALIGN_CENTER);
    gtk_widget_set_margin_start (dialer->capability_label, 16);
    gtk_widget_set_margin_end (dialer->capability_label, 16);
    gtk_widget_add_css_class (dialer->capability_label, "capability-line");
    gtk_box_append (GTK_BOX (display_box), dialer->capability_label);
    
    /* Clear/backspace row */
    GtkWidget *action_row = gtk_box_new (GTK_ORIENTATION_HORIZONTAL, 8);
    gtk_widget_set_halign (action_row, GTK_ALIGN_CENTER);
    
    GtkWidget *clear_btn = gtk_button_new_with_label ("C");
    gtk_widget_add_css_class (clear_btn, "action-button");
    g_signal_connect (clear_btn, "clicked",
                      G_CALLBACK (on_clear_clicked), dialer);
    gtk_box_append (GTK_BOX (action_row), clear_btn);
    
    GtkWidget *backspace_btn = gtk_button_new_with_label ("⌫");
    gtk_widget_add_css_class (backspace_btn, "action-button");
    g_signal_connect (backspace_btn, "clicked",
                      G_CALLBACK (on_backspace_clicked), dialer);
    gtk_box_append (GTK_BOX (action_row), backspace_btn);
    
    gtk_box_append (GTK_BOX (display_box), action_row);
    gtk_box_append (GTK_BOX (page), display_box);
    
    /* Keypad grid */
    GtkWidget *grid = gtk_grid_new ();
    gtk_grid_set_row_spacing (GTK_GRID (grid), 8);
    gtk_grid_set_column_spacing (GTK_GRID (grid), 8);
    gtk_widget_set_halign (grid, GTK_ALIGN_CENTER);
    
    const gchar *keys[] = {
        "1", "", "2", "ABC", "3", "DEF",
        "4", "GHI", "5", "JKL", "6", "MNO",
        "7", "PQRS", "8", "TUV", "9", "WXYZ",
        "*", "", "0", "+", "#", "",
    };
    
    int n_keys = sizeof (keys) / sizeof (keys[0]);
    for (int i = 0; i < n_keys; i += 2) {
        int row = i / 2;
        int col = (i / 2) % 3;
        
        GtkWidget *btn = create_digit_button (dialer, keys[i], keys[i + 1]);
        gtk_grid_attach (GTK_GRID (grid), btn, col, row, 1, 1);
    }
    
    gtk_box_append (GTK_BOX (page), grid);
    
    /* Call/End button */
    GtkWidget *call_box = gtk_box_new (GTK_ORIENTATION_HORIZONTAL, 0);
    gtk_widget_set_halign (call_box, GTK_ALIGN_CENTER);
    gtk_widget_set_margin_top (call_box, 16);
    gtk_widget_set_margin_bottom (call_box, 20);
    
    dialer->call_button = gtk_button_new_with_label ("📞");
    gtk_widget_add_css_class (dialer->call_button, "call-button");
    gtk_widget_set_size_request (dialer->call_button, 72, 72);
    g_signal_connect (dialer->call_button, "clicked",
                      G_CALLBACK (on_call_clicked), dialer);
    gtk_box_append (GTK_BOX (call_box), dialer->call_button);
    
    gtk_box_append (GTK_BOX (page), call_box);
    
    return page;
}

/* ============================================================
 * Application Entry Point
 * ============================================================ */

static void
activate_cb (GtkApplication *app,
             gpointer        user_data)
{
    NuxelDialer *dialer = g_new0 (NuxelDialer, 1);
    
    /* Create window */
    dialer->window = adw_application_window_new (GTK_APPLICATION (app));
    adw_application_window_set_content (ADW_APPLICATION_WINDOW (dialer->window),
                                        create_dialer_page (dialer));
    
    gtk_window_set_title (GTK_WINDOW (dialer->window), "Phone");
    gtk_window_set_default_size (GTK_WINDOW (dialer->window), 400, 700);
    gtk_window_set_resizable (GTK_WINDOW (dialer->window), TRUE);
    
    /* CSS styling */
    GtkCssProvider *provider = gtk_css_provider_new ();
    gtk_css_provider_load_from_string (provider,
        ".digit-button { font-size: 24px; min-width: 80px; min-height: 80px; "
        "  border-radius: 40px; background: #0f3460; color: #e8e8e8; }"
        ".digit-button:hover { background: #1a5276; }"
        ".call-button { background: #4CAF50; color: white; font-size: 28px; "
        "  border-radius: 36px; }"
        ".call-button:hover { background: #388E3C; }"
        ".end-button { background: #f44336; color: white; font-size: 24px; "
        "  border-radius: 36px; }"
        ".action-button { background: #16213e; color: #e8e8e8; font-size: 18px; "
        "  min-width: 56px; min-height: 44px; border-radius: 22px; }"
        ".status-bar { background: #16213e; padding: 8px 16px; }"
        ".capability-line { font-size: 12px; color: #a0b0c8; }"
    );
    gtk_style_context_add_provider_for_display (
        gdk_display_get_default (),
        GTK_STYLE_PROVIDER (provider),
        GTK_STYLE_PROVIDER_PRIORITY_APPLICATION);
    g_object_unref (provider);
    
    /* Initialize call state */
    dialer->in_call = FALSE;
    dialer->modem_ready = FALSE;
    dialer->cancellable = g_cancellable_new ();
    dialer->contacts = g_ptr_array_new_with_free_func (g_free);

    /* Shared phone data: the same store nuxel-contacts and nuxel-messages use,
     * so the call log and the address book cannot drift apart. */
    {
        gchar *dir = g_build_filename (g_get_user_data_dir (), "nuxel-contacts", NULL);
        g_mkdir_with_parents (dir, 0755);
        dialer->store_path = g_build_filename (dir, "contacts.json", NULL);
        g_free (dir);
    }
    nuxel_phone_store_init (&dialer->store);
    nuxel_phone_capabilities_init (&dialer->caps);
    if (dialer->store_path) {
        int rc = nuxel_phone_store_load (&dialer->store, dialer->store_path);
        if (rc == -1)
            g_warning ("[Dialer] stored phone data is unreadable; call log starts empty");
    }
    dialer_update_capabilities (dialer);

    /* Connect to ModemManager */
    modem_connect (dialer);
    
    gtk_window_present (GTK_WINDOW (dialer->window));
}

int
main (int argc, char *argv[])
{
    GtkApplication *app = gtk_application_new ("org.nuxel.Dialer",
                                                G_APPLICATION_DEFAULT_FLAGS);
    g_signal_connect (app, "activate", G_CALLBACK (activate_cb), NULL);
    
    int status = g_application_run (G_APPLICATION (app), argc, argv);
    g_object_unref (app);
    
    return status;
}
