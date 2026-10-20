/* Read-only ALSA control dump for identifying the S10+ playback route. */
#include <alsa/asoundlib.h>
#include <stdio.h>
#include <string.h>

int main(void) {
    snd_ctl_t *ctl;
    snd_ctl_elem_list_t *list;
    if (snd_ctl_open(&ctl, "hw:0", 0) < 0) return 2;
    snd_ctl_elem_list_alloca(&list);
    if (snd_ctl_elem_list(ctl, list) < 0) return 3;
    if (snd_ctl_elem_list_alloc_space(list, snd_ctl_elem_list_get_count(list)) < 0) return 4;
    if (snd_ctl_elem_list(ctl, list) < 0) return 5;
    unsigned count = snd_ctl_elem_list_get_used(list);
    for (unsigned i = 0; i < count; ++i) {
        snd_ctl_elem_id_t *id;
        snd_ctl_elem_id_alloca(&id);
        snd_ctl_elem_list_get_id(list, i, id);
        const char *name = snd_ctl_elem_id_get_name(id);
        if ((snd_ctl_elem_id_get_numid(id) < 690 || snd_ctl_elem_id_get_numid(id) > 740) &&
            !strstr(name, "RDMA") && !strstr(name, "AIF") && !strstr(name, "SPK") &&
            !strstr(name, "SIFS") && !strstr(name, "SIFM") && !strstr(name, "RSRC") &&
            !strstr(name, "NSRC") && !strstr(name, "AMP") && !strstr(name, "Route") && !strstr(name, "Speaker") &&
            !strstr(name, "Output") && !strstr(name, "PCM")) continue;
        snd_ctl_elem_info_t *info;
        snd_ctl_elem_value_t *value;
        snd_ctl_elem_info_alloca(&info); snd_ctl_elem_value_alloca(&value);
        snd_ctl_elem_info_set_id(info, id); snd_ctl_elem_value_set_id(value, id);
        if (snd_ctl_elem_info(ctl, info) < 0 || snd_ctl_elem_read(ctl, value) < 0) continue;
        printf("numid=%u type=%d name=%s value=", snd_ctl_elem_id_get_numid(id),
               snd_ctl_elem_info_get_type(info), name);
        unsigned n = snd_ctl_elem_info_get_count(info);
        for (unsigned j = 0; j < n; ++j) {
            if (j) putchar(',');
            if (snd_ctl_elem_info_get_type(info) == SND_CTL_ELEM_TYPE_ENUMERATED) {
                unsigned item = snd_ctl_elem_value_get_enumerated(value, j);
                snd_ctl_elem_info_set_item(info, item);
                if (snd_ctl_elem_info(ctl, info) == 0) fputs(snd_ctl_elem_info_get_item_name(info), stdout);
                else printf("#%u", item);
            } else if (snd_ctl_elem_info_get_type(info) == SND_CTL_ELEM_TYPE_BOOLEAN ||
                       snd_ctl_elem_info_get_type(info) == SND_CTL_ELEM_TYPE_INTEGER) {
                printf("%ld", snd_ctl_elem_value_get_integer(value, j));
            } else printf("?");
        }
        if (snd_ctl_elem_info_get_type(info) == SND_CTL_ELEM_TYPE_ENUMERATED &&
            !strncmp(name, "ABOX UAIF", 9)) {
            printf(" options=");
            unsigned items = snd_ctl_elem_info_get_items(info);
            for (unsigned k = 0; k < items; ++k) {
                if (k) putchar('|');
                snd_ctl_elem_info_set_item(info, k);
                if (snd_ctl_elem_info(ctl, info) == 0) fputs(snd_ctl_elem_info_get_item_name(info), stdout);
            }
        }
        putchar('\n');
    }
    snd_ctl_close(ctl);
    return 0;
}
