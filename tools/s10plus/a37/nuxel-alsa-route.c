/* Explicit, narrowly-scoped writer for the observed S10+ speaker controls. */
#include <alsa/asoundlib.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

static int set_named(snd_ctl_t *ctl, const char *name, long value) {
    snd_ctl_elem_list_t *list;
    snd_ctl_elem_list_alloca(&list);
    if (snd_ctl_elem_list(ctl, list) < 0 ||
        snd_ctl_elem_list_alloc_space(list, snd_ctl_elem_list_get_count(list)) < 0 ||
        snd_ctl_elem_list(ctl, list) < 0) return -1;
    for (unsigned i = 0; i < snd_ctl_elem_list_get_used(list); ++i) {
        snd_ctl_elem_id_t *id; snd_ctl_elem_id_alloca(&id);
        snd_ctl_elem_list_get_id(list, i, id);
        if (strcmp(snd_ctl_elem_id_get_name(id), name)) continue;
        snd_ctl_elem_info_t *info; snd_ctl_elem_value_t *val;
        snd_ctl_elem_info_alloca(&info); snd_ctl_elem_value_alloca(&val);
        snd_ctl_elem_info_set_id(info, id); snd_ctl_elem_value_set_id(val, id);
        if (snd_ctl_elem_info(ctl, info) < 0 || snd_ctl_elem_read(ctl, val) < 0) return -1;
        unsigned count = snd_ctl_elem_info_get_count(info);
        for (unsigned j = 0; j < count; ++j) snd_ctl_elem_value_set_integer(val, j, value);
        if (snd_ctl_elem_write(ctl, val) < 0) return -1;
        printf("%s=%ld\n", name, value);
        return 0;
    }
    fprintf(stderr, "missing control: %s\n", name);
    return -1;
}

static int set_enum(snd_ctl_t *ctl, const char *name, const char *item_name) {
    snd_ctl_elem_list_t *list;
    snd_ctl_elem_list_alloca(&list);
    if (snd_ctl_elem_list(ctl, list) < 0 || snd_ctl_elem_list_alloc_space(list, snd_ctl_elem_list_get_count(list)) < 0 || snd_ctl_elem_list(ctl, list) < 0) return -1;
    for (unsigned i = 0; i < snd_ctl_elem_list_get_used(list); ++i) {
        snd_ctl_elem_id_t *id; snd_ctl_elem_id_alloca(&id); snd_ctl_elem_list_get_id(list, i, id);
        if (strcmp(snd_ctl_elem_id_get_name(id), name)) continue;
        snd_ctl_elem_info_t *info; snd_ctl_elem_value_t *val;
        snd_ctl_elem_info_alloca(&info); snd_ctl_elem_value_alloca(&val);
        snd_ctl_elem_info_set_id(info, id); snd_ctl_elem_value_set_id(val, id);
        if (snd_ctl_elem_info(ctl, info) < 0 || snd_ctl_elem_info_get_type(info) != SND_CTL_ELEM_TYPE_ENUMERATED) return -1;
        unsigned found = snd_ctl_elem_info_get_items(info);
        for (unsigned item = 0; item < found; ++item) { snd_ctl_elem_info_set_item(info, item); if (snd_ctl_elem_info(ctl, info) == 0 && !strcmp(snd_ctl_elem_info_get_item_name(info), item_name)) { found = item; goto selected; } }
        return -1;
selected:
        snd_ctl_elem_value_set_enumerated(val, 0, found);
        if (snd_ctl_elem_write(ctl, val) < 0) return -1;
        printf("%s=%s\n", name, item_name); return 0;
    }
    return -1;
}

int main(int argc, char **argv) {
    if (argc == 2 && !strcmp(argv[1], "--restore")) {
        snd_ctl_t *ctl; if (snd_ctl_open(&ctl, "hw:0", 0) < 0) return 3;
        int rc = set_enum(ctl, "ABOX SPUS OUT0", "SIFS1") ||
                 set_enum(ctl, "ABOX UAIF0 SPK", "RESERVED") ||
                 set_named(ctl, "Right AMP PCM Gain", 19) ||
                 set_named(ctl, "Right AMP Enable Switch", 0);
        snd_ctl_close(ctl); return rc ? 4 : 0;
    }
    if (argc != 3 || strcmp(argv[1], "--gain")) return 2;
    char *end = NULL; long gain = strtol(argv[2], &end, 10);
    if (!end || *end || gain < 0 || gain > 5) return 2; /* strict A37 25% ceiling */
    snd_ctl_t *ctl;
    if (snd_ctl_open(&ctl, "hw:0", 0) < 0) return 3;
    int rc = set_enum(ctl, "ABOX SPUS OUT0", "SIFS0") ||
             set_enum(ctl, "ABOX UAIF0 SPK", "SIFS0") ||
             set_named(ctl, "Right AMP PCM Gain", gain) ||
             set_named(ctl, "Right AMP Enable Switch", 1);
    snd_ctl_close(ctl);
    return rc ? 4 : 0;
}
