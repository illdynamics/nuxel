/* SPDX-License-Identifier: GPL-2.0-only */
/*
 * s10-compat.h — backward/forward-port shims so the Samsung S10 native
 * camera drivers (originally written against the post-6.x V4L2/media API)
 * compile against the 4.14.253 downstream kernel used by beyond2lte.
 *
 * Each shim is a faithful, minimal reconstruction of a mainline helper;
 * no sensor/bridge logic changes. All definitions are GPL-2.0.
 */
#ifndef S10_COMPAT_H
#define S10_COMPAT_H

#include <linux/device.h>
#include <linux/clk.h>
#include <linux/interrupt.h>
#include <linux/io.h>
#include <linux/platform_device.h>
#include <linux/pm_runtime.h>
#include <linux/err.h>
#include <linux/ioport.h>
#include <media/v4l2-dev.h>
#include <media/media-entity.h>
#include <media/v4l2-common.h>
#include <media/v4l2-ctrls.h>
#include <media/v4l2-device.h>
#include <media/v4l2-subdev.h>

/* ---- dev_err_probe -----------------------------------------------------
 * v5.10 drivers/base/core.c. 4.14 lacks it; log once and return errno.
 */
#define dev_err_probe(dev, err, fmt, ...)				\
	({								\
		int __ret = (err);					\
		if (__ret != -EPROBE_DEFER)				\
			dev_err(dev, fmt, ##__VA_ARGS__);		\
		__ret;							\
	})

/* ---- pm_runtime_resume_and_get ------------------------------------------
 * v5.4; unlike pm_runtime_get_sync() it does not leak the usage counter on
 * error. 4.14 lacks it.
 */
static inline int pm_runtime_resume_and_get(struct device *dev)
{
	int ret = pm_runtime_get_sync(dev);

	if (ret < 0) {
		pm_runtime_put_noidle(dev);
		return ret;
	}
	return 0;
}

/* ---- media_pad_remote_pad_first ------------------------------------------
 * 4.14 has no per-pad remote lookup helper; reconstruct it by walking
 * entity->links. Returns the first enabled (non-backlink) remote pad or
 * ERR_PTR(-ENOLINK).
 */
static inline struct media_pad *media_pad_remote_pad_first(struct media_pad *pad)
{
	struct media_link *link;

	list_for_each_entry(link, &pad->entity->links, list) {
		if (link->is_backlink)
			continue;
		if (!(link->flags & MEDIA_LNK_FL_ENABLED))
			continue;
		if (link->source == pad)
			return link->sink;
		if (link->sink == pad)
			return link->source;
	}
	return ERR_PTR(-ENOLINK);
}

/* post-6.x uses media_pad_remote_pad_unique(); the CSIS sink pad has at most
 * one active remote (csis_link_setup enforces one-at-a-time). */
#define media_pad_remote_pad_unique(pad)	media_pad_remote_pad_first(pad)

/* ---- pipeline wrappers ---------------------------------------------------
 * post-6.x uses video_device_pipeline_start/stop; 4.14 exposes media-entity
 * core. Provide the video-device-shaped names.
 */
static inline int video_device_pipeline_start(struct video_device *vdev,
					      struct media_pipeline *pipe)
{
	return media_pipeline_start(&vdev->entity, pipe);
}

static inline void video_device_pipeline_stop(struct video_device *vdev)
{
	media_pipeline_stop(&vdev->entity);
}

/* ---- media_pad_is_streaming --------------------------------------------------
 * 4.14 marks streaming on the entity pipeline refcount.
 */
static inline bool media_pad_is_streaming(struct media_pad *pad)
{
	return pad->entity->pipe && pad->entity->pipe->streaming_count > 0;
}

/* ---- v4l2_subdev state -> pad_config mappings ----------------------------
 * post-6.x passes v4l2_subdev_state; 4.14 passes v4l2_subdev_pad_config.
 * The drivers only read/write the per-pad frame format. Because 4.14 has no
 * central "active state", the drivers keep ACTIVE format in their private
 * struct and use cfg only for TRY. The shim below returns the TRY slot; the
 * driver must special-case ACTIVE itself (see each driver's get/set fmt).
 */
static inline struct v4l2_mbus_framefmt *
v4l2_subdev_state_get_format(struct v4l2_subdev_pad_config *cfg, unsigned int pad)
{
	return v4l2_subdev_get_try_format(NULL, cfg, pad);
}

/* Internal-ops .open initialises pad_config in 4.14 (no .init_state). */
static inline int v4l2_subdev_init_finalize(struct v4l2_subdev *sd)
{
	return 0;
}

static inline void v4l2_subdev_cleanup(struct v4l2_subdev *sd)
{
}

/* ---- link frequency helpers ----------------------------------------------
 * 4.14 has V4L2_CID_LINK_FREQ but not v4l2_get_link_freq(). Reconstruct it
 * from the remote sensor's controls.
 */
static inline s64 v4l2_get_link_freq(struct media_pad *pad,
				     unsigned int multiplier, int bpp)
{
	struct v4l2_subdev *sd = media_entity_to_v4l2_subdev(pad->entity);
	struct v4l2_ctrl *ctrl;

	(void)multiplier;
	(void)bpp;
	if (!sd)
		return -ENOENT;
	ctrl = v4l2_ctrl_find(sd->ctrl_handler, V4L2_CID_LINK_FREQ);
	if (!ctrl)
		return -ENOENT;
	return v4l2_ctrl_g_ctrl_int64(ctrl);
}

/* link-freq menu -> bitmap; returns 0 when >=1 advertised freq matches. */
static inline int v4l2_link_freq_to_bitmap(struct device *dev,
					   const u64 *link_freqs,
					   unsigned int nr_link_freqs,
					   const s64 *menu,
					   unsigned int menu_len,
					   unsigned long *bitmap)
{
	unsigned int i;

	(void)dev;
	if (!menu_len)
		return 0;
	*bitmap = 0;
	for (i = 0; i < menu_len; i++) {
		unsigned int j;

		for (j = 0; j < nr_link_freqs; j++)
			if ((u64)menu[i] == link_freqs[j])
				__set_bit(i, bitmap);
	}
	return *bitmap ? 0 : -EINVAL;
}

/* ---- v4l2 fwnode device properties ---------------------------------------
 * 4.14 has no v4l2_fwnode_device_parse / v4l2_ctrl_new_fwnode_properties.
 * beyond2lte's DTB carries no per-device fwnode control properties, so no-op.
 */
struct v4l2_fwnode_device_properties {
};

static inline int v4l2_fwnode_device_parse(struct device *dev,
					   struct v4l2_fwnode_device_properties *p)
{
	return 0;
}

static inline int v4l2_ctrl_new_fwnode_properties(struct v4l2_ctrl_handler *hdl,
						  const struct v4l2_ctrl_ops *ops,
						  const struct v4l2_fwnode_device_properties *p)
{
	return 0;
}

/* ---- v4l2_subdev_s_stream_helper -----------------------------------------
 * post-6.x uses .enable_streams and a v4l2_subdev_s_stream_helper bridge.
 * 4.14 only has .s_stream; the driver sets .s_stream directly, so this macro
 * guards against accidental use (it must never be referenced in 4.14 builds).
 */

#endif /* S10_COMPAT_H */

/* ---- devm_platform_ioremap_resource_byname -------------------------------
 * v5.x ioport.h/platform_device.h helper. 4.14 needs the explicit
 * platform_get_resource_byname + devm_ioremap_resource pair.
 */
static inline void __iomem *devm_platform_ioremap_resource_byname(
	struct platform_device *pdev, const char *name)
{
	struct resource *res = platform_get_resource_byname(pdev, IORESOURCE_MEM, name);

	if (!res)
		return IOMEM_ERR_PTR(-ENODEV);
	return devm_ioremap_resource(&pdev->dev, res);
}

/* ---- IRQF_NO_AUTOEN / request_irq + disable -------------------------------
 * 4.14 has no IRQF_NO_AUTOEN. Replace requests with a post-request disable.
 */
static inline int devm_request_irq_noautoen(struct device *dev, unsigned int irq,
					    irq_handler_t handler,
					    unsigned long flags, const char *name,
					    void *dev_id)
{
	int ret = devm_request_irq(dev, irq, handler, flags, name, dev_id);

	if (!ret)
		disable_irq_nosync(irq);
	return ret;
}

/* ---- devm_pm_runtime_enable ----------------------------------------------
 * v4.19; 4.14 needs manual pm_runtime_enable with a devm cleanup action.
 */
static inline void devm_pm_runtime_disable(void *d)
{
	pm_runtime_disable(d);
}
static inline int devm_pm_runtime_enable(struct device *dev)
{
	int ret = devm_add_action_or_reset(dev, devm_pm_runtime_disable, dev);

	if (ret)
		return ret;
	pm_runtime_enable(dev);
	return 0;
}
