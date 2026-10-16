/*
 * nuxel-phone-data.h - shared phone data layer for the Nuxel core phone apps
 * (nuxel-dialer, nuxel-contacts, nuxel-messages).
 *
 * WHY THIS EXISTS
 *   The three GTK apps each grew their own ad-hoc model: nuxel-contacts wrote a
 *   contacts.json it never actually flushed, nuxel-messages held conversations
 *   in memory only, and nothing shared a number normalisation rule.  This module
 *   is the single data model they all use:
 *
 *     - contacts        (id, name, phone, email, avatar colour, updated_at)
 *     - call log        (id, number, resolved name, direction, started_at,
 *                        duration, state)
 *     - messages        (id, thread peer, body, direction, state, timestamp)
 *
 *   It has NO external dependencies (no glib, no json-glib) so the whole data
 *   layer - including vCard import/export and the JSON store - is compiled and
 *   exercised by an offline unit test on any machine:
 *
 *       ./run-tests.sh
 *
 * STORE FORMAT (JSON, version 1)
 *   { "schema_version": 1,
 *     "contacts": [ ... ], "calls": [ ... ], "messages": [ ... ] }
 *   Written atomically (write to <path>.tmp then rename) so a crash mid-save
 *   cannot leave a half-written address book behind.
 *
 * HONESTY CONTRACT
 *   nuxel_phone_capability_label() never claims a modem it has not seen.  The
 *   caller probes ModemManager; the label text is derived only from that probe,
 *   and the S10+ (Samsung Shannon modem, no upstream ModemManager plugin) is
 *   described exactly as it behaves: no modem -> no calls, no SMS, and the UI
 *   must say so instead of pretending to place a call.
 */
#ifndef NUXEL_PHONE_DATA_H
#define NUXEL_PHONE_DATA_H

#include <stddef.h>
#include <time.h>

#ifdef __cplusplus
extern "C" {
#endif

#define NUXEL_PHONE_DATA_VERSION 1

#define NUXEL_ID_MAX      48
#define NUXEL_NAME_MAX    128
#define NUXEL_NUMBER_MAX  48
#define NUXEL_EMAIL_MAX   128
#define NUXEL_BODY_MAX    1024
#define NUXEL_STATE_MAX   32
#define NUXEL_LABEL_MAX   512

typedef struct {
    char id[NUXEL_ID_MAX];
    char name[NUXEL_NAME_MAX];
    char phone[NUXEL_NUMBER_MAX];
    char email[NUXEL_EMAIL_MAX];
    char avatar_color[10];
    long long updated_at;     /* unix seconds */
} NuxelContact;

typedef struct {
    char id[NUXEL_ID_MAX];
    char number[NUXEL_NUMBER_MAX];
    char name[NUXEL_NAME_MAX];      /* resolved from contacts at insert time */
    char direction[12];             /* "in" | "out" | "missed" */
    char state[NUXEL_STATE_MAX];    /* "completed" | "no-modem" | "failed" ... */
    long long started_at;
    long long duration_s;
} NuxelCall;

typedef struct {
    char id[NUXEL_ID_MAX];
    char peer[NUXEL_NUMBER_MAX];    /* normalised peer number = thread id */
    char body[NUXEL_BODY_MAX];
    char direction[12];             /* "in" | "out" */
    char state[NUXEL_STATE_MAX];    /* "stored" | "sent" | "queued" | "no-modem" */
    long long at;
} NuxelMessage;

typedef struct {
    NuxelContact *contacts;
    size_t        n_contacts, cap_contacts;
    NuxelCall    *calls;
    size_t        n_calls, cap_calls;
    NuxelMessage *messages;
    size_t        n_messages, cap_messages;
} NuxelPhoneStore;

/* Modem probe result, produced by the caller (GDBus / ModemManager). */
typedef struct {
    int  modem_present;      /* -1 unknown, 0 no modem, 1 modem present  */
    int  voice_calls;        /* 0/1 - can a voice call be placed?        */
    int  sms_send;           /* 0/1 - can an SMS be sent?                */
    int  data_connection;
    char modem_name[96];
    char detail[256];
} NuxelPhoneCapabilities;

/* ---- lifecycle ---------------------------------------------------------- */
void nuxel_phone_store_init(NuxelPhoneStore *s);
void nuxel_phone_store_free(NuxelPhoneStore *s);
void nuxel_phone_capabilities_init(NuxelPhoneCapabilities *c);

/* ---- numbers ------------------------------------------------------------ */
/* Normalise to +<digits> when a country/trunk prefix is present, otherwise the
 * bare digit run.  Returns 0 on success, -1 if there are no digits at all.
 * "+31 (0)6 1234 5678", "0031612345678" and "0612345678" all normalise so that
 * contact matching works no matter how a number was typed. */
int nuxel_phone_normalize_number(char *dst, size_t dstsz, const char *src);
/* Compare two numbers after normalisation. Returns 1 if they match. */
int nuxel_phone_number_match(const char *a, const char *b);

/* ---- contacts ---------------------------------------------------------- */
/* Returns a borrowed pointer to the stored contact, or NULL on error. */
NuxelContact *nuxel_phone_add_contact(NuxelPhoneStore *s, const char *name,
                                      const char *phone, const char *email);
NuxelContact *nuxel_phone_find_contact_by_id(NuxelPhoneStore *s, const char *id);
NuxelContact *nuxel_phone_find_contact_by_number(NuxelPhoneStore *s, const char *number);
const char   *nuxel_phone_display_name(NuxelPhoneStore *s, const char *number);
int           nuxel_phone_delete_contact(NuxelPhoneStore *s, const char *id);
/* Case-insensitive name/phone/email search; returns the number of matches and
 * fills out[] (up to outsz) with borrowed pointers. */
size_t        nuxel_phone_search_contacts(NuxelPhoneStore *s, const char *query,
                                          NuxelContact **out, size_t outsz);

/* ---- call log ---------------------------------------------------------- */
NuxelCall *nuxel_phone_add_call(NuxelPhoneStore *s, const char *number,
                                const char *direction, const char *state,
                                long long started_at, long long duration_s);

/* ---- messages ---------------------------------------------------------- */
NuxelMessage *nuxel_phone_add_message(NuxelPhoneStore *s, const char *peer,
                                      const char *body, const char *direction,
                                      const char *state);
/* Number of messages exchanged with a peer (normalised comparison). */
size_t        nuxel_phone_thread_count(NuxelPhoneStore *s, const char *peer);
/* Number of distinct threads. */
size_t        nuxel_phone_thread_count_all(NuxelPhoneStore *s);

/* ---- vCard 3.0 --------------------------------------------------------- */
/* Serialise every contact to a vCard 3.0 string.  Caller frees *out. */
int  nuxel_phone_export_vcard(NuxelPhoneStore *s, char **out);
/* Parse a vCard stream (one or more BEGIN:VCARD blocks); *imported receives the
 * number of contacts added.  Duplicate ids are re-keyed instead of overwritten. */
int  nuxel_phone_import_vcard(NuxelPhoneStore *s, const char *text, size_t len,
                              int *imported);

/* ---- JSON store -------------------------------------------------------- */
/* Load a store from disk.  A missing file is not an error (returns 1 = empty
 * store); a corrupt file is reported as -1 and the store is left empty. */
int  nuxel_phone_store_load(NuxelPhoneStore *s, const char *path);
/* Atomic save (tmp + rename). Returns 0 on success. */
int  nuxel_phone_store_save(NuxelPhoneStore *s, const char *path);
/* Serialise/deserialise without touching the filesystem (used by tests). */
int  nuxel_phone_store_to_json(NuxelPhoneStore *s, char **out);
int  nuxel_phone_store_from_json(NuxelPhoneStore *s, const char *json);

/* ---- capability labels (never over-claim) ------------------------------ */
/* Build the user-facing capability sentence for a modality.
 * modality: "voice" | "sms" | "data" | "summary".
 * out is always NUL-terminated. Returns the number of characters written. */
size_t nuxel_phone_capability_label(const NuxelPhoneCapabilities *c,
                                    const char *modality,
                                    char *out, size_t outsz);
/* 1 when the modality is usable according to the probe, else 0. */
int    nuxel_phone_capability_available(const NuxelPhoneCapabilities *c,
                                        const char *modality);

/* Small helpers shared with the apps (also unit-tested). */
int    nuxel_phone_escape_json(const char *in, char *out, size_t outsz);
long long nuxel_phone_now(void);

#ifdef __cplusplus
}
#endif

#endif /* NUXEL_PHONE_DATA_H */
