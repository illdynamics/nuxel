/* SPDX-License-Identifier: GPL-2.0-only */
#ifndef NUXEL_IMS_SECURITY_H
#define NUXEL_IMS_SECURITY_H
#include <stdbool.h>
#include <stdint.h>
#include <stddef.h>
struct ims_security_offer {
    uint32_t spi_c,spi_s;
    uint16_t port_c,port_s;
    bool sha1,aes;
};
/* A single ipsec-3gpp offer; unknown mandatory algorithm combinations fail. */
bool ims_security_parse(const char *value,struct ims_security_offer *out);
struct ims_security {
    struct ims_security_offer local,remote;
    int family;
    uint8_t local_ip[16],remote_ip[16];
    uint32_t reqid;
    unsigned states,policies;
    bool active;
};
/* Verify the negotiated algorithms against our offer, retaining each peer's
 * independently allocated SPIs/ports. No session keys are involved. */
bool ims_security_negotiate(struct ims_security *s,const char *client,const char *server);
/* Session CK/IK only, never the private USIM key. Netlink keys never enter
 * argv, logs or files. Installation rolls back a partially installed set. */
bool ims_security_install(struct ims_security *s,const uint8_t ck[16],const uint8_t ik[16]);
void ims_security_clear(struct ims_security *s);
#endif
