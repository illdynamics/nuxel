/*
 * nuxel-phone-data-test.c - offline unit test for the shared phone data layer.
 *
 * Compiles and runs with no dependencies at all:
 *
 *     ./run-tests.sh            (or)  cc -std=c11 -Wall -Wextra \
 *                                       nuxel-phone-data.c nuxel-phone-data-test.c -o /tmp/t && /tmp/t
 *
 * It exercises the real implementation: number normalisation, contact matching,
 * the call log, message threads, vCard round trip (with line folding) and the
 * atomic JSON store.  Exit status is the number of failed checks.
 */
#include "nuxel-phone-data.h"

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/stat.h>
#include <unistd.h>

static int checks = 0, failures = 0;

static void check(const char *what, int cond, const char *detail)
{
    checks++;
    if (cond) {
        printf("PASS %s\n", what);
    } else {
        failures++;
        printf("FAIL %s%s%s\n", what, detail ? "  -- " : "", detail ? detail : "");
    }
}

static void check_str(const char *what, const char *got, const char *want)
{
    int ok = got && want && strcmp(got, want) == 0;
    char detail[512];
    snprintf(detail, sizeof detail, "got \"%s\" want \"%s\"", got ? got : "(null)", want ? want : "(null)");
    check(what, ok, detail);
}

static void check_contains(const char *what, const char *hay, const char *needle)
{
    int ok = hay && needle && strstr(hay, needle) != NULL;
    char detail[512];
    snprintf(detail, sizeof detail, "\"%s\" does not contain \"%s\"", hay ? hay : "(null)", needle ? needle : "");
    check(what, ok, detail);
}

static void test_numbers(void)
{
    char out[128];
    check("normalize: plain digits", nuxel_phone_normalize_number(out, sizeof out, "0612345678") == 0 &&
                                      strcmp(out, "0612345678") == 0, out);
    (void)nuxel_phone_normalize_number(out, sizeof out, "+31 (0)6 1234 5678");
    check_str("normalize: +31 (0)6 1234 5678 -> +31612345678", out, "+31612345678");
    (void)nuxel_phone_normalize_number(out, sizeof out, "0031612345678");
    check_str("normalize: 00 international prefix -> +", out, "+31612345678");
    (void)nuxel_phone_normalize_number(out, sizeof out, "+1-555-0101");
    check_str("normalize: dashes stripped", out, "+15550101");
    check("normalize: garbage rejected", nuxel_phone_normalize_number(out, sizeof out, "call me maybe") == -1, NULL);
    check("normalize: NULL rejected", nuxel_phone_normalize_number(out, sizeof out, NULL) == -1, NULL);

    (void)nuxel_phone_normalize_number(out, sizeof out, "+31600000000");
    check_str("normalize: a zero inside the subscriber number is never stripped", out, "+31600000000");
    (void)nuxel_phone_normalize_number(out, sizeof out, "0031 (0)6 1234 5678");
    check_str("normalize: 00 prefix plus explicit (0)", out, "+31612345678");
    check("match: international vs national trunk", nuxel_phone_number_match("+31612345678", "0612345678") == 1, NULL);
    check("match: international vs subscriber only", nuxel_phone_number_match("+31612345678", "612345678") == 1, NULL);
    check("match: formatted vs plain", nuxel_phone_number_match("+31 6 1234 5678", "+31612345678") == 1, NULL);
    check("match: different numbers", nuxel_phone_number_match("+31612345678", "+31612345999") == 0, NULL);
    check("match: short numbers do not suffix-match", nuxel_phone_number_match("112", "9112") == 0, NULL);
}

static void test_contacts(void)
{
    NuxelPhoneStore s; nuxel_phone_store_init(&s);
    NuxelContact *a = nuxel_phone_add_contact(&s, "Alice Johnson", "+31 6 1234 5678", "alice@example.com");
    check("add contact returns a record", a != NULL, NULL);
    check("contact id assigned", a && strncmp(a->id, "contact-", 8) == 0, a ? a->id : "");
    check("contact normalised phone stored", a && strcmp(a->phone, "+31612345678") == 0, a ? a->phone : "");
    check("avatar colour derived", a && a->avatar_color[0] == '#', a ? a->avatar_color : "");
    check("store count", s.n_contacts == 1, NULL);

    nuxel_phone_add_contact(&s, "Bob Smith", "+15550102", "");
    nuxel_phone_add_contact(&s, "Carol Davis", "+15550103", "carol@example.com");
    check("three contacts", s.n_contacts == 3, NULL);

    NuxelContact *found = nuxel_phone_find_contact_by_number(&s, "0612345678");
    check("find by national form matches stored international", found != NULL, NULL);
    check_str("find returns the right person", found ? found->name : "", "Alice Johnson");
    check_str("display name for unknown number is the number", nuxel_phone_display_name(&s, "+31600000000"), "+31600000000");

    NuxelContact *out[8];
    size_t n = nuxel_phone_search_contacts(&s, "carol", out, 8);
    check("search by name (case insensitive)", n == 1 && strcmp(out[0]->name, "Carol Davis") == 0, NULL);
    n = nuxel_phone_search_contacts(&s, "example.com", out, 8);
    check("search by email", n == 2, NULL);
    n = nuxel_phone_search_contacts(&s, "555010", out, 8);
    check("search by partial phone", n == 2, NULL);
    n = nuxel_phone_search_contacts(&s, "", out, 8);
    check("empty query lists everything", n == 3, NULL);

    check("delete removes", nuxel_phone_delete_contact(&s, a->id) == 0 && s.n_contacts == 2, NULL);
    check("delete unknown id fails cleanly", nuxel_phone_delete_contact(&s, "nope") == -1, NULL);
    nuxel_phone_store_free(&s);
}

static void test_calls_and_threads(void)
{
    NuxelPhoneStore s; nuxel_phone_store_init(&s);
    nuxel_phone_add_contact(&s, "Alice Johnson", "+31612345678", "alice@example.com");

    NuxelCall *c1 = nuxel_phone_add_call(&s, "0612345678", "out", "no-modem", 1700000000, 0);
    check("call logged", c1 != NULL, NULL);
    check_str("call resolves the contact name", c1 ? c1->name : "", "Alice Johnson");
    check_str("call state records the honest outcome", c1 ? c1->state : "", "no-modem");
    nuxel_phone_add_call(&s, "+31612345678", "in", "missed", 1700000100, 0);
    check("call log count", s.n_calls == 2, NULL);

    nuxel_phone_add_message(&s, "0612345678", "Hello from Nuxel", "out", "stored");
    nuxel_phone_add_message(&s, "+31 6 1234 5678", "Hello back", "in", "stored");
    nuxel_phone_add_message(&s, "+15550102", "Different peer", "out", "stored");
    check("thread count groups formatted numbers", nuxel_phone_thread_count(&s, "+31612345678") == 2, NULL);
    check("distinct thread count", nuxel_phone_thread_count_all(&s) == 2, NULL);
    check("unrelated peer has no thread", nuxel_phone_thread_count(&s, "+31999999999") == 0, NULL);
    nuxel_phone_store_free(&s);
}

static void test_vcard_roundtrip(void)
{
    NuxelPhoneStore a; nuxel_phone_store_init(&a);
    nuxel_phone_add_contact(&a, "Alice Johnson", "+31612345678", "alice@example.com");
    nuxel_phone_add_contact(&a, "Bob; Smith, Jr", "+15550102", "");
    /* A deliberately long name to force vCard line folding at 75 octets. */
    nuxel_phone_add_contact(&a,
        "Someone With A Very Long Display Name Used To Force Folding Behaviour In The Vcard Writer",
        "+31600000000", "long@example.com");

    char *vc = NULL;
    check("vcard export succeeds", nuxel_phone_export_vcard(&a, &vc) == 0 && vc != NULL, NULL);
    check_contains("vcard has BEGIN", vc, "BEGIN:VCARD\r\nVERSION:3.0\r\n");
    check_contains("vcard has FN for Alice", vc, "FN:Alice Johnson");
    check_contains("vcard has TEL of the normalised number", vc, "TEL;TYPE=CELL:+31612345678");
    check_contains("vcard escapes the semicolon in a name", vc, "Bob\\; Smith\\, Jr");
    check_contains("vcard folds long lines", vc, "\r\n ");
    check_contains("vcard ends each record", vc, "END:VCARD\r\n");

    NuxelPhoneStore b; nuxel_phone_store_init(&b);
    int imported = 0;
    check("vcard import succeeds", nuxel_phone_import_vcard(&b, vc, strlen(vc), &imported) == 0, NULL);
    check("vcard imported three contacts", imported == 3 && b.n_contacts == 3, NULL);
    NuxelContact *f = nuxel_phone_find_contact_by_number(&b, "+31612345678");
    check_str("round trip kept Alice", f ? f->name : "", "Alice Johnson");
    check_str("round trip kept the email", f ? f->email : "", "alice@example.com");
    NuxelContact *folded = nuxel_phone_find_contact_by_number(&b, "+31600000000");
    check("round trip unfolded the long name",
          folded && strstr(folded->name, "Force Folding") != NULL, folded ? folded->name : "");
    check("vcard import of garbage does not crash",
          nuxel_phone_import_vcard(&b, "not a vcard at all", 20, &imported) == 0 && imported == 0, NULL);

    free(vc);
    nuxel_phone_store_free(&a);
    nuxel_phone_store_free(&b);
}

static void test_json_store(const char *dir)
{
    char path[1024];
    snprintf(path, sizeof path, "%s/phone.json", dir);

    NuxelPhoneStore s; nuxel_phone_store_init(&s);
    check("load of a missing store is empty, not an error", nuxel_phone_store_load(&s, path) == 1, NULL);
    check("empty store still saves", nuxel_phone_store_save(&s, path) == 0, NULL);

    nuxel_phone_add_contact(&s, "Alice Johnson", "+31612345678", "alice@example.com");
    nuxel_phone_add_call(&s, "0612345678", "out", "no-modem", 1700000000, 0);
    nuxel_phone_add_message(&s, "0612345678", "Quote: \" hi \" \\ line\nbreak", "out", "stored");
    check("save with content", nuxel_phone_store_save(&s, path) == 0, NULL);

    struct stat st;
    check("store file exists and is non-empty", stat(path, &st) == 0 && st.st_size > 100, NULL);
    char tmp_path[1024];
    snprintf(tmp_path, sizeof tmp_path, "%s.tmp", path);
    check("atomic save left no .tmp behind", stat(tmp_path, &st) != 0, NULL);

    NuxelPhoneStore r; nuxel_phone_store_init(&r);
    check("reload succeeds", nuxel_phone_store_load(&r, path) == 0, NULL);
    check("contacts survived", r.n_contacts == 1, NULL);
    NuxelContact *c = nuxel_phone_find_contact_by_number(&r, "+31612345678");
    check_str("contact survived with the same normalised number", c ? c->phone : "", "+31612345678");
    check("calls survived", r.n_calls == 1, NULL);
    check_str("call state survived", r.n_calls ? r.calls[0].state : "", "no-modem");
    check("messages survived", r.n_messages == 1, NULL);
    check_contains("JSON escaping kept the quote", r.n_messages ? r.messages[0].body : "", "\" hi \"");
    check_contains("JSON escaping kept the backslash", r.n_messages ? r.messages[0].body : "", "\\ line");

    check("corrupt store is reported and does not lose the previous file",
          nuxel_phone_store_from_json(&r, "{ this is not json") == -1, NULL);

    nuxel_phone_store_free(&s);
    nuxel_phone_store_free(&r);
    remove(path);
}

static void test_capabilities(void)
{
    NuxelPhoneCapabilities c;
    char label[NUXEL_LABEL_MAX];

    nuxel_phone_capabilities_init(&c);
    check("init leaves the modem unknown, never 'available'",
          c.modem_present == -1 && nuxel_phone_capability_available(&c, "voice") == 0, NULL);
    nuxel_phone_capability_label(&c, "voice", label, sizeof label);
    check_contains("unknown modem must not claim availability", label, "unknown");
    check_contains("unknown modem explains the refusal", label, "will not pretend");

    c.modem_present = 0;                 /* the S10+ case today */
    strcpy(c.detail, "Samsung Shannon LTE modem has no upstream ModemManager plugin");
    nuxel_phone_capability_label(&c, "voice", label, sizeof label);
    check_contains("no modem -> says so for voice", label, "No modem detected");
    check_contains("no modem -> says nothing is dialled", label, "Nothing is dialled");
    nuxel_phone_capability_label(&c, "sms", label, sizeof label);
    check_contains("no modem -> says so for SMS", label, "No modem detected");
    check("availability probe false without a modem",
          nuxel_phone_capability_available(&c, "sms") == 0 &&
          nuxel_phone_capability_available(&c, "voice") == 0 &&
          nuxel_phone_capability_available(&c, "data") == 0, NULL);

    c.modem_present = 1; c.voice_calls = 0; c.sms_send = 0; c.data_connection = 0;
    strcpy(c.modem_name, "Shannon");
    nuxel_phone_capability_label(&c, "voice", label, sizeof label);
    check_contains("present modem without a call interface is described honestly", label, "not available");

    c.voice_calls = 1; c.sms_send = 1; c.data_connection = 1;
    nuxel_phone_capability_label(&c, "voice", label, sizeof label);
    check_contains("a working modem is reported as available", label, "available for voice calls");
    nuxel_phone_capability_label(&c, "summary", label, sizeof label);
    check_contains("summary mentions all three modalities", label, "Voice: available");
    check_contains("summary mentions SMS", label, "SMS: available");
    check_contains("summary mentions data", label, "Data: available");
}

int main(void)
{
    char dir[] = "/tmp/nuxel-phone-data-test-XXXXXX";
    if (!mkdtemp(dir)) { fprintf(stderr, "cannot create temp dir\n"); return 99; }

    printf("== nuxel phone data layer tests ==\n");
    test_numbers();
    test_contacts();
    test_calls_and_threads();
    test_vcard_roundtrip();
    test_json_store(dir);
    test_capabilities();

    printf("\n%d checks, %d failure(s)\n", checks, failures);
    rmdir(dir);
    return failures;
}
