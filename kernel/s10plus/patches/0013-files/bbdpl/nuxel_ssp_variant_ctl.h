/*
 * Nuxel PWNAGE-SSP — kernel debug counters for the BBD/SSI transport.
 *
 * Read-only diagnostics: the userspace bridge prints these once per session
 * so a silent hub is attributed to the right layer (transport work queue,
 * transfer completion, or the MCU stream itself).
 */
#ifndef NUXEL_SSP_VARIANT_CTL_H
#define NUXEL_SSP_VARIANT_CTL_H

/* Incremented for every SPI message the ttyBCM work queue sends (SSI frames). */
extern unsigned long ssp_bcm_spi_tx;
/* Incremented for every SPI message the ttyBCM work queue receives. */
extern unsigned long ssp_bcm_spi_rx;
/* IRQ enable/disable imbalance attempts on the shared host-req line. */
extern unsigned long ssp_bcm_irq_count;

#endif
