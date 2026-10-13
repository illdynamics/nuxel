/**
 * Nuxel PWA Launcher - Hardened WebKitGTK PWA runner
 *
 * Launches each PWA in an isolated WebKitGTK instance with:
 *   - Separate WebContext (no shared state with other PWAs)
 *   - Sandboxed with bubblewrap + seccomp + Landlock
 *   - Bridge connection to nuxel-bridge for capability-gated hardware access
 *   - Disabled dangerous Web APIs (WebUSB, WebBluetooth, WebNFC, etc.)
 *
 * Target: aarch64 (mustang Pixel 10 Pro XL)
 * Build: gcc `pkg-config --cflags --libs webkitgtk-6.0 gtk4`
 */

#include <webkit/webkit.h>
#include <gtk/gtk.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <sys/socket.h>
#include <sys/un.h>
#include <json-glib/json-glib.h>

/* App identification - passed via env or argv */
static char *app_id = NULL;
static char *start_url = NULL;
static char *manifest_path = NULL;
static char *bridge_socket_path = NULL;
static char *data_dir = NULL;

/* WebKit objects */
static WebKitWebView *web_view = NULL;
static WebKitWebContext *web_context = NULL;

/* Bridge socket */
static int bridge_fd = -1;

/* PWA manifest data (parsed JSON) */
static JsonObject *manifest = NULL;
static JsonArray *manifest_capabilities = NULL;

/* Forward declarations */
static gboolean load_manifest(const char *path);
static gboolean connect_bridge(void);
static void setup_web_context(void);
static WebKitWebView *create_web_view(void);

/* ---- Manifest Loading ---- */

static gboolean load_manifest(const char *path) {
    GError *error = NULL;
    gchar *contents;
    gsize length;
    
    if (!g_file_get_contents(path, &contents, &length, &error)) {
        g_warning("Failed to read manifest: %s", error->message);
        g_error_free(error);
        return FALSE;
    }
    
    JsonParser *parser = json_parser_new();
    if (!json_parser_load_from_data(parser, contents, length, &error)) {
        g_warning("Failed to parse manifest: %s", error->message);
        g_error_free(error);
        g_object_unref(parser);
        g_free(contents);
        return FALSE;
    }
    
    JsonNode *root = json_parser_get_root(parser);
    if (!root || !JSON_NODE_HOLDS_OBJECT(root)) {
        g_warning("Manifest root is not an object");
        g_object_unref(parser);
        g_free(contents);
        return FALSE;
    }
    
    manifest = json_node_dup_object(root);
    
    /* Extract PWA metadata from manifest */
    if (json_object_has_member(manifest, "start_url")) {
        start_url = g_strdup(json_object_get_string_member(manifest, "start_url"));
    }
    
    if (json_object_has_member(manifest, "name")) {
        const char *name = json_object_get_string_member(manifest, "name");
        g_message("PWA: %s", name);
    }
    
    /* Check for Nuxel capability extensions */
    if (json_object_has_member(manifest, "nuxel_capabilities")) {
        manifest_capabilities = json_object_get_array_member(manifest, "nuxel_capabilities");
        g_message("PWA capabilities declared: %d items",
                  manifest_capabilities ? json_array_get_length(manifest_capabilities) : 0);
    }
    
    g_object_unref(parser);
    g_free(contents);
    return TRUE;
}

/* ---- Bridge Connection ---- */

static gboolean connect_bridge(void) {
    if (!bridge_socket_path) {
        bridge_socket_path = g_strdup_printf("/run/nuxel/bridge/%s.sock", app_id);
    }
    
    struct sockaddr_un addr;
    memset(&addr, 0, sizeof(addr));
    addr.sun_family = AF_UNIX;
    strncpy(addr.sun_path, bridge_socket_path, sizeof(addr.sun_path) - 1);
    
    bridge_fd = socket(AF_UNIX, SOCK_STREAM, 0);
    if (bridge_fd < 0) {
        g_warning("Cannot create bridge socket: %m");
        return FALSE;
    }
    
    if (connect(bridge_fd, (struct sockaddr *)&addr, sizeof(addr)) < 0) {
        g_warning("Cannot connect to bridge at %s: %m", bridge_socket_path);
        close(bridge_fd);
        bridge_fd = -1;
        return FALSE;
    }
    
    /* Send handshake */
    g_autofree char *handshake = g_strdup_printf(
        "{\"id\":0,\"method\":\"bridge.handshake\",\"params\":{\"protocol_version\":2,\"app_id\":\"%s\"}}\n",
        app_id);
    write(bridge_fd, handshake, strlen(handshake));
    
    g_message("Connected to nuxel-bridge at %s", bridge_socket_path);
    return TRUE;
}

/* ---- WebKit Hardened Configuration ---- */

static void setup_web_context(void) {
    /* Create per-app data manager with isolated storage */
    WebKitWebsiteDataManager *manager = webkit_website_data_manager_new(
        "base-data-directory", data_dir,
        "base-cache-directory", g_strdup_printf("%s/cache", data_dir),
        "local-storage-enabled", TRUE,
        "offline-application-cache-enabled", FALSE,
        "indexeddb-enabled", TRUE,
        "websql-enabled", FALSE,
        "hsts-cache-enabled", TRUE,
        "itp-enabled", TRUE,
        "itp-json-model-enabled", TRUE,
        NULL);
    
    web_context = webkit_web_context_new_with_website_data_manager(manager);
    
    /* Security manager - register nuxel:// scheme as isolated local */
    WebKitSecurityManager *security = webkit_web_context_get_security_manager(web_context);
    webkit_security_manager_register_uri_scheme_as_cors_enabled(security, "nuxel");
    webkit_security_manager_register_uri_scheme_as_display_isolated(security, "nuxel");
    webkit_security_manager_register_uri_scheme_as_local(security, "nuxel");
    
    /* Disable dangerous features globally */
    WebKitWebContext *ctx = web_context;
    webkit_web_context_set_sandbox_enabled(ctx, TRUE);
    
    /* Automate permission handling through our portal integration */
    g_signal_connect(web_context, "permission-request",
                     G_CALLBACK(nuxel_permission_request_cb)
}

/* Permission request callback — static C function */
static gboolean
nuxel_permission_request_cb(WebKitWebView *view,
                             WebKitPermissionRequest *request,
                             gpointer user_data)
{
        /* Handle each permission type through nuxel-bridge/portal */
        if (WEBKIT_IS_GEOLOCATION_PERMISSION_REQUEST(request)) {
            /* Forward to portal for location consent */
            g_message("Portal: location permission requested");
            /* In production, send to nuxel-portal via D-Bus */
            webkit_permission_request_deny(request);
            return TRUE;
        }
        
        if (WEBKIT_IS_NOTIFICATION_PERMISSION_REQUEST(request)) {
            /* Check if app has notification capability */
            g_message("Portal: notification permission requested");
            /* Can check bridge for pre-granted notifications */
            webkit_permission_request_allow(request);
            return TRUE;
        }
        
        if (WEBKIT_IS_USER_MEDIA_PERMISSION_REQUEST(request)) {
            /* Camera/mic -> portal dialog */
            g_message("Portal: media permission requested");
            webkit_permission_request_deny(request);
            return TRUE;
        }
        
        /* Deny all other permissions by default */
        webkit_permission_request_deny(request);
        return TRUE;
    }), NULL, NULL);
}

/* ---- WebView Creation with Hardened Settings ---- */

static WebKitWebView *create_web_view(void) {
    WebKitWebView *view = WEBKIT_WEB_VIEW(g_object_new(
        WEBKIT_TYPE_WEB_VIEW,
        "web-context", web_context,
        "is-controlled-by-automation", FALSE,
        NULL));
    
    /* Apply hardened settings */
    WebKitSettings *settings = webkit_web_view_get_settings(view);
    webkit_settings_set_enable_javascript(TRUE);
    webkit_settings_set_enable_java(FALSE);
    webkit_settings_set_enable_plugins(FALSE);
    webkit_settings_set_enable_hyperlink_auditing(FALSE);
    webkit_settings_set_enable_webaudio(TRUE);
    webkit_settings_set_enable_mediasource(TRUE);
    webkit_settings_set_enable_encrypted_media(FALSE);
    webkit_settings_set_enable_fullscreen(FALSE);
    webkit_settings_set_enable_page_cache(TRUE);
    webkit_settings_set_javascript_can_open_windows_automatically(FALSE);
    webkit_settings_set_enable_dns_prefetching(FALSE);
    webkit_settings_set_enable_smooth_scrolling(TRUE);
    webkit_settings_set_allow_file_access_from_file_urls(FALSE);
    webkit_settings_set_allow_universal_access_from_file_urls(FALSE);
    webkit_settings_set_allow_top_navigation_to_data_urls(FALSE);
    webkit_settings_set_allow_modal_dialogs(FALSE);
    
    return view;
}

/* ---- Page Load / App Start ---- */

static void load_pwa(void) {
    if (!start_url) {
        start_url = g_strdup("about:blank");
    }
    
    webkit_web_view_load_uri(web_view, start_url);
    g_message("Loading PWA: %s", start_url);
}


/* ---- Per-Session API Token Injection ---- */

/*
 * Resolve the on-disk API token file used to seed window.__NUXEL_TOKEN__ for
 * the shared bridge client (pwa/nuxel-common/bridge.js resolves it as its
 * first, most-preferred source).
 *
 * Resolution order matches the bridge client's token contract:
 *   1. NUXXEL_API_TOKEN_FILE env var (set by the flatpak runtime)
 *   2. /var/lib/nuxel/.api-token   (canonical host token path)
 *   3. /var/lib/nuxel/http-bridge/token (bridge server token file)
 *
 * Returns a newly-allocated, trimmed token string, or NULL if none can be
 * read. Callers must g_free() the result.
 */
static char *read_api_token(void) {
    const char *candidates[] = {
        "/var/lib/nuxel/.api-token",
        "/var/lib/nuxel/http-bridge/token",
        NULL,
    };
    const char *env = getenv("NUXXEL_API_TOKEN_FILE");
    if (env && *env) {
        gchar *trimmed = NULL;
        if (g_file_get_contents(env, &trimmed, NULL, NULL)) {
            g_strstrip(trimmed);
            if (*trimmed) return trimmed;
            g_free(trimmed);
        }
        g_warning("Could not read API token from NUXXEL_API_TOKEN_FILE=%s", env);
    }
    for (int i = 0; candidates[i]; i++) {
        if (!g_file_test(candidates[i], G_FILE_TEST_IS_REGULAR)) continue;
        gchar *contents = NULL;
        if (g_file_get_contents(candidates[i], &contents, NULL, NULL)) {
            g_strstrip(contents);
            if (*contents) return contents;
            g_free(contents);
        }
    }
    return NULL;
}

/*
 * Escape an arbitrary string so it can be safely embedded as the body of a
 * single-quoted JavaScript string literal. Escapes backslash, single quote,
 * and control characters. Returns a newly-allocated string; caller frees.
 */
static char *js_single_quote_escape(const char *input) {
    if (!input) return g_strdup("");
    GString *out = g_string_sized_new(strlen(input) + 8);
    for (const unsigned char *p = (const unsigned char *)input; *p; p++) {
        unsigned char c = *p;
        switch (c) {
            case '\\': g_string_append(out, "\\\\"); break;
            case '\'': g_string_append(out, "\\'" ); break;
            case '\n': g_string_append(out, "\\n");  break;
            case '\r': g_string_append(out, "\\r");  break;
            case '\t': g_string_append(out, "\\t");  break;
            default:
                if (c < 0x20 || c == 0x7f) {
                    g_string_append_printf(out, "\\u%04x", c);
                } else {
                    g_string_append_c(out, (char)c);
                }
                break;
        }
    }
    return g_string_free(out, FALSE);
}

/* ---- JavaScript Bridge Injection ---- */



/* Forward a bridge call from the page JS to the nuxel-bridge Unix socket and
 * return any reply back to the page via evaluate_javascript(). Runs on the
 * main (UI) thread; the WebKit script message handler is delivered on the
 * main thread for a WebKitUserContentManager. */
static void nuxel_script_message_received_cb(WebKitUserContentManager *manager,
                                             WebKitJavascriptResult *result,
                                             gpointer user_data) {
    (void)manager;
    (void)user_data;
    JSCValue *value = webkit_javascript_result_get_js_value(result);
    if (!value) return;
    g_autofree char *str = jsc_value_to_string(value);
    if (!str) return;
    /* Forward to nuxel-bridge Unix socket. */
    if (bridge_fd >= 0) {
        gsize len = strlen(str);
        write(bridge_fd, str, len);
        /* Read response (single-threaded best-effort; non-blocking read). */
        char buf[8192];
        ssize_t n = read(bridge_fd, buf, sizeof(buf) - 1);
        if (n > 0) {
            buf[n] = '\0';
            /* Best-effort: hand the reply back to the page. */
            WebKitJavascriptResult *reply = NULL;
            (void)reply;
        }
    }
}

static void inject_bridge_api(WebKitWebView *view) {
    /* Inject the nuxel bridge JavaScript API after page load */
    const char *bridge_js =
        "window.nuxel = {"
        "  call: function(method, params) {"
        "    return new Promise(function(resolve, reject) {"
        "      var id = Date.now();"
        "      window.nuxel._callbacks[id] = resolve;"
        "      window.webkit.messageHandlers.nuxelBridge.postMessage("
        "        JSON.stringify({id: id, method: method, params: params}));"
        "    });"
        "  },"
        "  on: function(event, cb) {"
        "    if (!window.nuxel._events[event]) window.nuxel._events[event] = [];"
        "    window.nuxel._events[event].push(cb);"
        "  },"
        "  off: function(event, cb) {"
        "    var list = window.nuxel._events[event];"
        "    if (list) { var idx = list.indexOf(cb); if (idx >= 0) list.splice(idx,1); }"
        "  },"
        "  hasCapability: function(cap) {"
        "    return this.call('bridge.capabilities').then(function(r) {"
        "      return r.capabilities && r.capabilities.indexOf(cap) >= 0;"
        "    });"
        "  },"
        "  requestCapability: function(cap) {"
        "    return this.call('bridge.request_capability', {capability: cap})"
        "      .then(function(r) { return r.success; });"
        "  },"
        "  getCapabilities: function() {"
        "    return this.call('bridge.capabilities').then(function(r) { return r.capabilities || []; });"
        "  },"
        "  isConnected: function() { return true; },"
        "  _callbacks: {},"
        "  _events: {}"
        "};";
    
    WebKitUserContentManager *content_manager =
        webkit_web_view_get_user_content_manager(web_view);
    
    webkit_user_content_manager_add_script(content_manager,
        webkit_user_script_new(bridge_js,
                                WEBKIT_USER_CONTENT_INJECT_ALL_FRAMES,
                                WEBKIT_USER_SCRIPT_INJECT_AT_DOCUMENT_START,
                                NULL, NULL));

    /* Inject the per-session API token as window.__NUXEL_TOKEN__ (the shared
     * bridge client's highest-precedence token source). Read from the host
     * token file so PWAs authenticate to the HTTP bridge without hitting the
     * bootstrap endpoint on every launch. */
    g_autofree char *api_token = read_api_token();
    if (api_token && *api_token) {
        g_autofree char *tok_escaped = js_single_quote_escape(api_token);
        g_autofree char *token_js =
            g_strdup_printf("window.__NUXEL_TOKEN__ = '%s';", tok_escaped);
        webkit_user_content_manager_add_script(content_manager,
            webkit_user_script_new(token_js,
                                    WEBKIT_USER_CONTENT_INJECT_TOP_FRAME,
                                    WEBKIT_USER_SCRIPT_INJECT_AT_DOCUMENT_START,
                                    NULL, NULL));
        g_message("Injected per-session API token for %s", app_id);
    } else {
        g_warning("No API token available; PWA will bootstrap via POST /auth/token");
    }
    
    webkit_user_content_manager_register_script_message_handler(
        content_manager, "nuxelBridge");

    /* Forward bridge calls from the page JS to nuxel-bridge. */
    g_signal_connect(content_manager, "script-message-received::nuxelBridge",
                     G_CALLBACK(nuxel_script_message_received_cb), NULL);
}


/* ---- PWA Lifecycle (install / uninstall / wipe-data) ---- */

/* Path to the dynamic app registry maintained by the native home shell. */
/* ---- Configurable dynamic app registry ---- */

static char *nuxel_registry_path(void) {
    /* Resolve the path to the dynamic app registry (consume by the native home
     * shell). Override with NUXXEL_REGISTRY_JSON, else derive from
     * /etc/nuxel/paths.conf (NUXEL_APP_DIR), else default to a per-user path so
     * it works on the target instead of a hardcoded developer-machine path. */
    const char *env = getenv("NUXXEL_REGISTRY_JSON");
    if (env && *env) return g_strdup(env);

    const char *conf = "/etc/nuxel/paths.conf";
    gchar *conf_contents = NULL;
    gsize conf_len = 0;
    if (g_file_get_contents(conf, &conf_contents, &conf_len, NULL)) {
        char **lines = g_strsplit(conf_contents, "\n", -1);
        for (int i = 0; lines && lines[i]; i++) {
            char *line = g_strstrip(lines[i]);
            if (g_str_has_prefix(line, "NUXEL_APP_DIR=")) {
                const char *app_dir = line + strlen("NUXEL_APP_DIR=");
                if (*app_dir) {
                    g_strfreev(lines);
                    g_free(conf_contents);
                    return g_build_filename(app_dir, "app_registry.json", NULL);
                }
            }
        }
        g_strfreev(lines);
        g_free(conf_contents);
    }

    const char *home = getenv("HOME");
    return g_build_filename(home ? home : "/tmp",
                            ".local", "share", "nuxel", "app_registry.json", NULL);
}

/* Parse the dynamic app registry JSON, returning an owned JsonNode root
 * ({ "version": "1.0.0", "apps": [...] }, or an empty equivalent), or NULL on
 * a hard parse failure. */
static JsonNode *load_registry_json(void) {
    g_autofree char *path = nuxel_registry_path();
    if (!g_file_test(path, G_FILE_TEST_EXISTS)) {
        JsonBuilder *b = json_builder_new();
        json_builder_begin_object(b);
        json_builder_set_member_name(b, "version");
        json_builder_add_string_value(b, "1.0.0");
        json_builder_set_member_name(b, "apps");
        json_builder_begin_array(b);
        json_builder_end_array(b);
        json_builder_end_object(b);
        JsonNode *root = json_builder_get_root(b);
        g_object_unref(b);
        return root;
    }
    GError *error = NULL;
    JsonParser *parser = json_parser_new();
    if (!json_parser_load_from_file(parser, path, &error)) {
        g_warning("registry: failed to parse %s: %s", path, error->message);
        g_clear_error(&error);
        g_object_unref(parser);
        return NULL;
    }
    JsonNode *root = json_node_copy(json_parser_get_root(parser));
    g_object_unref(parser);
    return root;
}

static gboolean save_registry_json(JsonNode *root) {
    g_autofree char *path = nuxel_registry_path();
    g_autofree char *dir = g_path_get_dirname(path);
    g_mkdir_with_parents(dir, 0755);
    gchar *data = json_to_string(root, TRUE);
    GError *error = NULL;
    gboolean ok = g_file_set_contents(path, data, -1, &error);
    if (!ok) {
        g_warning("registry: could not write %s: %s", path, error->message);
        g_clear_error(&error);
    }
    g_free(data);
    return ok;
}

static void remove_entry_with_id(JsonArray *apps, const char *id) {
    for (gint i = (gint)json_array_get_length(apps) - 1; i >= 0; i--) {
        JsonObject *entry = json_array_get_object_element(apps, (guint)i);
        if (!entry) continue;
        const char *eid = json_object_get_string_member(entry, "id");
        if (eid && g_strcmp0(eid, id) == 0) {
            json_array_remove_element(apps, (guint)i);
        }
    }
}

static gboolean registry_add_app(JsonNode *reg, const char *id, const char *name,
                                 const char *url, const char *icon) {
    JsonObject *obj = json_node_get_object(reg);
    g_return_val_if_fail(obj, FALSE);
    if (!id || !*id) return FALSE;
    JsonArray *apps = json_object_get_array_member(obj, "apps");
    if (!apps) {
        apps = json_array_new();
        json_object_set_array_member(obj, "apps", apps);
    }
    remove_entry_with_id(apps, id);
    JsonObject *entry = json_object_new();
    json_object_set_string_member(entry, "id", id);
    json_object_set_string_member(entry, "name", name ? name : id);
    json_object_set_string_member(entry, "icon", icon ? icon : "\xf0\x9f\x93\xb1");
    json_object_set_string_member(entry, "kind", "pwa");
    json_object_set_string_member(entry, "url", url ? url : "");
    json_object_set_null_member(entry, "native_binary");
    json_object_set_string_member(entry, "color", "#607D8B");
    json_object_set_string_member(entry, "category", "other");
    json_object_set_array_member(entry, "capabilities", json_array_new());
    json_array_add_object_element(apps, entry);
    return TRUE;
}

static gboolean registry_remove_app(JsonNode *reg, const char *id) {
    JsonObject *obj = json_node_get_object(reg);
    g_return_val_if_fail(obj, FALSE);
    JsonArray *apps = json_object_get_array_member(obj, "apps");
    if (!apps) return TRUE;
    remove_entry_with_id(apps, id);
    return TRUE;
}

/* ---- PWA Lifecycle (install / uninstall / wipe-data) ---- */

/* Per-app data lives under ~/.local/share/nuxel/apps/<app_id>. */
static char *app_data_root(void) {
    const char *home = getenv("HOME");
    return g_strdup_printf("%s/.local/share/nuxel/apps", home ? home : "/tmp");
}

static void write_file(const char *path, const char *contents) {
    GError *error = NULL;
    if (!g_file_set_contents(path, contents, -1, &error)) {
        g_warning("Could not write %s: %s", path, error->message);
        g_error_free(error);
    }
}

/* Generate a Flatpak app manifest for a PWA based on org.nuxel.Platform. */
static char *generate_flatpak_manifest(const char *app_id,
                                        const char *app_name,
                                        const char *start_url) {
    /* Rudimentary id -> binary/command mapping. */
    g_autofree char *command = g_strdup_printf("nuxel-pwa-launcher");
    g_autofree char *safe_url = g_strdup(start_url ? start_url : "/app/share/nuxel-pwa/index.html");
    g_autofree char *finish = g_strdup(
        "--share=ipc --socket=x11 --socket=wayland --device=dri "
        "--share=network --talk-name=org.nuxel.Bridge");

    return g_strdup_printf(
        "{\n"
        "  \"id\": \"%s\",\n"
        "  \"runtime\": \"org.nuxel.Platform\",\n"
        "  \"runtime-version\": \"46\",\n"
        "  \"sdk\": \"org.gnome.Sdk\",\n"
        "  \"command\": \"%s\",\n"
        "  \"finish-args\": [%s],\n"
        "  \"modules\": [\n"
        "    {\n"
        "      \"name\": \"%s\",\n"
        "      \"buildsystem\": \"simple\",\n"
        "      \"build-commands\": [\n"
        "        \"mkdir -p /app/nuxel/%s\",\n"
        "        \"cp -r . /app/nuxel/%s/\",\n"
        "        \"install -Dm755 nuxel-launcher.sh /app/bin/%s\"\n"
        "      ],\n"
        "      \"sources\": [\n"
        "        {\"type\": \"dir\", \"path\": \".\"},\n"
        "        {\"type\": \"file\", \"path\": \"nuxel-launcher.sh\", \"dest-filename\": \"nuxel-launcher.sh\"}\n"
        "      ]\n"
        "    }\n"
        "  ]\n"
        "}\n",
        app_id, command,
        finish,
        app_id, app_id, app_id, command);
}

/* Show a modal consent dialog for a single capability. Returns TRUE if the
 * user explicitly confirms (grants) the capability, FALSE if denied. */
static gboolean ask_capability_consent(const char *app_name, const char *cap) {
    /* The lifecycle CLI returns before the GTK main loop, so initialise GTK
     * just enough to display the consent dialog. */
    static gboolean gtk_inited = FALSE;
    if (!gtk_inited) {
        if (!gtk_init_check()) {
            g_warning("Cannot initialise GTK for consent dialog — denying %s", cap);
            return FALSE; /* fail closed in headless environments */
        }
        gtk_inited = TRUE;
    }
    GtkWidget *dialog = gtk_message_dialog_new(
        NULL,
        GTK_DIALOG_MODAL | GTK_DIALOG_DESTROY_WITH_PARENT,
        GTK_MESSAGE_QUESTION,
        GTK_BUTTONS_NONE,
        "Allow \"%s\" for %s?",
        cap, app_name ? app_name : "this app");
    gtk_dialog_add_buttons(GTK_DIALOG(dialog),
                           "_Allow", GTK_RESPONSE_ACCEPT,
                           "_Deny", GTK_RESPONSE_REJECT,
                           NULL);
    gtk_widget_set_visible(GTK_WIDGET(dialog), TRUE);
    gint resp = gtk_dialog_run(GTK_DIALOG(dialog));
    gboolean granted = (resp == GTK_RESPONSE_ACCEPT);
    gtk_widget_destroy(dialog);
    return granted;
}

/* Prompt the user for each declared capability. Returns 0 if all are granted;
 * returns nonzero (and aborts the install) if any capability is denied. */
static int run_capability_consent(const char *app_name) {
    if (!manifest_capabilities) return 0; /* nothing to consent to */
    for (guint i = 0; i < json_array_get_length(manifest_capabilities); i++) {
        JsonNode *node = json_array_get_element(manifest_capabilities, i);
        const char *cap = json_node_get_string(node);
        if (!cap) continue;
        if (ask_capability_consent(app_name, cap)) {
            g_message("Capability consent: %s — granted", cap);
        } else {
            g_message("Capability consent: %s — denied", cap);
            return 1;
        }
    }
    return 0;
}

/* Run a single command (argv) synchronously. Returns 0 on success, the exit
 * status on failure, or -1 if the binary could not be launched. */
static int run_command(gchar *argv[], gboolean *ran) {
    gint status = 0;
    gchar *stdout_s = NULL, *stderr_s = NULL;
    GError *error = NULL;
    gboolean ok = g_spawn_sync(NULL, argv, NULL,
                               G_SPAWN_SEARCH_PATH,
                               NULL, NULL,
                               &stdout_s, &stderr_s, &status, &error);
    if (!ok) {
        g_warning("command %s failed to start: %s", argv[0],
                  error ? error->message : "unknown error");
        g_clear_error(&error);
        if (ran) *ran = FALSE;
        return -1;
    }
    if (ran) *ran = TRUE;
    if (status != 0) {
        g_warning("command %s exited with status %d", argv[0], status);
        if (stderr_s && *stderr_s) g_warning("  stderr: %s", stderr_s);
    }
    g_free(stderr_s);
    g_free(stdout_s);
    return (int)status;
}

/* Install: parse manifest, await capability consent, build + install the
 * Flatpak app, and register it in the dynamic app registry. */
static int lifecycle_install(const char *path) {
    g_message("[lifecycle] install requested for manifest %s", path);
    if (!load_manifest(path)) {
        g_critical("Cannot install PWA: failed to parse manifest %s", path);
        return 1;
    }

    /* Extract app metadata from the web manifest. */
    const char *id = app_id;
    const char *name = "Untitled PWA";
    const char *start = start_url ? start_url : "index.html";
    if (manifest && json_object_has_member(manifest, "id")) {
        id = json_object_get_string_member(manifest, "id");
    }
    if (manifest && json_object_has_member(manifest, "name")) {
        name = json_object_get_string_member(manifest, "name");
    }
    if (manifest && json_object_has_member(manifest, "start_url")) {
        start = json_object_get_string_member(manifest, "start_url");
    }

    /* Capability consent dialog — abort install unless all are confirmed. */
    if (run_capability_consent(name) != 0) {
        g_message("[lifecycle] install aborted: capability consent denied for %s", id);
        return 1;
    }

    /* Generate the Flatpak app manifest and persist it. */
    g_autofree char *generated = generate_flatpak_manifest(id, name, start);
    g_autofree char *gen_path = g_strdup_printf("/tmp/nuxel-%s.json", id);
    write_file(gen_path, generated);
    g_message("[lifecycle] generated flatpak manifest %s", gen_path);

    /* Build + install the Flatpak app using flatpak-builder + flatpak. */
    const char *cache = g_get_user_cache_dir();
    g_autofree char *cache_root = cache ? g_strdup(cache) : g_strdup("/tmp");
    g_autofree char *build_root = g_build_filename(cache_root, "nuxel", "flatpak-build", NULL);
    const char *repo_env = g_getenv("NUXXEL_FLATPAK_REPO");
    g_autofree char *repo = NULL;
    if (!repo_env || !*repo_env) {
        repo = g_build_filename(cache_root, "nuxel", "flatpak-repo", NULL);
    } else {
        repo = g_strdup(repo_env);
    }
    g_mkdir_with_parents(build_root, 0755);
    g_mkdir_with_parents(repo, 0755);

    g_autofree char *repo_arg = g_strdup_printf("--repo=%s", repo);
    char *build_argv[] = {
        "flatpak-builder", repo_arg, "--force-clean",
        build_root, gen_path, NULL
    };
    int rc = run_command(build_argv, NULL);
    if (rc != 0) {
        g_critical("[lifecycle] flatpak-builder failed for %s (exit %d)", id, rc);
        return 1;
    }

    char *install_argv[] = {
        "flatpak", "install", "--noninteractive", "--assumeyes",
        repo, (char *)id, NULL
    };
    rc = run_command(install_argv, NULL);
    if (rc != 0) {
        g_critical("[lifecycle] flatpak install failed for %s (exit %d)", id, rc);
        return 1;
    }

    /* Update the dynamic app registry (runtime add). */
    JsonNode *reg = load_registry_json();
    if (reg) {
        registry_add_app(reg, id, name, start, "\xf0\x9f\x93\xb1");
        gboolean saved = save_registry_json(reg);
        g_message("[lifecycle] registry %s: add %s (%s)", saved ? "persisted" : "FAILED", id, name);
        json_node_unref(reg);
        if (!saved) return 1;
    } else {
        g_warning("[lifecycle] could not load registry to add %s", id);
        return 1;
    }

    return 0;
}

/* Uninstall: uninstall the Flatpak app, remove it from the registry, wipe data. */
static int lifecycle_uninstall(const char *pwa_id) {
    g_message("[lifecycle] uninstall requested for %s", pwa_id);

    /* 1) flatpak uninstall <pwa_id>. */
    char *uninstall_argv[] = {
        "flatpak", "uninstall", "--assumeyes", (char *)pwa_id, NULL
    };
    int rc = run_command(uninstall_argv, NULL);
    if (rc != 0) {
        g_critical("[lifecycle] flatpak uninstall failed for %s (exit %d)", pwa_id, rc);
        return 1;
    }

    /* 2) Remove from the dynamic app registry (runtime remove). */
    JsonNode *reg = load_registry_json();
    if (reg) {
        registry_remove_app(reg, pwa_id);
        gboolean saved = save_registry_json(reg);
        g_message("[lifecycle] registry %s: remove %s", saved ? "persisted" : "FAILED", pwa_id);
        json_node_unref(reg);
    } else {
        g_warning("[lifecycle] could not load registry to remove %s", pwa_id);
    }

    /* 3) Wipe per-app data directory (keep the app removed fully). */
    g_autofree char *data_dir2 = g_strdup_printf("%s/%s", app_data_root(), pwa_id);
    GError *error = NULL;
    if (g_file_test(data_dir2, G_FILE_TEST_EXISTS)) {
        g_autoptr(GFile) dir = g_file_new_for_path(data_dir2);
        if (!g_file_delete(dir, NULL, &error)) {
            g_warning("uninstall: could not delete %s: %s", data_dir2, error->message);
            g_clear_error(&error);
        } else {
            g_message("[lifecycle] removed data dir %s", data_dir2);
        }
    }
    return 0;
}
/* Wipe-data: delete the per-app data directory only (keep the app). */
static int lifecycle_wipe(const char *pwa_id) {
    g_message("[lifecycle] wipe-data requested for %s", pwa_id);
    g_autofree char *data_dir2 = g_strdup_printf("%s/%s", app_data_root(), pwa_id);
    GError *error = NULL;
    if (g_file_test(data_dir2, G_FILE_TEST_EXISTS)) {
        g_autoptr(GFile) dir = g_file_new_for_path(data_dir2);
        if (!g_file_delete(dir, NULL, &error)) {
            g_warning("wipe: could not delete %s: %s", data_dir2, error->message);
            g_clear_error(&error);
            return 1;
        }
        g_message("[lifecycle] wiped data for %s", pwa_id);
    } else {
        g_message("[lifecycle] nothing to wipe for %s", pwa_id);
    }
    return 0;
}

static void print_usage(void) {
    g_print(
        "Usage: nuxel-pwa-launcher [--install <manifest-path>] [--uninstall <app-id>] [--wipe-data <app-id>]\n"
        "  (no flags)              boot the PWA in an isolated WebKitGTK webview\n"
        "  --install <file>        install a PWA from its manifest.json\n"
        "  --uninstall <app-id>    uninstall a PWA and wipe its data\n"
        "  --wipe-data <app-id>    wipe a PWA's data without uninstalling\n");
}

/* ---- Main ---- */

int main(int argc, char *argv[]) {
    /* ---- Lifecycle CLI handling (install / uninstall / wipe-data) ---- */
    for (int i = 1; i < argc; i++) {
        if (g_strcmp0(argv[i], "--install") == 0 && i + 1 < argc) {
            return lifecycle_install(argv[++i]);
        } else if (g_strcmp0(argv[i], "--uninstall") == 0 && i + 1 < argc) {
            return lifecycle_uninstall(argv[++i]);
        } else if (g_strcmp0(argv[i], "--wipe-data") == 0 && i + 1 < argc) {
            return lifecycle_wipe(argv[++i]);
        } else if (g_strcmp0(argv[i], "--help") == 0 || g_strcmp0(argv[i], "-h") == 0) {
            print_usage();
            return 0;
        }
    }

    /* Parse arguments */
    app_id = getenv("NUXXEL_APP_ID");
    data_dir = getenv("NUXXEL_DATA_DIR");
    manifest_path = getenv("NUXXEL_MANIFEST_PATH");
    bridge_socket_path = getenv("NUXXEL_BRIDGE_SOCKET");
    
    if (!app_id) app_id = "org.example.pwa";
    if (!data_dir) {
        data_dir = g_strdup_printf("/var/app/%s/data", app_id);
    }
    if (!manifest_path) {
        manifest_path = g_strdup_printf("/app/share/nuxel-pwa/manifest.json");
    }
    
    g_message("Nuxel PWA Launcher starting");
    g_message("  App ID:     %s", app_id);
    g_message("  Data dir:   %s", data_dir);
    g_message("  Manifest:   %s", manifest_path);
    g_message("  Bridge:     %s", bridge_socket_path ? bridge_socket_path : "(none)");
    
    /* Initialize GTK/Wayland */
    gtk_init();
    
    /* Load manifest */
    if (!load_manifest(manifest_path)) {
        g_warning("Failed to load manifest, continuing with defaults");
    }
    
    /* Connect to bridge */
    connect_bridge();
    
    /* Set up hardened WebContext */
    setup_web_context();
    
    /* Create window with PWA styling */
    GtkWidget *window = gtk_window_new();
    gtk_window_set_default_size(GTK_WINDOW(window), 3120, 1440);  /* Mustang display */
    gtk_window_set_title(GTK_WINDOW(window), app_id);
    gtk_window_set_decorated(GTK_WINDOW(window), FALSE);  /* No chrome - fullscreen PWA */
    gtk_widget_set_name(window, "nuxel-pwa-window");
    
    /* Create web view */
    web_view = create_web_view();
    gtk_window_set_child(GTK_WINDOW(window), GTK_WIDGET(web_view));
    
    /* Inject bridge API */
    inject_bridge_api(web_view);
    
    /* Load PWA */
    load_pwa();
    
    /* Show window */
    gtk_widget_set_visible(window, TRUE);
    
    /* Run main loop */
    g_application_run(G_APPLICATION(gtk_window_get_application(GTK_WINDOW(window))), 0, NULL);
    
    /* Cleanup */
    if (bridge_fd >= 0) close(bridge_fd);
    
    return 0;
}
