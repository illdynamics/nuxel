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
#include <json-glib/json-glib.h>

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
} NuxelContacts;

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
save_contacts(NuxelContacts *app)
{
    if (!app->data_dir) return;
    
    gchar *path = g_build_filename(app->data_dir, "contacts.json", NULL);
    
    GFile *file = g_file_new_for_path(path);
    GFileOutputStream *stream = g_file_replace(file, NULL, FALSE, G_FILE_CREATE_NONE, NULL, NULL);
    
    if (!stream) {
        g_warning("Failed to open contacts file for writing");
        g_free(path);
        return;
    }
    
    /* Build JSON */
    g_autoptr(JsonBuilder) builder = json_builder_new();
    json_builder_begin_object(builder);
    json_builder_set_member_name(builder, "contacts");
    json_builder_begin_array(builder);
    
    for (guint i = 0; i < app->contacts->len; i++) {
        Contact *c = g_ptr_array_index(app->contacts, i);
        json_builder_begin_object(builder);
        json_builder_set_member_name(builder, "id");    json_builder_add_string_value(builder, c->id);
        json_builder_set_member_name(builder, "name");  json_builder_add_string_value(builder, c->name);
        json_builder_set_member_name(builder, "phone"); json_builder_add_string_value(builder, c->phone);
        json_builder_set_member_name(builder, "email"); json_builder_add_string_value(builder, c->email);
        json_builder_end_object(builder);
    }
    
    json_builder_end_array(builder);
    json_builder_end_object(builder);
    
    g_output_stream_close(G_OUTPUT_STREAM(stream), NULL, NULL);
    g_object_unref(stream);
    g_object_unref(file);
    g_free(path);
}

static void
load_contacts(NuxelContacts *app)
{
    if (!app->data_dir) return;
    
    gchar *path = g_build_filename(app->data_dir, "contacts.json", NULL);
    
    /* Load using simple key-file approach */
    gchar *content;
    gsize length;
    if (!g_file_get_contents(path, &content, &length, NULL)) {
        /* Create default contacts */
        Contact *c1 = contact_new("Alice Johnson", "+1-555-0101", "alice@example.com");
        Contact *c2 = contact_new("Bob Smith", "+1-555-0102", "bob@example.com");
        Contact *c3 = contact_new("Carol Davis", "+1-555-0103", "carol@example.com");
        g_ptr_array_add(app->contacts, c1);
        g_ptr_array_add(app->contacts, c2);
        g_ptr_array_add(app->contacts, c3);
        g_hash_table_insert(app->contacts_by_id, c1->id, c1);
        g_hash_table_insert(app->contacts_by_id, c2->id, c2);
        g_hash_table_insert(app->contacts_by_id, c3->id, c3);
        save_contacts(app);
        g_free(path);
        return;
    }
    
    /* Parse JSON (using json-glib) */
    g_autoptr(JsonParser) parser = json_parser_new();
    if (json_parser_load_from_data(parser, content, length, NULL)) {
        JsonNode *root = json_parser_get_root(parser);
        JsonObject *obj = json_node_get_object(root);
        JsonArray *arr = json_object_get_array_member(obj, "contacts");
        
        for (guint i = 0; i < json_array_get_length(arr); i++) {
            JsonObject *cobj = json_array_get_object_element(arr, i);
            Contact *c = contact_new(
                json_object_get_string_member(cobj, "name"),
                json_object_get_string_member(cobj, "phone"),
                json_object_get_string_member(cobj, "email")
            );
            g_free(c->id);
            c->id = g_strdup(json_object_get_string_member(cobj, "id"));
            g_ptr_array_add(app->contacts, c);
            g_hash_table_insert(app->contacts_by_id, c->id, c);
        }
    }
    
    g_free(content);
    g_free(path);
}

/* ============================================================
 * UI Callbacks
 * ============================================================ */

static void
on_add_contact_clicked(GtkWidget *btn, gpointer user_data)
{
    NuxelContacts *app = (NuxelContacts *)user_data;
    gtk_stack_set_visible_child_name(GTK_STACK(app->stack), "edit");
    gtk_entry_set_text(GTK_ENTRY(app->edit_name_entry), "");
    gtk_entry_set_text(GTK_ENTRY(app->edit_phone_entry), "");
    gtk_entry_set_text(GTK_ENTRY(app->edit_email_entry), "");
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
        gtk_widget_set_margin(box, 8);
        
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
    gtk_widget_set_margin(title, 12);
    gtk_box_append(GTK_BOX(header), title);
    
    GtkWidget *add_btn = gtk_button_new_with_label("+");
    gtk_widget_add_css_class(add_btn, "flat");
    g_signal_connect(add_btn, "clicked", G_CALLBACK(on_add_contact_clicked), app);
    gtk_box_append(GTK_BOX(header), add_btn);
    
    gtk_box_append(GTK_BOX(list_page), header);
    
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
    gtk_widget_set_margin(detail_content, 16);
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
    gtk_widget_set_margin(edit_form, 16);
    
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
        gtk_widget_set_margin(box, 8);
        
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
