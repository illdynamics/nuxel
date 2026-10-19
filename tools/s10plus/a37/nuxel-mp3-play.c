/* Tiny, dependency-light MP3 -> ALSA player for the Nuxel live image.
 *
 * The image contains libmpg123.so.0 but deliberately has no mpg123 command or
 * GStreamer MP3 decoder.  Load the library at runtime so the cross build does
 * not smuggle a new binary codec into the device.  Hardware volume remains the
 * button manager's capped mixer control; --gain only attenuates PCM samples.
 */
#include <alsa/asoundlib.h>
#include <dlfcn.h>
#include <errno.h>
#include <getopt.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

typedef struct mpg123_handle mpg123_handle;
enum { MPG123_OK = 0, MPG123_NEW_FORMAT = -11, MPG123_DONE = -12 };

struct mpg_api {
    int (*init)(void);
    void (*exit)(void);
    mpg123_handle *(*new_handle)(const char *, int *);
    void (*delete_handle)(mpg123_handle *);
    int (*open_file)(mpg123_handle *, const char *);
    int (*close_file)(mpg123_handle *);
    int (*read_data)(mpg123_handle *, unsigned char *, size_t, size_t *);
    int (*getformat)(mpg123_handle *, long *, int *, int *);
};

static int load_api(void *lib, struct mpg_api *api) {
#define LOAD(sym, name) do { *(void **)(&api->sym) = dlsym(lib, name); if (!api->sym) return -1; } while (0)
    LOAD(init, "mpg123_init");
    LOAD(exit, "mpg123_exit");
    LOAD(new_handle, "mpg123_new");
    LOAD(delete_handle, "mpg123_delete");
    LOAD(open_file, "mpg123_open");
    LOAD(close_file, "mpg123_close");
    LOAD(read_data, "mpg123_read");
    LOAD(getformat, "mpg123_getformat");
#undef LOAD
    return 0;
}

static int open_pcm(snd_pcm_t **out, const char *device, long rate, int channels) {
    snd_pcm_t *pcm = NULL;
    snd_pcm_hw_params_t *params;
    unsigned int actual_rate = (unsigned int)rate;
    snd_pcm_uframes_t period = 1024, buffer = 4096;
    int rc = snd_pcm_open(&pcm, device, SND_PCM_STREAM_PLAYBACK, 0);
    if (rc < 0) { fprintf(stderr, "alsa_open(%s): %s\n", device, snd_strerror(rc)); return -1; }
    snd_pcm_hw_params_alloca(&params);
    const char *step = "any";
    if ((rc = snd_pcm_hw_params_any(pcm, params)) < 0 ||
        (step = "access", (rc = snd_pcm_hw_params_set_access(pcm, params, SND_PCM_ACCESS_RW_INTERLEAVED)) < 0) ||
        (step = "format", (rc = snd_pcm_hw_params_set_format(pcm, params, SND_PCM_FORMAT_S16_LE)) < 0) ||
        (step = "channels", (rc = snd_pcm_hw_params_set_channels(pcm, params, (unsigned int)channels)) < 0) ||
        (step = "rate", (rc = snd_pcm_hw_params_set_rate_near(pcm, params, &actual_rate, NULL)) < 0) ||
        (step = "period", (rc = snd_pcm_hw_params_set_period_size_near(pcm, params, &period, NULL)) < 0) ||
        (step = "buffer", (rc = snd_pcm_hw_params_set_buffer_size_near(pcm, params, &buffer)) < 0) ||
        (step = "commit", (rc = snd_pcm_hw_params(pcm, params)) < 0) ||
        (step = "prepare", (rc = snd_pcm_prepare(pcm)) < 0)) {
        fprintf(stderr, "alsa_params(%s,%s): %s\n", device, step, snd_strerror(rc));
        snd_pcm_close(pcm); return -1;
    }
    *out = pcm;
    return 0;
}

int main(int argc, char **argv) {
    int gain = 100;
    const char *device = "default";
    static const struct option opts[] = {{"gain", required_argument, 0, 'g'}, {"device", required_argument, 0, 'd'}, {0,0,0,0}};
    int ch;
    while ((ch = getopt_long(argc, argv, "g:d:", opts, NULL)) != -1) {
        if (ch == 'g') gain = atoi(optarg);
        else if (ch == 'd') device = optarg;
        else return 2;
    }
    if (gain < 0 || gain > 100 || optind != argc - 1) return 2;

    void *lib = dlopen("libmpg123.so.0", RTLD_NOW | RTLD_LOCAL);
    struct mpg_api api = {0};
    if (!lib || load_api(lib, &api)) { fprintf(stderr, "libmpg123 unavailable\n"); return 3; }
    if (api.init() != MPG123_OK) { fprintf(stderr, "mpg123_init failed\n"); dlclose(lib); return 3; }
    int mpg_error = 0;
    mpg123_handle *mh = api.new_handle(NULL, &mpg_error);
    if (!mh || api.open_file(mh, argv[optind]) != MPG123_OK) { fprintf(stderr, "mpg123_open failed\n"); if (mh) api.delete_handle(mh); api.exit(); dlclose(lib); return 4; }

    unsigned char data[32768];
    snd_pcm_t *pcm = NULL;
    int configured = 0, status = 0;
    for (;;) {
        size_t got = 0;
        int rc = api.read_data(mh, data, sizeof(data), &got);
        if ((rc == MPG123_NEW_FORMAT || !configured) && !configured) {
            long rate = 0; int channels = 0, encoding = 0;
            if (api.getformat(mh, &rate, &channels, &encoding) != MPG123_OK ||
                rate <= 0 || channels < 1 || channels > 2 || open_pcm(&pcm, device, rate, channels)) {
                status = 5; break;
            }
            configured = 1;
            fprintf(stderr, "alsa_playback device=%s rate=%ld channels=%d gain=%d\n", device, rate, channels, gain);
        }
        if (got) {
            int16_t *samples = (int16_t *)data;
            size_t frames = got / (configured ? (size_t)(2 * 2) : 4); /* corrected below after format */
            long rate = 0; int channels = 0, encoding = 0;
            if (api.getformat(mh, &rate, &channels, &encoding) != MPG123_OK || channels < 1) { status = 5; break; }
            frames = got / ((size_t)channels * sizeof(*samples));
            for (size_t i = 0; i < frames * (size_t)channels; ++i) samples[i] = (int16_t)(((int32_t)samples[i] * gain) / 100);
            while (frames) {
                snd_pcm_sframes_t wrote = snd_pcm_writei(pcm, samples, frames);
                if (wrote < 0) { wrote = snd_pcm_recover(pcm, (int)wrote, 1); if (wrote < 0) { fprintf(stderr, "alsa_write: %s\n", snd_strerror((int)wrote)); status = 6; break; } continue; }
                samples += wrote * channels;
                frames -= (size_t)wrote;
            }
            if (status) break;
        }
        if (rc == MPG123_DONE) break;
        if (rc != MPG123_OK && rc != MPG123_NEW_FORMAT) { fprintf(stderr, "mpg123_read=%d\n", rc); status = 4; break; }
    }
    if (pcm) { if (!status) snd_pcm_drain(pcm); snd_pcm_close(pcm); }
    api.close_file(mh); api.delete_handle(mh); api.exit(); dlclose(lib);
    return status;
}
