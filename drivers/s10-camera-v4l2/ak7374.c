// SPDX-License-Identifier: GPL-2.0
/*
 * AK737x voice-coil lens actuator of the Galaxy S10 tele camera (S5K3M3).
 *
 * Register protocol from Samsung's GPL fimc-is-actuator-ak737x.c
 * (LineageOS/android_kernel_samsung_exynos9820 @ 4bcfb0263b21):
 *   position: two 8-bit registers, 9-bit value left-aligned,
 *             reg 0x00 = val >> 1, reg 0x01 = (val & 1) << 7
 *   control:  reg 0x02, 0x00 active / 0x40 standby / 0x20 sleep
 *   product id: reg 0xf3, 0x0e on this handset's tele (AK7374)
 * Position 0 is infinity, 511 macro; Samsung's first position is 120.
 * The actuator needs ~10 ms after its supply comes up before it answers.
 *
 * The sensor node links here with lens-focus; v4l2-async then creates the
 * ancillary link that libcamera's CameraLens looks for.
 */
#include <linux/delay.h>
#include <linux/i2c.h>
#include <linux/module.h>
#include <linux/list.h>
#include <linux/mutex.h>
#include <linux/pinctrl/consumer.h>
#include <linux/pm_runtime.h>
#include <linux/regulator/consumer.h>
#include <media/v4l2-ctrls.h>
#include <media/v4l2-device.h>

#define AK7374_REG_POS_HIGH	0x00
#define AK7374_REG_POS_LOW	0x01
#define AK7374_REG_CONT		0x02
#define AK7374_REG_ID		0xf3

#define AK7374_ACTIVE		0x00
#define AK7374_STANDBY		0x40

#define AK7374_POS_MAX		511	/* 9 bit, 0 = infinity */
#define AK7374_FIRST_POS	120
#define AK7374_POWER_DELAY_US	10000
#define AK7374_FIRST_DELAY_US	2000

struct ak7374 {
	struct v4l2_ctrl_handler ctrls;
	struct v4l2_subdev sd;
	struct v4l2_ctrl *focus;
	struct regulator *vdd;
	struct regulator *vddio;	/* rear-flex camera I/O (S2MPB03 LDO3) */
	struct pinctrl *pins;
	struct pinctrl_state *pins_idle, *pins_active;
	bool active;
	bool pins_enabled;
	struct list_head bus_node;
	struct i2c_adapter *adapter;
};

/* Main and tele share CAM3. An idle lens must not park a live peer's pins. */
static LIST_HEAD(ak7374_lenses);
static DEFINE_MUTEX(ak7374_bus_lock);

static void ak7374_unlist(void *data)
{
	struct ak7374 *vcm = data;

	mutex_lock(&ak7374_bus_lock);
	list_del(&vcm->bus_node);
	mutex_unlock(&ak7374_bus_lock);
}

static int ak7374_bus_pins(struct ak7374 *vcm, bool enable)
{
	struct ak7374 *peer;
	int ret = 0;

	mutex_lock(&ak7374_bus_lock);
	if (enable) {
		ret = pinctrl_select_state(vcm->pins, vcm->pins_active);
		if (!ret)
			vcm->pins_enabled = true;
	} else {
		vcm->pins_enabled = false;
		list_for_each_entry(peer, &ak7374_lenses, bus_node) {
			if (peer->adapter == vcm->adapter && peer->pins_enabled)
				goto out;
		}
		ret = pinctrl_select_state(vcm->pins, vcm->pins_idle);
	}
out:
	mutex_unlock(&ak7374_bus_lock);
	return ret;
}

static inline struct ak7374 *sd_to_ak7374(struct v4l2_subdev *sd)
{
	return container_of(sd, struct ak7374, sd);
}

static inline struct ak7374 *ctrl_to_ak7374(struct v4l2_ctrl *ctrl)
{
	return container_of(ctrl->handler, struct ak7374, ctrls);
}

static int ak7374_write8(struct ak7374 *vcm, u8 reg, u8 val)
{
	struct i2c_client *client = v4l2_get_subdevdata(&vcm->sd);
	u8 buf[2] = { reg, val };
	int ret = i2c_master_send(client, buf, sizeof(buf));

	return ret == sizeof(buf) ? 0 : ret < 0 ? ret : -EIO;
}

static int ak7374_read8(struct ak7374 *vcm, u8 reg, u8 *val)
{
	struct i2c_client *client = v4l2_get_subdevdata(&vcm->sd);
	int ret = i2c_smbus_read_byte_data(client, reg);

	if (ret < 0)
		return ret;
	*val = ret;
	return 0;
}

static int ak7374_set_position(struct ak7374 *vcm, u32 val)
{
	int ret;

	if (val > AK7374_POS_MAX)
		return -EINVAL;

	ret = ak7374_write8(vcm, AK7374_REG_POS_HIGH, val >> 1);
	if (ret)
		return ret;
	return ak7374_write8(vcm, AK7374_REG_POS_LOW, (val & 1) << 7);
}

static int ak7374_set_ctrl(struct v4l2_ctrl *ctrl)
{
	struct ak7374 *vcm = ctrl_to_ak7374(ctrl);

	if (ctrl->id != V4L2_CID_FOCUS_ABSOLUTE)
		return -EINVAL;
	if (!vcm->active)
		return -ENODEV;
	return ak7374_set_position(vcm, ctrl->val);
}

static const struct v4l2_ctrl_ops ak7374_ctrl_ops = {
	.s_ctrl = ak7374_set_ctrl,
};

static int ak7374_open(struct v4l2_subdev *sd, struct v4l2_subdev_fh *fh)
{
	return pm_runtime_resume_and_get(sd->dev);
}

static int ak7374_close(struct v4l2_subdev *sd, struct v4l2_subdev_fh *fh)
{
	pm_runtime_put(sd->dev);
	return 0;
}

static const struct v4l2_subdev_internal_ops ak7374_int_ops = {
	.open = ak7374_open,
	.close = ak7374_close,
};

static const struct v4l2_subdev_ops ak7374_ops = { };

static int ak7374_power_on(struct device *dev)
{
	struct v4l2_subdev *sd = dev_get_drvdata(dev);
	struct ak7374 *vcm = sd_to_ak7374(sd);
	u8 id;
	int ret;

	ret = ak7374_bus_pins(vcm, true);
	if (ret)
		return ret;

	/* The rear-flex I/O rail powers the bus pull-ups; it must be up
	 * before anything on the CAM3 bus answers. */
	if (vcm->vddio) {
		ret = regulator_enable(vcm->vddio);
		if (ret) {
			ak7374_bus_pins(vcm, false);
			return ret;
		}
		usleep_range(1000, 1500);
	}

	ret = regulator_enable(vcm->vdd);
	if (ret) {
		if (vcm->vddio)
			regulator_disable(vcm->vddio);
		ak7374_bus_pins(vcm, false);
		return ret;
	}
	/* The actuator answers about 10 ms after its supply comes up */
	usleep_range(AK7374_POWER_DELAY_US, AK7374_POWER_DELAY_US + 500);

	ret = ak7374_read8(vcm, AK7374_REG_ID, &id);
	if (ret) {
		/*
		 * A dead CAM3 bus is a bring-up condition (missing bus pull-up
		 * rail), not a reason to latch a runtime-PM error: probe daemons
		 * (udev) open the node on registration. Log and keep going;
		 * individual position writes will report the real I2C errors.
		 */
		dev_warn(dev, "actuator does not answer: %d\n", ret);
	} else {
		/* Samsung's board lists 0x0e (AK7374); log everything */
		dev_info(dev, "product id register 0x%02x = 0x%02x\n",
			 AK7374_REG_ID, id);
	}

	ret = ak7374_set_position(vcm, vcm->focus->val);
	if (ret)
		dev_warn(dev, "initial position write failed: %d\n", ret);
	usleep_range(AK7374_FIRST_DELAY_US, AK7374_FIRST_DELAY_US + 100);

	ret = ak7374_write8(vcm, AK7374_REG_CONT, AK7374_ACTIVE);
	if (ret)
		dev_warn(dev, "active-mode write failed: %d\n", ret);

	vcm->active = true;
	return 0;
}

static int ak7374_power_off(struct device *dev)
{
	struct v4l2_subdev *sd = dev_get_drvdata(dev);
	struct ak7374 *vcm = sd_to_ak7374(sd);

	if (vcm->active) {
		int ret = ak7374_write8(vcm, AK7374_REG_CONT, AK7374_STANDBY);

		if (ret)
			dev_err(dev, "standby write failed: %d\n", ret);
		vcm->active = false;
	}
	regulator_disable(vcm->vdd);
	if (vcm->vddio)
		regulator_disable(vcm->vddio);
	ak7374_bus_pins(vcm, false);
	return 0;
}

static int ak7374_probe(struct i2c_client *client)
{
	struct device *dev = &client->dev;
	struct ak7374 *vcm;
	int ret;

	vcm = devm_kzalloc(dev, sizeof(*vcm), GFP_KERNEL);
	if (!vcm)
		return -ENOMEM;

	vcm->vdd = devm_regulator_get(dev, "vdd");
	if (IS_ERR(vcm->vdd))
		return dev_err_probe(dev, PTR_ERR(vcm->vdd), "vdd supply\n");

	vcm->vddio = devm_regulator_get_optional(dev, "vddio");
	if (IS_ERR(vcm->vddio)) {
		if (PTR_ERR(vcm->vddio) != -ENODEV)
			return dev_err_probe(dev, PTR_ERR(vcm->vddio), "vddio supply\n");
		vcm->vddio = NULL;
	}

	/*
	 * Like the sensor buses: the CAM3 I2C pins must only be driven while
	 * something on that bus is powered. The states live on the controller.
	 */
	vcm->pins = pinctrl_get(client->adapter->dev.parent);
	if (IS_ERR(vcm->pins))
		return dev_err_probe(dev, PTR_ERR(vcm->pins), "pinctrl\n");
	vcm->pins_idle = pinctrl_lookup_state(vcm->pins, "default");
	vcm->pins_active = pinctrl_lookup_state(vcm->pins, "camera-on");
	if (IS_ERR(vcm->pins_idle) || IS_ERR(vcm->pins_active))
		return dev_err_probe(dev, -EINVAL,
				      "adapter needs \"default\" and \"camera-on\" pin states\n");

	v4l2_i2c_subdev_init(&vcm->sd, client, &ak7374_ops);
	vcm->sd.flags |= V4L2_SUBDEV_FL_HAS_DEVNODE;
	vcm->sd.internal_ops = &ak7374_int_ops;
	vcm->sd.entity.function = MEDIA_ENT_F_LENS;
	snprintf(vcm->sd.name, sizeof(vcm->sd.name), "ak7374 %d-%04x",
		 i2c_adapter_id(client->adapter), client->addr);

	v4l2_ctrl_handler_init(&vcm->ctrls, 1);
	vcm->focus = v4l2_ctrl_new_std(&vcm->ctrls, &ak7374_ctrl_ops,
				       V4L2_CID_FOCUS_ABSOLUTE, 0,
				       AK7374_POS_MAX, 1, AK7374_FIRST_POS);
	if (vcm->ctrls.error) {
		ret = vcm->ctrls.error;
		goto err_ctrls;
	}
	vcm->sd.ctrl_handler = &vcm->ctrls;

	ret = media_entity_pads_init(&vcm->sd.entity, 0, NULL);
	if (ret)
		goto err_ctrls;

	vcm->adapter = client->adapter;
	mutex_lock(&ak7374_bus_lock);
	list_add(&vcm->bus_node, &ak7374_lenses);
	mutex_unlock(&ak7374_bus_lock);
	ret = devm_add_action_or_reset(dev, ak7374_unlist, vcm);
	if (ret)
		goto err_entity;

	ret = v4l2_async_register_subdev(&vcm->sd);
	if (ret < 0)
		goto err_entity;

	pm_runtime_enable(dev);
	pm_runtime_idle(dev);

	return 0;

err_entity:
	media_entity_cleanup(&vcm->sd.entity);
err_ctrls:
	v4l2_ctrl_handler_free(&vcm->ctrls);
	return ret;
}

static void ak7374_remove(struct i2c_client *client)
{
	struct v4l2_subdev *sd = i2c_get_clientdata(client);
	struct ak7374 *vcm = sd_to_ak7374(sd);

	v4l2_async_unregister_subdev(sd);
	pm_runtime_disable(&client->dev);
	if (!pm_runtime_status_suspended(&client->dev))
		ak7374_power_off(&client->dev);
	pm_runtime_set_suspended(&client->dev);
	media_entity_cleanup(&sd->entity);
	v4l2_ctrl_handler_free(&vcm->ctrls);
}

static const struct of_device_id ak7374_of_match[] = {
	{ .compatible = "asahi-kasei,ak7374" },
	{ }
};
MODULE_DEVICE_TABLE(of, ak7374_of_match);

static const struct dev_pm_ops ak7374_pm_ops = {
	SET_RUNTIME_PM_OPS(ak7374_power_off, ak7374_power_on, NULL)
};

static struct i2c_driver ak7374_driver = {
	.driver = {
		.name = "ak7374",
		.of_match_table = ak7374_of_match,
		.pm = &ak7374_pm_ops,
	},
	.probe = ak7374_probe,
	.remove = ak7374_remove,
};
module_i2c_driver(ak7374_driver);

MODULE_DESCRIPTION("AK7374 lens actuator of the Galaxy S10 tele camera");
MODULE_LICENSE("GPL");
