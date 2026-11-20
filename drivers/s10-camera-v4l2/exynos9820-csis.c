// SPDX-License-Identifier: GPL-2.0-only
/*
 * Exynos 9820 MIPI CSI-2 receiver (CSIS) with its CSISX4 write DMA.
 *
 * Camera path of the Galaxy S10: sensor -> M0S4S4S4 D-PHY -> CSIS1 -> write
 * DMA channel 1 -> memory. The media graph is
 *
 *   sensor [0] ---> [0] csis [1] ---> [0] video capture node
 *
 * Register layouts and sequences follow Samsung's GPL fimc-is-hw-csi-v5_2.[ch]
 * and phy-exynos-mipi.c (LineageOS/android_kernel_samsung_exynos9820), the
 * recipe was verified on hardware (see docs/camera-bringup.md).
 *
 * The write DMA has a ring of address slots. Every frame goes to the next
 * slot; at the end of a frame the finished slot is handed back to userspace
 * and re-armed with the next queued buffer (or a scratch buffer when userspace
 * is too slow, in which case the frame is dropped and the sequence number
 * skips).
 *
 * The ISPPRE power domain must never be powered off: once off, its CMU is
 * unreachable until reboot. s10-isppre-hold.ko keeps it on and must be
 * loaded first.
 */
#include <linux/bitfield.h>
#include <linux/clk.h>
#include <linux/delay.h>
#include <linux/dma-mapping.h>
#include <linux/interrupt.h>
#include <linux/io.h>
#include <linux/ktime.h>
#include <linux/mfd/syscon.h>
#include <linux/module.h>
#include <linux/of.h>
#include <linux/platform_device.h>
#include <linux/pm_runtime.h>
#include <linux/regmap.h>
#include <media/media-device.h>
#include <media/v4l2-async.h>
#include <media/v4l2-common.h>
#include <media/v4l2-device.h>
#include <media/v4l2-fwnode.h>
#include <media/v4l2-ioctl.h>
#include <media/v4l2-mc.h>
#include <media/v4l2-subdev.h>
#include <media/videobuf2-dma-contig.h>
#include <media/videobuf2-v4l2.h>

#include "exynos9820-csis-settle.h"

#define DRV_NAME "exynos9820-csis"

static unsigned long bus_hz = 400000000;
module_param(bus_hz, ulong, 0644);
MODULE_PARM_DESC(bus_hz, "ISPPRE bus rate while streaming (200 MHz is too slow, the DMA overflows)");
static unsigned int settle;
module_param(settle, uint, 0644);
MODULE_PARM_DESC(settle, "D-PHY T_HS_SETTLE override (0: Samsung's table for the lane rate)");
static int dc_combo = -1;
module_param(dc_combo, int, 0644);
MODULE_PARM_DESC(dc_combo, "D/C-combo PHY lane setup: -1 from the device tree, 0 off, 1 on");
static bool rx_error_drops_frame = true;
module_param(rx_error_drops_frame, bool, 0644);
MODULE_PARM_DESC(rx_error_drops_frame, "Return frames with receiver errors as failed (diagnostics: 0 delivers them)");
static unsigned int vc0_pixel_mode = 1;
module_param(vc0_pixel_mode, uint, 0644);
MODULE_PARM_DESC(vc0_pixel_mode, "CSIS image channel pixels per clock: 0 single, 1 dual (Samsung), 2 quad");
static int pdaf_vc1 = -1;
module_param(pdaf_vc1, int, 0644);
MODULE_PARM_DESC(pdaf_vc1, "Configure the PDAF channel VC1 (quad pixel, height/4): -1 from the device tree, 0 off, 1 on");
static unsigned int sram_split = 0x480;
module_param(sram_split, uint, 0644);
static unsigned int interleave = 2;
module_param(interleave, uint, 0644);

/* ---- CSIS v5.2 registers ------------------------------------------------- */
#define CSIS_CMN_CTRL		0x004
#define   CMN_CSI_EN		BIT(0)
#define   CMN_SW_RESET		BIT(1)
#define   CMN_LANE_SHIFT	8
#define   CMN_INTERLEAVE_SHIFT	10
#define   CMN_UPDATE_SHADOW	GENMASK(19, 16)
#define   CMN_QCHANNEL_EN	BIT(20)
#define   CMN_PHY_SEL		BIT(21)
#define CSIS_INT_MSK0		0x010
#define CSIS_INT_SRC0		0x014
#define CSIS_INT_MSK1		0x018
#define CSIS_INT_SRC1		0x01c
#define CSIS_ISP_CONFIG_CH0	0x040
#define   ISP_DUAL_PIXEL	BIT(12)
#define CSIS_ISP_RESOL_CH0	0x044
#define CSIS_ISP_CONFIG_CH1	0x050
#define CSIS_ISP_RESOL_CH1	0x054
#define   ISP_QUAD_PIXEL	(2 << 12)
#define CSIS_DEBUG_OPTION	0x500
#define CSIS_PHY_CMN_CTRL	0x704
/* Errors only: no frame start/end, the DMA reports those */
#define CSIS_ERR_MASK0		0x000fff1f
/*
 * Only channel 0 carries image data. The tele sensor also puts data on other
 * channels, which raises the per-channel resolution mismatch errors of
 * channels 1..3 on every line; they are not interesting.
 */
#define CSIS_ERR_MASK1		0x000011f0
#define MIPI_DT_RAW10		0x2b

/* ---- CSISX4 write-DMA channel registers --------------------------------- */
#define DMA_CTRL		0x000
#define   DMA_ENABLE		BIT(0)
#define   DMA_UPDT_PTR_EN	BIT(1)
#define   DMA_UPDT_FRAMEPTR	GENMASK(6, 2)
#define DMA_FMT			0x004	/* 0: 16 bit per pixel, 2D, RAW10 */
#define DMA_ADDR(n)		(0x010 + 4 * (n))
#define DMA_ACT_CTRL		0x090
#define   DMA_ACT_FRAMEPTR	GENMASK(6, 2)
#define DMA_RESOL		0x0a4
#define DMA_FCNTSEQ		0x0b0
#define DMA_DATA_CTRL		0x400
#define DMA_INT_MASK		0x404
#define DMA_INT_SRC		0x408
#define   DMA_INT_FRM_START	BIT(4)
#define   DMA_INT_FRM_END	BIT(8)
#define   DMA_INT_ERROR		BIT(12)
#define   DMA_INT_ABORT_DONE	BIT(16)
#define   DMA_INT_OVERLAP	GENMASK(23, 20)
#define DMA_CMN_CTRL		0x414
#define DMA_OTF_FORMAT		0x41c
#define DMA_IRQ_MASK		(DMA_INT_FRM_START | DMA_INT_FRM_END | \
				 DMA_INT_ERROR | DMA_INT_OVERLAP)

/* ---- CSISX4 PDP DMA top -------------------------------------------------- */
#define TOP_ARB_PRI		0x00
#define TOP_CTRL		0x08
#define   TOP_IP_PROCESSING	BIT(1)
#define TOP_SRAM_SPLIT		0x0c
#define TOP_MATRIX		0x10

/*
 * Per instance, from the device tree: the PMU isolation register of the PHY
 * (samsung,pmu-phy-offset) and its reset bit in the ISPPRE sysreg at
 * 0x17020500 (samsung,phy-reset-bit).
 */

#define CSIS_PAD_SINK		0
#define CSIS_PAD_SRC		1
#define CSIS_NUM_PADS		2
#define CSIS_NUM_SLOTS		3
#define CSIS_MIN_WIDTH		64
#define CSIS_MAX_WIDTH		4608
#define CSIS_MIN_HEIGHT		64
#define CSIS_MAX_HEIGHT		3456
#define CSIS_WIDTH_ALIGN	8

enum { C_CSIS, C_DMA, C_MMU, C_BUS, C_NUM };

struct csis_format {
	u32 mbus_code;
	u32 fourcc;
};

/* 10 bit samples in 16 bit words, in the low bits (DMA_FMT = 0) */
static const struct csis_format csis_formats[] = {
	{ MEDIA_BUS_FMT_SBGGR10_1X10, V4L2_PIX_FMT_SBGGR10 },
	{ MEDIA_BUS_FMT_SGBRG10_1X10, V4L2_PIX_FMT_SGBRG10 },
	{ MEDIA_BUS_FMT_SGRBG10_1X10, V4L2_PIX_FMT_SGRBG10 },
	{ MEDIA_BUS_FMT_SRGGB10_1X10, V4L2_PIX_FMT_SRGGB10 },
};

struct csis_buffer {
	struct vb2_v4l2_buffer vb;
	struct list_head list;
	dma_addr_t dma;
};
#define to_csis_buffer(v) container_of(v, struct csis_buffer, vb)

struct csis {
	struct device *dev;
	void __iomem *regs, *top, *rst, *phy, *dma;
	struct regmap *pmu;
	u32 pmu_phy_offset, phy_reset_bit;
	bool phy_dc_combo;
	bool pdaf_vc1;
	unsigned int lanes, nr_sensors;
	struct clk_bulk_data clks[C_NUM];
	unsigned long old_bus_rate;
	bool rate_set;
	int irq_csis, irq_dma;

	struct media_device mdev;
	struct v4l2_device v4l2_dev;
	struct v4l2_async_notifier notifier;
	struct v4l2_subdev sd;
	struct media_pad pads[CSIS_NUM_PADS];
	bool registered;

	struct video_device vdev;
	struct media_pad vdev_pad;
	struct media_pipeline vdev_pipe;
	struct vb2_queue queue;
	struct mutex lock;		/* video node and vb2 */
	struct v4l2_pix_format fmt;

	/* Buffer ring, shared with the interrupt handler */
	spinlock_t qlock;
	struct list_head queued;
	struct csis_buffer *slot[CSIS_NUM_SLOTS];	/* NULL: scratch buffer */
	void *scratch;
	dma_addr_t scratch_dma;
	size_t scratch_size;
	unsigned int cur_slot;
	u64 frame_ts;
	u32 sequence;
	bool frame_error;
	bool running;

	unsigned long n_done, n_dropped, n_errors, n_csis_errors;
};

static inline struct csis *sd_to_csis(struct v4l2_subdev *sd)
{
	return container_of(sd, struct csis, sd);
}

static void rmw(void __iomem *p, u32 mask, u32 val)
{
	writel((readl(p) & ~mask) | (val & mask), p);
}

static const struct csis_format *csis_find_code(u32 code)
{
	unsigned int i;

	for (i = 0; i < ARRAY_SIZE(csis_formats); i++)
		if (csis_formats[i].mbus_code == code)
			return &csis_formats[i];
	return NULL;
}

static const struct csis_format *csis_find_fourcc(u32 fourcc)
{
	unsigned int i;

	for (i = 0; i < ARRAY_SIZE(csis_formats); i++)
		if (csis_formats[i].fourcc == fourcc)
			return &csis_formats[i];
	return NULL;
}

/* ------------------------------------------------------------- hardware */

static int csis_runtime_resume(struct device *dev)
{
	struct csis *c = dev_get_drvdata(dev);
	int ret, i;

	ret = clk_prepare_enable(c->clks[C_BUS].clk);
	if (ret)
		return ret;
	c->old_bus_rate = clk_get_rate(c->clks[C_BUS].clk);
	if (bus_hz && bus_hz != c->old_bus_rate) {
		ret = clk_set_rate(c->clks[C_BUS].clk, bus_hz);
		if (ret)
			dev_warn(dev, "cannot set the bus clock to %lu Hz: %d\n",
				 bus_hz, ret);
		else
			c->rate_set = true;
	}
	for (i = C_CSIS; i <= C_MMU; i++) {
		ret = clk_prepare_enable(c->clks[i].clk);
		if (ret)
			goto err;
	}
	return 0;
err:
	while (i-- > C_CSIS)
		clk_disable_unprepare(c->clks[i].clk);
	if (c->rate_set)
		clk_set_rate(c->clks[C_BUS].clk, c->old_bus_rate);
	c->rate_set = false;
	clk_disable_unprepare(c->clks[C_BUS].clk);
	return ret;
}

static int csis_runtime_suspend(struct device *dev)
{
	struct csis *c = dev_get_drvdata(dev);
	int i;

	for (i = C_MMU; i >= C_CSIS; i--)
		clk_disable_unprepare(c->clks[i].clk);
	if (c->rate_set)
		clk_set_rate(c->clks[C_BUS].clk, c->old_bus_rate);
	c->rate_set = false;
	clk_disable_unprepare(c->clks[C_BUS].clk);
	return 0;
}

static void phy_bits(void __iomem *a, unsigned int start, unsigned int width, u32 val)
{
	u32 mask = width >= 32 ? ~0U : (1U << width) - 1;
	u32 cfg = readl(a);

	cfg &= ~(mask << start);
	cfg |= (val & mask) << start;
	writel(cfg, a);
}

/* __set_phy_cfg_0502_0002_dphy(), 4 lanes, plain D-PHY. */
/* Samsung's fimc_is_hw_find_settle(): lane rate rounded up to 10 Mbit/s */
static u32 csis_settle_for(u32 speed)
{
	speed = clamp(roundup(speed, 10), CSIS_SETTLE_MIN_RATE, CSIS_SETTLE_MAX_RATE);
	return csis_settle_table[(CSIS_SETTLE_MAX_RATE - speed) / 10];
}

static void csis_phy_configure(struct csis *c, u32 speed)
{
	u32 hs_settle = settle ?: csis_settle_for(speed);
	void __iomem *regs = c->phy;
	u32 settle_clk_sel = 1, skew_delay_sel = 0, skew_cal_en = 0, t_clk_miss = 3;
	u32 clk_div;
	int i;

	if (speed >= 1500) {
		settle_clk_sel = 0;
		skew_cal_en = 1;
		if (speed < 4000)
			skew_delay_sel = speed >= 3000 ? 1 : speed >= 2000 ? 2 : 3;
	}
	writel(0x00000001, regs + 0x0000);	/* SC_GNR_CON0 */
	writel(0x00001450, regs + 0x0004);
	writel(speed > 4500 ? 0 : 4, regs + 0x0008);
	writel(speed > 4500 ? 0x8000 : 0x9000, regs + 0x000c);
	writel(0x00000005, regs + 0x0010);
	clk_div = max(0, (int)(5 - DIV_ROUND_UP(((t_clk_miss - 1) * speed) >> 2, 26)));
	phy_bits(regs + 0x0010, 8, 2, clk_div);
	writel(0x00000600, regs + 0x0014);
	writel(0x00000301, regs + 0x0030);
	for (i = 0; i < 4; i++) {
		void __iomem *l = regs + i * 0x100;

		writel(0x00000001, l + 0x0100);	/* SD_GNR_CON0 */
		writel(0x00001450, l + 0x0104);
		writel(speed > 4500 ? 0 : 4, l + 0x0108);
		writel(speed > 4500 ? 0x8260 : speed == 4500 ? 0x9260 : 0x9000, l + 0x010c);
		writel(0x00000005, l + 0x0110);
		phy_bits(l + 0x0110, 8, 2, skew_delay_sel);
		writel(0x00000600, l + 0x0114);
		/* D/C-PHY combo lanes 0..2 (Samsung PHY type 0xDC: CSIS0, CSIS2) */
		if ((dc_combo < 0 ? c->phy_dc_combo : dc_combo) && i < 3)
			writel(0x00000040, l + 0x0124);	/* SD_ANA_CON7 */
		phy_bits(l + 0x0130, 0, 8, hs_settle);
		phy_bits(l + 0x0130, 8, 1, settle_clk_sel);
		writel(0x00000003, l + 0x0134);
		phy_bits(l + 0x0140, 0, 1, skew_cal_en);
		writel(0x0000081a, l + 0x0150);
	}
}

static int csis_phy_on(struct csis *c, u32 speed)
{
	int ret;

	ret = regmap_update_bits(c->pmu, c->pmu_phy_offset, 1, 1);	/* isolation bypass */
	if (ret)
		return ret;
	writel(readl(c->rst) & ~BIT(c->phy_reset_bit), c->rst);
	udelay(10);
	writel(readl(c->rst) | BIT(c->phy_reset_bit), c->rst);
	udelay(10);
	csis_phy_configure(c, speed);
	return 0;
}

static void csis_phy_off(struct csis *c)
{
	writel(readl(c->rst) & ~BIT(c->phy_reset_bit), c->rst);
	regmap_update_bits(c->pmu, c->pmu_phy_offset, 1, 0);
}

static void csis_csi_enable(struct csis *c, u32 width, u32 height)
{
	u32 v;
	int i;

	rmw(c->regs + CSIS_CMN_CTRL, CMN_SW_RESET, CMN_SW_RESET);
	for (i = 0; i < 20 && (readl(c->regs + CSIS_CMN_CTRL) & CMN_SW_RESET); i++)
		udelay(10);

	/* lane count (zero based), lane interleave */
	v = readl(c->regs + CSIS_CMN_CTRL);
	v &= ~(GENMASK(1, 0) << CMN_LANE_SHIFT);
	v |= (c->lanes - 1) << CMN_LANE_SHIFT;
	v &= ~(GENMASK(1, 0) << CMN_INTERLEAVE_SHIFT);
	v |= (interleave & 3) << CMN_INTERLEAVE_SHIFT;
	writel(v, c->regs + CSIS_CMN_CTRL);
	rmw(c->regs + CSIS_PHY_CMN_CTRL, GENMASK(4, 1), GENMASK(c->lanes, 1));	/* data lanes */
	writel(1, c->regs + CSIS_DEBUG_OPTION);				/* pixel align */

	writel((min(vc0_pixel_mode, 2U) << 12) | (MIPI_DT_RAW10 << 2), c->regs + CSIS_ISP_CONFIG_CH0);
	writel((height << 16) | width, c->regs + CSIS_ISP_RESOL_CH0);
	/*
	 * S5K2L4 (Samsung PD_MOD3): phase-detection lines arrive interleaved on
	 * VC1, one per four image lines. Samsung runs that channel in quad pixel
	 * mode; it has no DMA here, so its data is dropped.
	 */
	if (pdaf_vc1 < 0 ? c->pdaf_vc1 : pdaf_vc1) {
		writel(ISP_QUAD_PIXEL | (MIPI_DT_RAW10 << 2) | 1, c->regs + CSIS_ISP_CONFIG_CH1);
		writel(((height / 4) << 16) | width, c->regs + CSIS_ISP_RESOL_CH1);
	}

	writel(readl(c->regs + CSIS_INT_SRC0), c->regs + CSIS_INT_SRC0);
	writel(readl(c->regs + CSIS_INT_SRC1), c->regs + CSIS_INT_SRC1);
	writel(CSIS_ERR_MASK0, c->regs + CSIS_INT_MSK0);
	writel(CSIS_ERR_MASK1, c->regs + CSIS_INT_MSK1);

	rmw(c->regs + CSIS_CMN_CTRL, CMN_UPDATE_SHADOW, CMN_UPDATE_SHADOW);
	rmw(c->regs + CSIS_CMN_CTRL, CMN_PHY_SEL, 0);
	rmw(c->regs + CSIS_PHY_CMN_CTRL, BIT(0), 1);			/* clock lane */
	rmw(c->regs + CSIS_CMN_CTRL, CMN_QCHANNEL_EN, 0);
	rmw(c->regs + CSIS_CMN_CTRL, CMN_CSI_EN, CMN_CSI_EN);
}

static void csis_csi_disable(struct csis *c)
{
	rmw(c->regs + CSIS_PHY_CMN_CTRL, GENMASK(4, 0), 0);
	rmw(c->regs + CSIS_CMN_CTRL, CMN_CSI_EN, 0);
	writel(0, c->regs + CSIS_INT_MSK0);
	writel(0, c->regs + CSIS_INT_MSK1);
}

/* DMA_ABORT_REQ handshake: also clears a stale "aborted" state. */
static void csis_dma_abort(struct csis *c)
{
	u32 src = 0;
	int i;

	writel(1, c->dma + DMA_CMN_CTRL);
	for (i = 0; i < 100; i++) {
		src = readl(c->dma + DMA_INT_SRC);
		if (src & DMA_INT_ABORT_DONE)
			break;
		udelay(10);
	}
	writel(src, c->dma + DMA_INT_SRC);
	writel(0, c->dma + DMA_CMN_CTRL);
}

static void csis_dma_start(struct csis *c, u32 width)
{
	unsigned int i;

	csis_dma_abort(c);

	writel((1 << 2) | 2, c->top + TOP_ARB_PRI);
	rmw(c->top + TOP_CTRL, TOP_IP_PROCESSING, TOP_IP_PROCESSING);
	writel((sram_split << 16) | sram_split, c->top + TOP_SRAM_SPLIT);
	writel(0, c->top + TOP_MATRIX);

	writel(0, c->dma + DMA_OTF_FORMAT);	/* RAW10 over the OTF path */
	writel(0, c->dma + DMA_DATA_CTRL);
	writel(DMA_IRQ_MASK, c->dma + DMA_INT_MASK);
	writel(readl(c->dma + DMA_INT_SRC), c->dma + DMA_INT_SRC);
	writel(0, c->dma + DMA_FMT);
	writel(width, c->dma + DMA_RESOL);

	writel(0, c->dma + DMA_FCNTSEQ);
	rmw(c->dma + DMA_CTRL, DMA_UPDT_FRAMEPTR, 0);
	for (i = 0; i < CSIS_NUM_SLOTS; i++) {
		dma_addr_t addr = c->slot[i] ? c->slot[i]->dma : c->scratch_dma;

		writel(lower_32_bits(addr), c->dma + DMA_ADDR(i));
	}
	writel(GENMASK(CSIS_NUM_SLOTS - 1, 0), c->dma + DMA_FCNTSEQ);
	rmw(c->dma + DMA_CTRL, DMA_ENABLE | DMA_UPDT_PTR_EN,
	    DMA_ENABLE | DMA_UPDT_PTR_EN);
}

static void csis_dma_stop(struct csis *c)
{
	rmw(c->dma + DMA_CTRL, DMA_ENABLE | DMA_UPDT_PTR_EN, 0);
	writel(0, c->dma + DMA_INT_MASK);
}

/* ----------------------------------------------------------- interrupts */

static irqreturn_t csis_dma_irq(int irq, void *data)
{
	struct csis *c = data;
	struct csis_buffer *done = NULL;
	u32 src = readl(c->dma + DMA_INT_SRC);
	unsigned long flags;
	bool err;

	if (!(src & (DMA_IRQ_MASK)))
		return IRQ_NONE;
	writel(src, c->dma + DMA_INT_SRC);

	if (src & (DMA_INT_ERROR | DMA_INT_OVERLAP)) {
		c->frame_error = true;
		c->n_errors++;
	}

	/* If both are pending, the end belongs to the previous frame */
	if (src & DMA_INT_FRM_END) {
		unsigned int slot = c->cur_slot;
		struct csis_buffer *next;
		dma_addr_t addr;

		spin_lock_irqsave(&c->qlock, flags);
		done = c->slot[slot];
		next = list_first_entry_or_null(&c->queued, struct csis_buffer, list);
		if (next) {
			list_del(&next->list);
			addr = next->dma;
		} else {
			addr = c->scratch_dma;
		}
		c->slot[slot] = next;
		writel(lower_32_bits(addr), c->dma + DMA_ADDR(slot));
		spin_unlock_irqrestore(&c->qlock, flags);

		err = c->frame_error && rx_error_drops_frame;
		c->frame_error = false;
		if (done) {
			done->vb.vb2_buf.timestamp = c->frame_ts;
			done->vb.sequence = c->sequence;
			done->vb.field = V4L2_FIELD_NONE;
			vb2_buffer_done(&done->vb.vb2_buf,
					err ? VB2_BUF_STATE_ERROR : VB2_BUF_STATE_DONE);
			c->n_done++;
		} else {
			c->n_dropped++;
		}
		c->sequence++;
	}

	if (src & DMA_INT_FRM_START) {
		c->cur_slot = FIELD_GET(DMA_ACT_FRAMEPTR, readl(c->dma + DMA_ACT_CTRL));
		if (c->cur_slot >= CSIS_NUM_SLOTS)
			c->cur_slot = 0;
		c->frame_ts = ktime_get_ns();
	}
	return IRQ_HANDLED;
}

static irqreturn_t csis_csi_irq(int irq, void *data)
{
	struct csis *c = data;
	u32 src0 = readl(c->regs + CSIS_INT_SRC0);
	u32 src1 = readl(c->regs + CSIS_INT_SRC1);

	if (!src0 && !src1)
		return IRQ_NONE;
	writel(src0, c->regs + CSIS_INT_SRC0);
	writel(src1, c->regs + CSIS_INT_SRC1);

	c->frame_error = true;
	if (!(c->n_csis_errors++ % 256))
		dev_warn_ratelimited(c->dev, "receiver error src0=%08x src1=%08x (%lu so far)\n",
				     src0, src1, c->n_csis_errors);
	if (c->n_csis_errors > 100000) {
		dev_err(c->dev, "error storm, masking the receiver interrupts\n");
		writel(0, c->regs + CSIS_INT_MSK0);
		writel(0, c->regs + CSIS_INT_MSK1);
	}
	return IRQ_HANDLED;
}

/* ------------------------------------------------------- CSIS subdevice */

static void csis_fill_format(struct v4l2_mbus_framefmt *f, u32 code, u32 w, u32 h)
{
	f->width = w;
	f->height = h;
	f->code = code;
	f->field = V4L2_FIELD_NONE;
	f->colorspace = V4L2_COLORSPACE_RAW;
	f->ycbcr_enc = V4L2_YCBCR_ENC_601;
	f->quantization = V4L2_QUANTIZATION_FULL_RANGE;
	f->xfer_func = V4L2_XFER_FUNC_NONE;
}

static int csis_init_state(struct v4l2_subdev *sd, struct v4l2_subdev_state *state)
{
	unsigned int i;

	for (i = 0; i < CSIS_NUM_PADS; i++)
		csis_fill_format(v4l2_subdev_state_get_format(state, i),
				 MEDIA_BUS_FMT_SGRBG10_1X10, 2304, 1728);
	return 0;
}

static int csis_enum_mbus_code(struct v4l2_subdev *sd, struct v4l2_subdev_state *state,
			       struct v4l2_subdev_mbus_code_enum *code)
{
	if (code->pad == CSIS_PAD_SRC) {
		if (code->index)
			return -EINVAL;
		code->code = v4l2_subdev_state_get_format(state, CSIS_PAD_SINK)->code;
		return 0;
	}
	if (code->index >= ARRAY_SIZE(csis_formats))
		return -EINVAL;
	code->code = csis_formats[code->index].mbus_code;
	return 0;
}

static int csis_enum_frame_size(struct v4l2_subdev *sd, struct v4l2_subdev_state *state,
				struct v4l2_subdev_frame_size_enum *fse)
{
	if (fse->index || !csis_find_code(fse->code))
		return -EINVAL;
	if (fse->pad == CSIS_PAD_SRC) {
		const struct v4l2_mbus_framefmt *f =
			v4l2_subdev_state_get_format(state, CSIS_PAD_SINK);

		if (fse->code != f->code)
			return -EINVAL;
		fse->min_width = fse->max_width = f->width;
		fse->min_height = fse->max_height = f->height;
		return 0;
	}
	fse->min_width = CSIS_MIN_WIDTH;
	fse->max_width = CSIS_MAX_WIDTH;
	fse->min_height = CSIS_MIN_HEIGHT;
	fse->max_height = CSIS_MAX_HEIGHT;
	return 0;
}

static int csis_set_fmt(struct v4l2_subdev *sd, struct v4l2_subdev_state *state,
			struct v4l2_subdev_format *fmt)
{
	const struct csis_format *f;
	struct v4l2_mbus_framefmt *sink, *src;
	u32 w, h;

	if (fmt->pad == CSIS_PAD_SRC)	/* the source follows the sink */
		return v4l2_subdev_get_fmt(sd, state, fmt);

	if (sd_to_csis(sd)->running && fmt->which == V4L2_SUBDEV_FORMAT_ACTIVE)
		return -EBUSY;

	f = csis_find_code(fmt->format.code) ?: &csis_formats[0];
	w = clamp(ALIGN(fmt->format.width, CSIS_WIDTH_ALIGN), CSIS_MIN_WIDTH, CSIS_MAX_WIDTH);
	h = clamp_t(u32, fmt->format.height, CSIS_MIN_HEIGHT, CSIS_MAX_HEIGHT);

	sink = v4l2_subdev_state_get_format(state, CSIS_PAD_SINK);
	src = v4l2_subdev_state_get_format(state, CSIS_PAD_SRC);
	csis_fill_format(sink, f->mbus_code, w, h);
	*src = *sink;
	fmt->format = *sink;
	return 0;
}

static int csis_enable_streams(struct v4l2_subdev *sd, struct v4l2_subdev_state *state,
			       u32 pad, u64 streams_mask)
{
	struct csis *c = sd_to_csis(sd);
	const struct v4l2_mbus_framefmt *fmt =
		v4l2_subdev_state_get_format(state, CSIS_PAD_SINK);
	struct media_pad *remote = media_pad_remote_pad_unique(&c->pads[CSIS_PAD_SINK]);
	unsigned long flags;
	s64 link_freq;
	unsigned int i;
	int ret;

	if (IS_ERR(remote))
		return PTR_ERR(remote);

	/* 10 bits per pixel, double data rate */
	link_freq = v4l2_get_link_freq(remote, 10, c->lanes * 2);
	if (link_freq <= 0)
		return dev_err_probe(c->dev, link_freq ? link_freq : -EINVAL,
				     "the sensor does not report its link frequency\n");

	ret = pm_runtime_resume_and_get(c->dev);
	if (ret < 0)
		return ret;

	c->scratch_size = fmt->width * fmt->height * 2;
	c->scratch = dma_alloc_coherent(c->dev, c->scratch_size, &c->scratch_dma, GFP_KERNEL);
	if (!c->scratch) {
		ret = -ENOMEM;
		goto err_pm;
	}

	spin_lock_irqsave(&c->qlock, flags);
	for (i = 0; i < CSIS_NUM_SLOTS; i++) {
		c->slot[i] = list_first_entry_or_null(&c->queued, struct csis_buffer, list);
		if (c->slot[i])
			list_del(&c->slot[i]->list);
	}
	spin_unlock_irqrestore(&c->qlock, flags);

	c->cur_slot = 0;
	c->sequence = 0;
	c->frame_error = false;
	c->n_done = c->n_dropped = c->n_errors = c->n_csis_errors = 0;

	ret = csis_phy_on(c, div_u64(link_freq * 2, 1000000));
	if (ret)
		goto err_slots;
	csis_dma_start(c, fmt->width);
	csis_csi_enable(c, fmt->width, fmt->height);
	c->running = true;
	enable_irq(c->irq_dma);
	enable_irq(c->irq_csis);

	ret = v4l2_subdev_enable_streams(media_entity_to_v4l2_subdev(remote->entity),
					 remote->index, BIT(0));
	if (ret) {
		dev_err(c->dev, "cannot start the sensor: %d\n", ret);
		goto err_hw;
	}
	return 0;

err_hw:
	disable_irq(c->irq_csis);
	disable_irq(c->irq_dma);
	c->running = false;
	csis_csi_disable(c);
	csis_dma_stop(c);
	csis_phy_off(c);
err_slots:
	spin_lock_irqsave(&c->qlock, flags);
	for (i = CSIS_NUM_SLOTS; i-- > 0;)
		if (c->slot[i]) {
			list_add(&c->slot[i]->list, &c->queued);
			c->slot[i] = NULL;
		}
	spin_unlock_irqrestore(&c->qlock, flags);
	dma_free_coherent(c->dev, c->scratch_size, c->scratch, c->scratch_dma);
	c->scratch = NULL;
err_pm:
	pm_runtime_put(c->dev);
	return ret;
}

static int csis_disable_streams(struct v4l2_subdev *sd, struct v4l2_subdev_state *state,
				u32 pad, u64 streams_mask)
{
	struct csis *c = sd_to_csis(sd);
	struct media_pad *remote = media_pad_remote_pad_unique(&c->pads[CSIS_PAD_SINK]);
	unsigned long flags;
	unsigned int i;

	if (!IS_ERR(remote))
		v4l2_subdev_disable_streams(media_entity_to_v4l2_subdev(remote->entity),
					 remote->index, BIT(0));
	/* Let the frame in flight finish */
	msleep(40);

	disable_irq(c->irq_csis);
	disable_irq(c->irq_dma);
	c->running = false;
	csis_csi_disable(c);
	csis_dma_stop(c);
	csis_dma_abort(c);
	csis_phy_off(c);

	/* Whatever is still armed was never completed */
	spin_lock_irqsave(&c->qlock, flags);
	for (i = 0; i < CSIS_NUM_SLOTS; i++) {
		if (c->slot[i])
			list_add_tail(&c->slot[i]->list, &c->queued);
		c->slot[i] = NULL;
	}
	spin_unlock_irqrestore(&c->qlock, flags);

	dev_dbg(c->dev, "stopped: %lu frames, %lu dropped, %lu DMA errors, %lu receiver errors\n",
		c->n_done, c->n_dropped, c->n_errors, c->n_csis_errors);
	if (c->n_errors || c->n_csis_errors)
		dev_info(c->dev, "%lu frames, %lu dropped, %lu DMA errors, %lu receiver errors\n",
			 c->n_done, c->n_dropped, c->n_errors, c->n_csis_errors);

	dma_free_coherent(c->dev, c->scratch_size, c->scratch, c->scratch_dma);
	c->scratch = NULL;
	pm_runtime_put(c->dev);
	return 0;
}

static const struct v4l2_subdev_video_ops csis_video_ops = {
	.s_stream = v4l2_subdev_s_stream_helper,
};

static const struct v4l2_subdev_pad_ops csis_pad_ops = {
	.enum_mbus_code = csis_enum_mbus_code,
	.enum_frame_size = csis_enum_frame_size,
	.get_fmt = v4l2_subdev_get_fmt,
	.set_fmt = csis_set_fmt,
	.link_validate = v4l2_subdev_link_validate_default,
	.enable_streams = csis_enable_streams,
	.disable_streams = csis_disable_streams,
};

static const struct v4l2_subdev_ops csis_subdev_ops = {
	.video = &csis_video_ops,
	.pad = &csis_pad_ops,
};

static const struct v4l2_subdev_internal_ops csis_internal_ops = {
	.init_state = csis_init_state,
};

/* One sensor at a time on the sink pad (the tele and front cameras share a port). */
static int csis_link_setup(struct media_entity *entity, const struct media_pad *local,
			   const struct media_pad *remote, u32 flags)
{
	struct media_link *link;

	if (local->index != CSIS_PAD_SINK || !(flags & MEDIA_LNK_FL_ENABLED))
		return 0;
	list_for_each_entry(link, &entity->links, list)
		if (link->sink == local && link->source != remote &&
		    (link->flags & MEDIA_LNK_FL_ENABLED))
			return -EBUSY;
	return 0;
}

static const struct media_entity_operations csis_entity_ops = {
	.link_setup = csis_link_setup,
	.link_validate = v4l2_subdev_link_validate,
};

/* ----------------------------------------------------------- video node */

static int csis_vb2_queue_setup(struct vb2_queue *q, unsigned int *nbuffers,
				unsigned int *nplanes, unsigned int sizes[],
				struct device *alloc_devs[])
{
	struct csis *c = vb2_get_drv_priv(q);

	if (*nplanes)
		return sizes[0] < c->fmt.sizeimage ? -EINVAL : 0;
	*nplanes = 1;
	sizes[0] = c->fmt.sizeimage;
	return 0;
}

static int csis_vb2_buf_prepare(struct vb2_buffer *vb)
{
	struct csis *c = vb2_get_drv_priv(vb->vb2_queue);

	if (vb2_plane_size(vb, 0) < c->fmt.sizeimage)
		return -EINVAL;
	vb2_set_plane_payload(vb, 0, c->fmt.sizeimage);
	to_csis_buffer(to_vb2_v4l2_buffer(vb))->dma = vb2_dma_contig_plane_dma_addr(vb, 0);
	return 0;
}

static void csis_vb2_buf_queue(struct vb2_buffer *vb)
{
	struct csis *c = vb2_get_drv_priv(vb->vb2_queue);
	struct csis_buffer *buf = to_csis_buffer(to_vb2_v4l2_buffer(vb));
	unsigned long flags;

	spin_lock_irqsave(&c->qlock, flags);
	list_add_tail(&buf->list, &c->queued);
	spin_unlock_irqrestore(&c->qlock, flags);
}

static void csis_return_buffers(struct csis *c, enum vb2_buffer_state state)
{
	struct csis_buffer *buf, *tmp;
	unsigned long flags;
	LIST_HEAD(list);

	spin_lock_irqsave(&c->qlock, flags);
	list_splice_init(&c->queued, &list);
	spin_unlock_irqrestore(&c->qlock, flags);
	list_for_each_entry_safe(buf, tmp, &list, list) {
		list_del(&buf->list);
		vb2_buffer_done(&buf->vb.vb2_buf, state);
	}
}

static int csis_vb2_start_streaming(struct vb2_queue *q, unsigned int count)
{
	struct csis *c = vb2_get_drv_priv(q);
	int ret;

	ret = video_device_pipeline_start(&c->vdev, &c->vdev_pipe);
	if (ret) {
		dev_err(c->dev, "cannot start the pipeline: %d\n", ret);
		goto err_buffers;
	}
	ret = v4l2_subdev_enable_streams(&c->sd, CSIS_PAD_SRC, BIT(0));
	if (ret)
		goto err_pipeline;
	return 0;

err_pipeline:
	video_device_pipeline_stop(&c->vdev);
err_buffers:
	csis_return_buffers(c, VB2_BUF_STATE_QUEUED);
	return ret;
}

static void csis_vb2_stop_streaming(struct vb2_queue *q)
{
	struct csis *c = vb2_get_drv_priv(q);

	v4l2_subdev_disable_streams(&c->sd, CSIS_PAD_SRC, BIT(0));
	video_device_pipeline_stop(&c->vdev);
	csis_return_buffers(c, VB2_BUF_STATE_ERROR);
}

static const struct vb2_ops csis_vb2_ops = {
	.queue_setup = csis_vb2_queue_setup,
	.buf_prepare = csis_vb2_buf_prepare,
	.buf_queue = csis_vb2_buf_queue,
	.start_streaming = csis_vb2_start_streaming,
	.stop_streaming = csis_vb2_stop_streaming,
};

static void csis_try_pix(struct v4l2_pix_format *p)
{
	const struct csis_format *f = csis_find_fourcc(p->pixelformat) ?: &csis_formats[0];

	p->pixelformat = f->fourcc;
	p->width = clamp(ALIGN(p->width, CSIS_WIDTH_ALIGN), CSIS_MIN_WIDTH, CSIS_MAX_WIDTH);
	p->height = clamp_t(u32, p->height, CSIS_MIN_HEIGHT, CSIS_MAX_HEIGHT);
	p->field = V4L2_FIELD_NONE;
	p->colorspace = V4L2_COLORSPACE_RAW;
	p->ycbcr_enc = V4L2_YCBCR_ENC_601;
	p->quantization = V4L2_QUANTIZATION_FULL_RANGE;
	p->xfer_func = V4L2_XFER_FUNC_NONE;
	p->bytesperline = p->width * 2;
	p->sizeimage = p->bytesperline * p->height;
}

static int csis_querycap(struct file *file, void *priv, struct v4l2_capability *cap)
{
	struct csis *c = video_drvdata(file);

	strscpy(cap->driver, DRV_NAME, sizeof(cap->driver));
	strscpy(cap->card, "Exynos 9820 CSIS camera", sizeof(cap->card));
	snprintf(cap->bus_info, sizeof(cap->bus_info), "platform:%s", dev_name(c->dev));
	return 0;
}

static int csis_enum_fmt(struct file *file, void *priv, struct v4l2_fmtdesc *f)
{
	if (f->mbus_code) {
		const struct csis_format *fmt = csis_find_code(f->mbus_code);

		if (f->index || !fmt)
			return -EINVAL;
		f->pixelformat = fmt->fourcc;
		return 0;
	}
	if (f->index >= ARRAY_SIZE(csis_formats))
		return -EINVAL;
	f->pixelformat = csis_formats[f->index].fourcc;
	return 0;
}

static int csis_enum_framesizes(struct file *file, void *priv,
				struct v4l2_frmsizeenum *fsize)
{
	if (fsize->index || !csis_find_fourcc(fsize->pixel_format))
		return -EINVAL;
	fsize->type = V4L2_FRMSIZE_TYPE_STEPWISE;
	fsize->stepwise.min_width = CSIS_MIN_WIDTH;
	fsize->stepwise.max_width = CSIS_MAX_WIDTH;
	fsize->stepwise.step_width = CSIS_WIDTH_ALIGN;
	fsize->stepwise.min_height = CSIS_MIN_HEIGHT;
	fsize->stepwise.max_height = CSIS_MAX_HEIGHT;
	fsize->stepwise.step_height = 1;
	return 0;
}

static int csis_g_fmt(struct file *file, void *priv, struct v4l2_format *f)
{
	f->fmt.pix = ((struct csis *)video_drvdata(file))->fmt;
	return 0;
}

static int csis_try_fmt(struct file *file, void *priv, struct v4l2_format *f)
{
	csis_try_pix(&f->fmt.pix);
	return 0;
}

static int csis_s_fmt(struct file *file, void *priv, struct v4l2_format *f)
{
	struct csis *c = video_drvdata(file);

	if (vb2_is_busy(&c->queue))
		return -EBUSY;
	csis_try_pix(&f->fmt.pix);
	c->fmt = f->fmt.pix;
	return 0;
}

static const struct v4l2_ioctl_ops csis_ioctl_ops = {
	.vidioc_querycap = csis_querycap,
	.vidioc_enum_fmt_vid_cap = csis_enum_fmt,
	.vidioc_enum_framesizes = csis_enum_framesizes,
	.vidioc_g_fmt_vid_cap = csis_g_fmt,
	.vidioc_s_fmt_vid_cap = csis_s_fmt,
	.vidioc_try_fmt_vid_cap = csis_try_fmt,
	.vidioc_reqbufs = vb2_ioctl_reqbufs,
	.vidioc_create_bufs = vb2_ioctl_create_bufs,
	.vidioc_prepare_buf = vb2_ioctl_prepare_buf,
	.vidioc_querybuf = vb2_ioctl_querybuf,
	.vidioc_qbuf = vb2_ioctl_qbuf,
	.vidioc_dqbuf = vb2_ioctl_dqbuf,
	.vidioc_expbuf = vb2_ioctl_expbuf,
	.vidioc_streamon = vb2_ioctl_streamon,
	.vidioc_streamoff = vb2_ioctl_streamoff,
};

static const struct v4l2_file_operations csis_fops = {
	.owner = THIS_MODULE,
	.open = v4l2_fh_open,
	.release = vb2_fop_release,
	.poll = vb2_fop_poll,
	.unlocked_ioctl = video_ioctl2,
	.mmap = vb2_fop_mmap,
};

static int csis_video_link_validate(struct media_link *link)
{
	struct video_device *vdev = media_entity_to_video_device(link->sink->entity);
	struct v4l2_subdev *sd = media_entity_to_v4l2_subdev(link->source->entity);
	struct csis *c = video_get_drvdata(vdev);
	const struct v4l2_mbus_framefmt *f;
	struct v4l2_subdev_state *state;
	struct v4l2_mbus_framefmt fmt;

	state = v4l2_subdev_lock_and_get_active_state(sd);
	f = v4l2_subdev_state_get_format(state, link->source->index);
	fmt = *f;
	v4l2_subdev_unlock_state(state);

	if (fmt.width != c->fmt.width || fmt.height != c->fmt.height ||
	    !csis_find_code(fmt.code) ||
	    csis_find_code(fmt.code)->fourcc != c->fmt.pixelformat) {
		dev_dbg(c->dev, "video format %ux%u %p4cc does not match the pipeline %ux%u code %#x\n",
			c->fmt.width, c->fmt.height, &c->fmt.pixelformat,
			fmt.width, fmt.height, fmt.code);
		return -EPIPE;
	}
	return 0;
}

static const struct media_entity_operations csis_video_entity_ops = {
	.link_validate = csis_video_link_validate,
};

/* ------------------------------------------------------ registration */

static void csis_unregister(struct csis *c)
{
	if (!c->registered)
		return;
	c->registered = false;
	media_device_unregister(&c->mdev);
}

static int csis_notify_bound(struct v4l2_async_notifier *n, struct v4l2_subdev *sd,
			     struct v4l2_async_connection *asc)
{
	struct csis *c = container_of(n, struct csis, notifier);
	int ret;

	/*
	 * Several sensors can share the port (the tele and front cameras sit
	 * behind a mux): their links are selectable, never enabled by default,
	 * and csis_link_setup() allows one at a time. A lone sensor is wired
	 * permanently.
	 */
	ret = v4l2_create_fwnode_links_to_pad(sd, &c->pads[CSIS_PAD_SINK],
					      c->nr_sensors == 1 ?
					      MEDIA_LNK_FL_ENABLED | MEDIA_LNK_FL_IMMUTABLE : 0);
	if (ret)
		return ret;
	return 0;
}

static void csis_notify_unbind(struct v4l2_async_notifier *n, struct v4l2_subdev *sd,
			       struct v4l2_async_connection *asc)
{
	struct csis *c = container_of(n, struct csis, notifier);

	csis_unregister(c);
}

static int csis_notify_complete(struct v4l2_async_notifier *n)
{
	struct csis *c = container_of(n, struct csis, notifier);
	int ret;

	ret = v4l2_device_register_subdev_nodes(&c->v4l2_dev);
	if (ret)
		return ret;
	ret = media_device_register(&c->mdev);
	if (ret)
		return ret;
	c->registered = true;
	dev_info(c->dev, "camera ready: %s\n", video_device_node_name(&c->vdev));
	return 0;
}

static const struct v4l2_async_notifier_operations csis_notify_ops = {
	.bound = csis_notify_bound,
	.unbind = csis_notify_unbind,
	.complete = csis_notify_complete,
};

static int csis_parse_dt(struct csis *c)
{
	struct fwnode_handle *fwnode;
	int ret = 0;

	c->lanes = 0;
	fwnode_graph_for_each_endpoint(dev_fwnode(c->dev), fwnode) {
		struct v4l2_fwnode_endpoint ep = { .bus_type = V4L2_MBUS_CSI2_DPHY };

		if (!c->nr_sensors)
			v4l2_async_nf_init(&c->notifier, &c->v4l2_dev);
		ret = v4l2_fwnode_endpoint_parse(fwnode, &ep);
		if (ret) {
			dev_err_probe(c->dev, ret, "cannot parse the endpoint\n");
			break;
		}
		if (ep.bus.mipi_csi2.num_data_lanes < 1 || ep.bus.mipi_csi2.num_data_lanes > 4 ||
		    (c->lanes && c->lanes != ep.bus.mipi_csi2.num_data_lanes)) {
			ret = dev_err_probe(c->dev, -EINVAL,
					    "1..4 data lanes, the same for all sensors\n");
			break;
		}
		c->lanes = ep.bus.mipi_csi2.num_data_lanes;
		if (IS_ERR(v4l2_async_nf_add_fwnode_remote(&c->notifier, fwnode,
							    struct v4l2_async_connection))) {
			ret = -ENOMEM;
			break;
		}
		c->nr_sensors++;
	}
	if (!ret && !c->nr_sensors)
		return dev_err_probe(c->dev, -EINVAL, "no sensor endpoint in the device tree\n");
	if (ret) {
		fwnode_handle_put(fwnode);
		if (c->nr_sensors)
			v4l2_async_nf_cleanup(&c->notifier);
		return ret;
	}
	c->notifier.ops = &csis_notify_ops;
	return 0;
}

static void __iomem *csis_map(struct platform_device *pdev, const char *name)
{
	return devm_platform_ioremap_resource_byname(pdev, name);
}

/* The DMA top block and the PHY reset register are shared by all channels. */
static void __iomem *csis_map_shared(struct platform_device *pdev, const char *name)
{
	struct resource *res = platform_get_resource_byname(pdev, IORESOURCE_MEM, name);

	if (!res)
		return IOMEM_ERR_PTR(-ENODEV);
	return devm_ioremap(&pdev->dev, res->start, resource_size(res)) ?:
	       IOMEM_ERR_PTR(-ENOMEM);
}

static int csis_probe(struct platform_device *pdev)
{
	static const char * const clk_names[C_NUM] = { "csis", "dma", "mmu", "bus" };
	struct device *dev = &pdev->dev;
	struct csis *c;
	int ret, i;

	c = devm_kzalloc(dev, sizeof(*c), GFP_KERNEL);
	if (!c)
		return -ENOMEM;
	c->dev = dev;
	platform_set_drvdata(pdev, c);
	mutex_init(&c->lock);
	spin_lock_init(&c->qlock);
	INIT_LIST_HEAD(&c->queued);

	c->regs = csis_map(pdev, "csis");
	c->top = csis_map_shared(pdev, "dma-top");
	c->rst = csis_map_shared(pdev, "phy-reset");
	c->phy = csis_map(pdev, "phy");
	c->dma = csis_map(pdev, "dma");
	if (IS_ERR(c->regs) || IS_ERR(c->top) || IS_ERR(c->rst) || IS_ERR(c->phy) ||
	    IS_ERR(c->dma))
		return dev_err_probe(dev, -ENODEV, "register windows\n");
	if (of_property_read_u32(dev->of_node, "samsung,pmu-phy-offset", &c->pmu_phy_offset) ||
	    of_property_read_u32(dev->of_node, "samsung,phy-reset-bit", &c->phy_reset_bit) ||
	    c->phy_reset_bit > 31)
		return dev_err_probe(dev, -EINVAL,
				     "samsung,pmu-phy-offset / samsung,phy-reset-bit missing\n");
	c->phy_dc_combo = of_property_read_bool(dev->of_node, "samsung,phy-dc-combo");
	c->pdaf_vc1 = of_property_read_bool(dev->of_node, "samsung,pdaf-vc1");
	c->pmu = syscon_regmap_lookup_by_phandle(dev->of_node, "samsung,pmu-syscon");
	if (IS_ERR(c->pmu))
		return dev_err_probe(dev, PTR_ERR(c->pmu), "PMU syscon\n");
	for (i = 0; i < C_NUM; i++)
		c->clks[i].id = clk_names[i];
	ret = devm_clk_bulk_get(dev, C_NUM, c->clks);
	if (ret)
		return dev_err_probe(dev, ret, "clocks\n");

	ret = dma_set_mask_and_coherent(dev, DMA_BIT_MASK(32));
	if (ret)
		return ret;
	dma_set_max_seg_size(dev, UINT_MAX);

	c->irq_csis = platform_get_irq_byname(pdev, "csis");
	c->irq_dma = platform_get_irq_byname(pdev, "dma");
	if (c->irq_csis < 0 || c->irq_dma < 0)
		return dev_err_probe(dev, -ENODEV, "interrupts\n");
	/* Both stay off until the hardware is set up: the block is unclocked */
	ret = devm_request_irq(dev, c->irq_csis, csis_csi_irq, IRQF_NO_AUTOEN, DRV_NAME "-csis", c);
	if (ret)
		return ret;
	ret = devm_request_irq(dev, c->irq_dma, csis_dma_irq, IRQF_NO_AUTOEN, DRV_NAME "-dma", c);
	if (ret)
		return ret;

	ret = devm_pm_runtime_enable(dev);
	if (ret)
		return ret;

	/* Media device and V4L2 device */
	c->mdev.dev = dev;
	strscpy(c->mdev.model, "Exynos 9820 camera", sizeof(c->mdev.model));
	snprintf(c->mdev.bus_info, sizeof(c->mdev.bus_info), "platform:%s", dev_name(dev));
	media_device_init(&c->mdev);
	c->v4l2_dev.mdev = &c->mdev;
	ret = v4l2_device_register(dev, &c->v4l2_dev);
	if (ret)
		goto err_mdev;

	/* CSIS subdevice */
	v4l2_subdev_init(&c->sd, &csis_subdev_ops);
	c->sd.internal_ops = &csis_internal_ops;
	c->sd.owner = THIS_MODULE;
	c->sd.dev = dev;
	c->sd.flags |= V4L2_SUBDEV_FL_HAS_DEVNODE;
	c->sd.entity.function = MEDIA_ENT_F_VID_IF_BRIDGE;
	c->sd.entity.ops = &csis_entity_ops;
	snprintf(c->sd.name, sizeof(c->sd.name), "csis-%s", dev_name(dev));
	v4l2_set_subdevdata(&c->sd, c);
	c->pads[CSIS_PAD_SINK].flags = MEDIA_PAD_FL_SINK | MEDIA_PAD_FL_MUST_CONNECT;
	c->pads[CSIS_PAD_SRC].flags = MEDIA_PAD_FL_SOURCE | MEDIA_PAD_FL_MUST_CONNECT;
	ret = media_entity_pads_init(&c->sd.entity, CSIS_NUM_PADS, c->pads);
	if (ret)
		goto err_v4l2;
	ret = v4l2_subdev_init_finalize(&c->sd);
	if (ret)
		goto err_entity;

	/* Capture node */
	c->fmt.width = 2304;
	c->fmt.height = 1728;
	c->fmt.pixelformat = V4L2_PIX_FMT_SGRBG10;
	csis_try_pix(&c->fmt);

	c->queue.type = V4L2_BUF_TYPE_VIDEO_CAPTURE;
	c->queue.io_modes = VB2_MMAP | VB2_DMABUF;
	c->queue.drv_priv = c;
	c->queue.buf_struct_size = sizeof(struct csis_buffer);
	c->queue.ops = &csis_vb2_ops;
	c->queue.mem_ops = &vb2_dma_contig_memops;
	c->queue.timestamp_flags = V4L2_BUF_FLAG_TIMESTAMP_MONOTONIC | V4L2_BUF_FLAG_TSTAMP_SRC_SOE;
	c->queue.lock = &c->lock;
	c->queue.dev = dev;
	c->queue.allow_cache_hints = 1;
	c->queue.min_queued_buffers = 1;
	c->queue.min_reqbufs_allocation = 4;
	ret = vb2_queue_init(&c->queue);
	if (ret)
		goto err_subdev;

	strscpy(c->vdev.name, "exynos9820-csis capture", sizeof(c->vdev.name));
	c->vdev.fops = &csis_fops;
	c->vdev.ioctl_ops = &csis_ioctl_ops;
	c->vdev.release = video_device_release_empty;
	c->vdev.v4l2_dev = &c->v4l2_dev;
	c->vdev.queue = &c->queue;
	c->vdev.lock = &c->lock;
	c->vdev.vfl_dir = VFL_DIR_RX;
	c->vdev.device_caps = V4L2_CAP_VIDEO_CAPTURE | V4L2_CAP_STREAMING | V4L2_CAP_IO_MC;
	c->vdev.entity.ops = &csis_video_entity_ops;
	c->vdev_pad.flags = MEDIA_PAD_FL_SINK | MEDIA_PAD_FL_MUST_CONNECT;
	ret = media_entity_pads_init(&c->vdev.entity, 1, &c->vdev_pad);
	if (ret)
		goto err_subdev;
	video_set_drvdata(&c->vdev, c);

	/*
	 * Entities have to be registered with the media device before links
	 * can be created to them, so both are registered now; the media device
	 * node itself appears once the sensor is bound.
	 */
	ret = v4l2_device_register_subdev(&c->v4l2_dev, &c->sd);
	if (ret)
		goto err_vdev_entity;
	ret = video_register_device(&c->vdev, VFL_TYPE_VIDEO, -1);
	if (ret)
		goto err_reg_sd;
	ret = media_create_pad_link(&c->sd.entity, CSIS_PAD_SRC, &c->vdev.entity, 0,
				    MEDIA_LNK_FL_ENABLED | MEDIA_LNK_FL_IMMUTABLE);
	if (ret)
		goto err_reg_video;

	ret = csis_parse_dt(c);
	if (ret)
		goto err_reg_video;
	ret = v4l2_async_nf_register(&c->notifier);
	if (ret) {
		v4l2_async_nf_cleanup(&c->notifier);
		goto err_reg_video;
	}
	dev_info(dev, "waiting for the sensor (needs s10-isppre-hold.ko to keep the ISPPRE domain on)\n");
	return 0;

err_reg_video:
	video_unregister_device(&c->vdev);
err_reg_sd:
	v4l2_device_unregister_subdev(&c->sd);
err_vdev_entity:
	media_entity_cleanup(&c->vdev.entity);
err_subdev:
	v4l2_subdev_cleanup(&c->sd);
err_entity:
	media_entity_cleanup(&c->sd.entity);
err_v4l2:
	v4l2_device_unregister(&c->v4l2_dev);
err_mdev:
	media_device_cleanup(&c->mdev);
	return ret;
}

static void csis_remove(struct platform_device *pdev)
{
	struct csis *c = platform_get_drvdata(pdev);

	v4l2_async_nf_unregister(&c->notifier);
	csis_unregister(c);
	video_unregister_device(&c->vdev);
	v4l2_device_unregister_subdev(&c->sd);
	v4l2_async_nf_cleanup(&c->notifier);
	media_entity_cleanup(&c->vdev.entity);
	v4l2_subdev_cleanup(&c->sd);
	media_entity_cleanup(&c->sd.entity);
	v4l2_device_unregister(&c->v4l2_dev);
	media_device_cleanup(&c->mdev);
}

static const struct dev_pm_ops csis_pm_ops = {
	SET_RUNTIME_PM_OPS(csis_runtime_suspend, csis_runtime_resume, NULL)
};

static const struct of_device_id csis_of_match[] = {
	{ .compatible = "samsung,exynos9820-csis" },
	{ }
};
MODULE_DEVICE_TABLE(of, csis_of_match);

static struct platform_driver csis_driver = {
	.probe = csis_probe,
	.remove = csis_remove,
	.driver = {
		.name = DRV_NAME,
		.of_match_table = csis_of_match,
		.pm = &csis_pm_ops,
	},
};
module_platform_driver(csis_driver);

MODULE_DESCRIPTION("Exynos 9820 MIPI CSI-2 receiver and write DMA");
MODULE_LICENSE("GPL");
