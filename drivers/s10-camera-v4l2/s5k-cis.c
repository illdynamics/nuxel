// SPDX-License-Identifier: GPL-2.0-only
/*
 * Samsung S5K image sensors of the Galaxy S10 (SM-G973F):
 *
 *   samsung,s5k3p9   ultra-wide rear camera, 2304x1728 @ 60 fps
 *   samsung,s5k3m3   tele rear camera, 4032x3024 and 2016x1512 @ 30 fps
 *   samsung,s5k3j1   front camera, 3648x2736 and 1824x1368 @ 30 fps
 *
 * All of them speak the same 16 bit register protocol, output RAW10 on four
 * D-PHY lanes and run from a 26 MHz master clock. The register tables are
 * externally supplied runtime data; they are only valid for the sensor
 * revisions listed in the model descriptions. No sensor program is embedded.
 */
#include <crypto/sha2.h>
#include <linux/firmware.h>
#include <linux/hex.h>
#include <linux/slab.h>
#include <linux/clk.h>
#include <linux/delay.h>
#include <linux/gpio/consumer.h>
#include <linux/i2c.h>
#include <linux/module.h>
#include <linux/mux/consumer.h>
#include <linux/of.h>
#include <linux/pinctrl/consumer.h>
#include <linux/pm_runtime.h>
#include <linux/regulator/consumer.h>
#include <linux/unaligned.h>
#include <media/v4l2-ctrls.h>
#include <media/v4l2-device.h>
#include <media/v4l2-fwnode.h>
#include <media/v4l2-subdev.h>

#define S5K_REG_MODEL		0x0000
#define S5K_REG_REVISION	0x0002
#define S5K_REG_FRAME_COUNT	0x0005
#define S5K_REG_MODE_SELECT	0x0100
#define S5K_REG_COARSE_INTEG	0x0202
#define S5K_REG_ANALOG_GAIN	0x0204
#define S5K_REG_FRAME_LENGTH	0x0340
#define S5K_REG_PAGE		0xfcfc

#define S5K_XCLK_FREQ		26000000
#define S5K_GAIN_MIN		0x20	/* 1.0x */
#define S5K_GAIN_MAX		0x200

#define S5K_DELAY		0xffff
#define S5K_BURST		0xfffe

struct s5k_reg {
	u16 reg;
	u16 val;
	u8 len;
};

struct s5k_burst {
	const u8 *data;
	size_t len;
};

struct s5k_mode {
	u32 width, height;
	u32 line_length;	/* pixel clocks */
	u32 frame_length;	/* lines, default */
	s64 pixel_rate;
	s64 link_freq;
	struct v4l2_rect crop;	/* region of the pixel array that is read */
	const struct s5k_reg *regs;
	unsigned int num_regs;
};

struct s5k_model {
	const char *name;
	const char *firmware_name, *firmware_sha256;
	bool has_master;
	u16 model_id;		/* 0: not known yet, only logged */
	u16 revision;
	u32 native_width, native_height;
	u32 mbus_code;
	u8 orientation;		/* image_orientation (0x0101): bit 0 H, bit 1 V flip */
	const char * const *supplies;
	unsigned int num_supplies;
	int mux_state;		/* sub-camera MIPI mux position, -1: none */
	bool reset_before_clk;
	unsigned int exposure_min, exposure_margin;

	const struct s5k_reg *global;
	unsigned int num_global;
	const struct s5k_reg *master;	/* applied after the mode, may be NULL */
	unsigned int num_master;
	const struct s5k_burst *bursts;
	unsigned int num_bursts;
	const struct s5k_mode *modes;
	unsigned int num_modes;
};

#include "s5k-fw.h"
#include "s5k-fw-manifest.h"

/* Plasma Camera showed red/blue exchanged on all three rear cameras when they
 * were advertised as GBRG. Reporting GRBG fixes the colours on all three in
 * the live application (verified on-device 2026-10-23). This changes the V4L2
 * media-bus CFA metadata used by libcamera's software ISP; sensor register
 * programming and the S5K2L4's physical orientation are unchanged. Earlier
 * raw-frame analysis classified the CFA as GBRG, so keep the raw capture
 * distinction in mind if adding another pipeline or hardware ISP.
 */
#define S5K_MBUS_CODE		MEDIA_BUS_FMT_SGRBG10_1X10

static const char * const s5k3p9_supplies[] = {
	"pre", "avdd", "dvdd", "iovdd", "vtio",
};
static const char * const s5k3m3_supplies[] = {
	"pre", "avdd", "dvdd", "iovdd",
};
static const char * const s5k3j1_supplies[] = {
	"pre", "avdd", "iovdd", "dvdd",
};
/* Samsung's S5K2L4 NORMAL/ON order: retention, analog 2.8/2.4 V, core, I/O, VDDQ */
static const char * const s5k2l4_supplies[] = {
	"retention", "avdd28", "avdd24", "core", "iovdd", "vddq",
};

#define MODE(_w, _h, _llp, _fll, _pclk, _link, _cx, _cy, _cw, _ch) { \
	.width = _w, .height = _h, .line_length = _llp, .frame_length = _fll, \
	.pixel_rate = _pclk, .link_freq = _link, \
	.crop = { .left = _cx, .top = _cy, .width = _cw, .height = _ch }, \
}

static const struct s5k_mode s5k3p9_modes[] = {
	/* 26 MHz / 6 * 226 * 4 / 7 from the PLL registers of the mode table */
	MODE(2304, 1728, 5088, 1832, 559619048, 1027000000,
	     0, 0, 4608, 3456),
};

/* pclk = 481 MHz, 1196 Mbit/s per lane */
static const struct s5k_mode s5k3m3_modes[] = {
	MODE(4032, 3024, 4712, 3400, 481000000, 598000000,
	     96, 56, 4032, 3024),
	MODE(2016, 1512, 9768, 1639, 481000000, 598000000,
	     96, 56, 4032, 3024),
};

/* pclk = 4 * ~201.9 MHz, 1807 Mbit/s per lane */
static const struct s5k_mode s5k3j1_modes[] = {
	MODE(3648, 2736, 9384, 2864, 807720000, 903500000,
	     164, 0, 3648, 2736),
	MODE(1824, 1368, 18752, 1431, 806000000, 903500000,
	     164, 0, 3648, 2736),
};

/*
 * S5K2L4: Samsung's pllinfo pclk is 1080.444 MHz with line_length_pck 0x0b20 and
 * frame_length_lines 0x3160 (30.0 fps). The coarse integration register counts
 * in the same frame-length units; the line length is given in pixel units
 * (x4, as the 3-stack reads four pixels per clock) so that it covers the width.
 * 4032x3024 runs at 1846 Mbit/s per lane (Samsung's 923 MHz MIPI variant, see the
 * table generator), 2016x1512 at 1352 Mbit/s.
 */
static const struct s5k_mode s5k2l4_modes[] = {
	MODE(4032, 3024, 11392, 12640, 4321776000LL, 923000000,
	     0, 0, 4032, 3024),
	MODE(2016, 1512, 5696, 25280, 4321776000LL, 676000000,
	     0, 0, 4032, 3024),
};

static const struct s5k_model s5k3p9_model = {
	.name = "s5k3p9",
	.firmware_name = "samsung/s10/s5k3p9.s5k",
	.firmware_sha256 = S5K3P9_FW_SHA256,
	.has_master = true,
	.model_id = 0x3109, .revision = 0xa101,
	.native_width = 4608, .native_height = 3456,
	.mbus_code = S5K_MBUS_CODE,
	.supplies = s5k3p9_supplies, .num_supplies = ARRAY_SIZE(s5k3p9_supplies),
	.mux_state = -1,
	.reset_before_clk = true,
	.exposure_min = 7, .exposure_margin = 8,
	.modes = s5k3p9_modes, .num_modes = ARRAY_SIZE(s5k3p9_modes),
};

static const struct s5k_model s5k3m3_model = {
	.name = "s5k3m3",
	.firmware_name = "samsung/s10/s5k3m3.s5k",
	.firmware_sha256 = S5K3M3_FW_SHA256,
	.has_master = false,
	.model_id = 0x30d3, .revision = 0xa301,
	.native_width = 4208, .native_height = 3120,
	.mbus_code = S5K_MBUS_CODE,
	.supplies = s5k3m3_supplies, .num_supplies = ARRAY_SIZE(s5k3m3_supplies),
	.mux_state = 1,
	.reset_before_clk = false,
	.exposure_min = 7, .exposure_margin = 28,
	.modes = s5k3m3_modes, .num_modes = ARRAY_SIZE(s5k3m3_modes),
};

static const struct s5k_model s5k3j1_model = {
	.name = "s5k3j1",
	.firmware_name = "samsung/s10/s5k3j1.s5k",
	.firmware_sha256 = S5K3J1_FW_SHA256,
	.has_master = true,
	.model_id = 0x30a1, .revision = 0xa101,
	.native_width = 3976, .native_height = 2736,
	.mbus_code = S5K_MBUS_CODE,
	.supplies = s5k3j1_supplies, .num_supplies = ARRAY_SIZE(s5k3j1_supplies),
	.mux_state = 0,
	.reset_before_clk = true,
	.exposure_min = 2, .exposure_margin = 4,
	.modes = s5k3j1_modes, .num_modes = ARRAY_SIZE(s5k3j1_modes),
};

/* Main back camera: MCLK first, then reset (Samsung's 2L4 pin table) */
static const struct s5k_model s5k2l4_model = {
	.name = "s5k2l4",
	.firmware_name = "samsung/s10/s5k2l4.s5k",
	.firmware_sha256 = S5K2L4_FW_SHA256,
	.has_master = false,
	.model_id = 0x20c4, .revision = 0xa102,
	.native_width = 4032, .native_height = 3024,
	.mbus_code = S5K_MBUS_CODE,
	/* Mounted 180 degrees from the 3P9/3M3: flip so all back cameras read out alike */
	.orientation = 0x03,
	.supplies = s5k2l4_supplies, .num_supplies = ARRAY_SIZE(s5k2l4_supplies),
	.mux_state = -1,
	.reset_before_clk = false,
	.exposure_min = 16, .exposure_margin = 48,
	.modes = s5k2l4_modes, .num_modes = ARRAY_SIZE(s5k2l4_modes),
};

struct s5k {
	struct v4l2_subdev sd;
	struct media_pad pad;
	struct i2c_client *client;
	const struct s5k_model *model;

	struct regulator_bulk_data *supplies;
	unsigned int enabled;
	struct mux_control *mux;
	bool mux_selected;
	struct pinctrl *pins;
	struct pinctrl_state *pins_idle, *pins_active;
	struct gpio_desc *reset;
	struct clk *xclk;

	struct v4l2_ctrl_handler ctrl_handler;
	struct v4l2_ctrl *link_freq;
	struct v4l2_ctrl *pixel_rate;
	struct v4l2_ctrl *hblank;
	struct v4l2_ctrl *vblank;
	struct v4l2_ctrl *exposure;
	struct v4l2_ctrl *gain;
	s64 *link_freq_menu;
	unsigned int num_link_freqs;

	const struct s5k_mode *mode;
};

static inline struct s5k *to_s5k(struct v4l2_subdev *sd)
{
	return container_of(sd, struct s5k, sd);
}

/* ------------------------------------------------------------------ I2C */

static int s5k_read(struct s5k *s, u16 reg, void *data, int len)
{
	u8 address[] = { reg >> 8, reg & 0xff };
	struct i2c_msg msgs[] = {
		{ .addr = s->client->addr, .len = 2, .buf = address },
		{ .addr = s->client->addr, .flags = I2C_M_RD, .len = len,
		  .buf = data },
	};
	int ret = i2c_transfer(s->client->adapter, msgs, ARRAY_SIZE(msgs));

	return ret == ARRAY_SIZE(msgs) ? 0 : ret < 0 ? ret : -EIO;
}

static int s5k_read16(struct s5k *s, u16 reg, u16 *value)
{
	u8 data[2];
	int ret = s5k_read(s, reg, data, sizeof(data));

	if (!ret)
		*value = get_unaligned_be16(data);
	return ret;
}

static int s5k_write(struct s5k *s, u16 reg, u16 value, unsigned int len)
{
	u8 bytes[] = { reg >> 8, reg & 0xff, value >> 8, value & 0xff };
	unsigned int size = 2 + len;
	int ret;

	if (len == 1) {
		bytes[2] = value & 0xff;
	}
	ret = i2c_master_send(s->client, bytes, size);
	return ret == size ? 0 : ret < 0 ? ret : -EIO;
}

static int s5k_write16(struct s5k *s, u16 reg, u16 value)
{
	return s5k_write(s, reg, value, 2);
}

static int s5k_write_table(struct s5k *s, const struct s5k_reg *t, size_t n)
{
	const struct s5k_burst *b;
	size_t i;
	int ret;

	usleep_range(3000, 3500);
	for (i = 0; i < n; i++) {
		if (t[i].reg == S5K_DELAY) {
			usleep_range(t[i].val, t[i].val + 500);
			continue;
		}
		if (t[i].reg == S5K_BURST) {
			if (t[i].val >= s->model->num_bursts)
				return -EINVAL;
			b = &s->model->bursts[t[i].val];
			ret = i2c_master_send(s->client, b->data, b->len);
			ret = ret == b->len ? 0 : ret < 0 ? ret : -EIO;
		} else {
			ret = s5k_write(s, t[i].reg, t[i].val, t[i].len);
		}
		if (ret) {
			dev_err(&s->client->dev,
				"table[%zu] register %#06x failed: %d\n",
				i, t[i].reg, ret);
			return ret;
		}
	}
	return 0;
}

/* ---------------------------------------------------------------- power */

static int s5k_power_on(struct device *dev)
{
	struct v4l2_subdev *sd = dev_get_drvdata(dev);
	struct s5k *s = to_s5k(sd);
	const struct s5k_model *m = s->model;
	int i, ret;

	if (s->mux) {
		/* Blocks while the other sub-camera is powered */
		ret = mux_control_select(s->mux, m->mux_state);
		if (ret)
			return ret;
		s->mux_selected = true;
	}

	for (i = 0; i < m->num_supplies; i++) {
		ret = regulator_enable(s->supplies[i].consumer);
		if (ret) {
			dev_err(dev, "supply %s: %d\n", s->supplies[i].supply, ret);
			goto err_supplies;
		}
		s->enabled++;
		usleep_range(500, 1000);
	}

	ret = pinctrl_select_state(s->pins, s->pins_active);
	if (ret)
		goto err_supplies;
	udelay(10);

	if (m->reset_before_clk)
		gpiod_set_value_cansleep(s->reset, 0);
	ret = clk_prepare_enable(s->xclk);
	if (ret)
		goto err_reset;
	if (!m->reset_before_clk) {
		usleep_range(1000, 1500);
		gpiod_set_value_cansleep(s->reset, 0);
	}

	/* The sensor answers on I2C about 20 ms after clock and reset */
	usleep_range(20000, 22000);
	return 0;

err_reset:
	gpiod_set_value_cansleep(s->reset, 1);
	pinctrl_select_state(s->pins, s->pins_idle);
err_supplies:
	while (s->enabled)
		regulator_disable(s->supplies[--s->enabled].consumer);
	if (s->mux_selected) {
		mux_control_deselect(s->mux);
		s->mux_selected = false;
	}
	return ret;
}

static int s5k_power_off(struct device *dev)
{
	struct v4l2_subdev *sd = dev_get_drvdata(dev);
	struct s5k *s = to_s5k(sd);

	gpiod_set_value_cansleep(s->reset, 1);
	clk_disable_unprepare(s->xclk);
	if (pinctrl_select_state(s->pins, s->pins_idle))
		dev_err(dev, "failed to restore idle pins\n");
	while (s->enabled)
		regulator_disable(s->supplies[--s->enabled].consumer);
	if (s->mux_selected) {
		mux_control_deselect(s->mux);
		s->mux_selected = false;
	}
	return 0;
}

/* ------------------------------------------------------------- controls */

/*
 * Default exposure: about 16 ms, so that every sensor starts from a similar
 * brightness (line times range from 1.3 us on the S5K2L4 to 9 us on the S5K3P9)
 * and libcamera's slow software AGC does not take seconds to catch up.
 */
static unsigned int s5k_exposure_default(const struct s5k_mode *mode,
					 unsigned int exp_max)
{
	u64 lines = div_u64((u64)mode->pixel_rate * 16, 1000 * mode->line_length);

	return min_t(u64, lines, exp_max);
}

static void s5k_mode_ranges(struct s5k *s, const struct s5k_mode *mode)
{
	const struct s5k_model *m = s->model;
	unsigned int vblank = mode->frame_length - mode->height;
	unsigned int hblank = mode->line_length - mode->width;
	unsigned int exp_max = mode->frame_length - m->exposure_margin;
	unsigned int exp_def = s5k_exposure_default(mode, exp_max);

	__v4l2_ctrl_modify_range(s->pixel_rate, mode->pixel_rate,
				 mode->pixel_rate, 1, mode->pixel_rate);
	__v4l2_ctrl_modify_range(s->hblank, hblank, hblank, 1, hblank);
	__v4l2_ctrl_modify_range(s->vblank, vblank, 0xffff - mode->height, 1,
				 vblank);
	__v4l2_ctrl_s_ctrl(s->vblank, vblank);
	__v4l2_ctrl_modify_range(s->exposure, m->exposure_min, exp_max, 1,
				 exp_def);
	__v4l2_ctrl_s_ctrl(s->exposure, exp_def);
}

static int s5k_set_ctrl(struct v4l2_ctrl *ctrl)
{
	struct s5k *s = container_of(ctrl->handler, struct s5k, ctrl_handler);
	struct device *dev = &s->client->dev;
	int ret = 0;

	if (ctrl->id == V4L2_CID_VBLANK) {
		int max = s->mode->height + ctrl->val - s->model->exposure_margin;
		int def = s5k_exposure_default(s->mode, max);

		ret = __v4l2_ctrl_modify_range(s->exposure,
					       s->exposure->minimum, max,
					       s->exposure->step, def);
		if (ret)
			return ret;
	}

	/* Values are applied when streaming starts if the sensor is off */
	if (pm_runtime_get_if_in_use(dev) <= 0)
		return 0;

	switch (ctrl->id) {
	case V4L2_CID_ANALOGUE_GAIN:
		ret = s5k_write16(s, S5K_REG_ANALOG_GAIN, ctrl->val);
		break;
	case V4L2_CID_EXPOSURE:
		ret = s5k_write16(s, S5K_REG_COARSE_INTEG, ctrl->val);
		break;
	case V4L2_CID_VBLANK:
		ret = s5k_write16(s, S5K_REG_FRAME_LENGTH,
				  s->mode->height + ctrl->val);
		break;
	default:
		break;
	}

	pm_runtime_put(dev);
	return ret;
}

static const struct v4l2_ctrl_ops s5k_ctrl_ops = {
	.s_ctrl = s5k_set_ctrl,
};

static int s5k_init_controls(struct s5k *s)
{
	const struct s5k_mode *mode = s->mode;
	const struct s5k_model *m = s->model;
	struct v4l2_ctrl_handler *hdl = &s->ctrl_handler;
	struct v4l2_fwnode_device_properties props;
	unsigned int vblank = mode->frame_length - mode->height;
	unsigned int hblank = mode->line_length - mode->width;
	unsigned int exp_max = mode->frame_length - m->exposure_margin;
	int ret;

	v4l2_ctrl_handler_init(hdl, 9);

	s->link_freq = v4l2_ctrl_new_int_menu(hdl, NULL, V4L2_CID_LINK_FREQ,
					      s->num_link_freqs - 1, 0,
					      s->link_freq_menu);
	if (s->link_freq)
		s->link_freq->flags |= V4L2_CTRL_FLAG_READ_ONLY;

	s->pixel_rate = v4l2_ctrl_new_std(hdl, NULL, V4L2_CID_PIXEL_RATE,
					  mode->pixel_rate, mode->pixel_rate,
					  1, mode->pixel_rate);
	s->hblank = v4l2_ctrl_new_std(hdl, NULL, V4L2_CID_HBLANK, hblank,
				      hblank, 1, hblank);
	if (s->hblank)
		s->hblank->flags |= V4L2_CTRL_FLAG_READ_ONLY;
	s->vblank = v4l2_ctrl_new_std(hdl, &s5k_ctrl_ops, V4L2_CID_VBLANK,
				      vblank, 0xffff - mode->height, 1, vblank);
	s->exposure = v4l2_ctrl_new_std(hdl, &s5k_ctrl_ops, V4L2_CID_EXPOSURE,
					m->exposure_min, exp_max, 1,
					s5k_exposure_default(mode, exp_max));
	s->gain = v4l2_ctrl_new_std(hdl, &s5k_ctrl_ops, V4L2_CID_ANALOGUE_GAIN,
				    S5K_GAIN_MIN, S5K_GAIN_MAX, 1, 0x80);
	if (hdl->error) {
		ret = hdl->error;
		goto err;
	}

	ret = v4l2_fwnode_device_parse(&s->client->dev, &props);
	if (ret)
		goto err;
	ret = v4l2_ctrl_new_fwnode_properties(hdl, &s5k_ctrl_ops, &props);
	if (ret)
		goto err;

	s->sd.ctrl_handler = hdl;
	return 0;
err:
	v4l2_ctrl_handler_free(hdl);
	return ret;
}

/* --------------------------------------------------------------- subdev */

static int s5k_stream_wait(struct s5k *s, bool on)
{
	u8 counter;
	int i, ret;

	for (i = 0; i < 25; i++) {
		usleep_range(10000, 11000);
		ret = s5k_read(s, S5K_REG_FRAME_COUNT, &counter, 1);
		if (ret)
			return ret;
		/* 0xff means "not streaming" */
		if (on ? counter != 0xff : counter == 0xff)
			return 0;
	}
	return -ETIMEDOUT;
}

static int s5k_check_id(struct s5k *s)
{
	const struct s5k_model *m = s->model;
	u16 model, revision;
	int ret;

	ret = s5k_read16(s, S5K_REG_MODEL, &model);
	ret = ret ?: s5k_read16(s, S5K_REG_REVISION, &revision);
	if (ret)
		return ret;
	dev_info(&s->client->dev, "%s: model %#06x revision %#06x\n", m->name,
		 model, revision);
	if ((m->model_id && model != m->model_id) || revision != m->revision) {
		dev_err(&s->client->dev,
			"sensor %#06x/%#06x is not supported (need %#06x/%#06x)\n",
			model, revision, m->model_id, m->revision);
		return -ENODEV;
	}
	return 0;
}

static int s5k_enable_streams(struct v4l2_subdev *sd,
			      struct v4l2_subdev_state *state, u32 pad,
			      u64 streams_mask)
{
	struct s5k *s = to_s5k(sd);
	const struct s5k_model *m = s->model;
	struct device *dev = &s->client->dev;
	u16 val;
	int ret;

	ret = pm_runtime_resume_and_get(dev);
	if (ret < 0)
		return ret;

	ret = s5k_check_id(s);
	if (ret)
		goto err_rpm;
	ret = s5k_read16(s, S5K_REG_MODE_SELECT, &val);
	if (ret)
		goto err_rpm;
	if (val >> 8) {
		ret = -EBUSY;
		goto err_rpm;
	}

	ret = s5k_write_table(s, m->global, m->num_global);
	ret = ret ?: s5k_write_table(s, s->mode->regs, s->mode->num_regs);
	if (m->master)
		ret = ret ?: s5k_write_table(s, m->master, m->num_master);
	ret = ret ?: s5k_write16(s, S5K_REG_PAGE, 0x4000);
	if (ret)
		goto err_rpm;

	/* The tables overwrite frame length, exposure and gain */
	ret = __v4l2_ctrl_handler_setup(&s->ctrl_handler);
	if (ret)
		goto err_rpm;

	ret = s5k_write16(s, S5K_REG_PAGE, 0x4000);
	/* 16-bit write: mode_select (0x0100) and image_orientation (0x0101) */
	ret = ret ?: s5k_write16(s, S5K_REG_MODE_SELECT, 0x0100 | m->orientation);
	ret = ret ?: s5k_stream_wait(s, true);
	if (ret) {
		dev_err(dev, "failed to start streaming: %d\n", ret);
		goto err_rpm;
	}

	return 0;

err_rpm:
	pm_runtime_put_sync(dev);
	return ret;
}

static int s5k_disable_streams(struct v4l2_subdev *sd,
			       struct v4l2_subdev_state *state, u32 pad,
			       u64 streams_mask)
{
	struct s5k *s = to_s5k(sd);
	struct device *dev = &s->client->dev;
	int ret;

	ret = s5k_write16(s, S5K_REG_PAGE, 0x4000);
	ret = ret ?: s5k_write16(s, S5K_REG_MODE_SELECT, s->model->orientation);
	ret = ret ?: s5k_stream_wait(s, false);
	if (ret)
		dev_err(dev, "sensor stop not confirmed: %d\n", ret);

	pm_runtime_put_autosuspend(dev);
	return 0;
}

static int s5k_enum_mbus_code(struct v4l2_subdev *sd,
			      struct v4l2_subdev_state *state,
			      struct v4l2_subdev_mbus_code_enum *code)
{
	struct s5k *s = to_s5k(sd);

	if (code->index)
		return -EINVAL;
	code->code = s->model->mbus_code;
	return 0;
}

static int s5k_enum_frame_size(struct v4l2_subdev *sd,
			       struct v4l2_subdev_state *state,
			       struct v4l2_subdev_frame_size_enum *fse)
{
	struct s5k *s = to_s5k(sd);

	if (fse->index >= s->model->num_modes ||
	    fse->code != s->model->mbus_code)
		return -EINVAL;
	fse->min_width = fse->max_width = s->model->modes[fse->index].width;
	fse->min_height = fse->max_height = s->model->modes[fse->index].height;
	return 0;
}

static void s5k_fill_format(struct s5k *s, const struct s5k_mode *mode,
			    struct v4l2_mbus_framefmt *fmt)
{
	fmt->width = mode->width;
	fmt->height = mode->height;
	fmt->code = s->model->mbus_code;
	fmt->field = V4L2_FIELD_NONE;
	fmt->colorspace = V4L2_COLORSPACE_RAW;
	fmt->ycbcr_enc = V4L2_YCBCR_ENC_601;
	fmt->quantization = V4L2_QUANTIZATION_FULL_RANGE;
	fmt->xfer_func = V4L2_XFER_FUNC_NONE;
}

static const struct s5k_mode *s5k_find_mode(struct s5k *s, u32 width, u32 height)
{
	const struct s5k_mode *best = &s->model->modes[0];
	u64 best_diff = U64_MAX;
	unsigned int i;

	for (i = 0; i < s->model->num_modes; i++) {
		const struct s5k_mode *mode = &s->model->modes[i];
		s64 dw = (s64)mode->width - width, dh = (s64)mode->height - height;
		u64 diff = dw * dw + dh * dh;

		if (diff < best_diff) {
			best_diff = diff;
			best = mode;
		}
	}
	return best;
}

static int s5k_set_fmt(struct v4l2_subdev *sd, struct v4l2_subdev_state *state,
		       struct v4l2_subdev_format *fmt)
{
	struct s5k *s = to_s5k(sd);
	const struct s5k_mode *mode;

	if (fmt->which == V4L2_SUBDEV_FORMAT_ACTIVE &&
	    media_pad_is_streaming(&s->pad))
		return v4l2_subdev_get_fmt(sd, state, fmt);

	mode = s5k_find_mode(s, fmt->format.width, fmt->format.height);
	s5k_fill_format(s, mode, &fmt->format);
	*v4l2_subdev_state_get_format(state, 0) = fmt->format;

	if (fmt->which == V4L2_SUBDEV_FORMAT_ACTIVE && mode != s->mode) {
		s->mode = mode;
		s5k_mode_ranges(s, mode);
	}
	return 0;
}

static int s5k_get_selection(struct v4l2_subdev *sd,
			     struct v4l2_subdev_state *state,
			     struct v4l2_subdev_selection *sel)
{
	struct s5k *s = to_s5k(sd);
	const struct s5k_mode *mode = s->mode;

	switch (sel->target) {
	case V4L2_SEL_TGT_CROP:
	case V4L2_SEL_TGT_CROP_DEFAULT:
		sel->r = mode->crop;
		return 0;
	case V4L2_SEL_TGT_CROP_BOUNDS:
	case V4L2_SEL_TGT_NATIVE_SIZE:
		sel->r.top = 0;
		sel->r.left = 0;
		sel->r.width = s->model->native_width;
		sel->r.height = s->model->native_height;
		return 0;
	}
	return -EINVAL;
}

static int s5k_init_state(struct v4l2_subdev *sd, struct v4l2_subdev_state *state)
{
	struct s5k *s = to_s5k(sd);

	s5k_fill_format(s, &s->model->modes[0], v4l2_subdev_state_get_format(state, 0));
	return 0;
}

static const struct v4l2_subdev_video_ops s5k_video_ops = {
	.s_stream = v4l2_subdev_s_stream_helper,
};

static const struct v4l2_subdev_pad_ops s5k_pad_ops = {
	.enum_mbus_code = s5k_enum_mbus_code,
	.enum_frame_size = s5k_enum_frame_size,
	.get_fmt = v4l2_subdev_get_fmt,
	.set_fmt = s5k_set_fmt,
	.get_selection = s5k_get_selection,
	.enable_streams = s5k_enable_streams,
	.disable_streams = s5k_disable_streams,
};

static const struct v4l2_subdev_ops s5k_subdev_ops = {
	.video = &s5k_video_ops,
	.pad = &s5k_pad_ops,
};

static const struct v4l2_subdev_internal_ops s5k_internal_ops = {
	.init_state = s5k_init_state,
};

/* ---------------------------------------------------------------- probe */

static int s5k_check_hwcfg(struct s5k *s)
{
	const struct s5k_model *m = s->model;
	struct device *dev = &s->client->dev;
	struct v4l2_fwnode_endpoint ep = { .bus_type = V4L2_MBUS_CSI2_DPHY };
	struct fwnode_handle *endpoint;
	unsigned long bitmap;
	unsigned int i, n = 0;
	int ret;

	endpoint = fwnode_graph_get_next_endpoint(dev_fwnode(dev), NULL);
	if (!endpoint)
		return dev_err_probe(dev, -EINVAL, "no endpoint\n");

	ret = v4l2_fwnode_endpoint_alloc_parse(endpoint, &ep);
	fwnode_handle_put(endpoint);
	if (ret)
		return dev_err_probe(dev, ret, "cannot parse endpoint\n");

	if (ep.bus.mipi_csi2.num_data_lanes != 4) {
		ret = dev_err_probe(dev, -EINVAL, "only 4 data lanes are supported\n");
		goto out;
	}

	/* The menu holds each link frequency of the modes once */
	s->link_freq_menu = devm_kcalloc(dev, m->num_modes, sizeof(s64), GFP_KERNEL);
	if (!s->link_freq_menu) {
		ret = -ENOMEM;
		goto out;
	}
	for (i = 0; i < m->num_modes; i++) {
		unsigned int j;

		for (j = 0; j < n; j++)
			if (s->link_freq_menu[j] == m->modes[i].link_freq)
				break;
		if (j == n)
			s->link_freq_menu[n++] = m->modes[i].link_freq;
	}
	s->num_link_freqs = n;

	ret = v4l2_link_freq_to_bitmap(dev, ep.link_frequencies,
				       ep.nr_of_link_frequencies,
				       s->link_freq_menu, n, &bitmap);
	if (ret)
		dev_err_probe(dev, ret, "link frequency %lld Hz is required\n",
			      s->link_freq_menu[0]);
out:
	v4l2_fwnode_endpoint_free(&ep);
	return ret;
}

static void s5k_pinctrl_put(void *data)
{
	pinctrl_put(data);
}

static void s5k_release_firmware(void *data)
{
	release_firmware(data);
}

static int s5k_decode_table(struct device *dev, const struct s5k_fw_view *view,
			   unsigned int index, const struct s5k_reg **result,
			   unsigned int *num)
{
	const u8 *d = s5k_fw_table(view, index);
	u32 offset = s5k_fw_u32(d + 4), count = s5k_fw_u32(d + 8);
	struct s5k_reg *regs;
	unsigned int i;

	regs = devm_kcalloc(dev, count, sizeof(*regs), GFP_KERNEL);
	if (!regs)
		return -ENOMEM;
	for (i = 0; i < count; i++) {
		const u8 *op = view->data + offset + 5 * i;

		regs[i].reg = s5k_fw_u16(op);
		regs[i].val = s5k_fw_u16(op + 2);
		regs[i].len = op[4];
	}
	*result = regs;
	*num = count;
	return 0;
}

static int s5k_load_firmware(struct s5k *s, const struct s5k_model *base)
{
	struct device *dev = &s->client->dev;
	const struct firmware *fw;
	struct s5k_fw_view view;
	struct s5k_model *model;
	struct s5k_mode *modes;
	struct s5k_burst *bursts;
	u8 digest[SHA256_DIGEST_SIZE], expected[SHA256_DIGEST_SIZE];
	unsigned int i;
	int ret;

	if (!base)
		return -ENODEV;
	ret = request_firmware_direct(&fw, base->firmware_name, dev);
	if (ret)
		return ret;
	ret = s5k_fw_validate(fw->data, fw->size, base->model_id, base->revision,
			      base->num_modes, base->has_master, &view);
	if (ret)
		goto release;
	ret = hex2bin(expected, base->firmware_sha256, sizeof(expected));
	if (ret)
		goto release;
	sha256(fw->data, fw->size, digest);
	if (memcmp(digest, expected, sizeof(digest))) {
		ret = -EINVAL;
		goto release;
	}
	ret = devm_add_action_or_reset(dev, s5k_release_firmware, (void *)fw);
	if (ret)
		return ret;
	model = devm_kmemdup(dev, base, sizeof(*model), GFP_KERNEL);
	modes = devm_kmemdup(dev, base->modes,
			     base->num_modes * sizeof(*modes), GFP_KERNEL);
	if (!model || !modes)
		return -ENOMEM;
	model->modes = modes;
	ret = s5k_decode_table(dev, &view, 0, &model->global, &model->num_global);
	if (ret)
		return ret;
	for (i = 0; i < model->num_modes; i++) {
		ret = s5k_decode_table(dev, &view, i + 1,
				       &modes[i].regs, &modes[i].num_regs);
		if (ret)
			return ret;
	}
	if (base->has_master) {
		ret = s5k_decode_table(dev, &view, view.tables - 1,
				       &model->master, &model->num_master);
		if (ret)
			return ret;
	}
	bursts = devm_kcalloc(dev, view.bursts, sizeof(*bursts), GFP_KERNEL);
	if (view.bursts && !bursts)
		return -ENOMEM;
	for (i = 0; i < view.bursts; i++) {
		const u8 *d = s5k_fw_burst(&view, i);

		bursts[i].data = fw->data + s5k_fw_u32(d);
		bursts[i].len = s5k_fw_u32(d + 4);
	}
	model->bursts = bursts;
	model->num_bursts = view.bursts;
	s->model = model;
	return 0;
release:
	release_firmware(fw);
	return ret;
}

static int s5k_probe(struct i2c_client *client)
{
	struct device *dev = &client->dev;
	struct s5k *s;
	int i, ret;

	s = devm_kzalloc(dev, sizeof(*s), GFP_KERNEL);
	if (!s)
		return -ENOMEM;
	s->client = client;
	ret = s5k_load_firmware(s, of_device_get_match_data(dev));
	if (ret)
		return dev_err_probe(dev, ret, "sensor runtime data unavailable or invalid\n");
	s->mode = &s->model->modes[0];
	v4l2_i2c_subdev_init(&s->sd, client, &s5k_subdev_ops);
	/* One driver, several sensors: name the entity after the sensor */
	snprintf(s->sd.name, sizeof(s->sd.name), "%s %d-%04x", s->model->name,
		 i2c_adapter_id(client->adapter), client->addr);
	s->sd.internal_ops = &s5k_internal_ops;

	ret = s5k_check_hwcfg(s);
	if (ret)
		return ret;

	s->xclk = devm_clk_get(dev, "mclk");
	if (IS_ERR(s->xclk))
		return dev_err_probe(dev, PTR_ERR(s->xclk), "mclk\n");
	if (clk_get_rate(s->xclk) != S5K_XCLK_FREQ)
		return dev_err_probe(dev, -EINVAL, "mclk must be %u Hz\n",
				     S5K_XCLK_FREQ);

	s->supplies = devm_kcalloc(dev, s->model->num_supplies,
				   sizeof(*s->supplies), GFP_KERNEL);
	if (!s->supplies)
		return -ENOMEM;
	for (i = 0; i < s->model->num_supplies; i++)
		s->supplies[i].supply = s->model->supplies[i];
	ret = devm_regulator_bulk_get(dev, s->model->num_supplies, s->supplies);
	if (ret)
		return dev_err_probe(dev, ret, "supplies\n");

	s->reset = devm_gpiod_get(dev, "reset", GPIOD_OUT_HIGH);
	if (IS_ERR(s->reset))
		return dev_err_probe(dev, PTR_ERR(s->reset), "reset GPIO\n");

	if (s->model->mux_state >= 0) {
		s->mux = devm_mux_control_get(dev, NULL);
		if (IS_ERR(s->mux))
			return dev_err_probe(dev, PTR_ERR(s->mux), "mux\n");
	}

	/*
	 * The I2C pins and MCLK share the pin groups of the I2C controller,
	 * which must not drive them while the sensor is unpowered. The states
	 * live on the controller node.
	 */
	s->pins = pinctrl_get(client->adapter->dev.parent);
	if (IS_ERR(s->pins))
		return dev_err_probe(dev, PTR_ERR(s->pins), "pinctrl\n");
	ret = devm_add_action_or_reset(dev, s5k_pinctrl_put, s->pins);
	if (ret)
		return ret;
	s->pins_idle = pinctrl_lookup_state(s->pins, "default");
	s->pins_active = pinctrl_lookup_state(s->pins, "camera-on");
	if (IS_ERR(s->pins_idle) || IS_ERR(s->pins_active))
		return dev_err_probe(dev, -EINVAL,
				     "adapter needs \"default\" and \"camera-on\" pin states\n");

	ret = s5k_power_on(dev);
	if (ret)
		return ret;

	ret = s5k_check_id(s);
	if (ret)
		goto err_power_off;

	ret = s5k_init_controls(s);
	if (ret)
		goto err_power_off;

	s->sd.flags |= V4L2_SUBDEV_FL_HAS_DEVNODE;
	s->sd.entity.function = MEDIA_ENT_F_CAM_SENSOR;
	s->pad.flags = MEDIA_PAD_FL_SOURCE;
	ret = media_entity_pads_init(&s->sd.entity, 1, &s->pad);
	if (ret)
		goto err_ctrls;

	s->sd.state_lock = s->ctrl_handler.lock;
	ret = v4l2_subdev_init_finalize(&s->sd);
	if (ret)
		goto err_entity;

	pm_runtime_set_active(dev);
	pm_runtime_get_noresume(dev);
	pm_runtime_enable(dev);
	pm_runtime_set_autosuspend_delay(dev, 1000);
	pm_runtime_use_autosuspend(dev);

	ret = v4l2_async_register_subdev_sensor(&s->sd);
	if (ret)
		goto err_subdev;

	pm_runtime_put_autosuspend(dev);
	return 0;

err_subdev:
	pm_runtime_disable(dev);
	pm_runtime_put_noidle(dev);
	pm_runtime_set_suspended(dev);
	v4l2_subdev_cleanup(&s->sd);
err_entity:
	media_entity_cleanup(&s->sd.entity);
err_ctrls:
	v4l2_ctrl_handler_free(&s->ctrl_handler);
err_power_off:
	if (pm_runtime_status_suspended(dev) || !pm_runtime_enabled(dev))
		s5k_power_off(dev);
	return ret;
}

static void s5k_remove(struct i2c_client *client)
{
	struct v4l2_subdev *sd = i2c_get_clientdata(client);
	struct s5k *s = to_s5k(sd);
	struct device *dev = &client->dev;

	v4l2_async_unregister_subdev(sd);
	v4l2_subdev_cleanup(sd);
	media_entity_cleanup(&sd->entity);
	v4l2_ctrl_handler_free(&s->ctrl_handler);

	pm_runtime_disable(dev);
	if (!pm_runtime_status_suspended(dev))
		s5k_power_off(dev);
	pm_runtime_set_suspended(dev);
}

static const struct of_device_id s5k_of_match[] = {
	{ .compatible = "samsung,s5k3p9", .data = &s5k3p9_model },
	{ .compatible = "samsung,s5k3m3", .data = &s5k3m3_model },
	{ .compatible = "samsung,s5k3j1", .data = &s5k3j1_model },
	{ .compatible = "samsung,s5k2l4", .data = &s5k2l4_model },
	{ }
};
MODULE_DEVICE_TABLE(of, s5k_of_match);

static const struct dev_pm_ops s5k_pm_ops = {
	SET_RUNTIME_PM_OPS(s5k_power_off, s5k_power_on, NULL)
};

static struct i2c_driver s5k_driver = {
	.driver = {
		.name = "s5k-cis",
		.of_match_table = s5k_of_match,
		.pm = &s5k_pm_ops,
	},
	.probe = s5k_probe,
	.remove = s5k_remove,
};
module_i2c_driver(s5k_driver);

MODULE_DESCRIPTION("Samsung S5K3P9 / S5K3M3 / S5K3J1 image sensor driver (Galaxy S10)");
MODULE_LICENSE("GPL");

MODULE_FIRMWARE("samsung/s10/s5k3p9.s5k");
MODULE_FIRMWARE("samsung/s10/s5k3m3.s5k");
MODULE_FIRMWARE("samsung/s10/s5k3j1.s5k");
MODULE_FIRMWARE("samsung/s10/s5k2l4.s5k");
