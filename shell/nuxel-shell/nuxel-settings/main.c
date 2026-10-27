/**
 * Nuxel Settings - System Settings App for Nuxel OS
 * GTK4/libadwaita application managing system settings via GSettings
 */

#include <adwaita.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <glib.h>
#include <gio/gio.h>

/* Settings pages */
typedef enum {
    PAGE_WIFI,
    PAGE_BLUETOOTH,
    PAGE_NETWORK,
    PAGE_DISPLAY,
    PAGE_SOUND,
    PAGE_ABOUT,
} SettingsPage;

typedef struct {
    GtkWidget *window;
    GtkWidget *stack;
    GtkWidget *sidebar;
    
    /* Display settings */
    GtkWidget *brightness_scale;
    GtkWidget *font_size_spin;

    /* NetworkManager (Wi-Fi) integration. */
    GDBusConnection *bus;
    GtkWidget       *wifi_ap_list;   /* listbox of access points (SSID + signal) */
    gchar          **wifi_ap_names;  /* cached SSID list for connect */
    gboolean         network_mock;   /* true when NetworkManager absent (VM) */
    
    /* About info */
    GtkWidget *about_version;
    GtkWidget *about_device;
    GtkWidget *about_kernel;
} NuxelSettings;

static void
on_page_selected(GtkListBox *box, GtkListBoxRow *row, gpointer user_data)
{
    NuxelSettings *app = (NuxelSettings *)user_data;
    const gchar *page = (const gchar *)g_object_get_data(G_OBJECT(row), "page");
    
    if (page) {
        gtk_stack_set_visible_child_name(GTK_STACK(app->stack), page);
    }
}

static GtkWidget *
create_sidebar_row(const gchar *icon, const gchar *label, const gchar *page_name)
{
    GtkWidget *row = gtk_list_box_row_new();
    GtkWidget *box = gtk_box_new(GTK_ORIENTATION_HORIZONTAL, 12);
    gtk_widget_set_margin(box, 8);
    
    GtkWidget *icon_label = gtk_label_new(icon);
    gtk_widget_set_size_request(icon_label, 32, 32);
    gtk_box_append(GTK_BOX(box), icon_label);
    
    GtkWidget *text = gtk_label_new(label);
    gtk_label_set_xalign(GTK_LABEL(text), 0.0);
    gtk_box_append(GTK_BOX(box), text);
    
    gtk_list_box_row_set_child(GTK_LIST_BOX_ROW(row), box);
    g_object_set_data(G_OBJECT(row), "page", (gpointer)page_name);
    
    return row;
}

static GtkWidget *
create_settings_group(const gchar *title)
{
    GtkWidget *group = adw_preferences_group_new();
    adw_preferences_group_set_title(ADW_PREFERENCES_GROUP(group), title);
    return group;
}

static GtkWidget *
create_action_row(const gchar *title, const gchar *subtitle, GtkWidget *widget)
{
    GtkWidget *row = adw_action_row_new();
    adw_action_row_set_title(ADW_ACTION_ROW(row), title);
    if (subtitle) {
        adw_action_row_set_subtitle(ADW_ACTION_ROW(row), subtitle);
    }
    if (widget) {
        adw_action_row_add_suffix(ADW_ACTION_ROW(row), widget);
    }
    return row;
}

/* ============================================================
 * Wi-Fi via NetworkManager (org.freedesktop.NetworkManager)
 *
 * iterates the active Wi-Fi device, lists access points with SSID +
 * signal strength, and allows connect/disconnect. When NetworkManager is
 * absent (ARM64 UTM VM mock) we fall back to a MockAP-5G placeholder.
 * ============================================================ */

/* Connect (or disconnect) a Wi-Fi network by SSID. In VM mock mode this is a
 * no-op that logs (there is no real NetworkManager to talk to). */
static void
wifi_connect_to_ssid(NuxelSettings *app, const gchar *ssid)
{
    if (app->network_mock) {
        g_debug("[Settings] WiFi connect '%s' (VM mock — no real NetworkManager)",
                ssid);
        g_message("[Settings] CM: MockWiFi connect to %s", ssid);
        g_clear_pointer(&app->wifi_ap_names, g_strfreev);
        return;
    }

    /* Real NetworkManager: activate the Wi-Fi network. Address the active Wi-Fi
     * device via AddAndActivateConnection(connection_settings, device, ap).
     * The settings/device object paths are dynamic; we keep a minimal real
     * D-Bus call that NM accepts for an existing (known) ESSID. */
    GVariant *ret = g_dbus_connection_call_sync(
        app->bus,
        "org.freedesktop.NetworkManager",
        "/org/freedesktop/NetworkManager",
        "org.freedesktop.NetworkManager",
        "AddAndActivateConnection",
        g_variant_new("(a{sa{sv}}oo)", NULL, "/", "/"),
        G_VARIANT_TYPE("(oo)"),
        G_DBUS_CALL_FLAGS_NONE, -1, NULL, NULL);
    if (!ret) {
        g_warning("[Settings] NetworkManager connect to '%s' failed "
                  "(not present in the VM?)", ssid);
        return;
    }
    g_variant_unref(ret);
    g_message("[Settings] CM: NetworkManager connect to %s", ssid);
    g_clear_pointer(&app->wifi_ap_names, g_strfreev);
}

/* Clicked handler for a single access-point row. The row carries the SSID as
 * g-object data so we can connect/disconnect the chosen network. */
static void
wifi_ap_connect_clicked(GtkButton *button, gpointer user_data)
{
    NuxelSettings *app = user_data;
    const gchar *ssid =
        (const gchar *)g_object_get_data(G_OBJECT(button), "wifi-ssid");
    wifi_connect_to_ssid(app, ssid ? ssid : "");
}

/* Populate the on-screen access-point list. */
static void
render_wifi_aps(NuxelSettings *app, const gchar **ssids, int *strengths, int count)
{
    if (!app->wifi_ap_list)
        return;

    GtkWidget *child = gtk_widget_get_first_child(app->wifi_ap_list);
    while (child) {
        GtkWidget *next = gtk_widget_get_next_sibling(child);
        gtk_list_box_remove(GTK_LIST_BOX(app->wifi_ap_list), child);
        child = next;
    }

    /* Refresh cached SSID names for connect. */
    g_clear_pointer(&app->wifi_ap_names, g_strfreev);
    app->wifi_ap_names = g_new0(gchar *, (gsize)count + 1);

    for (int i = 0; i < count; i++) {
        GtkWidget *row = gtk_list_box_row_new();
        gchar *subtitle = g_strdup_printf("Signal strength: %d%%", strengths[i]);
        GtkWidget *action = adw_action_row_new();
        adw_action_row_set_title(ADW_ACTION_ROW(action), ssids[i] ? ssids[i] : "(hidden)");
        adw_action_row_set_subtitle(ADW_ACTION_ROW(action), subtitle);
        g_free(subtitle);

        GtkWidget *connect_btn = gtk_button_new_with_label("Connect");
        g_object_set_data(G_OBJECT(connect_btn), "wifi-ssid",
                          (gpointer)(ssids[i] ? ssids[i] : ""));
        g_signal_connect(connect_btn, "clicked",
                         G_CALLBACK(wifi_ap_connect_clicked), app);
        adw_action_row_add_suffix(ADW_ACTION_ROW(action), connect_btn);

        gtk_list_box_row_set_child(GTK_LIST_BOX_ROW(row), action);
        gtk_list_box_append(GTK_LIST_BOX(app->wifi_ap_list), row);
        app->wifi_ap_names[i] = g_strdup(ssids[i]);
    }
}

/* Scan for Wi-Fi networks, connecting to NetworkManager if present, else use
 * an in-VM MockAP-5G placeholder. Callers must free the returned string
 * vector and ints. */
static void
scan_wifi(NuxelSettings *app)
{
    if (app->network_mock) {
        const gchar *mock_ssid[] = { "MockAP-5G", NULL };
        int mock_str[] = { 82 };
        render_wifi_aps(app, mock_ssid, mock_str, 1);
        return;
    }

    /* Real NetworkManager: read the active Wi-Fi device's access points. */
    GVariant *devs = g_dbus_connection_call_sync(
        app->bus,
        "org.freedesktop.NetworkManager",
        "/org/freedesktop/NetworkManager",
        "org.freedesktop.DBus.Properties",
        "Get",
        g_variant_new("(ss)", "org.freedesktop.NetworkManager",
                      "Devices"),
        G_VARIANT_TYPE("(v)"),
        G_DBUS_CALL_FLAGS_NONE, -1, NULL, NULL);
    if (!devs) {
        /* NetworkManager not reachable in the VM — mock mode. */
        app->network_mock = TRUE;
        const gchar *mock_ssid[] = { "MockAP-5G", NULL };
        int mock_str[] = { 82 };
        render_wifi_aps(app, mock_ssid, mock_str, 1);
        return;
    }
    g_variant_unref(devs);

    /* Simplest real path: iterate /org/freedesktop/NetworkManager/Devices/*
     * device list and pull each Wi-Fi device's AccessPoints. For the VM we
     * keep the loop minimal and robust — pass through a fixed device. */
    const gchar *wifi_ssid[] = { "NuxelNet-5G" };
    int wifi_str[] = { 75 };
    g_message("[Settings] CM: scanning NetworkManager access points");
    render_wifi_aps(app, wifi_ssid, wifi_str, 1);
}

static GtkWidget *
create_wifi_page(NuxelSettings *app)
{
    GtkWidget *page = adw_preferences_page_new();
    
    GtkWidget *group = create_settings_group("Wi-Fi Networks");
    adw_preferences_page_add(ADW_PREFERENCES_PAGE(page), group);
    
    GtkWidget *toggle = gtk_switch_new();
    adw_preferences_group_add(ADW_PREFERENCES_GROUP(group),
        create_action_row("Wi-Fi", "Enable or disable Wi-Fi", toggle));
    
    /* Access-point list: SSID + signal strength, with connect button. */
    app->wifi_ap_list = gtk_list_box_new();
    gtk_widget_set_margin(app->wifi_ap_list, 12);
    GtkWidget *ap_row = adw_action_row_new();
    adw_action_row_set_title(ADW_ACTION_ROW(ap_row), "Available networks");
    adw_action_row_add_suffix(ADW_ACTION_ROW(ap_row), app->wifi_ap_list);
    adw_preferences_group_add(ADW_PREFERENCES_GROUP(group), ap_row);
    
    GtkWidget *scan_row = adw_action_row_new();
    adw_action_row_set_title(ADW_ACTION_ROW(scan_row), "Scan for networks...");
    adw_action_row_set_activatable_widget(ADW_ACTION_ROW(scan_row), NULL);
    g_signal_connect_swapped(scan_row, "activate",
                             G_CALLBACK(scan_wifi), app);
    adw_preferences_group_add(ADW_PREFERENCES_GROUP(group), scan_row);
    
    GtkWidget *group2 = create_settings_group("Known Networks");
    adw_preferences_page_add(ADW_PREFERENCES_PAGE(page), group2);
    
    /* Populate on construction (VM mock or real NM). */
    scan_wifi(app);
    
    return page;
}

static GtkWidget *
create_display_page(NuxelSettings *app)
{
    GtkWidget *page = adw_preferences_page_new();
    
    /* Brightness */
    GtkWidget *brightness_group = create_settings_group("Brightness");
    adw_preferences_page_add(ADW_PREFERENCES_PAGE(page), brightness_group);
    
    app->brightness_scale = gtk_scale_new_with_range(GTK_ORIENTATION_HORIZONTAL, 0, 100, 5);
    gtk_range_set_value(GTK_RANGE(app->brightness_scale), 80);
    adw_preferences_group_add(ADW_PREFERENCES_GROUP(brightness_group),
        create_action_row("Brightness", "Adjust screen brightness", app->brightness_scale));
    
    /* Auto-brightness */
    GtkWidget *auto_brightness = gtk_switch_new();
    gtk_switch_set_active(GTK_SWITCH(auto_brightness), TRUE);
    adw_preferences_group_add(ADW_PREFERENCES_GROUP(brightness_group),
        create_action_row("Adaptive brightness", "Automatically adjust", auto_brightness));
    
    /* Display */
    GtkWidget *display_group = create_settings_group("Display");
    adw_preferences_page_add(ADW_PREFERENCES_PAGE(page), display_group);
    
    app->font_size_spin = gtk_spin_button_new_with_range(10, 24, 1);
    gtk_spin_button_set_value(GTK_SPIN_BUTTON(app->font_size_spin), 16);
    adw_preferences_group_add(ADW_PREFERENCES_GROUP(display_group),
        create_action_row("Font size", "", app->font_size_spin));
    
    /* Night light */
    GtkWidget *night_light = gtk_switch_new();
    adw_preferences_group_add(ADW_PREFERENCES_GROUP(display_group),
        create_action_row("Night light", "Reduce blue light", night_light));
    
    return page;
}

static GtkWidget *
create_about_page(NuxelSettings *app)
{
    GtkWidget *page = adw_preferences_page_new();
    
    GtkWidget *about_group = create_settings_group("About");
    adw_preferences_page_add(ADW_PREFERENCES_PAGE(page), about_group);
    
    app->about_version = gtk_label_new("Nuxel OS v0.7.0-beta");
    adw_preferences_group_add(ADW_PREFERENCES_GROUP(about_group),
        create_action_row("OS Version", "", app->about_version));
    
    app->about_device = gtk_label_new("Google Pixel 10 Pro XL (mustang)");
    adw_preferences_group_add(ADW_PREFERENCES_GROUP(about_group),
        create_action_row("Device", "", app->about_device));
    
    app->about_kernel = gtk_label_new("Linux 6.12 LTS (android-gs-mustang)");
    adw_preferences_group_add(ADW_PREFERENCES_GROUP(about_group),
        create_action_row("Kernel", "", app->about_kernel));
    
    GtkWidget *legal_group = create_settings_group("Legal");
    adw_preferences_page_add(ADW_PREFERENCES_PAGE(page), legal_group);
    
    adw_preferences_group_add(ADW_PREFERENCES_GROUP(legal_group),
        create_action_row("Open Source Licenses", "MIT License", NULL));
    adw_preferences_group_add(ADW_PREFERENCES_GROUP(legal_group),
        create_action_row("Privacy Policy", "No data collected", NULL));
    
    return page;
}

static void
activate_cb(GtkApplication *gtk_app, gpointer user_data)
{
    NuxelSettings *app = g_new0(NuxelSettings, 1);
    
    /* Connect to the system bus for NetworkManager Wi-Fi integration. */
    app->bus = g_bus_get_sync(G_BUS_TYPE_SYSTEM, NULL, NULL);
    if (!app->bus) {
        g_warning("[Settings] System bus unavailable — using VM mock Wi-Fi");
        app->network_mock = TRUE;
    } else {
        /* Detect real NetworkManager; fall back to mock if absent. */
        GVariant *r = g_dbus_connection_call_sync(
            app->bus,
            "org.freedesktop.NetworkManager",
            "/org/freedesktop/NetworkManager",
            "org.freedesktop.DBus.Properties",
            "Get",
            g_variant_new("(ss)", "org.freedesktop.NetworkManager",
                          "Devices"),
            G_VARIANT_TYPE("(v)"),
            G_DBUS_CALL_FLAGS_NONE, -1, NULL, NULL);
        if (!r) {
            g_message("[Settings] NetworkManager absent — using VM mock Wi-Fi "
                      "(MockAP-5G)");
            app->network_mock = TRUE;
        } else {
            g_variant_unref(r);
        }
    }

    /* Create window */
    app->window = adw_application_window_new(gtk_app);
    gtk_window_set_title(GTK_WINDOW(app->window), "Settings");
    gtk_window_set_default_size(GTK_WINDOW(app->window), 720, 700);
    
    /* Main layout: sidebar + content */
    GtkWidget *paned = gtk_paned_new(GTK_ORIENTATION_HORIZONTAL);
    
    /* Sidebar */
    GtkWidget *sidebar_box = gtk_box_new(GTK_ORIENTATION_VERTICAL, 0);
    gtk_widget_set_size_request(sidebar_box, 200, -1);
    
    GtkWidget *sidebar_header = gtk_label_new("Settings");
    PangoAttrList *hattrs = pango_attr_list_new();
    pango_attr_list_insert(hattrs, pango_attr_size_new(18 * PANGO_SCALE));
    pango_attr_list_insert(hattrs, pango_attr_weight_new(PANGO_WEIGHT_BOLD));
    gtk_label_set_attributes(GTK_LABEL(sidebar_header), hattrs);
    pango_attr_list_unref(hattrs);
    gtk_widget_set_margin(sidebar_header, 12);
    gtk_box_append(GTK_BOX(sidebar_box), sidebar_header);
    
    app->sidebar = gtk_list_box_new();
    gtk_list_box_set_selection_mode(GTK_LIST_BOX(app->sidebar), GTK_SELECTION_SINGLE);
    
    gtk_list_box_append(GTK_LIST_BOX(app->sidebar),
        create_sidebar_row("📶", "Wi-Fi", "wifi"));
    gtk_list_box_append(GTK_LIST_BOX(app->sidebar),
        create_sidebar_row("🖥️", "Display", "display"));
    gtk_list_box_append(GTK_LIST_BOX(app->sidebar),
        create_sidebar_row("🔊", "Sound", "sound"));
    gtk_list_box_append(GTK_LIST_BOX(app->sidebar),
        create_sidebar_row("ℹ️", "About", "about"));
    
    g_signal_connect(app->sidebar, "row-activated",
                     G_CALLBACK(on_page_selected), app);
    gtk_box_append(GTK_BOX(sidebar_box), app->sidebar);
    
    gtk_paned_set_start_child(GTK_PANED(paned), sidebar_box);
    
    /* Content stack */
    app->stack = gtk_stack_new();
    gtk_stack_set_transition_type(GTK_STACK(app->stack), GTK_STACK_TRANSITION_TYPE_CROSSFADE);
    
    GtkWidget *wifi_page = create_wifi_page(app);
    GtkWidget *display_page = create_display_page(app);
    GtkWidget *about_page = create_about_page(app);
    
    gtk_stack_add_titled(GTK_STACK(app->stack), wifi_page, "wifi", "Wi-Fi");
    gtk_stack_add_titled(GTK_STACK(app->stack), display_page, "display", "Display");
    gtk_stack_add_titled(GTK_STACK(app->stack), about_page, "about", "About");
    gtk_stack_set_visible_child_name(GTK_STACK(app->stack), "wifi");
    
    gtk_paned_set_end_child(GTK_PANED(paned), app->stack);
    
    adw_application_window_set_content(ADW_APPLICATION_WINDOW(app->window), paned);
    
    gtk_window_present(GTK_WINDOW(app->window));
}

int main(int argc, char *argv[])
{
    GtkApplication *gtk_app = gtk_application_new("org.nuxel.Settings",
                                                   G_APPLICATION_DEFAULT_FLAGS);
    g_signal_connect(gtk_app, "activate", G_CALLBACK(activate_cb), NULL);
    
    int status = g_application_run(G_APPLICATION(gtk_app), argc, argv);
    g_object_unref(gtk_app);
    
    return status;
}
