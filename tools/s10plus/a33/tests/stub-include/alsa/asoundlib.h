/* Stub alsa/asoundlib.h — SYNTAX GATE ONLY, never a build substitute.
 *
 * WHY THIS EXISTS
 *   nuxel-button-manager.c needs alsa-lib (snd_mixer_*) and <linux/input.h>. A
 *   development host without alsa-lib-devel cannot build it, so a syntax error
 *   in the daemon would otherwise only be discovered on the UTM guest or the
 *   handset. This header declares exactly the snd_mixer_* surface the daemon
 *   uses, with the REAL alsa-lib prototypes, so
 *
 *     cc -fsyntax-only -I tests/stub-include nuxel-button-manager.c
 *
 * fails on a real C error in the daemon instead of passing silently.
 *
 * WHAT IT IS NOT
 *   It is NOT a build: no code from here is ever linked, and a green syntax
 *   check is never a substitute for the aarch64 build on Fedora 43 (the build
 *   script still does the real build and reports SKIP when alsa-lib is absent).
 *   The LINKED ABI always comes from the real <alsa/asoundlib.h>.
 */
#ifndef NUXEL_TEST_STUB_ASOUNDLIB_H
#define NUXEL_TEST_STUB_ASOUNDLIB_H

typedef struct _snd_mixer snd_mixer_t;
typedef struct _snd_mixer_elem snd_mixer_elem_t;

typedef enum _snd_mixer_selem_channel_id {
  SND_MIXER_SCHN_UNKNOWN = -1,
  SND_MIXER_SCHN_FRONT_LEFT = 0,
  SND_MIXER_SCHN_FRONT_RIGHT,
  SND_MIXER_SCHN_REAR_LEFT,
  SND_MIXER_SCHN_REAR_RIGHT,
  SND_MIXER_SCHN_FRONT_CENTER,
  SND_MIXER_SCHN_WOOFER,
  SND_MIXER_SCHN_SIDE_LEFT,
  SND_MIXER_SCHN_SIDE_RIGHT,
  SND_MIXER_SCHN_REAR_CENTER,
  SND_MIXER_SCHN_LAST = -1
} snd_mixer_selem_channel_id_t;

int snd_mixer_open(snd_mixer_t **mixer, int mode);
int snd_mixer_close(snd_mixer_t *mixer);
int snd_mixer_attach(snd_mixer_t *mixer, const char *name);
int snd_mixer_selem_register(snd_mixer_t *mixer, void *options, void **classp);
int snd_mixer_load(snd_mixer_t *mixer);
snd_mixer_elem_t *snd_mixer_first_elem(snd_mixer_t *mixer);
snd_mixer_elem_t *snd_mixer_elem_next(snd_mixer_elem_t *elem);
const char *snd_mixer_selem_get_name(snd_mixer_elem_t *elem);
int snd_mixer_selem_is_active(snd_mixer_elem_t *elem);
int snd_mixer_selem_has_playback_volume(snd_mixer_elem_t *elem);
int snd_mixer_selem_has_playback_switch(snd_mixer_elem_t *elem);
int snd_mixer_selem_get_playback_volume_range(snd_mixer_elem_t *elem, long *min, long *max);
int snd_mixer_selem_get_playback_volume(snd_mixer_elem_t *elem,
                                        snd_mixer_selem_channel_id_t channel, long *value);
int snd_mixer_selem_set_playback_volume_all(snd_mixer_elem_t *elem, long value);
int snd_mixer_selem_get_playback_switch(snd_mixer_elem_t *elem,
                                        snd_mixer_selem_channel_id_t channel, int *value);
int snd_mixer_selem_set_playback_switch_all(snd_mixer_elem_t *elem, int value);

#endif /* NUXEL_TEST_STUB_ASOUNDLIB_H */
