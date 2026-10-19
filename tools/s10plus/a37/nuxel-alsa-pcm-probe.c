/* Read-only playback-capability probe; does not prepare or write a PCM stream. */
#include <alsa/asoundlib.h>
#include <stdio.h>

int main(void) {
    const int devices[] = {0,1,2,3,4,6,7,8,9,10,11};
    for (unsigned i = 0; i < sizeof(devices)/sizeof(devices[0]); ++i) {
        char name[24]; snprintf(name, sizeof(name), "hw:0,%d", devices[i]);
        snd_pcm_t *pcm = NULL; snd_pcm_hw_params_t *p;
        int rc = snd_pcm_open(&pcm, name, SND_PCM_STREAM_PLAYBACK, SND_PCM_NONBLOCK);
        if (rc < 0) { printf("%s open=%s\n", name, snd_strerror(rc)); continue; }
        snd_pcm_hw_params_alloca(&p); rc = snd_pcm_hw_params_any(pcm, p);
        if (rc < 0) { printf("%s params=%s\n", name, snd_strerror(rc)); snd_pcm_close(pcm); continue; }
        printf("%s s16le=%d 44100=%d 48000=%d ch1=%d ch2=%d rw=%d mmap=%d\n", name,
               snd_pcm_hw_params_test_format(pcm,p,SND_PCM_FORMAT_S16_LE),
               snd_pcm_hw_params_test_rate(pcm,p,44100,0),
               snd_pcm_hw_params_test_rate(pcm,p,48000,0),
               snd_pcm_hw_params_test_channels(pcm,p,1),
               snd_pcm_hw_params_test_channels(pcm,p,2),
               snd_pcm_hw_params_test_access(pcm,p,SND_PCM_ACCESS_RW_INTERLEAVED),
               snd_pcm_hw_params_test_access(pcm,p,SND_PCM_ACCESS_MMAP_INTERLEAVED));
        snd_pcm_close(pcm);
    }
    return 0;
}
