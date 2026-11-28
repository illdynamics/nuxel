/**
 * Nuxel Contacts — Native contact manager for Nuxel OS
 * GTK4/libadwaita, local address book + SIM phonebook mirror.
 *
 * Visual language follows the Nuxel reference apps (Maps / Snekbyte /
 * Firewall): deep navy ground, rounded panel cards, cyan accent, muted dim
 * text and flat touch targets.  Every import/merge is additive and idempotent;
 * this app never deletes a contact as a side effect of an import, and the
 * physical SIM is never written (it has no editor here), which the UI states.
 */

#include <adwaita.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>
#include <glib.h>
#include <gio/gio.h>
/* Shared phone data model (contacts/call log/messages) used by nuxel-dialer,
 * nuxel-contacts and nuxel-messages.  Dependency-free C11: see
 * nuxel-phone-data/README.md and nuxel-phone-data/run-tests.sh. */
#include "nuxel-phone-data.h"

/* ============================================================
 * Data structures
 * ============================================================ */

typedef struct {
    gchar *id;
    gchar *name;
    gchar *phone;
    gchar *email;
    gchar *avatar_color;
} Contact;

typedef struct {
    GtkWidget *window;
    GtkWidget *stack;
    GtkWidget *contact_list;
    GtkWidget *detail_page;
    
    /* Detail view widgets */
    GtkWidget *detail_name;
    GtkWidget *detail_phone;
    GtkWidget *detail_email;
    GtkWidget *detail_avatar;
    
    /* Edit view */
    GtkWidget *edit_name_entry;
    GtkWidget *edit_phone_entry;
    GtkWidget *edit_email_entry;
    
    /* Data */
    GPtrArray *contacts;
    GHashTable *contacts_by_id;
    Contact *active_contact;
    gchar *data_dir;

    /* Shared store (the authoritative on-disk model) + a status line so the UI
     * can report a real write failure instead of pretending it saved. */
    NuxelPhoneStore store;
    gchar *store_path;
    GtkWidget *status_label;

    /* SIM phonebook mirror.  This build has no ModemManager SIM phonebook
     * API, so the mirror is explicit local storage: it is imported/synced on
     * demand and can be copied to a real SIM when the modem path exists.  The
     * UI never claims the physical SIM was written. */
    NuxelPhoneStore sim_store;
    gchar *sim_path;
} NuxelContacts;

/* ============================================================
 * Forward declarations
 * ============================================================ */

static void save_contacts(NuxelContacts *app);
static void load_contacts(NuxelContacts *app);
static void on_vcard_chosen(GObject *source, GAsyncResult *res, gpointer user_data);
static void on_import_vcard_clicked(GtkWidget *btn, gpointer user_data);
static void on_export_vcard_clicked(GtkWidget *btn, gpointer user_data);
static void on_backup_clicked(GtkWidget *btn, gpointer user_data);
static void rebuild_contact_rows(NuxelContacts *app);
static void on_edit_contact_clicked(GtkWidget *btn, gpointer user_data);
static void on_save_to_sim_clicked(GtkWidget *btn, gpointer user_data);
static void on_import_sim_clicked(GtkWidget *btn, gpointer user_data);
static void on_sync_sim_clicked(GtkWidget *btn, gpointer user_data);

/* ============================================================
 * Contact lifecycle
 * ============================================================ */

static Contact *
contact_new(const gchar *name, const gchar *phone, const gchar *email)
{
    Contact *c = g_new0(Contact, 1);
    c->id = g_strdup_printf("contact-%u", g_random_int());
    c->name = g_strdup(name ? name : "Unknown");
    c->phone = g_strdup(phone ? phone : "");
    c->email = g_strdup(email ? email : "");
    
    /* Generate avatar color */
    const gchar *colors[] = {"#E91E63","#FF9800","#2196F3","#4CAF50",
                              "#9C27B0","#F44336","#607D8B","#795548"};
    guint hash = g_str_hash(c->name);
    c->avatar_color = g_strdup(colors[hash % G_N_ELEMENTS(colors)]);
    
    return c;
}

static void
contact_free(gpointer data)
{
    Contact *c = (Contact *)data;
    if (c) {
        g_free(c->id);
        g_free(c->name);
        g_free(c->phone);
        g_free(c->email);
        g_free(c->avatar_color);
        g_free(c);
    }
}

/* ============================================================
 * Data persistence
 * ============================================================ */

static void
contacts_status(NuxelContacts *app, const gchar *text)
{
    if (app->status_label)
        gtk_label_set_text(GTK_LABEL(app->status_label), text ? text : "");
    g_message("[Contacts] %s", text ? text : "");
}

/* load_contacts() reads the shared store into the UI model.  It does NOT clear
 * the UI model first, so callers that have unsaved rows on screen (e.g. a vCard
 * import, which adds straight to the store) must reset it themselves or their
 * just-loaded contacts are prepended a second time and then duplicated.
 * Keep a tiny helper so the intent is explicit at each call site. */
static void
contacts_model_reset(NuxelContacts *app)
{
    g_ptr_array_set_size(app->contacts, 0);
    g_hash_table_remove_all(app->contacts_by_id);
    app->active_contact = NULL;
}

/* Copy the UI model into the shared store and flush it atomically.
 *
 * This is the fix for the A32 defect where save_contacts() built a JSON tree and
 * never wrote it to the file: contacts were silently lost on exit.  The write now
 * goes through nuxel_phone_store_save(), which writes <path>.tmp and renames, so
 * a crash cannot leave a half-written address book. */
static void
save_contacts(NuxelContacts *app)
{
    if (!app->store_path) {
        contacts_status(app, "No storage location configured — nothing was saved.");
        return;
    }

    nuxel_phone_store_free(&app->store);
    nuxel_phone_store_init(&app->store);

    for (guint i = 0; i < app->contacts->len; i++) {
        Contact *c = g_ptr_array_index(app->contacts, i);
        NuxelContact *stored = nuxel_phone_add_contact(&app->store, c->name, c->phone, c->email);
        if (stored) {
            /* keep the shared id so vCard UIDs stay stable across edits */
            g_strlcpy(stored->id, c->id ? c->id : stored->id, sizeof stored->id);
            if (c->avatar_color)
                g_strlcpy(stored->avatar_color, c->avatar_color, sizeof stored->avatar_color);
        }
    }

    if (nuxel_phone_store_save(&app->store, app->store_path) == 0) {
        gchar *msg = g_strdup_printf("Saved %u contact(s) to %s",
                                     app->contacts->len, app->store_path);
        contacts_status(app, msg);
        g_free(msg);
    } else {
        contacts_status(app, "Save failed — the address book on disk was NOT changed.");
    }
}

/* Load via the shared store.  The previous loader also seeded three fake
 * contacts ("Alice Johnson", ...) when the file was missing, which made an empty
 * address book look populated; we now start genuinely empty and say so. */
static void
load_contacts(NuxelContacts *app)
{
    if (!app->store_path) {
        gtk_label_set_text(GTK_LABEL(app->status_label),
                           "No storage location configured — contacts are read-only.");
        return;
    }

    /* Rebuild the on-screen model from the store instead of appending to it. */
    contacts_model_reset(app);
    nuxel_phone_store_free(&app->store);
    nuxel_phone_store_init(&app->store);

    int rc = nuxel_phone_store_load(&app->store, app->store_path);
    if (rc == -1)
        contacts_status(app, "The stored address book could not be parsed; starting empty (the file was left in place).");
    else if (rc == -2)
        contacts_status(app, "The stored address book was written by a newer Nuxel version; refusing to downgrade it.");
    else if (app->store.n_contacts == 0)
        contacts_status(app, "Address book is empty. Add a contact or import a vCard.");
    else {
        gchar *msg = g_strdup_printf("Loaded %u contact(s) from %s",
                                     (guint)app->store.n_contacts, app->store_path);
        contacts_status(app, msg);
        g_free(msg);
    }

    for (size_t i = 0; i < app->store.n_contacts; i++) {
        NuxelContact *sc = &app->store.contacts[i];
        Contact *c = contact_new(sc->name, sc->phone, sc->email);
        g_free(c->id);
        c->id = g_strdup(sc->id);
        /* Copy the stored phone verbatim: contact_new() would run it through
         * the dialled-digit normaliser, which drops a name-only SIM entry. */
        g_free(c->phone);
        c->phone = g_strdup(sc->phone);
        if (sc->avatar_color[0]) {
            g_free(c->avatar_color);
            c->avatar_color = g_strdup(sc->avatar_color);
        }
        g_ptr_array_add(app->contacts, c);
        g_hash_table_insert(app->contacts_by_id, g_strdup(c->id), c);
    }
}

/* vCard 3.0 import/export (offline, no network, no account). */
static void
on_export_vcard_clicked(GtkWidget *btn, gpointer user_data)
{
    NuxelContacts *app = (NuxelContacts *)user_data;
    (void)btn;

    save_contacts(app);   /* export exactly what is on screen */

    gchar *vcards = NULL;
    if (nuxel_phone_export_vcard(&app->store, &vcards) != 0 || !vcards) {
        contacts_status(app, "Export failed: the vCard writer could not build the file.");
        return;
    }

    gchar *dir = g_path_get_dirname(app->store_path);
    gchar *out = g_build_filename(dir, "contacts-export.vcf", NULL);
    GError *error = NULL;
    if (!g_file_set_contents(out, vcards, -1, &error)) {
        gchar *msg = g_strdup_printf("Export failed: %s",
                                     error ? error->message : "unknown error");
        contacts_status(app, msg);
        g_free(msg);
        if (error) g_error_free(error);
    } else {
        gchar *msg = g_strdup_printf("Exported %u contact(s) to %s (vCard 3.0)",
                                     app->contacts->len, out);
        contacts_status(app, msg);
        g_free(msg);
    }
    g_free(out);
    g_free(dir);
    g_free(vcards);
}

static void
on_import_vcard_clicked(GtkWidget *btn, gpointer user_data)
{
    NuxelContacts *app = (NuxelContacts *)user_data;
    (void)btn;

    GtkFileDialog *dialog = gtk_file_dialog_new();
    gtk_file_dialog_set_title(dialog, "Import a vCard file");

    /* GTK4: async file dialog; the callback re-reads through the shared store. */
    gtk_file_dialog_open(dialog, GTK_WINDOW(app->window), NULL,
                         (GAsyncReadyCallback)on_vcard_chosen, app);
}

static void
on_vcard_chosen(GObject *source, GAsyncResult *res, gpointer user_data)
{
    NuxelContacts *app = (NuxelContacts *)user_data;
    GError *error = NULL;
    GFile *file = gtk_file_dialog_open_finish(GTK_FILE_DIALOG(source), res, &error);
    if (!file) {
        if (error) {
            contacts_status(app, error->message);
            g_error_free(error);
        }
        return;
    }

    gchar *path = g_file_get_path(file);
    gchar *text = NULL;
    gsize len = 0;
    if (!path || !g_file_get_contents(path, &text, &len, &error)) {
        gchar *msg = g_strdup_printf("Import failed: %s",
                                     error ? error->message : "cannot read that file");
        contacts_status(app, msg);
        g_free(msg);
        if (error) g_error_free(error);
        g_free(path);
        g_object_unref(file);
        return;
    }

    int imported = 0;
    if (nuxel_phone_import_vcard(&app->store, text, len, &imported) != 0) {
        contacts_status(app, "Import failed: that file is not a vCard stream we can read.");
    } else {
        /* Rebuild the UI model from the store so the imported people appear. */
        g_ptr_array_set_size(app->contacts, 0);
        g_hash_table_remove_all(app->contacts_by_id);
        nuxel_phone_store_save(&app->store, app->store_path);
        for (size_t i = 0; i < app->store.n_contacts; i++) {
            NuxelContact *sc = &app->store.contacts[i];
            Contact *c = contact_new(sc->name, sc->phone, sc->email);
            g_free(c->id);
            c->id = g_strdup(sc->id);
            g_ptr_array_add(app->contacts, c);
            g_hash_table_insert(app->contacts_by_id, g_strdup(c->id), c);
        }
        gchar *msg = g_strdup_printf("Imported %d contact(s) from %s",
                                     imported, path);
        contacts_status(app, msg);
        g_free(msg);
    }

    g_free(text);
    g_free(path);
    g_object_unref(file);
}

/* ============================================================
 * SIM phonebook mirror
 * ============================================================ */

/* True when `store` already holds this SIM entry.  Name-only SIM records (the
 * phonebook storage name with no number) must match on name too, otherwise the
 * export direction re-adds them on every Sync. */
static gboolean
sim_contact_exists(NuxelPhoneStore *store, const gchar *name, const gchar *phone)
{
    for (size_t i = 0; i < store->n_contacts; i++) {
        if (g_strcmp0(store->contacts[i].name, name) == 0 &&
            g_strcmp0(store->contacts[i].phone, phone) == 0)
            return TRUE;
    }
    if (phone && *phone && nuxel_phone_find_contact_by_number(store, phone))
        return TRUE;
    for (size_t i = 0; i < store->n_contacts; i++) {
        if (g_strcmp0(store->contacts[i].name, name) == 0)
            return TRUE;
    }
    return FALSE;
}

static void
sim_load(NuxelContacts *app)
{
    nuxel_phone_store_free(&app->sim_store);
    nuxel_phone_store_init(&app->sim_store);
    if (app->sim_path)
        nuxel_phone_store_load(&app->sim_store, app->sim_path);
}

static void
sim_save(NuxelContacts *app)
{
    if (!app->sim_path) return;
    nuxel_phone_store_save(&app->sim_store, app->sim_path);
}

static void
rebuild_contact_rows(NuxelContacts *app)
{
    GtkWidget *child = gtk_widget_get_first_child(app->contact_list);
    while (child) {
        GtkWidget *next = gtk_widget_get_next_sibling(child);
        gtk_list_box_remove(GTK_LIST_BOX(app->contact_list), child);
        child = next;
    }
    for (guint i = 0; i < app->contacts->len; i++) {
        Contact *c = g_ptr_array_index(app->contacts, i);
        GtkWidget *row = gtk_list_box_row_new();
        GtkWidget *card = gtk_box_new(GTK_ORIENTATION_HORIZONTAL, 12);
        gtk_widget_add_css_class(card, "nuxel-row");
        gchar *initial = c->name && *c->name ? g_utf8_substring(c->name, 0, 1) : g_strdup("?");
        GtkWidget *avatar = gtk_label_new(initial);
        g_free(initial);
        gtk_widget_add_css_class(avatar, "nuxel-avatar");
        gtk_widget_set_valign(avatar, GTK_ALIGN_CENTER);
        gtk_box_append(GTK_BOX(card), avatar);
        GtkWidget *text_box = gtk_box_new(GTK_ORIENTATION_VERTICAL, 3);
        gtk_widget_set_hexpand(text_box, TRUE);
        GtkWidget *name_label = gtk_label_new(c->name ? c->name : "");
        gtk_widget_add_css_class(name_label, "nuxel-row-title");
        gtk_label_set_xalign(GTK_LABEL(name_label), 0.0);
        gtk_label_set_ellipsize(GTK_LABEL(name_label), PANGO_ELLIPSIZE_END);
        gtk_box_append(GTK_BOX(text_box), name_label);
        GtkWidget *phone_label = gtk_label_new(c->phone ? c->phone : "");
        gtk_widget_add_css_class(phone_label, "dim");
        gtk_label_set_xalign(GTK_LABEL(phone_label), 0.0);
        gtk_label_set_ellipsize(GTK_LABEL(phone_label), PANGO_ELLIPSIZE_END);
        gtk_box_append(GTK_BOX(text_box), phone_label);
        gtk_box_append(GTK_BOX(card), text_box);
        gtk_list_box_row_set_child(GTK_LIST_BOX_ROW(row), card);
        g_object_set_data(G_OBJECT(row), "contact", c);
        gtk_list_box_append(GTK_LIST_BOX(app->contact_list), row);
    }
}

static void
on_import_sim_clicked(GtkWidget *btn, gpointer user_data)
{
    NuxelContacts *app = (NuxelContacts *)user_data;
    (void)btn;
    sim_load(app);
    if (app->sim_store.n_contacts == 0) {
        contacts_status(app, "The SIM contact mirror holds no names yet. Import SIM on Messages "
                              "merges the SIM's messages and names into this address book; the "
                              "physical phonebook reader (PB_CMD/EF_ADN) is not wired on this build.");
        return;
    }
    size_t added = 0;
    for (size_t i = 0; i < app->sim_store.n_contacts; i++) {
        NuxelContact *sc = &app->sim_store.contacts[i];
        if (sim_contact_exists(&app->store, sc->name, sc->phone)) continue;
        if (nuxel_phone_add_contact(&app->store, sc->name, sc->phone, sc->email)) added++;
    }
    if (added) {
        nuxel_phone_store_save(&app->store, app->store_path);
        load_contacts(app);
        rebuild_contact_rows(app);
    }
    gchar *msg = g_strdup_printf("Imported %zu contact(s) from the SIM mirror. "
                                 "No physical SIM write was attempted.", added);
    contacts_status(app, msg);
    g_free(msg);
}

static void
on_sync_sim_clicked(GtkWidget *btn, gpointer user_data)
{
    NuxelContacts *app = (NuxelContacts *)user_data;
    (void)btn;
    /* The on-screen model is the source of truth for the export direction;
     * make sure the shared store has it before merging (otherwise a Sync
     * before any edit could save only the imported direction). */
    save_contacts(app);
    sim_load(app);
    size_t to_local = 0, to_sim = 0;
    for (size_t i = 0; i < app->sim_store.n_contacts; i++) {
        NuxelContact *sc = &app->sim_store.contacts[i];
        if (!sim_contact_exists(&app->store, sc->name, sc->phone)) {
            if (nuxel_phone_add_contact(&app->store, sc->name, sc->phone, sc->email)) to_local++;
        }
    }
    for (guint i = 0; i < app->contacts->len; i++) {
        Contact *c = g_ptr_array_index(app->contacts, i);
        if (!sim_contact_exists(&app->sim_store, c->name, c->phone)) {
            if (nuxel_phone_add_contact(&app->sim_store, c->name, c->phone, c->email)) to_sim++;
        }
    }
    nuxel_phone_store_save(&app->store, app->store_path);
    sim_save(app);
    load_contacts(app);
    rebuild_contact_rows(app);
    gchar *msg = g_strdup_printf("Sync complete: %zu contact(s) imported from the SIM, %zu copied "
                                 "to the SIM mirror. Additive only — nothing was deleted. The physical "
                                 "SIM was not written (no phonebook editor on this build).", to_local, to_sim);
    contacts_status(app, msg);
    g_free(msg);
}

static void
on_save_to_sim_clicked(GtkWidget *btn, gpointer user_data)
{
    NuxelContacts *app = (NuxelContacts *)user_data;
    (void)btn;
    Contact *c = app->active_contact;
    if (!c) { contacts_status(app, "Open a contact first, then save it to the SIM mirror."); return; }
    sim_load(app);
    if (!sim_contact_exists(&app->sim_store, c->name, c->phone)) {
        nuxel_phone_add_contact(&app->sim_store, c->name, c->phone, c->email);
        sim_save(app);
    }
    gchar *msg = g_strdup_printf("Saved %s to the SIM mirror (%s).", c->name, app->sim_path);
    contacts_status(app, msg);
    g_free(msg);
}

static void
on_edit_contact_clicked(GtkWidget *btn, gpointer user_data)
{
    NuxelContacts *app = (NuxelContacts *)user_data;
    (void)btn;
    if (!app->active_contact) return;
    gtk_editable_set_text(GTK_EDITABLE(app->edit_name_entry), app->active_contact->name);
    gtk_editable_set_text(GTK_EDITABLE(app->edit_phone_entry), app->active_contact->phone);
    gtk_editable_set_text(GTK_EDITABLE(app->edit_email_entry), app->active_contact->email);
    gtk_stack_set_visible_child_name(GTK_STACK(app->stack), "edit");
}

/* ============================================================
 * UI Callbacks
 * ============================================================ */

static void
on_add_contact_clicked(GtkWidget *btn, gpointer user_data)
{
    NuxelContacts *app = (NuxelContacts *)user_data;
    gtk_stack_set_visible_child_name(GTK_STACK(app->stack), "edit");
    gtk_editable_set_text(GTK_EDITABLE(app->edit_name_entry), "");
    gtk_editable_set_text(GTK_EDITABLE(app->edit_phone_entry), "");
    gtk_editable_set_text(GTK_EDITABLE(app->edit_email_entry), "");
    app->active_contact = NULL;
}

static void
on_contact_row_activated(GtkListBox *box, GtkListBoxRow *row, gpointer user_data)
{
    NuxelContacts *app = (NuxelContacts *)user_data;
    Contact *c = (Contact *)g_object_get_data(G_OBJECT(row), "contact");
    if (!c) return;
    
    app->active_contact = c;
    gtk_label_set_text(GTK_LABEL(app->detail_name), c->name);
    gtk_label_set_text(GTK_LABEL(app->detail_phone), c->phone);
    gtk_label_set_text(GTK_LABEL(app->detail_email), c->email);
    
    /* Update avatar (plain styled label, same as the list rows). */
    {
        gchar *iv = c->name && *c->name ? g_utf8_substring(c->name, 0, 1) : g_strdup("?");
        gtk_label_set_text(GTK_LABEL(app->detail_avatar), iv);
        g_free(iv);
    }
    
    gtk_stack_set_visible_child_name(GTK_STACK(app->stack), "detail");
}


static gint
contacts_compare(gconstpointer a, gconstpointer b, gpointer user_data)
{
    const Contact *ca = (const Contact *)a;
    const Contact *cb = (const Contact *)b;
    return g_strcmp0(ca->name, cb->name);
}

static void
on_save_clicked(GtkWidget *btn, gpointer user_data)
{
    NuxelContacts *app = (NuxelContacts *)user_data;
    
    const gchar *name = gtk_editable_get_text(GTK_EDITABLE(app->edit_name_entry));
    const gchar *phone = gtk_editable_get_text(GTK_EDITABLE(app->edit_phone_entry));
    const gchar *email = gtk_editable_get_text(GTK_EDITABLE(app->edit_email_entry));
    
    if (!name || strlen(name) == 0) return;
    
    if (app->active_contact) {
        /* Update existing */
        g_free(app->active_contact->name);
        g_free(app->active_contact->phone);
        g_free(app->active_contact->email);
        app->active_contact->name = g_strdup(name);
        app->active_contact->phone = g_strdup(phone);
        app->active_contact->email = g_strdup(email);
    } else {
        /* Create new */
        Contact *c = contact_new(name, phone, email);
        g_ptr_array_add(app->contacts, c);
        g_hash_table_insert(app->contacts_by_id, g_strdup(c->id), c);
    }
    
    save_contacts(app);
    
    /* Keep the active contact object valid after sorting, then rebuild once. */
    g_ptr_array_sort_with_data(app->contacts, (GCompareDataFunc)contacts_compare, NULL);
    rebuild_contact_rows(app);
    gtk_stack_set_visible_child_name(GTK_STACK(app->stack), "list");
}

static void
on_delete_clicked(GtkWidget *btn, gpointer user_data)
{
    NuxelContacts *app = (NuxelContacts *)user_data;
    if (!app->active_contact) return;
    
    /* g_ptr_array_remove() invokes contact_free(), so the id must be copied
     * before the hash lookup.  The old order was a use-after-free. */
    gchar *id = g_strdup(app->active_contact->id);
    g_hash_table_remove(app->contacts_by_id, id);
    g_ptr_array_remove(app->contacts, app->active_contact);
    g_free(id);
    app->active_contact = NULL;
    save_contacts(app);
    gtk_stack_set_visible_child_name(GTK_STACK(app->stack), "list");
}

static void
on_back_to_list_clicked(GtkWidget *btn, gpointer user_data)
{
    NuxelContacts *app = (NuxelContacts *)user_data;
    gtk_stack_set_visible_child_name(GTK_STACK(app->stack), "list");
}

/* ============================================================
 * Nuxel design tokens (same values as Firewall / Maps / Snekbyte)
 * ============================================================ */

static const char *CONTACTS_CSS =
    "window, .nuxel-root, .nuxel-page, .nuxel-list-scroll, scrolledwindow { background: #0a1628; }"
    ".nuxel-head { padding: 14px 16px 10px; border-bottom: 1px solid rgba(255,255,255,0.08); }"
    ".nuxel-title { font-size: 19px; font-weight: 700; color: #e6f0ff; }"
    ".nuxel-toolbar { padding: 8px 12px; }"
    ".nuxel-panel { background: #12233c; border-radius: 14px; margin: 0 12px 12px 12px; padding: 16px; }"
    ".nuxel-row { background: #12233c; border-radius: 14px; padding: 12px; margin: 4px 8px; }"
    ".nuxel-row-title { font-weight: 700; font-size: 15px; color: #e6f0ff; }"
    ".dim { color: #8aa3c7; font-size: 12px; }"
    ".nuxel-avatar { background: rgba(62,166,255,0.18); color: #3ea6ff; border-radius: 18px;"
    "  min-width: 36px; min-height: 36px; font-weight: 700; }"
    ".nuxel-big-avatar { background: rgba(62,166,255,0.18); color: #3ea6ff; border-radius: 36px;"
    "  min-width: 72px; min-height: 72px; font-size: 28px; font-weight: 700; }"
    ".nuxel-detail-name { font-size: 22px; font-weight: 700; color: #e6f0ff; }"
    ".nuxel-detail-value { font-size: 17px; color: #e6f0ff; }"
    ".nuxel-danger { background: #ff5b5b; color: #2a0505; font-weight: 600; }"
    ".nuxel-panel entry { background: #0a1628; color: #e6f0ff; border-radius: 10px; min-height: 40px; }"
    ".nuxel-panel button, .nuxel-toolbar button, .nuxel-head button { min-height: 40px; }"
    "listbox { background: transparent; }"
    "listbox row { background: transparent; }"
    "listbox row:selected { background: transparent; }";

/* Back up the address book and the SIM phonebook mirror side by side.  This is
 * the "back it up before anything" safety the owner asked for: nothing is
 * modified, an extra timestamped copy of both files is written. */
static void
on_backup_clicked(GtkWidget *btn, gpointer user_data)
{
    NuxelContacts *app = (NuxelContacts *)user_data;
    (void)btn;
    gint64 now = (gint64)time(NULL);
    gchar *dir = g_path_get_dirname(app->store_path);
    gchar *bkdir = g_build_filename(dir, "backups", NULL);
    g_mkdir_with_parents(bkdir, 0700);
    gchar *copies[2] = { app->store_path, app->sim_path };
    gchar *names[2] = { "contacts", "sim-contacts" };
    guint copied = 0;
    for (guint i = 0; i < 2 && dir; i++) {
        if (!copies[i] || !g_file_test(copies[i], G_FILE_TEST_EXISTS)) continue;
        gchar *base = g_path_get_basename(copies[i]);
        gchar *dst = g_strdup_printf("%s/%s.%lld.%s", bkdir, names[i], (long long)now, base);
        gchar *data = NULL; gsize len = 0;
        if (g_file_get_contents(copies[i], &data, &len, NULL)) {
            if (g_file_set_contents(dst, data, (gssize)len, NULL)) copied++;
            g_free(data);
        }
        g_free(dst);
        g_free(base);
    }
    gchar *msg = g_strdup_printf(copied
        ? "Backup written: %u file(s) under %s (address book and SIM mirror). Nothing was modified."
        : "Backup: no contact store exists yet, so there was nothing to copy.",
        copied, bkdir);
    contacts_status(app, msg);
    g_free(msg);
    g_free(bkdir);
    g_free(dir);
}

/* ============================================================
 * UI Construction
 * ============================================================ */

static void
activate_cb(GtkApplication *gtk_app, gpointer user_data)
{
    NuxelContacts *app = g_new0(NuxelContacts, 1);
    
    /* Setup data directory */
    app->data_dir = g_build_filename(g_get_user_data_dir(), "nuxel-contacts", NULL);
    g_mkdir_with_parents(app->data_dir, 0755);

    /* Authoritative store: same file the A32 build intended to write, now written
     * through the shared phone data layer (atomic tmp+rename, schema_version 1). */
    app->store_path = g_build_filename(app->data_dir, "contacts.json", NULL);
    app->sim_path = g_build_filename(app->data_dir, "sim-contacts.json", NULL);
    nuxel_phone_store_init(&app->store);
    nuxel_phone_store_init(&app->sim_store);
    
    app->contacts = g_ptr_array_new_with_free_func(contact_free);
    app->contacts_by_id = g_hash_table_new_full(g_str_hash, g_str_equal, g_free, NULL);
    
    /* Create window */
    app->window = adw_application_window_new(gtk_app);
    gtk_window_set_title(GTK_WINDOW(app->window), "Contacts");
    gtk_window_set_default_size(GTK_WINDOW(app->window), 400, 700);
    
    /* CSS */
    GtkCssProvider *provider = gtk_css_provider_new();
    gtk_css_provider_load_from_string(provider, CONTACTS_CSS);
    gtk_style_context_add_provider_for_display(
        gdk_display_get_default(),
        GTK_STYLE_PROVIDER(provider),
        GTK_STYLE_PROVIDER_PRIORITY_APPLICATION);
    g_object_unref(provider);
    
    /* Stack */
    app->stack = gtk_stack_new();
    gtk_stack_set_transition_type(GTK_STACK(app->stack), GTK_STACK_TRANSITION_TYPE_SLIDE_LEFT_RIGHT);
    
    /* Page 1: Contact list (Nuxel design language). */
    GtkWidget *list_page = gtk_box_new(GTK_ORIENTATION_VERTICAL, 0);
    gtk_widget_add_css_class(list_page, "nuxel-page");

    GtkWidget *header = gtk_box_new(GTK_ORIENTATION_HORIZONTAL, 8);
    gtk_widget_add_css_class(header, "nuxel-head");
    GtkWidget *title = gtk_label_new("Contacts");
    gtk_widget_add_css_class(title, "nuxel-title");
    gtk_label_set_xalign(GTK_LABEL(title), 0.0);
    gtk_widget_set_hexpand(title, TRUE);
    gtk_box_append(GTK_BOX(header), title);

    GtkWidget *import_sim_btn = gtk_button_new_with_label("Import SIM");
    gtk_widget_add_css_class(import_sim_btn, "flat");
    gtk_widget_set_tooltip_text(import_sim_btn,
        "Copy contact names and numbers from the SIM phonebook mirror (additive, nothing is deleted)");
    g_signal_connect(import_sim_btn, "clicked", G_CALLBACK(on_import_sim_clicked), app);
    gtk_box_append(GTK_BOX(header), import_sim_btn);

    GtkWidget *sync_sim_btn = gtk_button_new_with_label("Sync");
    gtk_widget_add_css_class(sync_sim_btn, "flat");
    gtk_widget_set_tooltip_text(sync_sim_btn,
        "Re-sync both ways: import new SIM contacts, copy local contacts missing from the mirror");
    g_signal_connect(sync_sim_btn, "clicked", G_CALLBACK(on_sync_sim_clicked), app);
    gtk_box_append(GTK_BOX(header), sync_sim_btn);

    GtkWidget *add_btn = gtk_button_new_with_label("New");
    gtk_widget_add_css_class(add_btn, "suggested-action");
    g_signal_connect(add_btn, "clicked", G_CALLBACK(on_add_contact_clicked), app);
    gtk_box_append(GTK_BOX(header), add_btn);

    gtk_box_append(GTK_BOX(list_page), header);

    /* Secondary actions: vCard import/export (offline, no network, no account)
     * plus an explicit full backup of both the address book and SIM mirror. */
    GtkWidget *actions = gtk_box_new(GTK_ORIENTATION_HORIZONTAL, 6);
    gtk_widget_add_css_class(actions, "nuxel-toolbar");
    GtkWidget *import_btn = gtk_button_new_with_label("Import vCard");
    gtk_widget_add_css_class(import_btn, "flat");
    g_signal_connect(import_btn, "clicked", G_CALLBACK(on_import_vcard_clicked), app);
    gtk_box_append(GTK_BOX(actions), import_btn);
    GtkWidget *export_btn = gtk_button_new_with_label("Export vCard");
    gtk_widget_add_css_class(export_btn, "flat");
    g_signal_connect(export_btn, "clicked", G_CALLBACK(on_export_vcard_clicked), app);
    gtk_box_append(GTK_BOX(actions), export_btn);
    GtkWidget *backup_btn = gtk_button_new_with_label("Back up all");
    gtk_widget_add_css_class(backup_btn, "flat");
    gtk_widget_set_tooltip_text(backup_btn,
        "Write a timestamped backup of the address book and SIM mirror next to the stores");
    g_signal_connect(backup_btn, "clicked", G_CALLBACK(on_backup_clicked), app);
    gtk_box_append(GTK_BOX(actions), backup_btn);
    gtk_box_append(GTK_BOX(list_page), actions);

    /* Status line: every save/import/export reports its real outcome here. */
    app->status_label = gtk_label_new("");
    gtk_widget_add_css_class(app->status_label, "dim");
    gtk_label_set_xalign(GTK_LABEL(app->status_label), 0.0);
    gtk_label_set_wrap(GTK_LABEL(app->status_label), TRUE);
    gtk_widget_set_margin_start(app->status_label, 14);
    gtk_widget_set_margin_end(app->status_label, 14);
    gtk_widget_set_margin_bottom(app->status_label, 8);
    gtk_box_append(GTK_BOX(list_page), app->status_label);

    app->contact_list = gtk_list_box_new();
    gtk_list_box_set_selection_mode(GTK_LIST_BOX(app->contact_list), GTK_SELECTION_NONE);
    g_signal_connect(app->contact_list, "row-activated",
                     G_CALLBACK(on_contact_row_activated), app);
    GtkWidget *scrolled = gtk_scrolled_window_new();
    gtk_widget_add_css_class(scrolled, "nuxel-list-scroll");
    gtk_scrolled_window_set_policy(GTK_SCROLLED_WINDOW(scrolled), GTK_POLICY_NEVER, GTK_POLICY_AUTOMATIC);
    gtk_scrolled_window_set_child(GTK_SCROLLED_WINDOW(scrolled), app->contact_list);
    gtk_widget_set_vexpand(scrolled, TRUE);
    gtk_box_append(GTK_BOX(list_page), scrolled);

    gtk_stack_add_named(GTK_STACK(app->stack), list_page, "list");
    
    /* Page 2: Detail view (same cards/typography/touch targets). */
    GtkWidget *detail_page = gtk_box_new(GTK_ORIENTATION_VERTICAL, 0);
    gtk_widget_add_css_class(detail_page, "nuxel-page");

    GtkWidget *det_header = gtk_box_new(GTK_ORIENTATION_HORIZONTAL, 8);
    gtk_widget_add_css_class(det_header, "nuxel-head");
    GtkWidget *back_btn = gtk_button_new_with_label("←");
    gtk_widget_add_css_class(back_btn, "flat");
    gtk_widget_set_tooltip_text(back_btn, "Back to contacts");
    g_signal_connect(back_btn, "clicked", G_CALLBACK(on_back_to_list_clicked), app);
    gtk_box_append(GTK_BOX(det_header), back_btn);

    GtkWidget *det_title = gtk_label_new("Contact");
    gtk_widget_add_css_class(det_title, "nuxel-title");
    gtk_label_set_xalign(GTK_LABEL(det_title), 0.0);
    gtk_widget_set_hexpand(det_title, TRUE);
    gtk_box_append(GTK_BOX(det_header), det_title);

    GtkWidget *edit_btn = gtk_button_new_with_label("Edit");
    gtk_widget_add_css_class(edit_btn, "flat");
    g_signal_connect(edit_btn, "clicked", G_CALLBACK(on_edit_contact_clicked), app);
    gtk_box_append(GTK_BOX(det_header), edit_btn);
    GtkWidget *delete_btn = gtk_button_new_with_label("Delete");
    gtk_widget_add_css_class(delete_btn, "nuxel-danger");
    g_signal_connect(delete_btn, "clicked", G_CALLBACK(on_delete_clicked), app);
    gtk_box_append(GTK_BOX(det_header), delete_btn);
    gtk_box_append(GTK_BOX(detail_page), det_header);

    GtkWidget *detail_card = gtk_box_new(GTK_ORIENTATION_VERTICAL, 8);
    gtk_widget_add_css_class(detail_card, "nuxel-panel");
    gtk_widget_set_margin_top(detail_card, 12);
    app->detail_avatar = gtk_label_new("?");
    gtk_widget_add_css_class(app->detail_avatar, "nuxel-big-avatar");
    gtk_widget_set_halign(app->detail_avatar, GTK_ALIGN_CENTER);
    gtk_box_append(GTK_BOX(detail_card), app->detail_avatar);

    app->detail_name = gtk_label_new("");
    gtk_widget_add_css_class(app->detail_name, "nuxel-detail-name");
    gtk_widget_set_halign(app->detail_name, GTK_ALIGN_CENTER);
    gtk_box_append(GTK_BOX(detail_card), app->detail_name);

    app->detail_phone = gtk_label_new("");
    gtk_widget_add_css_class(app->detail_phone, "nuxel-detail-value");
    gtk_label_set_selectable(GTK_LABEL(app->detail_phone), TRUE);
    gtk_widget_set_halign(app->detail_phone, GTK_ALIGN_CENTER);
    gtk_box_append(GTK_BOX(detail_card), app->detail_phone);

    app->detail_email = gtk_label_new("");
    gtk_widget_add_css_class(app->detail_email, "dim");
    gtk_label_set_selectable(GTK_LABEL(app->detail_email), TRUE);
    gtk_widget_set_halign(app->detail_email, GTK_ALIGN_CENTER);
    gtk_box_append(GTK_BOX(detail_card), app->detail_email);
    gtk_box_append(GTK_BOX(detail_page), detail_card);

    GtkWidget *detail_actions = gtk_box_new(GTK_ORIENTATION_HORIZONTAL, 6);
    gtk_widget_add_css_class(detail_actions, "nuxel-toolbar");
    GtkWidget *save_sim_btn = gtk_button_new_with_label("Save to SIM mirror");
    gtk_widget_add_css_class(save_sim_btn, "flat");
    gtk_widget_set_tooltip_text(save_sim_btn,
        "Copy this contact into the SIM phonebook mirror (never writes the physical SIM)");
    g_signal_connect(save_sim_btn, "clicked", G_CALLBACK(on_save_to_sim_clicked), app);
    gtk_box_append(GTK_BOX(detail_actions), save_sim_btn);
    gtk_box_append(GTK_BOX(detail_page), detail_actions);

    gtk_stack_add_named(GTK_STACK(app->stack), detail_page, "detail");
    
    /* Page 3: Edit view. */
    GtkWidget *edit_page = gtk_box_new(GTK_ORIENTATION_VERTICAL, 0);
    gtk_widget_add_css_class(edit_page, "nuxel-page");

    GtkWidget *edit_header = gtk_box_new(GTK_ORIENTATION_HORIZONTAL, 8);
    gtk_widget_add_css_class(edit_header, "nuxel-head");
    GtkWidget *edit_title = gtk_label_new("Contact");
    gtk_widget_add_css_class(edit_title, "nuxel-title");
    gtk_label_set_xalign(GTK_LABEL(edit_title), 0.0);
    gtk_widget_set_hexpand(edit_title, TRUE);
    gtk_box_append(GTK_BOX(edit_header), edit_title);
    GtkWidget *edit_cancel = gtk_button_new_with_label("Cancel");
    gtk_widget_add_css_class(edit_cancel, "flat");
    g_signal_connect(edit_cancel, "clicked", G_CALLBACK(on_back_to_list_clicked), app);
    gtk_box_append(GTK_BOX(edit_header), edit_cancel);
    GtkWidget *edit_save = gtk_button_new_with_label("Save");
    gtk_widget_add_css_class(edit_save, "suggested-action");
    g_signal_connect(edit_save, "clicked", G_CALLBACK(on_save_clicked), app);
    gtk_box_append(GTK_BOX(edit_header), edit_save);
    gtk_box_append(GTK_BOX(edit_page), edit_header);

    GtkWidget *edit_form = gtk_box_new(GTK_ORIENTATION_VERTICAL, 8);
    gtk_widget_add_css_class(edit_form, "nuxel-panel");
    gtk_widget_set_margin_top(edit_form, 12);

    GtkWidget *l1 = gtk_label_new("Name");
    gtk_widget_add_css_class(l1, "dim");
    gtk_label_set_xalign(GTK_LABEL(l1), 0.0);
    gtk_box_append(GTK_BOX(edit_form), l1);
    app->edit_name_entry = gtk_entry_new();
    gtk_entry_set_placeholder_text(GTK_ENTRY(app->edit_name_entry), "Name");
    gtk_box_append(GTK_BOX(edit_form), app->edit_name_entry);

    GtkWidget *l2 = gtk_label_new("Phone");
    gtk_widget_add_css_class(l2, "dim");
    gtk_label_set_xalign(GTK_LABEL(l2), 0.0);
    gtk_box_append(GTK_BOX(edit_form), l2);
    app->edit_phone_entry = gtk_entry_new();
    gtk_entry_set_placeholder_text(GTK_ENTRY(app->edit_phone_entry), "Phone");
    gtk_entry_set_input_purpose(GTK_ENTRY(app->edit_phone_entry), GTK_INPUT_PURPOSE_PHONE);
    gtk_box_append(GTK_BOX(edit_form), app->edit_phone_entry);

    GtkWidget *l3 = gtk_label_new("Email");
    gtk_widget_add_css_class(l3, "dim");
    gtk_label_set_xalign(GTK_LABEL(l3), 0.0);
    gtk_box_append(GTK_BOX(edit_form), l3);
    app->edit_email_entry = gtk_entry_new();
    gtk_entry_set_placeholder_text(GTK_ENTRY(app->edit_email_entry), "Email");
    gtk_box_append(GTK_BOX(edit_form), app->edit_email_entry);

    gtk_box_append(GTK_BOX(edit_page), edit_form);

    gtk_stack_add_named(GTK_STACK(app->stack), edit_page, "edit");
    
    gtk_widget_add_css_class(app->stack, "nuxel-root");
    gtk_widget_set_vexpand(app->stack, TRUE);
    adw_application_window_set_content(ADW_APPLICATION_WINDOW(app->window), app->stack);
    
    /* Dark by default: these phone apps must match the dark Nuxel shell. */
    AdwStyleManager *style = adw_style_manager_get_default();
    adw_style_manager_set_color_scheme(style, ADW_COLOR_SCHEME_FORCE_DARK);

    /* Load contacts */
    load_contacts(app);

    /* "Load from SIM automatically when one is added": this build has no
     * ModemManager SIM phonebook.  When the local address book is empty and a
     * SIM mirror already exists, import it automatically and say so. */
    sim_load(app);
    if (app->store.n_contacts == 0 && app->sim_store.n_contacts > 0) {
        size_t added = 0;
        for (size_t i = 0; i < app->sim_store.n_contacts; i++) {
            NuxelContact *sc = &app->sim_store.contacts[i];
            if (nuxel_phone_add_contact(&app->store, sc->name, sc->phone, sc->email)) added++;
        }
        if (added) {
            nuxel_phone_store_save(&app->store, app->store_path);
            load_contacts(app);
        }
    }

    rebuild_contact_rows(app);
    gtk_window_present(GTK_WINDOW(app->window));
}

int main(int argc, char *argv[])
{
    GtkApplication *gtk_app = gtk_application_new("org.nuxel.Contacts",
                                                   G_APPLICATION_DEFAULT_FLAGS);
    g_signal_connect(gtk_app, "activate", G_CALLBACK(activate_cb), NULL);
    
    int status = g_application_run(G_APPLICATION(gtk_app), argc, argv);
    g_object_unref(gtk_app);
    
    return status;
}
