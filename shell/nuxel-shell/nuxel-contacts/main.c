/**
 * Nuxel Contacts - Native Contact Manager for Nuxel OS
 * GTK4/libadwaita application with local contact storage
 */

#include <adwaita.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
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
} NuxelContacts;

/* ============================================================
 * Forward declarations
 * ============================================================ */

static void save_contacts(NuxelContacts *app);
static void load_contacts(NuxelContacts *app);
static void on_vcard_chosen(GObject *source, GAsyncResult *res, gpointer user_data);

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
        if (sc->avatar_color[0]) {
            g_free(c->avatar_color);
            c->avatar_color = g_strdup(sc->avatar_color);
        }
        g_ptr_array_add(app->contacts, c);
        g_hash_table_insert(app->contacts_by_id, c->id, c);
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
            g_hash_table_insert(app->contacts_by_id, c->id, c);
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
    
    /* Update avatar */
    {
    gchar *iv = c->name ? g_strndup(c->name, 1) : g_strdup("?");
    adw_avatar_set_text(ADW_AVATAR(app->detail_avatar), iv);
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
        g_hash_table_insert(app->contacts_by_id, c->id, c);
    }
    
    save_contacts(app);
    
    /* Rebuild list */
    g_ptr_array_sort_with_data(app->contacts, (GCompareDataFunc)contacts_compare, NULL);
    /* Remove all rows and re-add */
    GtkWidget *child = gtk_widget_get_first_child(app->contact_list);
    while (child) {
        GtkWidget *next = gtk_widget_get_next_sibling(child);
        gtk_list_box_remove(GTK_LIST_BOX(app->contact_list), child);
        child = next;
    }
    
    for (guint i = 0; i < app->contacts->len; i++) {
        Contact *c = g_ptr_array_index(app->contacts, i);
        GtkWidget *row = gtk_list_box_row_new();
        GtkWidget *box = gtk_box_new(GTK_ORIENTATION_HORIZONTAL, 12);
        gtk_widget_set_margin_start(box, 8);
    gtk_widget_set_margin_end(box, 8);
    gtk_widget_set_margin_top(box, 8);
    gtk_widget_set_margin_bottom(box, 8);
        
        GtkWidget *avatar = adw_avatar_new(32, c->name ? g_strndup(c->name, 1) : "?", TRUE);
        gtk_box_append(GTK_BOX(box), avatar);
        
        GtkWidget *name_label = gtk_label_new(c->name);
        gtk_widget_add_css_class(name_label, "heading");
        gtk_label_set_xalign(GTK_LABEL(name_label), 0.0);
        gtk_box_append(GTK_BOX(box), name_label);
        
        gtk_list_box_row_set_child(GTK_LIST_BOX_ROW(row), box);
        g_object_set_data(G_OBJECT(row), "contact", c);
        gtk_list_box_append(GTK_LIST_BOX(app->contact_list), row);
    }
    
    gtk_stack_set_visible_child_name(GTK_STACK(app->stack), "list");
}

static void
on_delete_clicked(GtkWidget *btn, gpointer user_data)
{
    NuxelContacts *app = (NuxelContacts *)user_data;
    if (!app->active_contact) return;
    
    g_ptr_array_remove(app->contacts, app->active_contact);
    g_hash_table_remove(app->contacts_by_id, app->active_contact->id);
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
    nuxel_phone_store_init(&app->store);
    
    app->contacts = g_ptr_array_new_with_free_func(contact_free);
    app->contacts_by_id = g_hash_table_new(g_str_hash, g_str_equal);
    
    /* Create window */
    app->window = adw_application_window_new(gtk_app);
    gtk_window_set_title(GTK_WINDOW(app->window), "Contacts");
    gtk_window_set_default_size(GTK_WINDOW(app->window), 400, 700);
    
    /* CSS */
    GtkCssProvider *provider = gtk_css_provider_new();
    gtk_css_provider_load_from_string(provider,
        ".heading { font-weight: 600; font-size: 15px; }"
        ".caption { font-size: 12px; color: #a0a0b0; }"
        ".detail-label { font-size: 18px; }"
    );
    gtk_style_context_add_provider_for_display(
        gdk_display_get_default(),
        GTK_STYLE_PROVIDER(provider),
        GTK_STYLE_PROVIDER_PRIORITY_APPLICATION);
    g_object_unref(provider);
    
    /* Stack */
    app->stack = gtk_stack_new();
    gtk_stack_set_transition_type(GTK_STACK(app->stack), GTK_STACK_TRANSITION_TYPE_SLIDE_LEFT_RIGHT);
    
    /* Page 1: Contact list */
    GtkWidget *list_page = gtk_box_new(GTK_ORIENTATION_VERTICAL, 0);
    
    GtkWidget *header = gtk_box_new(GTK_ORIENTATION_HORIZONTAL, 0);
    GtkWidget *title = gtk_label_new("Contacts");
    PangoAttrList *tattrs = pango_attr_list_new();
    pango_attr_list_insert(tattrs, pango_attr_size_new(20 * PANGO_SCALE));
    pango_attr_list_insert(tattrs, pango_attr_weight_new(PANGO_WEIGHT_BOLD));
    gtk_label_set_attributes(GTK_LABEL(title), tattrs);
    pango_attr_list_unref(tattrs);
    gtk_widget_set_margin_start(title, 12);
    gtk_widget_set_margin_end(title, 12);
    gtk_widget_set_margin_top(title, 12);
    gtk_widget_set_margin_bottom(title, 12);
    gtk_box_append(GTK_BOX(header), title);
    
    GtkWidget *spacer = gtk_box_new(GTK_ORIENTATION_HORIZONTAL, 0);
    gtk_widget_set_hexpand(spacer, TRUE);
    gtk_box_append(GTK_BOX(header), spacer);

    GtkWidget *import_btn = gtk_button_new_with_label("Import vCard");
    gtk_widget_add_css_class(import_btn, "flat");
    g_signal_connect(import_btn, "clicked", G_CALLBACK(on_import_vcard_clicked), app);
    gtk_box_append(GTK_BOX(header), import_btn);

    GtkWidget *export_btn = gtk_button_new_with_label("Export vCard");
    gtk_widget_add_css_class(export_btn, "flat");
    g_signal_connect(export_btn, "clicked", G_CALLBACK(on_export_vcard_clicked), app);
    gtk_box_append(GTK_BOX(header), export_btn);

    GtkWidget *add_btn = gtk_button_new_with_label("+");
    gtk_widget_add_css_class(add_btn, "flat");
    g_signal_connect(add_btn, "clicked", G_CALLBACK(on_add_contact_clicked), app);
    gtk_box_append(GTK_BOX(header), add_btn);
    
    gtk_box_append(GTK_BOX(list_page), header);

    /* Status line: every save/import/export reports its real outcome here. */
    app->status_label = gtk_label_new("");
    gtk_widget_add_css_class(app->status_label, "caption");
    gtk_label_set_xalign(GTK_LABEL(app->status_label), 0.0);
    gtk_label_set_wrap(GTK_LABEL(app->status_label), TRUE);
    gtk_widget_set_margin_start(app->status_label, 12);
    gtk_widget_set_margin_end(app->status_label, 12);
    gtk_widget_set_margin_bottom(app->status_label, 6);
    gtk_box_append(GTK_BOX(list_page), app->status_label);
    
    app->contact_list = gtk_list_box_new();
    g_signal_connect(app->contact_list, "row-activated",
                     G_CALLBACK(on_contact_row_activated), app);
    GtkWidget *scrolled = gtk_scrolled_window_new();
    gtk_scrolled_window_set_child(GTK_SCROLLED_WINDOW(scrolled), app->contact_list);
    gtk_box_append(GTK_BOX(list_page), scrolled);
    
    gtk_stack_add_titled(GTK_STACK(app->stack), list_page, "list", "Contacts");
    
    /* Page 2: Detail view */
    GtkWidget *detail_page = gtk_box_new(GTK_ORIENTATION_VERTICAL, 0);
    
    GtkWidget *det_header = gtk_box_new(GTK_ORIENTATION_HORIZONTAL, 8);
    GtkWidget *back_btn = gtk_button_new_with_label("←");
    gtk_widget_add_css_class(back_btn, "flat");
    g_signal_connect(back_btn, "clicked", G_CALLBACK(on_back_to_list_clicked), app);
    gtk_box_append(GTK_BOX(det_header), back_btn);
    
    GtkWidget *edit_btn = gtk_button_new_with_label("Edit");
    gtk_widget_add_css_class(edit_btn, "flat");
    g_signal_connect(edit_btn, "clicked", G_CALLBACK(on_add_contact_clicked), app);
    gtk_box_append(GTK_BOX(det_header), edit_btn);
    
    GtkWidget *delete_btn = gtk_button_new_with_label("Delete");
    gtk_widget_add_css_class(delete_btn, "flat");
    g_signal_connect(delete_btn, "clicked", G_CALLBACK(on_delete_clicked), app);
    gtk_box_append(GTK_BOX(det_header), delete_btn);
    
    gtk_box_append(GTK_BOX(detail_page), det_header);
    
    /* Avatar and details */
    GtkWidget *detail_content = gtk_box_new(GTK_ORIENTATION_VERTICAL, 8);
    gtk_widget_set_margin_start(detail_content, 16);
    gtk_widget_set_margin_end(detail_content, 16);
    gtk_widget_set_margin_top(detail_content, 16);
    gtk_widget_set_margin_bottom(detail_content, 16);
    gtk_widget_set_valign(detail_content, GTK_ALIGN_START);
    
    app->detail_avatar = adw_avatar_new(72, "?", TRUE);
    gtk_widget_set_halign(app->detail_avatar, GTK_ALIGN_CENTER);
    gtk_box_append(GTK_BOX(detail_content), app->detail_avatar);
    
    app->detail_name = gtk_label_new("");
    PangoAttrList *nattrs = pango_attr_list_new();
    pango_attr_list_insert(nattrs, pango_attr_size_new(24 * PANGO_SCALE));
    pango_attr_list_insert(nattrs, pango_attr_weight_new(PANGO_WEIGHT_BOLD));
    gtk_label_set_attributes(GTK_LABEL(app->detail_name), nattrs);
    pango_attr_list_unref(nattrs);
    gtk_widget_set_halign(app->detail_name, GTK_ALIGN_CENTER);
    gtk_box_append(GTK_BOX(detail_content), app->detail_name);
    
    app->detail_phone = gtk_label_new("");
    gtk_widget_add_css_class(app->detail_phone, "detail-label");
    gtk_widget_set_halign(app->detail_phone, GTK_ALIGN_CENTER);
    gtk_box_append(GTK_BOX(detail_content), app->detail_phone);
    
    app->detail_email = gtk_label_new("");
    gtk_widget_add_css_class(app->detail_email, "caption");
    gtk_widget_set_halign(app->detail_email, GTK_ALIGN_CENTER);
    gtk_box_append(GTK_BOX(detail_content), app->detail_email);
    
    gtk_box_append(GTK_BOX(detail_page), detail_content);
    
    gtk_stack_add_titled(GTK_STACK(app->stack), detail_page, "detail", "Contact");
    
    /* Page 3: Edit view */
    GtkWidget *edit_page = gtk_box_new(GTK_ORIENTATION_VERTICAL, 0);
    
    GtkWidget *edit_header = gtk_box_new(GTK_ORIENTATION_HORIZONTAL, 8);
    GtkWidget *edit_cancel = gtk_button_new_with_label("Cancel");
    gtk_widget_add_css_class(edit_cancel, "flat");
    g_signal_connect_swapped(edit_cancel, "clicked",
                             G_CALLBACK(gtk_stack_set_visible_child_name), app->stack);
    gtk_box_append(GTK_BOX(edit_header), edit_cancel);
    
    GtkWidget *edit_save = gtk_button_new_with_label("Save");
    gtk_widget_add_css_class(edit_save, "suggested-action");
    g_signal_connect(edit_save, "clicked", G_CALLBACK(on_save_clicked), app);
    gtk_box_append(GTK_BOX(edit_header), edit_save);
    
    gtk_box_append(GTK_BOX(edit_page), edit_header);
    
    GtkWidget *edit_form = gtk_box_new(GTK_ORIENTATION_VERTICAL, 8);
    gtk_widget_set_margin_start(edit_form, 16);
    gtk_widget_set_margin_end(edit_form, 16);
    gtk_widget_set_margin_top(edit_form, 16);
    gtk_widget_set_margin_bottom(edit_form, 16);
    
    app->edit_name_entry = gtk_entry_new();
    gtk_entry_set_placeholder_text(GTK_ENTRY(app->edit_name_entry), "Name");
    gtk_box_append(GTK_BOX(edit_form), app->edit_name_entry);
    
    app->edit_phone_entry = gtk_entry_new();
    gtk_entry_set_placeholder_text(GTK_ENTRY(app->edit_phone_entry), "Phone");
    gtk_box_append(GTK_BOX(edit_form), app->edit_phone_entry);
    
    app->edit_email_entry = gtk_entry_new();
    gtk_entry_set_placeholder_text(GTK_ENTRY(app->edit_email_entry), "Email");
    gtk_box_append(GTK_BOX(edit_form), app->edit_email_entry);
    
    gtk_box_append(GTK_BOX(edit_page), edit_form);
    
    gtk_stack_add_titled(GTK_STACK(app->stack), edit_page, "edit", "Edit Contact");
    
    adw_application_window_set_content(ADW_APPLICATION_WINDOW(app->window), app->stack);
    
    /* Load contacts */
    load_contacts(app);
    
    /* Populate list */
    for (guint i = 0; i < app->contacts->len; i++) {
        Contact *c = g_ptr_array_index(app->contacts, i);
        GtkWidget *row = gtk_list_box_row_new();
        GtkWidget *box = gtk_box_new(GTK_ORIENTATION_HORIZONTAL, 12);
        gtk_widget_set_margin_start(box, 8);
    gtk_widget_set_margin_end(box, 8);
    gtk_widget_set_margin_top(box, 8);
    gtk_widget_set_margin_bottom(box, 8);
        
        GtkWidget *avatar = adw_avatar_new(32, c->name ? g_strndup(c->name, 1) : "?", TRUE);
        gtk_box_append(GTK_BOX(box), avatar);
        
        GtkWidget *name_label = gtk_label_new(c->name);
        gtk_widget_add_css_class(name_label, "heading");
        gtk_label_set_xalign(GTK_LABEL(name_label), 0.0);
        gtk_box_append(GTK_BOX(box), name_label);
        
        gtk_list_box_row_set_child(GTK_LIST_BOX_ROW(row), box);
        g_object_set_data(G_OBJECT(row), "contact", c);
        gtk_list_box_append(GTK_LIST_BOX(app->contact_list), row);
    }
    
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
