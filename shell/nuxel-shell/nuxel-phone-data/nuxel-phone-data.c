#define _POSIX_C_SOURCE 200809L

/*
 * nuxel-phone-data.c - see nuxel-phone-data.h for the contract.
 *
 * Deliberately dependency-free C11: the file store, the tiny JSON reader and the
 * vCard codec are all implemented here so the data layer can be unit tested
 * offline on any machine (./run-tests.sh), independent of glib/GTK/ModemManager.
 */
#include "nuxel-phone-data.h"

#include <ctype.h>
#include <stdarg.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <strings.h>   /* strcasecmp/strncasecmp (POSIX) */
#include <sys/stat.h>
#include <sys/types.h>
#include <unistd.h>

/* ====================================================================== */
/* small helpers                                                          */
/* ====================================================================== */

long long nuxel_phone_now(void)
{
    return (long long)time(NULL);
}

static void copy_str(char *dst, size_t dstsz, const char *src)
{
    if (!dst || dstsz == 0) return;
    if (!src) { dst[0] = '\0'; return; }
    size_t i = 0;
    for (; i + 1 < dstsz && src[i]; i++) dst[i] = src[i];
    dst[i] = '\0';
}

int nuxel_phone_escape_json(const char *in, char *out, size_t outsz)
{
    if (!out || outsz == 0) return -1;
    size_t w = 0;
    const char *p = in ? in : "";
    for (; *p; p++) {
        const char *esc = NULL;
        switch (*p) {
            case '"':  esc = "\\\""; break;
            case '\\': esc = "\\\\"; break;
            case '\n': esc = "\\n";  break;
            case '\r': esc = "\\r";  break;
            case '\t': esc = "\\t";  break;
            default: break;
        }
        if (esc) {
            if (w + 2 >= outsz) { out[w] = '\0'; return -1; }
            out[w++] = esc[0];
            out[w++] = esc[1];
        } else {
            unsigned char c = (unsigned char)*p;
            if (c < 0x20) {                     /* control chars must be escaped */
                if (w + 6 >= outsz) { out[w] = '\0'; return -1; }
                int n = snprintf(out + w, outsz - w, "\\u%04x", c);
                if (n < 0) { out[w] = '\0'; return -1; }
                w += (size_t)n;
            } else {
                if (w + 1 >= outsz) { out[w] = '\0'; return -1; }
                out[w++] = (char)c;
            }
        }
    }
    out[w] = '\0';
    return (int)w;
}

static char *xstrdup(const char *s)
{
    size_t n = s ? strlen(s) : 0;
    char *r = (char *)malloc(n + 1);
    if (!r) return NULL;
    if (n) memcpy(r, s, n);
    r[n] = '\0';
    return r;
}

/* A tiny growable string buffer (no glib). */
typedef struct { char *p; size_t n, cap; } sbuf;
static void sb_init(sbuf *b) { b->p = NULL; b->n = 0; b->cap = 0; }
static int  sb_reserve(sbuf *b, size_t extra)
{
    if (b->n + extra + 1 <= b->cap) return 0;
    size_t ncap = b->cap ? b->cap * 2 : 256;
    while (ncap < b->n + extra + 1) ncap *= 2;
    char *np = (char *)realloc(b->p, ncap);
    if (!np) return -1;
    b->p = np; b->cap = ncap;
    return 0;
}
static int sb_puts(sbuf *b, const char *s)
{
    size_t n = s ? strlen(s) : 0;
    if (sb_reserve(b, n)) return -1;
    if (n) memcpy(b->p + b->n, s, n);
    b->n += n; b->p[b->n] = '\0';
    return 0;
}
static int sb_putc(sbuf *b, char c)
{
    if (sb_reserve(b, 1)) return -1;
    b->p[b->n++] = c; b->p[b->n] = '\0';
    return 0;
}
static int sb_printf(sbuf *b, const char *fmt, ...)
{
    va_list ap; va_start(ap, fmt);
    char tmp[1024];
    int n = vsnprintf(tmp, sizeof tmp, fmt, ap);
    va_end(ap);
    if (n < 0) return -1;
    if ((size_t)n >= sizeof tmp) return -1;
    return sb_puts(b, tmp);
}
static char *sb_take(sbuf *b) { char *p = b->p; b->p = NULL; b->n = b->cap = 0; return p; }
static void sb_free(sbuf *b) { free(b->p); b->p = NULL; b->n = b->cap = 0; }

/* ====================================================================== */
/* minimal JSON reader (objects, arrays, strings, numbers, bool, null)     */
/* ====================================================================== */

typedef enum { JS_NULL, JS_BOOL, JS_NUM, JS_STR, JS_ARR, JS_OBJ } JsonType;

typedef struct Json {
    JsonType type;
    int      bval;
    double   num;
    char    *str;                  /* owned */
    struct Json **items;           /* array elements / object values (owned) */
    char        **keys;            /* object keys (owned) */
    size_t     n, cap;
} Json;

static void json_free(Json *j)
{
    if (!j) return;
    free(j->str);
    for (size_t i = 0; i < j->n; i++) {
        json_free(j->items[i]);
        if (j->keys) free(j->keys[i]);
    }
    free(j->items);
    free(j->keys);
    free(j);
}

static Json *json_new(JsonType t)
{
    Json *j = (Json *)calloc(1, sizeof(Json));
    if (j) j->type = t;
    return j;
}
static int json_push(Json *j, const char *key, Json *child)
{
    if (j->n == j->cap) {
        size_t ncap = j->cap ? j->cap * 2 : 8;
        Json **ni = (Json **)realloc(j->items, ncap * sizeof(Json *));
        if (!ni) return -1;
        j->items = ni;
        if (j->type == JS_OBJ) {
            char **nk = (char **)realloc(j->keys, ncap * sizeof(char *));
            if (!nk) return -1;
            j->keys = nk;
        }
        j->cap = ncap;
    }
    j->items[j->n] = child;
    if (j->type == JS_OBJ) j->keys[j->n] = xstrdup(key ? key : "");
    j->n++;
    return 0;
}
static Json *json_obj_get(Json *o, const char *key)
{
    if (!o || o->type != JS_OBJ) return NULL;
    for (size_t i = 0; i < o->n; i++)
        if (o->keys[i] && strcmp(o->keys[i], key) == 0) return o->items[i];
    return NULL;
}
static const char *json_obj_str(Json *o, const char *key)
{
    Json *v = json_obj_get(o, key);
    if (v && v->type == JS_STR) return v->str;
    return NULL;
}
static long long json_obj_ll(Json *o, const char *key)
{
    Json *v = json_obj_get(o, key);
    if (v && v->type == JS_NUM) return (long long)v->num;
    return 0;
}

static void json_skip_ws(const char **p) { while (**p && isspace((unsigned char)**p)) (*p)++; }

static char *json_parse_string(const char **p)
{
    /* *p points at the opening quote */
    if (**p != '"') return NULL;
    (*p)++;
    sbuf b; sb_init(&b);
    while (**p && **p != '"') {
        if (**p == '\\') {
            (*p)++;
            char c = **p;
            switch (c) {
                case 'n': sb_putc(&b, '\n'); break;
                case 't': sb_putc(&b, '\t'); break;
                case 'r': sb_putc(&b, '\r'); break;
                case 'b': sb_putc(&b, '\b'); break;
                case 'f': sb_putc(&b, '\f'); break;
                case '/': sb_putc(&b, '/');  break;
                case '"': sb_putc(&b, '"');  break;
                case '\\': sb_putc(&b, '\\'); break;
                case 'u': {
                    if (p[0][1] && p[0][2] && p[0][3] && p[0][4]) {
                        char hex[5] = { (*p)[1], (*p)[2], (*p)[3], (*p)[4], '\0' };
                        unsigned int cp = (unsigned int)strtoul(hex, NULL, 16);
                        (*p) += 4;
                        /* BMP only: emit UTF-8 (enough for our own writer/round trip) */
                        if (cp < 0x80) sb_putc(&b, (char)cp);
                        else if (cp < 0x800) {
                            sb_putc(&b, (char)(0xC0 | (cp >> 6)));
                            sb_putc(&b, (char)(0x80 | (cp & 0x3F)));
                        } else {
                            sb_putc(&b, (char)(0xE0 | (cp >> 12)));
                            sb_putc(&b, (char)(0x80 | ((cp >> 6) & 0x3F)));
                            sb_putc(&b, (char)(0x80 | (cp & 0x3F)));
                        }
                    }
                    break;
                }
                default: sb_putc(&b, c); break;
            }
            if (**p) (*p)++;
        } else {
            sb_putc(&b, **p);
            (*p)++;
        }
    }
    if (**p != '"') { free(b.p); return NULL; }
    (*p)++;
    return sb_take(&b);
}

static Json *json_parse_value(const char **p)
{
    json_skip_ws(p);
    char c = **p;
    if (c == '{') {
        (*p)++;
        Json *o = json_new(JS_OBJ);
        json_skip_ws(p);
        if (**p == '}') { (*p)++; return o; }
        for (;;) {
            json_skip_ws(p);
            char *key = json_parse_string(p);
            if (!key) { json_free(o); return NULL; }
            json_skip_ws(p);
            if (**p != ':') { free(key); json_free(o); return NULL; }
            (*p)++;
            Json *v = json_parse_value(p);
            if (!v) { free(key); json_free(o); return NULL; }
            json_push(o, key, v);
            free(key);
            json_skip_ws(p);
            if (**p == ',') { (*p)++; continue; }
            if (**p == '}') { (*p)++; break; }
            json_free(o); return NULL;
        }
        return o;
    }
    if (c == '[') {
        (*p)++;
        Json *a = json_new(JS_ARR);
        json_skip_ws(p);
        if (**p == ']') { (*p)++; return a; }
        for (;;) {
            Json *v = json_parse_value(p);
            if (!v) { json_free(a); return NULL; }
            json_push(a, NULL, v);
            json_skip_ws(p);
            if (**p == ',') { (*p)++; continue; }
            if (**p == ']') { (*p)++; break; }
            json_free(a); return NULL;
        }
        return a;
    }
    if (c == '"') {
        char *s = json_parse_string(p);
        if (!s) return NULL;
        Json *j = json_new(JS_STR);
        j->str = s;
        return j;
    }
    if (strncmp(*p, "true", 4) == 0)  { (*p) += 4; Json *j = json_new(JS_BOOL); j->bval = 1; return j; }
    if (strncmp(*p, "false", 5) == 0) { (*p) += 5; Json *j = json_new(JS_BOOL); j->bval = 0; return j; }
    if (strncmp(*p, "null", 4) == 0)  { (*p) += 4; return json_new(JS_NULL); }
    if (c == '-' || isdigit((unsigned char)c)) {
        char *end = NULL;
        double v = strtod(*p, &end);
        if (end == *p) return NULL;
        *p = end;
        Json *j = json_new(JS_NUM);
        j->num = v;
        return j;
    }
    return NULL;
}

/* ====================================================================== */
/* numbers                                                                */
/* ====================================================================== */

int nuxel_phone_normalize_number(char *dst, size_t dstsz, const char *src)
{
    if (!dst || dstsz == 0) return -1;
    dst[0] = '\0';
    if (!src) return -1;

    int plus = 0;
    int explicit_trunk0 = 0;         /* source contained "(0)" after the country code */
    size_t trunk_index = 0;          /* digit index of that trunk '0' */
    sbuf digits; sb_init(&digits);
    for (const char *p = src; *p; p++) {
        if (isdigit((unsigned char)*p)) {
            sb_putc(&digits, *p);
        } else if (*p == '+' && digits.n == 0) {
            plus = 1;
        } else if (*p == '(' && p[1] == '0' && p[2] == ')') {
            /* The "(0)" trunk prefix only ever appears inside a written number,
             * so it is the one unambiguous marker we can trust. */
            explicit_trunk0 = 1;
            trunk_index = digits.n;
            p += 2;
        }
    }
    if (digits.n == 0) { sb_free(&digits); return -1; }

    /* international prefix 00 -> + */
    if (!plus && digits.n > 2 && digits.p[0] == '0' && digits.p[1] == '0') {
        memmove(digits.p, digits.p + 2, digits.n - 1);   /* keep the NUL */
        digits.n -= 2;
        plus = 1;
    }
    /* Trunk "(0)" written after a country code: "+31 (0)6 1234 5678" -> "+31612345678".
     * We only do this when the source literally contained "(0)": stripping a bare
     * leading zero would corrupt legitimate subscriber numbers such as +31600000000. */
    if (explicit_trunk0 && trunk_index < digits.n && digits.p[trunk_index] == '0' &&
        (digits.n - trunk_index) >= 6) {
        memmove(digits.p + trunk_index, digits.p + trunk_index + 1, digits.n - trunk_index);  /* NUL included */
        digits.n -= 1;
    }
    /* A national number that starts with 0 without +: keep the 0 (the dialer
     * needs it for a local call) but do not invent a country code. */

    size_t w = 0;
    if (plus) { if (w + 1 < dstsz) dst[w++] = '+'; }
    for (size_t i = 0; i < digits.n && w + 1 < dstsz; i++) dst[w++] = digits.p[i];
    dst[w] = '\0';
    sb_free(&digits);
    return 0;
}

int nuxel_phone_number_match(const char *a, const char *b)
{
    char na[NUXEL_NUMBER_MAX * 2], nb[NUXEL_NUMBER_MAX * 2];
    if (nuxel_phone_normalize_number(na, sizeof na, a) != 0) return 0;
    if (nuxel_phone_normalize_number(nb, sizeof nb, b) != 0) return 0;
    if (strcmp(na, nb) == 0) return 1;

    /* Drop the international "+" and any national trunk "0" so that
     * "+31612345678" matches both "0612345678" and "612345678". */
    const char *da = na, *db = nb;
    if (*da == '+') da++;
    if (*db == '+') db++;
    if (da[0] == '0') da++;
    if (db[0] == '0') db++;
    if (strcmp(da, db) == 0) return 1;

    /* Different country-code prefixes: accept when the shorter number is a
     * suffix of the longer one (classic subscriber-number match). */
    size_t la = strlen(da), lb = strlen(db);
    if (la == 0 || lb == 0) return 0;
    const char *longer = la >= lb ? da : db;
    const char *shorter = la >= lb ? db : da;
    size_t diff = (la >= lb ? la - lb : lb - la);
    if (diff > 3) return 0;
    if (strlen(shorter) < 6) return 0;
    return strcmp(longer + diff, shorter) == 0;
}

/* ====================================================================== */
/* lifecycle                                                              */
/* ====================================================================== */

void nuxel_phone_store_init(NuxelPhoneStore *s)
{
    if (!s) return;
    memset(s, 0, sizeof *s);
}

void nuxel_phone_store_free(NuxelPhoneStore *s)
{
    if (!s) return;
    free(s->contacts); free(s->calls); free(s->messages);
    memset(s, 0, sizeof *s);
}

void nuxel_phone_capabilities_init(NuxelPhoneCapabilities *c)
{
    if (!c) return;
    memset(c, 0, sizeof *c);
    c->modem_present = -1;                 /* unknown until probed */
    copy_str(c->detail, sizeof c->detail,
             "Modem not probed yet - the UI must say 'unknown', not 'available'.");
}


static int grow(void **arr, size_t *cap, size_t elem, size_t need)
{
    if (need <= *cap) return 0;
    size_t ncap = *cap ? *cap * 2 : 8;
    while (ncap < need) ncap *= 2;
    void *np = realloc(*arr, ncap * elem);
    if (!np) return -1;
    *arr = np; *cap = ncap;
    return 0;
}

/* ====================================================================== */
/* contacts                                                               */
/* ====================================================================== */

static void derive_avatar_color(const char *seed, char *out, size_t outsz)
{
    static const char *colors[] = {
        "#E91E63", "#FF9800", "#2196F3", "#4CAF50",
        "#9C27B0", "#F44336", "#607D8B", "#795548"
    };
    unsigned h = 2166136261u;
    for (const char *p = seed ? seed : ""; *p; p++) {
        h ^= (unsigned char)*p;
        h *= 16777619u;
    }
    copy_str(out, outsz, colors[h % (sizeof colors / sizeof colors[0])]);
}

static void make_id(char *dst, size_t dstsz, const char *prefix)
{
    static unsigned counter = 0;
    snprintf(dst, dstsz, "%s-%lld-%u", prefix, (long long)nuxel_phone_now(), ++counter);
}

NuxelContact *nuxel_phone_add_contact(NuxelPhoneStore *s, const char *name,
                                      const char *phone, const char *email)
{
    if (!s) return NULL;
    if (grow((void **)&s->contacts, &s->cap_contacts, sizeof(NuxelContact), s->n_contacts + 1) != 0)
        return NULL;
    NuxelContact *c = &s->contacts[s->n_contacts];
    memset(c, 0, sizeof *c);
    make_id(c->id, sizeof c->id, "contact");
    copy_str(c->name, sizeof c->name, (name && *name) ? name : "Unknown");
    if (phone && *phone) {
        char norm[NUXEL_NUMBER_MAX];
        if (nuxel_phone_normalize_number(norm, sizeof norm, phone) == 0)
            copy_str(c->phone, sizeof c->phone, norm);
        else
            copy_str(c->phone, sizeof c->phone, phone);
    } else {
        c->phone[0] = '\0';
    }
    copy_str(c->email, sizeof c->email, email ? email : "");
    derive_avatar_color(c->name, c->avatar_color, sizeof c->avatar_color);
    c->updated_at = nuxel_phone_now();
    s->n_contacts++;
    return c;
}

NuxelContact *nuxel_phone_find_contact_by_id(NuxelPhoneStore *s, const char *id)
{
    if (!s || !id) return NULL;
    for (size_t i = 0; i < s->n_contacts; i++)
        if (strcmp(s->contacts[i].id, id) == 0) return &s->contacts[i];
    return NULL;
}

NuxelContact *nuxel_phone_find_contact_by_number(NuxelPhoneStore *s, const char *number)
{
    if (!s || !number) return NULL;
    for (size_t i = 0; i < s->n_contacts; i++) {
        if (!s->contacts[i].phone[0]) continue;
        if (nuxel_phone_number_match(s->contacts[i].phone, number)) return &s->contacts[i];
    }
    return NULL;
}

const char *nuxel_phone_display_name(NuxelPhoneStore *s, const char *number)
{
    NuxelContact *c = nuxel_phone_find_contact_by_number(s, number);
    if (c) return c->name;
    return number ? number : "";
}

int nuxel_phone_delete_contact(NuxelPhoneStore *s, const char *id)
{
    if (!s || !id) return -1;
    for (size_t i = 0; i < s->n_contacts; i++) {
        if (strcmp(s->contacts[i].id, id) == 0) {
            memmove(&s->contacts[i], &s->contacts[i + 1],
                    (s->n_contacts - i - 1) * sizeof(NuxelContact));
            s->n_contacts--;
            return 0;
        }
    }
    return -1;
}

static int ci_contains(const char *hay, const char *needle)
{
    if (!hay || !needle || !*needle) return 0;
    size_t nl = strlen(needle);
    for (const char *p = hay; *p; p++) {
        size_t i = 0;
        while (i < nl && p[i] && tolower((unsigned char)p[i]) == tolower((unsigned char)needle[i])) i++;
        if (i == nl) return 1;
    }
    return 0;
}

size_t nuxel_phone_search_contacts(NuxelPhoneStore *s, const char *query,
                                   NuxelContact **out, size_t outsz)
{
    if (!s || !query) return 0;
    /* empty query = list everything (bounded by outsz) */
    size_t n = 0;
    for (size_t i = 0; i < s->n_contacts; i++) {
        NuxelContact *c = &s->contacts[i];
        int hit = (*query == '\0') || ci_contains(c->name, query) ||
                  ci_contains(c->phone, query) || ci_contains(c->email, query);
        if (!hit) continue;
        if (out && n < outsz) out[n] = c;
        n++;
    }
    return n;
}

/* ====================================================================== */
/* call log + messages                                                    */
/* ====================================================================== */

NuxelCall *nuxel_phone_add_call(NuxelPhoneStore *s, const char *number,
                                const char *direction, const char *state,
                                long long started_at, long long duration_s)
{
    if (!s) return NULL;
    if (grow((void **)&s->calls, &s->cap_calls, sizeof(NuxelCall), s->n_calls + 1) != 0)
        return NULL;
    NuxelCall *c = &s->calls[s->n_calls];
    memset(c, 0, sizeof *c);
    make_id(c->id, sizeof c->id, "call");
    copy_str(c->number, sizeof c->number, number ? number : "");
    copy_str(c->name, sizeof c->name, nuxel_phone_display_name(s, number));
    copy_str(c->direction, sizeof c->direction, direction ? direction : "out");
    copy_str(c->state, sizeof c->state, state ? state : "completed");
    c->started_at = started_at ? started_at : nuxel_phone_now();
    c->duration_s = duration_s;
    s->n_calls++;
    return c;
}

NuxelMessage *nuxel_phone_add_message(NuxelPhoneStore *s, const char *peer,
                                      const char *body, const char *direction,
                                      const char *state)
{
    if (!s) return NULL;
    if (grow((void **)&s->messages, &s->cap_messages, sizeof(NuxelMessage), s->n_messages + 1) != 0)
        return NULL;
    NuxelMessage *m = &s->messages[s->n_messages];
    memset(m, 0, sizeof *m);
    make_id(m->id, sizeof m->id, "msg");
    char norm[NUXEL_NUMBER_MAX];
    if (peer && nuxel_phone_normalize_number(norm, sizeof norm, peer) == 0)
        copy_str(m->peer, sizeof m->peer, norm);
    else
        copy_str(m->peer, sizeof m->peer, peer ? peer : "");
    copy_str(m->body, sizeof m->body, body ? body : "");
    copy_str(m->direction, sizeof m->direction, direction ? direction : "out");
    copy_str(m->state, sizeof m->state, state ? state : "stored");
    m->at = nuxel_phone_now();
    s->n_messages++;
    return m;
}

size_t nuxel_phone_thread_count(NuxelPhoneStore *s, const char *peer)
{
    if (!s || !peer) return 0;
    size_t n = 0;
    for (size_t i = 0; i < s->n_messages; i++)
        if (nuxel_phone_number_match(s->messages[i].peer, peer)) n++;
    return n;
}

size_t nuxel_phone_thread_count_all(NuxelPhoneStore *s)
{
    if (!s) return 0;
    size_t threads = 0;
    for (size_t i = 0; i < s->n_messages; i++) {
        int seen = 0;
        for (size_t j = 0; j < i; j++) {
            if (nuxel_phone_number_match(s->messages[j].peer, s->messages[i].peer)) { seen = 1; break; }
        }
        if (!seen) threads++;
    }
    return threads;
}

/* ====================================================================== */
/* JSON store                                                             */
/* ====================================================================== */

static void json_echo(sbuf *b, const char *s)
{
    char tmp[NUXEL_BODY_MAX * 2];
    if (nuxel_phone_escape_json(s ? s : "", tmp, sizeof tmp) < 0) {
        /* Value too long for the escape buffer: truncate rather than emit broken JSON. */
        copy_str(tmp, sizeof tmp, s ? s : "");
    }
    sb_putc(b, '"');
    sb_puts(b, tmp);
    sb_putc(b, '"');
}

int nuxel_phone_store_to_json(NuxelPhoneStore *s, char **out)
{
    if (!s || !out) return -1;
    sbuf b; sb_init(&b);
    sb_printf(&b, "{\n  \"schema_version\": %d,\n", NUXEL_PHONE_DATA_VERSION);
    sb_printf(&b, "  \"saved_at\": %lld,\n", (long long)nuxel_phone_now());

    sb_puts(&b, "  \"contacts\": [");
    for (size_t i = 0; i < s->n_contacts; i++) {
        NuxelContact *c = &s->contacts[i];
        sb_printf(&b, "%s\n    {", i ? "," : "");
        sb_puts(&b, "\"id\": ");       json_echo(&b, c->id);
        sb_puts(&b, ", \"name\": ");   json_echo(&b, c->name);
        sb_puts(&b, ", \"phone\": ");  json_echo(&b, c->phone);
        sb_puts(&b, ", \"email\": ");  json_echo(&b, c->email);
        sb_puts(&b, ", \"avatar_color\": "); json_echo(&b, c->avatar_color);
        sb_printf(&b, ", \"updated_at\": %lld}", c->updated_at);
    }
    sb_puts(&b, s->n_contacts ? "\n  ],\n" : "],\n");

    sb_puts(&b, "  \"calls\": [");
    for (size_t i = 0; i < s->n_calls; i++) {
        NuxelCall *c = &s->calls[i];
        sb_printf(&b, "%s\n    {", i ? "," : "");
        sb_puts(&b, "\"id\": ");        json_echo(&b, c->id);
        sb_puts(&b, ", \"number\": ");  json_echo(&b, c->number);
        sb_puts(&b, ", \"name\": ");    json_echo(&b, c->name);
        sb_puts(&b, ", \"direction\": "); json_echo(&b, c->direction);
        sb_puts(&b, ", \"state\": ");   json_echo(&b, c->state);
        sb_printf(&b, ", \"started_at\": %lld, \"duration_s\": %lld}", c->started_at, c->duration_s);
    }
    sb_puts(&b, s->n_calls ? "\n  ],\n" : "],\n");

    sb_puts(&b, "  \"messages\": [");
    for (size_t i = 0; i < s->n_messages; i++) {
        NuxelMessage *m = &s->messages[i];
        sb_printf(&b, "%s\n    {", i ? "," : "");
        sb_puts(&b, "\"id\": ");        json_echo(&b, m->id);
        sb_puts(&b, ", \"peer\": ");    json_echo(&b, m->peer);
        sb_puts(&b, ", \"body\": ");    json_echo(&b, m->body);
        sb_puts(&b, ", \"direction\": "); json_echo(&b, m->direction);
        sb_puts(&b, ", \"state\": ");   json_echo(&b, m->state);
        sb_printf(&b, ", \"at\": %lld}", m->at);
    }
    sb_puts(&b, s->n_messages ? "\n  ]\n" : "]\n");
    sb_puts(&b, "}\n");

    *out = sb_take(&b);
    return *out ? 0 : -1;
}

int nuxel_phone_store_from_json(NuxelPhoneStore *s, const char *json)
{
    if (!s || !json) return -1;
    const char *p = json;
    Json *root = json_parse_value(&p);
    if (!root || root->type != JS_OBJ) { json_free(root); return -1; }

    long long ver = json_obj_ll(root, "schema_version");
    if (ver > NUXEL_PHONE_DATA_VERSION) {
        /* Forward compatibility: refuse rather than silently downgrade a store
         * written by a newer build. */
        json_free(root);
        return -2;
    }

    Json *arr = json_obj_get(root, "contacts");
    if (arr && arr->type == JS_ARR) {
        for (size_t i = 0; i < arr->n; i++) {
            Json *o = arr->items[i];
            if (!o || o->type != JS_OBJ) continue;
            NuxelContact *c = nuxel_phone_add_contact(s,
                json_obj_str(o, "name"), json_obj_str(o, "phone"), json_obj_str(o, "email"));
            if (!c) continue;
            const char *id = json_obj_str(o, "id");
            if (id) copy_str(c->id, sizeof c->id, id);
            const char *col = json_obj_str(o, "avatar_color");
            if (col) copy_str(c->avatar_color, sizeof c->avatar_color, col);
            c->updated_at = json_obj_ll(o, "updated_at");
        }
    }
    arr = json_obj_get(root, "calls");
    if (arr && arr->type == JS_ARR) {
        for (size_t i = 0; i < arr->n; i++) {
            Json *o = arr->items[i];
            if (!o || o->type != JS_OBJ) continue;
            NuxelCall *c = nuxel_phone_add_call(s,
                json_obj_str(o, "number"), json_obj_str(o, "direction"),
                json_obj_str(o, "state"), json_obj_ll(o, "started_at"),
                json_obj_ll(o, "duration_s"));
            if (!c) continue;
            const char *id = json_obj_str(o, "id");
            if (id) copy_str(c->id, sizeof c->id, id);
            const char *nm = json_obj_str(o, "name");
            if (nm) copy_str(c->name, sizeof c->name, nm);
        }
    }
    arr = json_obj_get(root, "messages");
    if (arr && arr->type == JS_ARR) {
        for (size_t i = 0; i < arr->n; i++) {
            Json *o = arr->items[i];
            if (!o || o->type != JS_OBJ) continue;
            NuxelMessage *m = nuxel_phone_add_message(s,
                json_obj_str(o, "peer"), json_obj_str(o, "body"),
                json_obj_str(o, "direction"), json_obj_str(o, "state"));
            if (!m) continue;
            const char *id = json_obj_str(o, "id");
            if (id) copy_str(m->id, sizeof m->id, id);
            long long at = json_obj_ll(o, "at");
            if (at) m->at = at;
        }
    }
    json_free(root);
    return 0;
}

static int write_file_atomic(const char *path, const char *data, size_t len)
{
    char tmp[4096];
    if (snprintf(tmp, sizeof tmp, "%s.tmp", path) >= (int)sizeof tmp) return -1;
    FILE *f = fopen(tmp, "wb");
    if (!f) return -1;
    size_t w = fwrite(data, 1, len, f);
    if (fflush(f) != 0) { fclose(f); remove(tmp); return -1; }
    fclose(f);
    if (w != len) { remove(tmp); return -1; }
    if (rename(tmp, path) != 0) { remove(tmp); return -1; }
    return 0;
}

int nuxel_phone_store_save(NuxelPhoneStore *s, const char *path)
{
    if (!s || !path) return -1;
    char *json = NULL;
    if (nuxel_phone_store_to_json(s, &json) != 0) return -1;
    int rc = write_file_atomic(path, json, strlen(json));
    free(json);
    return rc;
}

int nuxel_phone_store_load(NuxelPhoneStore *s, const char *path)
{
    if (!s || !path) return -1;
    FILE *f = fopen(path, "rb");
    if (!f) return 1;                        /* no store yet: empty, not an error */
    sbuf b; sb_init(&b);
    char chunk[4096];
    size_t n;
    while ((n = fread(chunk, 1, sizeof chunk, f)) > 0) {
        if (sb_reserve(&b, n)) { fclose(f); sb_free(&b); return -1; }
        memcpy(b.p + b.n, chunk, n);
        b.n += n;
        b.p[b.n] = '\0';
    }
    fclose(f);
    int rc = 0;
    if (b.n == 0) {
        rc = 1;
    } else {
        rc = nuxel_phone_store_from_json(s, b.p);
        if (rc != 0) {
            /* Corrupt store: keep the user's data reachable instead of dropping it. */
            nuxel_phone_store_free(s);
            nuxel_phone_store_init(s);
            rc = -1;
        }
    }
    sb_free(&b);
    return rc;
}

/* ====================================================================== */
/* vCard 3.0 (RFC 2426 subset: FN, N, TEL, EMAIL, UID)                    */
/* ====================================================================== */

#define VCARD_FOLD 75

static void vcard_escape(sbuf *b, const char *s)
{
    for (const char *p = s ? s : ""; *p; p++) {
        switch (*p) {
            case '\\': sb_puts(b, "\\\\"); break;
            case ';':  sb_puts(b, "\\;");  break;
            case ',':  sb_puts(b, "\\,");  break;
            case '\n': sb_puts(b, "\\n");  break;
            case '\r': break;
            default:   sb_putc(b, *p);     break;
        }
    }
}

/* Append one logical content line, folded at 75 octets (RFC 2426 §2.6). */
static void vcard_line(sbuf *b, const char *fmt, const char *value)
{
    sbuf raw; sb_init(&raw);
    sb_printf(&raw, fmt, value ? value : "");
    const char *p = raw.p ? raw.p : "";
    size_t len = strlen(p);
    size_t col = 0;
    for (size_t i = 0; i < len; i++) {
        if (col == VCARD_FOLD) { sb_puts(b, "\r\n "); col = 1; }
        sb_putc(b, p[i]);
        col++;
    }
    sb_puts(b, "\r\n");
    sb_free(&raw);
}

int nuxel_phone_export_vcard(NuxelPhoneStore *s, char **out)
{
    if (!s || !out) return -1;
    sbuf b; sb_init(&b);
    for (size_t i = 0; i < s->n_contacts; i++) {
        NuxelContact *c = &s->contacts[i];
        sb_puts(&b, "BEGIN:VCARD\r\nVERSION:3.0\r\n");
        vcard_line(&b, "UID:%s", c->id);
        vcard_line(&b, "FN:%s", c->name);
        /* N is structured; we emit the display name in the family-name slot. */
        {
            sbuf raw; sb_init(&raw);
            sb_puts(&raw, "N:");
            vcard_escape(&raw, c->name);
            sb_puts(&raw, ";;;;");
            sb_puts(&b, raw.p ? raw.p : "");
            sb_puts(&b, "\r\n");
            sb_free(&raw);
        }
        if (c->phone[0]) vcard_line(&b, "TEL;TYPE=CELL:%s", c->phone);
        if (c->email[0]) vcard_line(&b, "EMAIL;TYPE=INTERNET:%s", c->email);
        if (c->avatar_color[0]) vcard_line(&b, "X-NUXEL-AVATAR:%s", c->avatar_color);
        if (c->updated_at) {
            char rev[64];
            snprintf(rev, sizeof rev, "%lld", c->updated_at);
            vcard_line(&b, "REV:%s", rev);
        }
        sb_puts(&b, "END:VCARD\r\n");
    }
    *out = sb_take(&b);
    return *out ? 0 : -1;
}

/* Unfold: join CRLF+space continuation lines. */
static char *vcard_unfold(const char *text, size_t len)
{
    sbuf b; sb_init(&b);
    for (size_t i = 0; i < len; i++) {
        char c = text[i];
        if (c == '\r' || c == '\n') {
            size_t j = i;
            while (j < len && (text[j] == '\r' || text[j] == '\n')) j++;
            if (j < len && (text[j] == ' ' || text[j] == '\t')) {
                i = j;                     /* skip the fold marker */
                continue;
            }
            sb_putc(&b, '\n');
            while (i + 1 < len && (text[i + 1] == '\r' || text[i + 1] == '\n')) i++;
            continue;
        }
        sb_putc(&b, c);
    }
    return sb_take(&b);
}

static void vcard_unescape(char *s)
{
    char *r = s;
    for (const char *p = s; *p; p++) {
        if (*p == '\\' && p[1]) {
            p++;
            switch (*p) {
                case 'n': case 'N': *r++ = '\n'; break;
                case 'r': *r++ = '\r'; break;
                default: *r++ = *p; break;
            }
        } else if (*p == ';' || *p == ',') {
            *r++ = *p;                      /* keep separators readable in the UI */
        } else {
            *r++ = *p;
        }
    }
    *r = '\0';
}

int nuxel_phone_import_vcard(NuxelPhoneStore *s, const char *text, size_t len, int *imported)
{
    if (!s || !text) return -1;
    if (imported) *imported = 0;
    char *flat = vcard_unfold(text, len);
    if (!flat) return -1;

    char fn[NUXEL_NAME_MAX] = "", tel[NUXEL_NUMBER_MAX] = "", email[NUXEL_EMAIL_MAX] = "",
         uid[NUXEL_ID_MAX] = "", avatar[10] = "";
    int in_card = 0, count = 0;

    char *save = NULL;
    for (char *line = strtok_r(flat, "\n", &save); line; line = strtok_r(NULL, "\n", &save)) {
        /* strip trailing CR and spaces */
        size_t l = strlen(line);
        while (l && (line[l - 1] == '\r' || line[l - 1] == ' ')) line[--l] = '\0';
        if (!*line) continue;

        if (strncasecmp(line, "BEGIN:VCARD", 11) == 0) {
            in_card = 1;
            fn[0] = tel[0] = email[0] = uid[0] = avatar[0] = '\0';
            continue;
        }
        if (strncasecmp(line, "END:VCARD", 9) == 0) {
            if (in_card) {
                char *name = fn[0] ? fn : NULL;
                if (!name && tel[0]) name = tel;
                if (name || tel[0] || email[0]) {
                    NuxelContact *c = nuxel_phone_add_contact(s, name, tel, email);
                    if (c) {
                        if (uid[0]) {
                            /* Never silently overwrite an existing contact. */
                            if (!nuxel_phone_find_contact_by_id(s, uid))
                                copy_str(c->id, sizeof c->id, uid);
                        }
                        if (avatar[0]) copy_str(c->avatar_color, sizeof c->avatar_color, avatar);
                        count++;
                    }
                }
            }
            in_card = 0;
            continue;
        }
        if (!in_card) continue;

        /* property name is everything before ':' (params after ';' are ignored
         * except that we keep the value only). */
        char *colon = strchr(line, ':');
        if (!colon) continue;
        *colon = '\0';
        char *params = strchr(line, ';');
        if (params) *params = '\0';
        char *value = colon + 1;
        while (*value == ' ') value++;

        if (strcasecmp(line, "FN") == 0) {
            /* FN is the display name: it always wins over the structured N. */
            char tmp[NUXEL_NAME_MAX * 2];
            copy_str(tmp, sizeof tmp, value);
            vcard_unescape(tmp);
            if (tmp[0]) copy_str(fn, sizeof fn, tmp);
        } else if (strcasecmp(line, "N") == 0) {
            if (!fn[0]) {
                /* N is "Family;Given;Middle;Prefix;Suffix" - empty parts skipped. */
                char tmp[NUXEL_NAME_MAX * 2];
                copy_str(tmp, sizeof tmp, value);
                vcard_unescape(tmp);
                char *parts[5] = { NULL, NULL, NULL, NULL, NULL };
                size_t np = 0;
                char *savep = NULL;
                for (char *tok = strtok_r(tmp, ";", &savep); tok && np < 5;
                     tok = strtok_r(NULL, ";", &savep)) {
                    while (*tok == ' ') tok++;
                    size_t tl = strlen(tok);
                    while (tl && tok[tl - 1] == ' ') tok[--tl] = '\0';
                    parts[np++] = tok;
                }
                const char *family = (np > 0 && parts[0] && parts[0][0]) ? parts[0] : NULL;
                const char *given  = (np > 1 && parts[1] && parts[1][0]) ? parts[1] : NULL;
                if (given && family) snprintf(fn, sizeof fn, "%s %s", given, family);
                else if (given) copy_str(fn, sizeof fn, given);
                else if (family) copy_str(fn, sizeof fn, family);
                else if (np > 0 && parts[0]) copy_str(fn, sizeof fn, parts[0]);
            }
        } else if (strcasecmp(line, "TEL") == 0) {
            char tmp[NUXEL_NUMBER_MAX * 2];
            copy_str(tmp, sizeof tmp, value);
            vcard_unescape(tmp);
            if (!tel[0]) copy_str(tel, sizeof tel, tmp);
        } else if (strcasecmp(line, "EMAIL") == 0) {
            char tmp[NUXEL_EMAIL_MAX * 2];
            copy_str(tmp, sizeof tmp, value);
            vcard_unescape(tmp);
            if (!email[0]) copy_str(email, sizeof email, tmp);
        } else if (strcasecmp(line, "UID") == 0) {
            copy_str(uid, sizeof uid, value);
        } else if (strcasecmp(line, "X-NUXEL-AVATAR") == 0) {
            copy_str(avatar, sizeof avatar, value);
        }
    }
    free(flat);
    if (imported) *imported = count;
    return 0;
}

/* ====================================================================== */
/* capability labels                                                      */
/* ====================================================================== */

int nuxel_phone_capability_available(const NuxelPhoneCapabilities *c, const char *modality)
{
    if (!c || !modality) return 0;
    if (c->modem_present != 1) return 0;            /* unknown or absent: not available */
    if (strcmp(modality, "voice") == 0) return c->voice_calls ? 1 : 0;
    if (strcmp(modality, "sms") == 0)   return c->sms_send ? 1 : 0;
    if (strcmp(modality, "data") == 0)  return c->data_connection ? 1 : 0;
    return 0;
}

size_t nuxel_phone_capability_label(const NuxelPhoneCapabilities *c,
                                    const char *modality, char *out, size_t outsz)
{
    if (!out || outsz == 0) return 0;
    out[0] = '\0';
    if (!c || !modality) return 0;

    const char *name = c->modem_name[0] ? c->modem_name : "an unnamed modem";
    char line[NUXEL_LABEL_MAX];
    line[0] = '\0';

    if (strcmp(modality, "summary") == 0) {
        snprintf(line, sizeof line,
                 "Voice: %s  |  SMS: %s  |  Data: %s",
                 nuxel_phone_capability_available(c, "voice") ? "available" : "unavailable",
                 nuxel_phone_capability_available(c, "sms") ? "available" : "unavailable",
                 nuxel_phone_capability_available(c, "data") ? "available" : "unavailable");
        copy_str(out, outsz, line);
        return strlen(out);
    }

    int want = (strcmp(modality, "voice") == 0) ? c->voice_calls
             : (strcmp(modality, "sms") == 0) ? c->sms_send
             : (strcmp(modality, "data") == 0) ? c->data_connection : 0;
    const char *what = (strcmp(modality, "voice") == 0) ? "voice calls"
                     : (strcmp(modality, "sms") == 0) ? "SMS"
                     : (strcmp(modality, "data") == 0) ? "mobile data" : modality;

    if (c->modem_present == 0) {
        snprintf(line, sizeof line,
                 "No modem detected: %s are unavailable on this device. "
                 "Nothing is dialled and nothing is queued for sending.", what);
    } else if (c->modem_present < 0) {
        snprintf(line, sizeof line,
                 "Modem status unknown: %s cannot be confirmed as available. "
                 "The app will not pretend to place a call or send a message.", what);
    } else if (!want) {
        snprintf(line, sizeof line,
                 "Modem present (%s) but %s are not available: the modem exposes no "
                 "call/messaging interface for this operation.", name, what);
    } else {
        snprintf(line, sizeof line, "Modem %s is available for %s.", name, what);
    }
    copy_str(out, outsz, line);
    return strlen(out);
}
