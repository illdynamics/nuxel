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
#include "nuxel-radio-client.h"

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
    NuxelRadioClient radio;
    gboolean incoming, command_pending, refreshing, refresh_again;
    guint call_id;
    gchar *native_state;
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

static void native_refresh(gpointer user);
static void dialer_update_capabilities(NuxelDialer *dialer)
{
    if(!nuxel_radio_available(&dialer->radio) && dialer->capability_label)
        gtk_label_set_text(GTK_LABEL(dialer->capability_label),"Native call service unavailable");
}
static void dialer_log_call(NuxelDialer *dialer,const gchar *number,const gchar *state)
{
    /* Reload to preserve contact edits from Contacts. Never manufacture a
     * completed call after loss of the native service. */
    nuxel_phone_store_free(&dialer->store);nuxel_phone_store_init(&dialer->store);
    if(nuxel_phone_store_load(&dialer->store,dialer->store_path)<0)return;
    nuxel_phone_add_call(&dialer->store,number,dialer->incoming ? "in" : "out",state,nuxel_phone_now(),0);
    nuxel_phone_store_save(&dialer->store,dialer->store_path);
}
static void native_calls(GVariant *reply,const GError *error,gpointer user)
{
    NuxelDialer *dialer=user;
    dialer->refreshing=FALSE;
    if(!reply || error) {
        dialer->in_call=FALSE;dialer->incoming=FALSE;
        gtk_label_set_text(GTK_LABEL(dialer->call_status),error ? error->message : "Call state unknown");
    } else {
        GVariant *list=g_variant_get_child_value(reply,0);
        gboolean was_call=dialer->in_call;
        if(g_variant_n_children(list)) {
            guint id;const char *state,*number;gboolean incoming;
            g_variant_get_child(list,0,"(u&s&sb)",&id,&state,&number,&incoming);
            dialer->in_call=TRUE;
            dialer->incoming=!strcmp(state,"incoming") || !strcmp(state,"waiting");
            if(dialer->call_id!=id || g_strcmp0(dialer->native_state,state)) {
                /* Only the observed transition is recorded, never ACK=active. */
                dialer_log_call(dialer,number,state);
                dialer->call_id=id;g_free(dialer->native_state);dialer->native_state=g_strdup(state);
            }
            g_free(dialer->current_number);dialer->current_number=g_strdup(number);
            gtk_label_set_text(GTK_LABEL(dialer->display_label),number);
            gtk_label_set_text(GTK_LABEL(dialer->call_status),state);
        } else {
            if(was_call && dialer->current_number)dialer_log_call(dialer,dialer->current_number,"ended");
            dialer->in_call=FALSE;dialer->incoming=FALSE;dialer->call_id=0;
            g_clear_pointer(&dialer->native_state,g_free);
            if(!dialer->command_pending)gtk_label_set_text(GTK_LABEL(dialer->call_status),"No active call");
        }
        g_variant_unref(list);
    }
    dialer_update_ui(dialer);
    if(dialer->refresh_again) { dialer->refresh_again=FALSE;native_refresh(dialer); }
}
static void native_status(GVariant *reply,const GError *error,gpointer user)
{
    NuxelDialer *dialer=user;
    if(!reply || error) {
        dialer->refreshing=FALSE;dialer->modem_ready=FALSE;dialer->in_call=FALSE;dialer->incoming=FALSE;
        gtk_label_set_text(GTK_LABEL(dialer->call_status),"Call state unknown; native service unavailable");
        dialer_update_ui(dialer);return;
    }
    GVariant *dict=g_variant_get_child_value(reply,0);
    const char *registration="unknown",*audio="unknown",*list="unknown",*pending="false";
    g_variant_lookup(dict,"registration","&s",&registration);g_variant_lookup(dict,"audio_route","&s",&audio);
    g_variant_lookup(dict,"call_list","&s",&list);g_variant_lookup(dict,"pending","&s",&pending);
    dialer->modem_ready=!strcmp(registration,"REGISTERED_HOME") || !strcmp(registration,"REGISTERED_ROAMING");
    gchar *label=g_strdup_printf("Native voice · %s · call audio %s",registration,audio);
    gtk_label_set_text(GTK_LABEL(dialer->capability_label),label);g_free(label);
    gboolean valid=!strcmp(list,"received");g_variant_unref(dict);
    if(!valid) {
        dialer->refreshing=FALSE;dialer->in_call=FALSE;dialer->incoming=FALSE;
        gtk_label_set_text(GTK_LABEL(dialer->call_status),"Call state unknown");dialer_update_ui(dialer);return;
    }
    nuxel_radio_call(&dialer->radio,"GetCalls",NULL,"call:status",native_calls,dialer);
}
static void native_refresh(gpointer user)
{
    NuxelDialer *dialer=user;
    if(dialer->refreshing) { dialer->refresh_again=TRUE;return; }
    dialer->refreshing=TRUE;
    nuxel_radio_call(&dialer->radio,"GetVoiceStatus",NULL,NULL,native_status,dialer);
}
static gboolean native_poll(gpointer user)
{ native_refresh(user);return G_SOURCE_CONTINUE; }
static void modem_connect(NuxelDialer *dialer)
{
    nuxel_radio_connect(&dialer->radio,"org.nuxel.Dialer",native_refresh,dialer);
    g_timeout_add_seconds(3,native_poll,dialer);
}
static void native_command_done(GVariant *reply,const GError *error,gpointer user)
{
    NuxelDialer *dialer=user;dialer->command_pending=FALSE;
    gboolean accepted=FALSE;if(reply)g_variant_get(reply,"(b)",&accepted);
    gtk_label_set_text(GTK_LABEL(dialer->call_status),error ? error->message :
                       accepted ? "Command accepted; waiting for call state" : "Command rejected");
    dialer_update_ui(dialer);
}
static void native_command(NuxelDialer *dialer,const char *method,GVariant *args,const char *capability)
{
    if(dialer->command_pending)return;
    dialer->command_pending=TRUE;dialer_update_ui(dialer);
    nuxel_radio_call(&dialer->radio,method,args,capability,native_command_done,dialer);
}
static void native_answer(GtkWidget *button,gpointer user)
{
    (void)button;NuxelDialer *dialer=user;
    if(dialer->incoming)native_command(dialer,"AnswerCall",NULL,"call:initiate");
}

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

static void dialer_initiate_call(NuxelDialer *dialer)
{
    const char *number=gtk_label_get_text(GTK_LABEL(dialer->display_label));
    if(!number || !*number)return;
    if(!dialer->modem_ready) {
        gtk_label_set_text(GTK_LABEL(dialer->call_status),"Voice network not registered");return;
    }
    native_command(dialer,"Dial",g_variant_new("(s)",number),"call:initiate");
}
static void dialer_end_call(NuxelDialer *dialer)
{ native_command(dialer,"HangupCall",NULL,"call:end"); }
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
                              !dialer->command_pending && (has_number || dialer->in_call));
    if(dialer->end_button) {
        gtk_widget_set_visible(dialer->end_button,dialer->incoming);
        gtk_widget_set_sensitive(dialer->end_button,!dialer->command_pending);
    }

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
        int row = (i / 2) / 3;
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
    dialer->end_button=gtk_button_new_with_label("Answer");
    g_signal_connect(dialer->end_button,"clicked",G_CALLBACK(native_answer),dialer);
    gtk_widget_set_visible(dialer->end_button,FALSE);
    gtk_box_append(GTK_BOX(call_box),dialer->end_button);
    
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
    AdwStyleManager *style = adw_style_manager_get_default();
    adw_style_manager_set_color_scheme(style, ADW_COLOR_SCHEME_FORCE_DARK);
    
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
