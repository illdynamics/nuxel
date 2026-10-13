/**
 * Nuxel App Permissions Manager
 * GTK4/libadwaita application for viewing and managing per-app permission grants.
 *
 * Architecture:
 *   - Reads permissions from /var/lib/nuxel/permissions/*.json
 *   - Queries nuxel-bridge D-Bus service for live permission state
 *   - Displays apps in a AdwPreferencesPage with per-app permission rows
 *   - Allows grant, deny, revoke, and "Revoke All" operations
 *   - Shows risk level and last-used timestamp per capability
 *   - Integrates with nuxel-portal D-Bus to update permission state
 *
 * Target: Phosh on Wayland, Pixel 10 Pro XL (mustang) display
 * Toolkit: GTK4 + libadwaita
 */

#include <adwaita.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <glib.h>
#include <gio/gio.h>
#include <json-glib/json-glib.h>
#include <dirent.h>
#include <time.h>

/* ── Constants ─────────────────────────────────────────────────────────── */

#define PERMISSIONS_DIR "/var/lib/nuxel/permissions"
#define PORTAL_DBUS_NAME "org.nuxel.Portal"
#define PORTAL_DBUS_PATH "/org/nuxel/Portal"
#define PORTAL_DBUS_INTERFACE "org.nuxel.Portal"

/* ── Data Structures ───────────────────────────────────────────────────── */

typedef struct {
    gchar *app_id;
    gchar *app_name;
    gchar *icon_name;
    GPtrArray *capabilities; /* of Capability* */
} AppInfo;

typedef struct {
    gchar *capability;
    gchar *description;
    gchar *duration;     /* "once", "session", "always", or "" if denied */
    gdouble granted_at;
    gboolean granted;
} Capability;

typedef struct {
    GtkWidget *window;
    GtkWidget *stack;
    GtkWidget *app_list_page;
    GtkWidget *app_detail_page;
    GtkWidget *app_list_box;
    GtkWidget *detail_app_name;
    GtkWidget *detail_app_id;
    GtkWidget *detail_permissions_group;
    GtkWidget *revoke_all_button;
    GtkWidget *toast_overlay;
    GPtrArray *apps;  /* of AppInfo* */
    GDBusProxy *portal_proxy;
    GDBusProxy *bridge_proxy;
} PermissionsApp;

/* ── Capability Risk & Metadata ────────────────────────────────────────── */

typedef struct {
    const gchar *capability;
    const gchar *description;
    const gchar *risk;       /* "low", "medium", "high" */
    const gchar *icon_name;
} CapabilityMeta;

static CapabilityMeta capability_metadata[] = {
    {"sms",           "Send SMS messages",             "high",   "chat-symbolic"},
    {"call",          "Place phone calls",              "high",   "call-start-symbolic"},
    {"contacts",      "Access contacts",                "high",   "contacts-symbolic"},
    {"phone_status",  "Read phone status",              "low",    "network-cellular-signal-excellent-symbolic"},
    {"location",      "Access GPS location",            "high",   "mark-location-symbolic"},
    {"camera",        "Use the camera",                 "high",   "camera-photo-symbolic"},
    {"microphone",    "Use the microphone",             "high",   "audio-input-microphone-symbolic"},
    {"settings",      "Change system settings",         "medium", "preferences-system-symbolic"},
    {"calendar",      "Access calendar",                "medium", "office-calendar-symbolic"},
    {"bluetooth",     "Use Bluetooth",                  "medium", "bluetooth-symbolic"},
    {"usb",           "Access USB devices",             "medium", "drive-removable-media-symbolic"},
    {"clipboard",     "Access clipboard",               "high",   "edit-paste-symbolic"},
    {"background",    "Run in background",               "medium", "system-run-symbolic"},
    {NULL, NULL, NULL, NULL}
};

static CapabilityMeta *
find_capability_meta(const gchar *capability) {
    for (gint i = 0; capability_metadata[i].capability != NULL; i++) {
        if (g_strcmp0(capability_metadata[i].capability, capability) == 0)
            return &capability_metadata[i];
    }
    return NULL;
}

static const gchar *
get_capability_description(const gchar *capability) {
    CapabilityMeta *meta = find_capability_meta(capability);
    return meta ? meta->description : capability;
}

static const gchar *
get_capability_risk(const gchar *capability) {
    CapabilityMeta *meta = find_capability_meta(capability);
    return meta ? meta->risk : "medium";
}

static const gchar *
get_capability_icon(const gchar *capability) {
    CapabilityMeta *meta = find_capability_meta(capability);
    return meta ? meta->icon_name : "dialog-question-symbolic";
}

/* ── App Name Resolution ───────────────────────────────────────────────── */

static const gchar *
resolve_app_name(const gchar *app_id) {
    static const struct {
        const gchar *id;
        const gchar *name;
    } app_names[] = {
        {"org.nuxel.Home",       "Nuxel Home"},
        {"org.nuxel.Mail",       "Nuxel Mail"},
        {"org.nuxel.Calendar",   "Nuxel Calendar"},
        {"org.nuxel.Notes",      "Nuxel Notes"},
        {"org.nuxel.Files",      "Nuxel Files"},
        {"org.nuxel.Camera",     "Nuxel Camera"},
        {"org.nuxel.dialer",     "Dialer"},
        {"org.nuxel.messages",   "Messages"},
        {"org.nuxel.contacts",   "Contacts"},
        {"org.nuxel.settings",   "Settings"},
        {"org.nuxel.calculator", "Calculator"},
        {"org.nuxel.maps",       "Maps"},
        {"org.nuxel.weather",    "Weather"},
        {"org.nuxel.clock",      "Clock"},
        {"org.nuxel.terminal",   "Terminal"},
        {NULL, NULL}
    };
    for (gint i = 0; app_names[i].id != NULL; i++) {
        if (g_strcmp0(app_names[i].id, app_id) == 0)
            return app_names[i].name;
    }
    return app_id;
}

static const gchar *
resolve_app_icon(const gchar *app_id) {
    static const struct {
        const gchar *id;
        const gchar *icon;
    } app_icons[] = {
        {"org.nuxel.Home",       "go-home-symbolic"},
        {"org.nuxel.Mail",       "mail-symbolic"},
        {"org.nuxel.Calendar",   "office-calendar-symbolic"},
        {"org.nuxel.Notes",      "x-office-document-symbolic"},
        {"org.nuxel.Files",      "folder-symbolic"},
        {"org.nuxel.Camera",     "camera-photo-symbolic"},
        {"org.nuxel.dialer",     "call-start-symbolic"},
        {"org.nuxel.messages",   "chat-symbolic"},
        {"org.nuxel.contacts",   "contacts-symbolic"},
        {"org.nuxel.settings",   "preferences-system-symbolic"},
        {"org.nuxel.calculator", "accessories-calculator-symbolic"},
        {NULL, NULL}
    };
    for (gint i = 0; app_icons[i].id != NULL; i++) {
        if (g_strcmp0(app_icons[i].id, app_id) == 0)
            return app_icons[i].icon;
    }
    return "application-x-executable-symbolic";
}

/* ── Permission File Parsing ───────────────────────────────────────────── */

static GPtrArray *
parse_permissions_file(const gchar *filepath) {
    GPtrArray *caps = g_ptr_array_new_with_free_func(g_free);

    JsonParser *parser = json_parser_new();
    GError *error = NULL;

    if (!json_parser_load_from_file(parser, filepath, &error)) {
        g_warning("Failed to parse %s: %s", filepath, error->message);
        g_error_free(error);
        g_object_unref(parser);
        return caps;
    }

    JsonNode *root = json_parser_get_root(parser);
    if (!root || !JSON_NODE_HOLDS_OBJECT(root)) {
        g_object_unref(parser);
        return caps;
    }

    JsonObject *obj = json_node_get_object(root);

    GList *members = json_object_get_members(obj);
    for (GList *l = members; l != NULL; l = l->next) {
        const gchar *cap_key = (const gchar *)l->data;
        JsonNode *val = json_object_get_member(obj, cap_key);

        if (!val || !JSON_NODE_HOLDS_OBJECT(val))
            continue;

        JsonObject *cap_obj = json_node_get_object(val);

        Capability *cap = g_new0(Capability, 1);
        cap->capability = g_strdup(cap_key);

        JsonNode *duration_node = json_object_get_member(cap_obj, "duration");
        if (duration_node && JSON_NODE_HOLDS_VALUE(duration_node)) {
            cap->duration = g_strdup(json_node_get_string(duration_node));
        } else {
            cap->duration = g_strdup("");
        }

        JsonNode *granted_at_node = json_object_get_member(cap_obj, "granted_at");
        if (granted_at_node && JSON_NODE_HOLDS_VALUE(granted_at_node)) {
            cap->granted_at = json_node_get_double(granted_at_node);
        } else {
            cap->granted_at = 0.0;
        }

        cap->granted = (g_strcmp0(cap->duration, "always") == 0);

        g_ptr_array_add(caps, cap);
    }

    g_list_free(members);
    g_object_unref(parser);
    return caps;
}

static AppInfo *
app_info_new(const gchar *app_id, GPtrArray *caps) {
    AppInfo *info = g_new0(AppInfo, 1);
    info->app_id = g_strdup(app_id);
    info->app_name = g_strdup(resolve_app_name(app_id));
    info->icon_name = g_strdup(resolve_app_icon(app_id));
    info->capabilities = caps;
    return info;
}

static void
app_info_free(AppInfo *info) {
    if (!info) return;
    g_free(info->app_id);
    g_free(info->app_name);
    g_free(info->icon_name);
    if (info->capabilities) {
        for (guint i = 0; i < info->capabilities->len; i++) {
            Capability *cap = g_ptr_array_index(info->capabilities, i);
            g_free(cap->capability);
            g_free(cap->description);
            g_free(cap->duration);
            g_free(cap);
        }
        g_ptr_array_free(info->capabilities, TRUE);
    }
    g_free(info);
}

static GPtrArray *
scan_all_permissions(void) {
    GPtrArray *apps = g_ptr_array_new_with_free_func((GDestroyNotify)app_info_free);

    DIR *dir = opendir(PERMISSIONS_DIR);
    if (!dir) {
        g_warning("Cannot open permissions directory: %s", PERMISSIONS_DIR);
        return apps;
    }

    struct dirent *entry;
    while ((entry = readdir(dir)) != NULL) {
        if (entry->d_type != DT_REG && entry->d_type != DT_LNK)
            continue;

        const gchar *name = entry->d_name;
        if (!g_str_has_suffix(name, ".json"))
            continue;

        /* Extract app_id from filename: "org.nuxel.Calendar.json" -> "org.nuxel.Calendar" */
        gchar *app_id = g_strndup(name, strlen(name) - 5); /* remove .json */

        gchar *filepath = g_build_filename(PERMISSIONS_DIR, name, NULL);
        GPtrArray *caps = parse_permissions_file(filepath);
        g_free(filepath);

        AppInfo *info = app_info_new(app_id, caps);
        g_ptr_array_add(apps, info);
        g_free(app_id);
    }
    closedir(dir);

    return apps;
}

/* ── D-Bus Integration ────────────────────────────────────────────────── */

static GDBusProxy *
get_portal_proxy(void) {
    GDBusProxy *proxy = NULL;
    GError *error = NULL;

    proxy = g_dbus_proxy_new_for_bus_sync(
        G_BUS_TYPE_SYSTEM,
        G_DBUS_PROXY_FLAGS_NONE,
        NULL,
        PORTAL_DBUS_NAME,
        PORTAL_DBUS_PATH,
        PORTAL_DBUS_INTERFACE,
        NULL,
        &error
    );

    if (!proxy) {
        g_warning("Failed to connect to portal D-Bus: %s", error->message);
        g_error_free(error);
    }

    return proxy;
}

static void
on_permission_revoked(GObject *source, GAsyncResult *res, gpointer user_data) {
    GError *error = NULL;
    GVariant *result = g_dbus_proxy_call_finish(
        G_DBUS_PROXY(source), res, &error
    );

    if (error) {
        g_warning("Failed to revoke permission: %s", error->message);
        g_error_free(error);
    } else {
        g_variant_unref(result);
    }
}

static void
revoke_permission_dbus(const gchar *app_id, const gchar *capability) {
    GDBusProxy *proxy = get_portal_proxy();
    if (!proxy) return;

    GVariant *params = g_variant_new("(ss)", app_id, capability);
    g_dbus_proxy_call(
        proxy,
        "RevokePermission",
        params,
        G_DBUS_CALL_FLAGS_NONE,
        -1,
        NULL,
        on_permission_revoked,
        NULL
    );

    g_object_unref(proxy);
}

static void
revoke_all_permissions_dbus(const gchar *app_id) {
    GDBusProxy *proxy = get_portal_proxy();
    if (!proxy) return;

    GVariant *params = g_variant_new("(s)", app_id);
    g_dbus_proxy_call(
        proxy,
        "RevokePermission",
        params,
        G_DBUS_CALL_FLAGS_NONE,
        -1,
        NULL,
        on_permission_revoked,
        NULL
    );

    g_object_unref(proxy);
}

/* ── UI: App List Page ────────────────────────────────────────────────── */

static void
show_app_detail(PermissionsApp *app, AppInfo *info);

static void
build_app_list(PermissionsApp *app) {
    /* Clear existing rows */
    GtkWidget *listbox = app->app_list_box;
    GtkWidget *child = gtk_widget_get_first_child(listbox);
    while (child) {
        GtkWidget *next = gtk_widget_get_next_sibling(child);
        gtk_list_box_remove(GTK_LIST_BOX(listbox), child);
        child = next;
    }

    /* Rescan permissions */
    if (app->apps) {
        for (guint i = 0; i < app->apps->len; i++) {
            app_info_free(g_ptr_array_index(app->apps, i));
        }
        g_ptr_array_free(app->apps, TRUE);
    }
    app->apps = scan_all_permissions();

    /* Build rows */
    for (guint i = 0; i < app->apps->len; i++) {
        AppInfo *info = g_ptr_array_index(app->apps, i);

        AdwActionRow *row = ADW_ACTION_ROW(adw_action_row_new());
        adw_action_row_set_title(row, info->app_name);
        adw_action_row_set_subtitle(row, info->app_id);

        /* Icon */
        GtkWidget *icon = gtk_image_new_from_icon_name(info->icon_name);
        gtk_image_set_pixel_size(GTK_IMAGE(icon), 32);
        adw_action_row_add_prefix(ADW_ACTION_ROW(row), icon);

        /* Permission summary badge */
        guint granted_count = 0;
        for (guint j = 0; j < info->capabilities->len; j++) {
            Capability *cap = g_ptr_array_index(info->capabilities, j);
            if (cap->granted) granted_count++;
        }

        gchar *summary = g_strdup_printf("%u permissions granted", granted_count);
        adw_action_row_set_subtitle(row, summary);
        g_free(summary);

        /* Risk indicator */
        gboolean has_high = FALSE;
        for (guint j = 0; j < info->capabilities->len; j++) {
            Capability *cap = g_ptr_array_index(info->capabilities, j);
            if (cap->granted && g_strcmp0(get_capability_risk(cap->capability), "high") == 0) {
                has_high = TRUE;
                break;
            }
        }

        if (has_high) {
            GtkWidget *badge = adw_badge_new();
            adw_badge_set_text(ADW_BADGE(badge), "!");
            adw_action_row_add_suffix(ADW_ACTION_ROW(row), badge);
        }

        /* Select handler */
        g_object_set_data(G_OBJECT(row), "app-info", info);
        g_signal_connect_swapped(row, "activated",
            G_CALLBACK(show_app_detail), app);

        gtk_list_box_append(GTK_LIST_BOX(listbox), GTK_WIDGET(row));
    }
}

/* ── UI: App Detail Page ──────────────────────────────────────────────── */

static void
on_revoke_capability(GtkButton *btn, gpointer user_data) {
    PermissionsApp *app = (PermissionsApp *)user_data;
    const gchar *capability = (const gchar *)g_object_get_data(G_OBJECT(btn), "capability");
    const gchar *app_id = (const gchar *)g_object_get_data(G_OBJECT(btn), "app-id");

    revoke_permission_dbus(app_id, capability);

    /* Refresh UI */
    build_app_list(app);
    gtk_stack_set_visible_child_name(GTK_STACK(app->stack), "list");

    /* Toast */
    gchar *msg = g_strdup_printf("Revoked %s for %s", capability, app_id);
    adw_toast_overlay_add_toast(
        ADW_TOAST_OVERLAY(app->toast_overlay),
        adw_toast_new(msg)
    );
    g_free(msg);
}

static void
on_revoke_all(GtkButton *btn, gpointer user_data) {
    PermissionsApp *app = (PermissionsApp *)user_data;
    AppInfo *info = (AppInfo *)g_object_get_data(G_OBJECT(btn), "app-info");

    if (!info) return;

    revoke_all_permissions_dbus(info->app_id);

    build_app_list(app);
    gtk_stack_set_visible_child_name(GTK_STACK(app->stack), "list");

    gchar *msg = g_strdup_printf("Revoked all permissions for %s", info->app_name);
    adw_toast_overlay_add_toast(
        ADW_TOAST_OVERLAY(app->toast_overlay),
        adw_toast_new(msg)
    );
    g_free(msg);
}

static void
on_back_to_list(GtkButton *btn, gpointer user_data) {
    PermissionsApp *app = (PermissionsApp *)user_data;
    gtk_stack_set_visible_child_name(GTK_STACK(app->stack), "list");
}

static void
show_app_detail(PermissionsApp *app, AppInfo *info) {
    if (!info) return;

    /* Set header */
    adw_preferences_group_set_title(
        ADW_PREFERENCES_GROUP(app->detail_permissions_group),
        info->app_name
    );
    gtk_label_set_text(GTK_LABEL(app->detail_app_id), info->app_id);

    gchar *name_markup = g_strdup_printf("<span size='x-large' weight='bold'>%s</span>", info->app_name);
    gtk_label_set_markup(GTK_LABEL(app->detail_app_name), name_markup);
    g_free(name_markup);

    /* Clear existing permission rows */
    GtkWidget *group_widget = GTK_WIDGET(app->detail_permissions_group);
    GtkWidget *child = gtk_widget_get_first_child(group_widget);
    while (child) {
        GtkWidget *next = gtk_widget_get_next_sibling(child);
        if (ADW_IS_ACTION_ROW(child) || GTK_IS_LIST_BOX(child)) {
            gtk_preferences_group_remove(
                ADW_PREFERENCES_GROUP(group_widget), child);
        }
        child = next;
    }

    /* Rebuild permission rows */
    for (guint i = 0; i < info->capabilities->len; i++) {
        Capability *cap = g_ptr_array_index(info->capabilities, i);

        AdwActionRow *row = ADW_ACTION_ROW(adw_action_row_new());
        adw_action_row_set_title(row, get_capability_description(cap->capability));
        adw_action_row_set_subtitle(row, cap->capability);

        /* Icon */
        GtkWidget *icon = gtk_image_new_from_icon_name(
            get_capability_icon(cap->capability));
        gtk_image_set_pixel_size(GTK_IMAGE(icon), 20);
        adw_action_row_add_prefix(ADW_ACTION_ROW(row), icon);

        /* Risk badge */
        const gchar *risk = get_capability_risk(cap->capability);
        GtkWidget *risk_label = gtk_label_new(risk);
        if (g_strcmp0(risk, "high") == 0)
            gtk_widget_add_css_class(risk_label, "error");
        else if (g_strcmp0(risk, "medium") == 0)
            gtk_widget_add_css_class(risk_label, "warning");
        adw_action_row_add_suffix(ADW_ACTION_ROW(row), risk_label);

        /* Status indicator */
        if (cap->granted) {
            GtkWidget *status_icon = gtk_image_new_from_icon_name("emblem-ok-symbolic");
            gtk_image_set_pixel_size(GTK_IMAGE(status_icon), 16);
            adw_action_row_add_suffix(ADW_ACTION_ROW(row), status_icon);
        } else {
            GtkWidget *status_icon = gtk_image_new_from_icon_name("emblem-default-symbolic");
            gtk_image_set_pixel_size(GTK_IMAGE(status_icon), 16);
            gtk_widget_set_opacity(status_icon, 0.4);
            adw_action_row_add_suffix(ADW_ACTION_ROW(row), status_icon);
        }

        /* Last used timestamp */
        if (cap->granted_at > 0) {
            gchar timebuf[64];
            time_t t = (time_t)cap->granted_at;
            struct tm *tm_info = localtime(&t);
            strftime(timebuf, sizeof(timebuf), "%Y-%m-%d %H:%M", tm_info);
            GtkWidget *time_label = gtk_label_new(timebuf);
            gtk_widget_set_opacity(time_label, 0.5);
            gtk_label_set_font_scale(GTK_LABEL(time_label), 0.8);
            adw_action_row_add_suffix(ADW_ACTION_ROW(row), time_label);
        }

        /* Revoke button for granted permissions */
        if (cap->granted) {
            GtkWidget *revoke_btn = gtk_button_new_from_icon_name("edit-delete-symbolic");
            gtk_button_set_tooltip_text(GTK_BUTTON(revoke_btn), "Revoke this permission");
            g_object_set_data(G_OBJECT(revoke_btn), "capability", (gpointer)cap->capability);
            g_object_set_data(G_OBJECT(revoke_btn), "app-id", (gpointer)info->app_id);
            g_signal_connect(revoke_btn, "clicked",
                G_CALLBACK(on_revoke_capability), app);
            adw_action_row_add_suffix(ADW_ACTION_ROW(row), revoke_btn);
        }

        gtk_preferences_group_add(
            ADW_PREFERENCES_GROUP(app->detail_permissions_group),
            GTK_WIDGET(row)
        );
    }

    /* Set revoke-all button data */
    g_object_set_data(G_OBJECT(app->revoke_all_button), "app-info", info);

    /* Navigate */
    gtk_stack_set_visible_child_name(GTK_STACK(app->stack), "detail");
}

/* ── UI: No Apps State ────────────────────────────────────────────────── */

static GtkWidget *
create_empty_state(void) {
    GtkBox *box = GTK_BOX(gtk_box_new(GTK_ORIENTATION_VERTICAL, 12));
    gtk_widget_set_halign(GTK_WIDGET(box), GTK_ALIGN_CENTER);
    gtk_widget_set_valign(GTK_WIDGET(box), GTK_ALIGN_CENTER);
    gtk_widget_set_margin_top(80);

    GtkWidget *icon = gtk_image_new_from_icon_name("security-high-symbolic");
    gtk_image_set_pixel_size(GTK_IMAGE(icon), 64);
    gtk_widget_set_opacity(icon, 0.4);
    gtk_box_append(box, icon);

    GtkWidget *label = gtk_label_new("No apps have requested permissions yet");
    gtk_widget_set_opacity(label, 0.5);
    gtk_box_append(box, label);

    GtkWidget *sublabel = gtk_label_new(
        "App permissions appear here when apps request access\nto features like camera, microphone, location, or SMS."
    );
    gtk_label_set_justify(GTK_LABEL(sublabel), GTK_JUSTIFICATION_CENTER);
    gtk_widget_set_opacity(sublabel, 0.4);
    gtk_box_append(box, sublabel);

    return GTK_WIDGET(box);
}

/* ── Main Application ─────────────────────────────────────────────────── */

static void
activate_cb(AdwApplication *app_adw, gpointer user_data) {
    PermissionsApp *perm_app = (PermissionsApp *)user_data;

    /* Create window */
    GtkWidget *window = adw_application_window_new(ADW_APPLICATION(app_adw));
    perm_app->window = window;
    gtk_window_set_title(GTK_WINDOW(window), "App Permissions");
    gtk_window_set_default_size(GTK_WINDOW(window), 400, 700);
    gtk_window_set_resizable(GTK_WINDOW(window), TRUE);

    /* Full-screen on mobile */
    gtk_window_maximize(GTK_WINDOW(window));

    /* Apply dark theme */
    AdwStyleManager *style = adw_style_manager_get_default();
    adw_style_manager_set_color_scheme(style, ADW_COLOR_SCHEME_PREFER_DARK);

    /* Toast overlay */
    perm_app->toast_overlay = adw_toast_overlay_new();
    gtk_window_set_child(GTK_WINDOW(window), perm_app->toast_overlay);

    /* Main stack for navigation */
    perm_app->stack = gtk_stack_new();
    gtk_stack_set_transition_type(GTK_STACK(perm_app->stack), GTK_STACK_TRANSITION_TYPE_SLIDE_LEFT_RIGHT);
    gtk_stack_set_transition_duration(GTK_STACK(perm_app->stack), 200);
    adw_toast_overlay_set_child(
        ADW_TOAST_OVERLAY(perm_app->toast_overlay), perm_app->stack);

    /* ── List Page ──────────────────────────────────────────────────── */

    AdwPreferencesPage *list_page = ADW_PREFERENCES_PAGE(adw_preferences_page_new());
    AdwPreferencesGroup *list_group = ADW_PREFERENCES_GROUP(adw_preferences_group_new());
    adw_preferences_group_set_title(list_group, "Installed Apps");

    perm_app->app_list_box = gtk_list_box_new();
    gtk_list_box_set_selection_mode(GTK_LIST_BOX(perm_app->app_list_box), GTK_SELECTION_NONE);

    /* Header bar for list page */
    AdwHeaderBar *header_bar = ADW_HEADER_BAR(adw_header_bar_new());
    gtk_widget_set_hexpand(GTK_WIDGET(header_bar), TRUE);

    GtkWidget *title_label = gtk_label_new("App Permissions");
    gtk_label_set_markup(GTK_LABEL(title_label),
        "<span weight='bold'>App Permissions</span>");
    adw_header_bar_set_title_widget(header_bar, title_label);

    /* Wrap list page */
    GtkBox *list_box_wrapper = GTK_BOX(gtk_box_new(GTK_ORIENTATION_VERTICAL, 0));
    gtk_box_append(list_box_wrapper, GTK_WIDGET(header_bar));
    gtk_preferences_group_add(list_group, perm_app->app_list_box);
    gtk_box_append(list_box_wrapper, GTK_WIDGET(list_page));
    gtk_preferences_page_add(list_page, list_group);

    gtk_stack_add_titled(GTK_STACK(perm_app->stack),
        GTK_WIDGET(list_box_wrapper), "list", "Apps");

    /* ── Detail Page ──────────────────────────────────────────────────── */

    GtkBox *detail_wrapper = GTK_BOX(gtk_box_new(GTK_ORIENTATION_VERTICAL, 0));

    AdwHeaderBar *detail_header = ADW_HEADER_BAR(adw_header_bar_new());

    /* Back button */
    GtkWidget *back_btn = gtk_button_new_from_icon_name("go-previous-symbolic");
    gtk_button_set_tooltip_text(GTK_BUTTON(back_btn), "Back to app list");
    g_signal_connect(back_btn, "clicked", G_CALLBACK(on_back_to_list), perm_app);
    adw_header_bar_pack_start(detail_header, back_btn);

    /* App name in header */
    perm_app->detail_app_name = gtk_label_new("");
    adw_header_bar_set_title_widget(detail_header, perm_app->detail_app_name);

    gtk_box_append(detail_wrapper, GTK_WIDGET(detail_header));

    /* Detail content as AdwPreferencesPage */
    AdwPreferencesPage *detail_page = ADW_PREFERENCES_PAGE(adw_preferences_page_new());

    /* App ID subtitle */
    AdwPreferencesGroup *id_group = ADW_PREFERENCES_GROUP(adw_preferences_group_new());
    adw_preferences_group_set_title(id_group, "App");
    perm_app->detail_app_id = gtk_label_new("");
    gtk_widget_set_opacity(perm_app->detail_app_id, 0.6);
    gtk_preferences_group_add(id_group, perm_app->detail_app_id);
    gtk_preferences_page_add(detail_page, id_group);

    /* Permissions group */
    perm_app->detail_permissions_group = ADW_PREFERENCES_GROUP(adw_preferences_group_new());
    adw_preferences_group_set_title(perm_app->detail_permissions_group, "Permissions");
    gtk_preferences_page_add(detail_page, perm_app->detail_permissions_group);

    /* Revoke All button */
    GtkWidget *revoke_all_btn = gtk_button_new_with_label("Revoke All Permissions");
    gtk_widget_add_css_class(revoke_all_btn, "destructive-action");
    gtk_widget_set_margin_top(12);
    gtk_widget_set_margin_bottom(12);
    gtk_widget_set_halign(revoke_all_btn, GTK_ALIGN_CENTER);
    g_signal_connect(revoke_all_btn, "clicked", G_CALLBACK(on_revoke_all), perm_app);
    perm_app->revoke_all_button = revoke_all_btn;
    gtk_preferences_page_add(detail_page, GTK_WIDGET(revoke_all_btn));

    gtk_box_append(detail_wrapper, GTK_WIDGET(detail_page));
    gtk_stack_add_titled(GTK_STACK(perm_app->stack),
        GTK_WIDGET(detail_wrapper), "detail", "Details");

    /* Build app list */
    build_app_list(perm_app);

    /* If no apps, show empty state */
    if (perm_app->apps->len == 0) {
        GtkWidget *empty = create_empty_state();
        gtk_list_box_append(GTK_LIST_BOX(perm_app->app_list_box), empty);
    }

    /* Show window */
    gtk_window_present(GTK_WINDOW(window));
}

int
main(int argc, char *argv[]) {
    PermissionsApp *app = g_new0(PermissionsApp, 1);
    app->apps = g_ptr_array_new_with_free_func((GDestroyNotify)app_info_free);

    /* Try to get D-Bus proxy */
    app->portal_proxy = get_portal_proxy();

    AdwApplication *adw_app = adw_application_new(
        "org.nuxel.Permissions", G_APPLICATION_DEFAULT_FLAGS);
    g_signal_connect(adw_app, "activate", G_CALLBACK(activate_cb), app);

    int status = g_application_run(G_APPLICATION(adw_app), argc, argv);

    /* Cleanup */
    if (app->portal_proxy) g_object_unref(app->portal_proxy);
    if (app->bridge_proxy) g_object_unref(app->bridge_proxy);
    if (app->apps) g_ptr_array_unref(app->apps);
    g_free(app);
    g_object_unref(adw_app);

    return status;
}
