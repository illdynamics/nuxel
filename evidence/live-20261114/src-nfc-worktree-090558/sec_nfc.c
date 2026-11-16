/*
 * SAMSUNG NFC Controller
 *
 * Copyright (C) 2013 Samsung Electronics Co.Ltd
 * Author: Woonki Lee <woonki84.lee@samsung.com>
 *         Heejae Kim <heejae12.kim@samsung.com>
 *
 * This program is free software; you can redistribute it and/or modify it
 * under  the terms of  the GNU General  Public License as published by the
 * Free Software Foundation;  either version 2 of the License, or (at your
 * option) any later version.
 *
 * This program is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 * GNU General Public License for more details.
 *
 * You should have received a copy of the GNU General Public License
 * along with this program;
 *
 */

#define pr_fmt(fmt)     "[sec_nfc] %s: " fmt, __func__

#include <linux/wait.h>
#include <linux/delay.h>

#include <linux/kernel.h>
#include <linux/io.h>
#include <linux/platform_device.h>
#include <linux/mutex.h>
#include <linux/module.h>
#include <linux/miscdevice.h>
#include <linux/gpio.h>
#include <linux/slab.h>
#include <linux/fs.h>
#include <linux/uaccess.h>
#include <linux/clk-provider.h>
#include <linux/interrupt.h>
#include <linux/wakelock.h>
#include <linux/of_gpio.h>
#include <linux/clk.h>
#include <linux/regulator/consumer.h>
#include <linux/interrupt.h>
#include <linux/poll.h>
#include <linux/sched.h>
#include <linux/i2c.h>

#ifdef CONFIG_ESE_SECURE
extern int tz_tee_ese_secure_check(void);
enum secure_state {
	NOT_CHECKED,
	ESE_SECURED,
	ESE_NOT_SECURED,
};
int nfc_ese_secured;
#endif

#include "sec_nfc.h"
#include "./nfc_logger/nfc_logger.h"

#define SEC_NFC_GET_INFO(dev) i2c_get_clientdata(to_i2c_client(dev))

enum sec_nfc_irq {
	SEC_NFC_SKIP = -1,
	SEC_NFC_NONE,
	SEC_NFC_INT,
	SEC_NFC_READ_TIMES,
};

struct sec_nfc_i2c_info {
	struct i2c_client *i2c_dev;
	struct mutex read_mutex;
	enum sec_nfc_irq read_irq;
	wait_queue_head_t read_wait;
	size_t buflen;
	u8 *buf;
	u8 parity;
};

struct sec_nfc_info {
	struct miscdevice miscdev;
	struct mutex mutex;
	enum sec_nfc_mode mode;
	struct device *dev;
	struct sec_nfc_platform_data *pdata;
	struct sec_nfc_i2c_info i2c_info;
	struct wake_lock nfc_wake_lock;
	bool clk_ctl;
	bool clk_state;
	struct platform_device *pdev;
};

#define FEATURE_SEC_NFC_TEST
#ifdef FEATURE_SEC_NFC_TEST
static struct sec_nfc_info *g_nfc_info;
static bool on_nfc_test;
static bool nfc_int_wait;
#endif
static irqreturn_t sec_nfc_irq_thread_fn(int irq, void *dev_id)
{
	struct sec_nfc_info *info = dev_id;
	struct sec_nfc_platform_data *pdata = info->pdata;

	NFC_LOG_REC("irq\n");

#ifdef FEATURE_SEC_NFC_TEST
	if (on_nfc_test) {
		nfc_int_wait = true;
		NFC_LOG_INFO("NFC_TEST: interrupt is raised\n");
		wake_up_interruptible(&info->i2c_info.read_wait);
		return IRQ_HANDLED;
	}
#endif

	if (gpio_get_value(pdata->irq) == 0) {
		NFC_LOG_REC("irq-gpio state is low!\n");
		return IRQ_HANDLED;
	}
	mutex_lock(&info->i2c_info.read_mutex);
	/* Skip interrupt during power switching
	 * It is released after first write
	 */
	if (info->i2c_info.read_irq == SEC_NFC_SKIP) {
		NFC_LOG_REC("Now power swiching. Skip this IRQ\n");
		mutex_unlock(&info->i2c_info.read_mutex);
		return IRQ_HANDLED;
	}

	info->i2c_info.read_irq += SEC_NFC_READ_TIMES;
	mutex_unlock(&info->i2c_info.read_mutex);

	wake_up_interruptible(&info->i2c_info.read_wait);
	wake_lock_timeout(&info->nfc_wake_lock, 2*HZ);

	return IRQ_HANDLED;
}

static int nfc_state_print(struct sec_nfc_info *info)
{
	struct sec_nfc_platform_data *pdata = info->pdata;
	struct regulator *regulator_nfc_pvdd;

	int en = gpio_get_value(info->pdata->ven);
	int firm =	gpio_get_value(info->pdata->firm);
	int irq = gpio_get_value(info->pdata->irq);
	int pvdd = 0;

	if (!pdata->nfc_pvdd)
		return -ENODEV;

	regulator_nfc_pvdd = regulator_get(NULL, pdata->nfc_pvdd);
	if (IS_ERR(regulator_nfc_pvdd) || regulator_nfc_pvdd == NULL) {
		NFC_LOG_ERR("%s - nfc_pvdd regulator_get fail\n", __func__);
		return -ENODEV;
	}
	pvdd = regulator_is_enabled(regulator_nfc_pvdd);

	NFC_LOG_INFO("%s en: %d, firm: %d power: %d irq: %d\n", __func__, en, firm, pvdd, irq);
	NFC_LOG_INFO("%s mode %d, clk_state: %d\n", __func__, info->mode, info->clk_state);

	regulator_put(regulator_nfc_pvdd);

	return 0;
}

static ssize_t sec_nfc_read(struct file *file, char __user *buf,
				size_t count, loff_t *ppos)
{
	struct sec_nfc_info *info = container_of(file->private_data,
						struct sec_nfc_info, miscdev);
	enum sec_nfc_irq irq;
	int ret = 0;

#ifdef FEATURE_SEC_NFC_TEST
	if (on_nfc_test)
		return 0;
#endif

	mutex_lock(&info->mutex);

	if (info->mode == SEC_NFC_MODE_OFF) {
		NFC_LOG_ERR("read() nfc is not enabled\n");
		ret = -ENODEV;
		goto out;
	}

	mutex_lock(&info->i2c_info.read_mutex);
	if (count == 0) {
		if (info->i2c_info.read_irq >= SEC_NFC_INT)
			info->i2c_info.read_irq--;
		mutex_unlock(&info->i2c_info.read_mutex);
		goto out;
	}

	irq = info->i2c_info.read_irq;
	mutex_unlock(&info->i2c_info.read_mutex);
	if (irq == SEC_NFC_NONE) {
		if (file->f_flags & O_NONBLOCK) {
			NFC_LOG_ERR("read() it is nonblock\n");
			ret = -EAGAIN;
			goto out;
		}
	}

	/* i2c recv */
	if (count > info->i2c_info.buflen)
		count = info->i2c_info.buflen;

	if (count > SEC_NFC_MSG_MAX_SIZE) {
		NFC_LOG_ERR("read() user required wrong size :%d\n", (u32)count);
		ret = -EINVAL;
		goto out;
	}

	NFC_LOG_REC("read(%zu)\n", count);
	mutex_lock(&info->i2c_info.read_mutex);
	memset(info->i2c_info.buf, 0, count);
	ret = i2c_master_recv(info->i2c_info.i2c_dev, info->i2c_info.buf, (u32)count);

	if (ret == -EREMOTEIO) {
		ret = -ERESTART;
		goto read_error;
	} else if (ret != count) {
		NFC_LOG_ERR("read failed: return: %d count: %d\n",
			ret, (u32)count);
		/*ret = -EREMOTEIO;*/
		goto read_error;
	}

	if (info->i2c_info.read_irq >= SEC_NFC_INT)
		info->i2c_info.read_irq--;

	if (info->i2c_info.read_irq == SEC_NFC_READ_TIMES)
		wake_up_interruptible(&info->i2c_info.read_wait);

	mutex_unlock(&info->i2c_info.read_mutex);

	if (copy_to_user(buf, info->i2c_info.buf, ret)) {
		NFC_LOG_ERR("read() copy failed to user\n");
		ret = -EFAULT;
	}

	goto out;

read_error:
	NFC_LOG_ERR("read error %d\n", ret);
	nfc_state_print(info);
	info->i2c_info.read_irq = SEC_NFC_NONE;
	mutex_unlock(&info->i2c_info.read_mutex);
out:
	mutex_unlock(&info->mutex);

	return ret;
}

static ssize_t sec_nfc_write(struct file *file, const char __user *buf,
				size_t count, loff_t *ppos)
{
	struct sec_nfc_info *info = container_of(file->private_data,
						struct sec_nfc_info, miscdev);
	int ret = 0;
	int wire = 0;

	NFC_LOG_DBG("write() count %d\n", (u32)count);

#ifdef FEATURE_SEC_NFC_TEST
	if (on_nfc_test)
		return 0;
#endif

	mutex_lock(&info->mutex);

	if (info->mode == SEC_NFC_MODE_OFF) {
		NFC_LOG_ERR("write() nfc is not enabled\n");
		ret = -ENODEV;
		goto out;
	}

	if (count > info->i2c_info.buflen)
		count = info->i2c_info.buflen;

	if (count > SEC_NFC_MSG_MAX_SIZE) {
		NFC_LOG_ERR("write() user required wrong size :%d\n", (u32)count);
		ret = -EINVAL;
		goto out;
	}

	if (copy_from_user(info->i2c_info.buf, buf, count)) {
		NFC_LOG_ERR("write() copy failed from user\n");
		ret = -EFAULT;
		goto out;
	}

	/*
	 * NUXEL NFC transport:
	 *
	 * The uapi says this file is an unframed NCI (or firmware-mode)
	 * byte stream.  The vendor driver wrote the caller's buffer as one
	 * I2C transfer without the per-packet parity bit that the controller
	 * requires.  The only historical user also mangled bit 7 of byte 0 by
	 * hand, and could corrupt a multi-byte write because it alternated
	 * after every partial write() call.
	 *
	 * Frame every write here so header/payload boundaries are preserved:
	 *   normal NCI mode : bit 7 toggles per control packet,
	 *   bootloader mode : fixed parity 0 (the vendor wrote 0x80 there only
	 *                     because their mode sequence left the bit set).
	 * Reads are always plain I2C.  Callers therefore see standard NCI
	 * bytes and never have to mutate frame headers.
	 */
	while (wire < count) {
		u8 frame[SEC_NFC_MAX_BUFFER_SIZE];
		size_t avail = count - wire;
		size_t hdr = info->mode == SEC_NFC_MODE_BOOTLOADER ? 4 : 3;
		size_t plen;
		size_t flen;

		if (avail < hdr) {
			NFC_LOG_ERR("write() truncated frame (%zu bytes)\n", avail);
			ret = -EINVAL;
			goto write_error;
		}
		if (hdr == 4)
			plen = ((size_t)info->i2c_info.buf[wire + 2]) |
			       ((size_t)info->i2c_info.buf[wire + 3] << 8);
		else
			plen = info->i2c_info.buf[wire + 2];
		flen = hdr + plen;
		if (flen > avail || flen > sizeof(frame)) {
			NFC_LOG_ERR("write() bad frame length %zu/%zu\n", flen, avail);
			ret = -EINVAL;
			goto write_error;
		}

		memcpy(frame, info->i2c_info.buf + wire, flen);
		if (info->mode == SEC_NFC_MODE_BOOTLOADER)
			frame[0] &= 0x7f;
		else
			frame[0] = (frame[0] & 0x7f) | info->i2c_info.parity;

		/* Skip interrupt during power switching; released by this write. */
		NFC_LOG_REC("write(%zu)\n", flen);
		mutex_lock(&info->i2c_info.read_mutex);
		ret = i2c_master_send(info->i2c_info.i2c_dev, frame, flen);
		if (info->i2c_info.read_irq == SEC_NFC_SKIP)
			info->i2c_info.read_irq = SEC_NFC_NONE;
		mutex_unlock(&info->i2c_info.read_mutex);

		if (ret == -EREMOTEIO || ret != flen) {
			NFC_LOG_ERR("write failed: return: %d count: %zu\n",
				ret, flen);
			ret = ret == -EREMOTEIO ? -ERESTART : -EREMOTEIO;
			goto write_error;
		}

		if (info->mode != SEC_NFC_MODE_BOOTLOADER)
			info->i2c_info.parity ^= 0x80;
		wire += flen;
	}

	ret = count;
	goto out;

write_error:
	nfc_state_print(info);
out:
	mutex_unlock(&info->mutex);

	return ret;
}

static unsigned int sec_nfc_poll(struct file *file, poll_table *wait)
{
	struct sec_nfc_info *info = container_of(file->private_data,
						struct sec_nfc_info, miscdev);
	enum sec_nfc_irq irq;

	int ret = 0;

	mutex_lock(&info->mutex);

	if (info->mode == SEC_NFC_MODE_OFF) {
		NFC_LOG_ERR("poll() nfc is not enabled\n");
		ret = -ENODEV;
		goto out;
	}

	poll_wait(file, &info->i2c_info.read_wait, wait);

	mutex_lock(&info->i2c_info.read_mutex);
	irq = info->i2c_info.read_irq;
	if (irq == SEC_NFC_READ_TIMES)
		ret = (POLLIN | POLLRDNORM);
	mutex_unlock(&info->i2c_info.read_mutex);

out:
	mutex_unlock(&info->mutex);

	return ret;
}

static int sec_nfc_regulator_onoff(struct sec_nfc_platform_data *data, int onoff)
{
	int rc = 0;
	struct regulator *regulator_nfc_pvdd;

	if (!data->nfc_pvdd)
		return -ENODEV;

	regulator_nfc_pvdd = regulator_get(NULL, data->nfc_pvdd);
	if (IS_ERR(regulator_nfc_pvdd) || regulator_nfc_pvdd == NULL) {
		NFC_LOG_ERR("nfc_pvdd regulator_get fail\n");
		return -ENODEV;
	}

	NFC_LOG_INFO("regulator onoff = %d\n", onoff);

	if (onoff == NFC_I2C_LDO_ON) {
		rc = regulator_enable(regulator_nfc_pvdd);
		if (rc) {
			NFC_LOG_ERR("regulator enable nfc_pvdd failed, rc=%d\n", rc);
			goto done;
		}
	} else {
		rc = regulator_disable(regulator_nfc_pvdd);
		if (rc) {
			NFC_LOG_ERR("regulator disable nfc_pvdd failed, rc=%d\n", rc);
			goto done;
		}
	}

done:
	regulator_put(regulator_nfc_pvdd);

	return rc;
}

void sec_nfc_i2c_irq_clear(struct sec_nfc_info *info)
{
	/* clear interrupt. Interrupt will be occurred at power off */
	mutex_lock(&info->i2c_info.read_mutex);
	info->i2c_info.read_irq = SEC_NFC_NONE;
	mutex_unlock(&info->i2c_info.read_mutex);
}

int sec_nfc_i2c_probe(struct i2c_client *client)
{
	struct device *dev = &client->dev;
	struct sec_nfc_info *info = dev_get_drvdata(dev);
	struct sec_nfc_platform_data *pdata = info->pdata;
	int ret;

	NFC_LOG_INFO("probe() start\n");

	if (!gpio_is_valid(pdata->irq) || client->irq <= 0) {
		NFC_LOG_ERR("probe() invalid IRQ (%d) or IRQ GPIO (%d)\n",
			    client->irq, pdata->irq);
		return -ENODEV;
	}

	info->i2c_info.buflen = SEC_NFC_MAX_BUFFER_SIZE;
	info->i2c_info.buf = kzalloc(SEC_NFC_MAX_BUFFER_SIZE, GFP_KERNEL);
	if (!info->i2c_info.buf) {
		NFC_LOG_ERR("probe() failed to allocate memory\n");
		return -ENOMEM;
	}
	info->i2c_info.i2c_dev = client;
	info->i2c_info.read_irq = SEC_NFC_NONE;
	mutex_init(&info->i2c_info.read_mutex);
	init_waitqueue_head(&info->i2c_info.read_wait);
	i2c_set_clientdata(client, info);

	ret = gpio_request(pdata->irq, "nfc_int");
	if (ret) {
		NFC_LOG_ERR("probe() GPIO request is failed to register IRQ\n");
		goto err_irq_req;
	}
	gpio_direction_input(pdata->irq);

	ret = request_threaded_irq(client->irq, NULL, sec_nfc_irq_thread_fn,
			IRQF_TRIGGER_RISING | IRQF_ONESHOT, SEC_NFC_DRIVER_NAME,
			info);
	if (ret < 0) {
		NFC_LOG_ERR("probe() failed to register IRQ handler\n");
		goto err_irq_handler;
	}

	if (of_get_property(dev->of_node, "sec-nfc,ldo_control", NULL)) {
		if (pdata->nfc_pvdd != NULL) {
			if (!lpcharge) {
				ret = sec_nfc_regulator_onoff(pdata, NFC_I2C_LDO_ON);
				if (ret < 0)
					NFC_LOG_ERR("max86900_regulator_on fail err = %d\n", ret);
				usleep_range(1000, 1100);
			}
		}
	}

	NFC_LOG_INFO("probe() success\n");
	return 0;

err_irq_handler:
	gpio_free(pdata->irq);
err_irq_req:
	kfree(info->i2c_info.buf);
	info->i2c_info.buf = NULL;
	return ret;
}

static irqreturn_t sec_nfc_clk_irq_thread(int irq, void *dev_id)
{
	struct sec_nfc_info *info = dev_id;
	struct sec_nfc_platform_data *pdata = info->pdata;
	bool value;

	value = gpio_get_value(pdata->clk_req) > 0 ? true : false;
	NFC_LOG_REC("clock req: %d\n", value);

	if (value == info->clk_state)
		return IRQ_HANDLED;

	if (value) {
		int ret = clk_prepare_enable(pdata->clk);

		if (ret) {
			NFC_LOG_ERR("clock enable failed\n");
			return IRQ_HANDLED;
		}
		info->clk_state = true;
	} else {
		/*
		 * NUXEL (beyond2lte): the clk_req line toggles per frame and
		 * this part NACKs the very next I2C read if the 26 MHz reference
		 * is gated between frames (measured: write ACK, reply IRQ, then
		 * -EREMOTEIO on read).  Keep the reference on for the whole
		 * open session; sec_nfc_clk_ctl_disable() turns it off when the
		 * device is closed or switched to OFF.
		 */
		if (!info->clk_ctl)
			info->clk_state = false;
	}

	return IRQ_HANDLED;
}

void sec_nfc_clk_ctl_enable(struct sec_nfc_info *info)
{
	struct sec_nfc_platform_data *pdata = info->pdata;

	if (info->clk_ctl)
		return;

	if (!pdata->clk)
		return;

	/* NUXEL: do not clear clk_state — sec_nfc_set_mode() may have already
	 * force-enabled the reference clock for this session. */
	enable_irq(pdata->clk_irq);
	info->clk_ctl = true;
}

void sec_nfc_clk_ctl_disable(struct sec_nfc_info *info)
{
	struct sec_nfc_platform_data *pdata = info->pdata;

	if (!info->clk_ctl)
		return;

	if (!pdata->clk)
		return;

	disable_irq(pdata->clk_irq);
	if (info->clk_state)
		clk_disable_unprepare(pdata->clk);

	info->clk_state = false;
	info->clk_ctl = false;
}

static void sec_nfc_set_mode(struct sec_nfc_info *info,
					enum sec_nfc_mode mode)
{
	struct sec_nfc_platform_data *pdata = info->pdata;

	/* intfo lock is aleady gotten before calling this function */
	if (info->mode == mode) {
		NFC_LOG_DBG("power mode is already %d", mode);
		return;
	}
	info->mode = mode;

	/* Skip interrupt during power switching
	 * It is released after first write
	 */
	mutex_lock(&info->i2c_info.read_mutex);
	info->i2c_info.read_irq = SEC_NFC_SKIP;
	mutex_unlock(&info->i2c_info.read_mutex);

	gpio_set_value(pdata->ven, SEC_NFC_PW_OFF);
	if (pdata->firm)
		gpio_set_value(pdata->firm, SEC_NFC_FW_OFF);

	if (mode == SEC_NFC_MODE_BOOTLOADER)
		if (pdata->firm)
			gpio_set_value(pdata->firm, SEC_NFC_FW_ON);

	if (mode != SEC_NFC_MODE_OFF) {
		int cret;

		msleep(SEC_NFC_VEN_WAIT_TIME);
		gpio_set_value(pdata->ven, SEC_NFC_PW_ON);
		/*
		 * NUXEL (beyond2lte): this S3NRN82 does not assert clk_req
		 * before it is clocked, so waiting for the clk_req IRQ leaves
		 * the 26 MHz reference permanently off and every I2C write
		 * NACKs (-ENXIO).  Force the reference clock on for every
		 * non-OFF mode; the clk_req handler keeps owning dynamic
		 * gating afterwards.
		 */
		if (pdata->clk) {
			cret = clk_prepare_enable(pdata->clk);
			if (!cret)
				info->clk_state = true;
			NFC_LOG_INFO("NUXEL: force oscclk_nfc enable = %d (%lu Hz)\n",
				     cret, (unsigned long)clk_get_rate(pdata->clk));
		}
		sec_nfc_clk_ctl_enable(info);
		enable_irq_wake(info->i2c_info.i2c_dev->irq);
		msleep(SEC_NFC_VEN_WAIT_TIME/2);
	} else {
		sec_nfc_clk_ctl_disable(info);
		disable_irq_wake(info->i2c_info.i2c_dev->irq);
	}

	if (wake_lock_active(&info->nfc_wake_lock))
		wake_unlock(&info->nfc_wake_lock);

	NFC_LOG_INFO("NFC mode is : %d\n", mode);
}

static long sec_nfc_ioctl(struct file *file, unsigned int cmd,
							unsigned long arg)
{
	struct sec_nfc_info *info = container_of(file->private_data,
						struct sec_nfc_info, miscdev);
	struct sec_nfc_platform_data *pdata = info->pdata;
	unsigned int new = (unsigned int)arg;
	int ret = 0;

	NFC_LOG_DBG("cmd: 0x%x\n", cmd);

	mutex_lock(&info->mutex);

	switch (cmd) {
	case SEC_NFC_DEBUG:
		NFC_LOG_ERR("SEC_NFC_DEBUG\n");
		nfc_state_print(info);
		break;
	case SEC_NFC_SET_MODE:
		if (info->mode == new)
			break;

		if (new >= SEC_NFC_MODE_COUNT) {
			NFC_LOG_ERR("wrong mode (%d)\n", new);
			ret = -EFAULT;
			break;
		}
		sec_nfc_set_mode(info, new);

		break;

	case SEC_NFC_SLEEP:
		if (info->mode != SEC_NFC_MODE_BOOTLOADER) {
			if (wake_lock_active(&info->nfc_wake_lock))
				wake_unlock(&info->nfc_wake_lock);
			gpio_set_value(pdata->wake, SEC_NFC_WAKE_SLEEP);
		}
		break;

	case SEC_NFC_WAKEUP:
		if (info->mode != SEC_NFC_MODE_BOOTLOADER) {
			gpio_set_value(pdata->wake, SEC_NFC_WAKE_UP);
			if (!wake_lock_active(&info->nfc_wake_lock))
				wake_lock(&info->nfc_wake_lock);
		}
		break;

// [START] NPT
	case SEC_NFC_SET_NPT_MODE:
		NFC_LOG_INFO("NPT: VEN=%d, FIRM:%d\n", gpio_get_value(pdata->ven),
					gpio_get_value(pdata->firm));

		if (new == SEC_NFC_NPT_CMD_ON) {
			NFC_LOG_INFO("NPT: NFC OFF mode NPT - Turn on VEN.\n");
			info->mode = SEC_NFC_MODE_FIRMWARE;
			mutex_lock(&info->i2c_info.read_mutex);
			info->i2c_info.read_irq = SEC_NFC_SKIP;
			mutex_unlock(&info->i2c_info.read_mutex);
			gpio_set_value(pdata->ven, SEC_NFC_PW_ON);
			sec_nfc_clk_ctl_enable(info);
			msleep(20);
			gpio_set_value(pdata->firm, SEC_NFC_FW_ON);
			enable_irq_wake(info->i2c_info.i2c_dev->irq);
		} else if (new == SEC_NFC_NPT_CMD_OFF) {
			NFC_LOG_INFO("NPT: NFC OFF mode NPT - Turn off VEN.\n");
			info->mode = SEC_NFC_MODE_OFF;
			gpio_set_value(pdata->firm, SEC_NFC_FW_OFF);
			gpio_set_value(pdata->ven, SEC_NFC_PW_OFF);
			sec_nfc_clk_ctl_disable(info);
			disable_irq_wake(info->i2c_info.i2c_dev->irq);
		}
		break;
// [END] NPT

	default:
		NFC_LOG_ERR("NPT: Unknown ioctl 0x%x\n", cmd);
		ret = -ENOIOCTLCMD;
		break;
	}

	mutex_unlock(&info->mutex);

	return ret;
}

static int sec_nfc_open(struct inode *inode, struct file *file)
{
	struct sec_nfc_info *info = container_of(file->private_data,
						struct sec_nfc_info, miscdev);
	int ret = 0;

	NFC_LOG_INFO("%s\n", __func__);

#ifdef CONFIG_ESE_SECURE
	/*
	 * NUXEL (SM-G975F, beyond2lte): the TEE eSE check gates the *embedded
	 * Secure Element* (Samsung Pay / payment), not the NFC reader.  The TEE
	 * on this Nuxel image reports the eSE is not secured, and the vendor
	 * driver then refuses to open the *NFC* misc device at all.  Nuxel does
	 * not support payment/eSE, so the eSE state is recorded as "not
	 * secured" without invoking the TEE (the call also trips the kernel
	 * open path on this image, see nfc3.md), and the NFC reader stays
	 * usable.  Any eSE consumer must check nfc_ese_secured itself.
	 */
	if (nfc_ese_secured == NOT_CHECKED)
		nfc_ese_secured = ESE_NOT_SECURED;
	if (nfc_ese_secured == ESE_NOT_SECURED)
		NFC_LOG_DBG("NUXEL: eSE not secured; NFC reader path continues\n");
#endif

	if (!info) {
		NFC_LOG_ERR("NUXEL: open() without driver data\n");
		return -ENODEV;
	}

	mutex_lock(&info->mutex);
	if (info->mode != SEC_NFC_MODE_OFF) {
		NFC_LOG_ERR("open() nfc is busy\n");
		nfc_state_print(info);
		ret = -EBUSY;
		goto out;
	}

	sec_nfc_set_mode(info, SEC_NFC_MODE_OFF);
	info->i2c_info.parity = 0;

out:
	mutex_unlock(&info->mutex);
	return ret;
}

static int sec_nfc_close(struct inode *inode, struct file *file)
{
	struct sec_nfc_info *info = container_of(file->private_data,
						struct sec_nfc_info, miscdev);

	nfc_state_print(info);

	NFC_LOG_INFO("%s\n", __func__);

	mutex_lock(&info->mutex);
	sec_nfc_set_mode(info, SEC_NFC_MODE_OFF);
	mutex_unlock(&info->mutex);

	return 0;
}

static const struct file_operations sec_nfc_fops = {
	.owner		= THIS_MODULE,
	.read		= sec_nfc_read,
	.write		= sec_nfc_write,
	.poll		= sec_nfc_poll,
	.open		= sec_nfc_open,
	.release	= sec_nfc_close,
	.unlocked_ioctl	= sec_nfc_ioctl,
};

#ifdef CONFIG_PM
static int sec_nfc_suspend(struct device *dev)
{
	struct sec_nfc_info *info = SEC_NFC_GET_INFO(dev);
	int ret = 0;

	mutex_lock(&info->mutex);

	if (info->mode == SEC_NFC_MODE_BOOTLOADER)
		ret = -EPERM;

	mutex_unlock(&info->mutex);

	return ret;
}

static int sec_nfc_resume(struct device *dev)
{
	return 0;
}

static SIMPLE_DEV_PM_OPS(sec_nfc_pm_ops, sec_nfc_suspend, sec_nfc_resume);
#endif

/*device tree parsing*/
static int sec_nfc_parse_dt(struct device *dev,
	struct sec_nfc_platform_data *pdata)
{
	struct device_node *np = dev->of_node;

	pdata->ven = of_get_named_gpio(np, "sec-nfc,ven-gpio", 0);
	pdata->firm = of_get_named_gpio(np, "sec-nfc,firm-gpio", 0);
	pdata->wake = pdata->firm;
	pdata->irq = of_get_named_gpio(np, "sec-nfc,irq-gpio", 0);
	pdata->clk = NULL;
	pdata->clk_irq = -1;
	pdata->nfc_pvdd = NULL;

	if (!gpio_is_valid(pdata->ven) || !gpio_is_valid(pdata->firm) ||
	    !gpio_is_valid(pdata->irq)) {
		NFC_LOG_ERR("parse_dt() missing ven/firm/irq GPIO\n");
		return -EINVAL;
	}

	if (of_get_property(dev->of_node, "sec-nfc,nfc_ap_clk", NULL)) {
		pdata->clk_req = of_get_named_gpio(np, "sec-nfc,clk_req-gpio", 0);
		if (!gpio_is_valid(pdata->clk_req)) {
			NFC_LOG_ERR("parse_dt() invalid clk_req GPIO\n");
			return -EINVAL;
		}
		NFC_LOG_INFO("parse_dt() clk_req : %d\n", pdata->clk_req);
	}

	if (of_get_property(dev->of_node, "sec-nfc,ldo_control", NULL)) {
		if (of_property_read_string(np, "sec-nfc,nfc_pvdd",
					&pdata->nfc_pvdd) < 0) {
			NFC_LOG_ERR("parse_dt() get nfc_pvdd error\n");
			return -EINVAL;
		}
	}

	NFC_LOG_INFO("parse_dt() irq : %d, ven : %d, firm : %d\n",
			pdata->irq, pdata->ven, pdata->firm);

	return 0;
}

#ifdef FEATURE_SEC_NFC_TEST
static int sec_nfc_i2c_read(char *buf, int count)
{
	struct sec_nfc_info *info = g_nfc_info;
	int ret = 0;

	mutex_lock(&info->mutex);

	if (info->mode == SEC_NFC_MODE_OFF) {
		NFC_LOG_ERR("NFC_TEST: sec_nfc is not enabled\n");
		ret = -ENODEV;
		goto out;
	}

	/* i2c recv */
	if (count > info->i2c_info.buflen)
		count = info->i2c_info.buflen;

	if (count > SEC_NFC_MSG_MAX_SIZE) {
		NFC_LOG_ERR("NFC_TEST: user required wrong size :%d\n", (u32)count);
		ret = -EINVAL;
		goto out;
	}

	mutex_lock(&info->i2c_info.read_mutex);
	memset(buf, 0, count);
	ret = i2c_master_recv(info->i2c_info.i2c_dev, buf, (u32)count);
	NFC_LOG_INFO("NFC_TEST: recv size : %d\n", ret);

	if (ret == -EREMOTEIO) {
		ret = -ERESTART;
		goto read_error;
	} else if (ret != count) {
		NFC_LOG_ERR("NFC_TEST: read failed: return: %d count: %d\n",
			ret, (u32)count);
		goto read_error;
	}

	mutex_unlock(&info->i2c_info.read_mutex);

	goto out;

read_error:
	info->i2c_info.read_irq = SEC_NFC_NONE;
	mutex_unlock(&info->i2c_info.read_mutex);
out:
	mutex_unlock(&info->mutex);

	return ret;
}

static int sec_nfc_i2c_write(char *buf,	int count)
{
	struct sec_nfc_info *info = g_nfc_info;
	int ret = 0;

	mutex_lock(&info->mutex);

	if (info->mode == SEC_NFC_MODE_OFF) {
		NFC_LOG_ERR("NFC_TEST: sec_nfc is not enabled\n");
		ret = -ENODEV;
		goto out;
	}

	if (count > info->i2c_info.buflen)
		count = info->i2c_info.buflen;

	if (count > SEC_NFC_MSG_MAX_SIZE) {
		NFC_LOG_ERR("NFC_TEST: user required wrong size :%d\n", (u32)count);
		ret = -EINVAL;
		goto out;
	}

	mutex_lock(&info->i2c_info.read_mutex);
	ret = i2c_master_send(info->i2c_info.i2c_dev, buf, count);
	mutex_unlock(&info->i2c_info.read_mutex);

	if (ret == -EREMOTEIO) {
		NFC_LOG_ERR("NFC_TEST: send failed: return: %d count: %d\n",
		ret, (u32)count);
		ret = -ERESTART;
		goto out;
	}

	if (ret != count) {
		NFC_LOG_ERR("NFC_TEST: send failed: return: %d count: %d\n",
		ret, (u32)count);
		ret = -EREMOTEIO;
	}

out:
	mutex_unlock(&info->mutex);

	return ret;
}

static ssize_t test_show(struct class *class,
					struct class_attribute *attr,
					char *buf)
{
	char cmd[8] = {0x0, 0x1, 0x0, 0x0,}; /*bootloader fw check*/
	enum sec_nfc_mode old_mode = g_nfc_info->mode;
	int size;
	int ret = 0;
	int timeout = 1;

	on_nfc_test = true;
	nfc_int_wait = false;
	NFC_LOG_INFO("NFC_TEST: mode = %d\n", old_mode);

	sec_nfc_set_mode(g_nfc_info, SEC_NFC_MODE_BOOTLOADER);
	ret = sec_nfc_i2c_write(cmd, 4);
	if (ret < 0) {
		NFC_LOG_INFO("NFC_TEST: i2c write error %d\n", ret);
		size = sprintf(buf, "NFC_TEST: i2c write error %d\n", ret);
		goto exit;
	}

	timeout = wait_event_interruptible_timeout(g_nfc_info->i2c_info.read_wait, nfc_int_wait, 100);
	ret = sec_nfc_i2c_read(buf, 16);
	if (ret < 0) {
		NFC_LOG_INFO("NFC_TEST: i2c read error %d\n", ret);
		size = sprintf(buf, "NFC_TEST: i2c read error %d\n", ret);
		goto exit;
	}

	NFC_LOG_INFO("NFC_TEST: BL ver: %02X %02X %02X %02X, INT: %s\n", buf[0],
				buf[1],	buf[2], buf[3], timeout ? "OK":"NOK");
	size = sprintf(buf, "BL ver: %02X.%02X.%02X.%02X, INT: %s\n", buf[0],
				buf[1], buf[2],	buf[3], timeout ? "OK":"NOK");

exit:
	sec_nfc_set_mode(g_nfc_info, old_mode);
	on_nfc_test = false;

	return size;
}

static CLASS_ATTR_RO(test);
#endif

static ssize_t nfc_support_show(struct class *class,
		struct class_attribute *attr, char *buf)
{
	NFC_LOG_INFO("\n");
	return 0;
}
static CLASS_ATTR_RO(nfc_support);

static int __sec_nfc_probe(struct device *dev)
{
	struct sec_nfc_info *info;
	struct sec_nfc_platform_data *pdata = NULL;
	int ret = 0;

#ifdef FEATURE_SEC_NFC_TEST
	struct class *nfc_class;
#endif
	NFC_LOG_INFO("probe start\n");
	if (dev->of_node) {
		pdata = devm_kzalloc(dev,
			sizeof(struct sec_nfc_platform_data), GFP_KERNEL);
		if (!pdata) {
			NFC_LOG_ERR("probe() Failed to allocate memory\n");
			return -ENOMEM;
		}
		ret = sec_nfc_parse_dt(dev, pdata);
		if (ret)
			return ret;
	} else {
		pdata = dev->platform_data;
	}

	if (!pdata) {
		NFC_LOG_ERR("probe() No platform data\n");
		ret = -ENOMEM;
		goto err_pdata;
	}

	info = kzalloc(sizeof(struct sec_nfc_info), GFP_KERNEL);
	if (!info) {
		NFC_LOG_ERR("probe() failed to allocate memory for sec_nfc_info\n");
		ret = -ENOMEM;
		goto err_info_alloc;
	}
	info->dev = dev;
	info->pdata = pdata;
	info->mode = SEC_NFC_MODE_OFF;

	mutex_init(&info->mutex);
	dev_set_drvdata(dev, info);

	info->miscdev.minor = MISC_DYNAMIC_MINOR;
	info->miscdev.name = SEC_NFC_DRIVER_NAME;
	info->miscdev.fops = &sec_nfc_fops;
	info->miscdev.parent = dev;
	ret = misc_register(&info->miscdev);
	if (ret < 0) {
		NFC_LOG_ERR("probe() failed to register Device\n");
		goto err_dev_reg;
	}

	if (of_get_property(dev->of_node, "sec-nfc,nfc_ap_clk", NULL)) {
		pdata->clk = clk_get(dev, "oscclk_nfc");
		if (IS_ERR(pdata->clk)) {
			NFC_LOG_ERR("probe() clk not found\n");
			pdata->clk = NULL;
			goto err_gpio_clk_parse;
		}
		pdata->clk_irq = gpio_to_irq(pdata->clk_req);
		if (pdata->clk_irq < 0) {
			pdata->clk_irq = -1;
			goto err_gpio_clk_parse;
		}

		ret = request_threaded_irq(pdata->clk_irq, NULL, sec_nfc_clk_irq_thread,
				IRQF_TRIGGER_RISING | IRQF_TRIGGER_FALLING | IRQF_ONESHOT,
				SEC_NFC_DRIVER_NAME, info);
		if (ret < 0) {
			NFC_LOG_ERR("probe() failed to register CLK REQ IRQ handler\n");
			pdata->clk_irq = -1;
			goto err_gpio_clk_parse;
		}
		disable_irq(pdata->clk_irq);
	}

	ret = gpio_request(pdata->ven, "nfc_ven");
	if (ret) {
		NFC_LOG_ERR("probe() failed to get gpio ven\n");
		goto err_gpio_ven;
	}
	gpio_direction_output(pdata->ven, SEC_NFC_PW_OFF);

	if (pdata->firm) {
		ret = gpio_request(pdata->firm, "nfc_firm");
		if (ret) {
			NFC_LOG_ERR("probe() failed to get gpio firm\n");
			goto err_gpio_firm;
		}
		gpio_direction_output(pdata->firm, SEC_NFC_FW_OFF);
	}

	wake_lock_init(&info->nfc_wake_lock, WAKE_LOCK_SUSPEND, "nfc_wake_lock");

#ifdef FEATURE_SEC_NFC_TEST
	g_nfc_info = info;
	nfc_class = class_create(THIS_MODULE, "nfc_test");
	if (IS_ERR(&nfc_class))
		NFC_LOG_ERR("NFC: failed to create nfc_test class\n");
	else {
		ret = class_create_file(nfc_class, &class_attr_test);
		if (ret)
			NFC_LOG_ERR("NFC: failed to create attr_test\n");
	}
#endif
	/*
	 * NUXEL: with CONFIG_NFC=y the generic NFC core already registers
	 * /sys/class/nfc.  Creating a second class with the same name makes
	 * sysfs_warn_dup() BUG and panics the kernel during early boot
	 * (measured 2026-11-01).  Keep the vendor support attribute under a
	 * device-private class name instead of colliding with the subsystem.
	 */
	nfc_class = class_create(THIS_MODULE, "sec_nfc");
	if (IS_ERR(&nfc_class))
		NFC_LOG_ERR("NFC: failed to create nfc class\n");
	else {
		ret = class_create_file(nfc_class, &class_attr_nfc_support);
		if (ret)
			NFC_LOG_ERR("NFC: failed to create attr_nfc_support\n");
	}

	NFC_LOG_INFO("probe() success\n");

	return 0;

err_gpio_firm:
	gpio_free(pdata->ven);
err_gpio_ven:
	if (pdata->clk_irq >= 0)
		free_irq(pdata->clk_irq, info);
	if (pdata->clk) {
		clk_put(pdata->clk);
		pdata->clk = NULL;
	}
err_gpio_clk_parse:
	misc_deregister(&info->miscdev);
err_dev_reg:
	mutex_destroy(&info->mutex);
	kfree(info);
err_info_alloc:
	devm_kfree(dev, pdata);
err_pdata:
	return ret;
}

static int __sec_nfc_remove(struct device *dev)
{
	struct sec_nfc_info *info = dev_get_drvdata(dev);
	struct i2c_client *client = info->i2c_info.i2c_dev;
	struct sec_nfc_platform_data *pdata = info->pdata;

	NFC_LOG_DBG("remove\n");

	sec_nfc_set_mode(info, SEC_NFC_MODE_OFF);
	misc_deregister(&info->miscdev);
	if (client->irq > 0)
		free_irq(client->irq, info);
	if (pdata->clk_irq >= 0)
		free_irq(pdata->clk_irq, info);
	if (pdata->clk)
		clk_put(pdata->clk);
	if (gpio_is_valid(pdata->irq))
		gpio_free(pdata->irq);
	if (gpio_is_valid(pdata->firm))
		gpio_free(pdata->firm);
	if (gpio_is_valid(pdata->ven))
		gpio_free(pdata->ven);

	wake_lock_destroy(&info->nfc_wake_lock);
	kfree(info->i2c_info.buf);
	kfree(info);

	return 0;
}

MODULE_DEVICE_TABLE(i2c, sec_nfc_id_table);
#define SEC_NFC_INIT(driver)	i2c_add_driver(driver)
#define SEC_NFC_EXIT(driver)	i2c_del_driver(driver)

#ifdef CONFIG_NFC_S3FWRN5_I2C
/*
 * NUXEL: the S3NRN82 on this board runs NCI firmware, so s3fwrn5_i2c is the
 * one owner of 7-0027.  s3fwrn5_i2c is registered at subsys_initcall() so it
 * is present in the driver list before any I2C client is probed; this driver
 * is registered with the default module_init() and therefore gets its chance
 * only afterwards.  Still, driver match order in i2c_device_match() follows
 * driver registration, so to make the outcome independent of link/init
 * ordering this probe defers exactly once: the deferred probe queue re-runs
 * after every driver that was registered before it has had its turn, which
 * includes s3fwrn5_i2c.
 *
 * This driver does not need to know whether s3fwrn5_i2c succeeded: that
 * driver verifies the NCI bootloader handshake and FAILS its probe on a part
 * it cannot drive (s3fwrn5/i2c.c), so either it claims the node or it is out
 * of the way by the time this probe runs the second time.
 */
static bool sec_nfc_deferred;

static bool sec_nfc_nci_defer(void)
{
	if (sec_nfc_deferred)
		return false;

	sec_nfc_deferred = true;
	return true;
}
#endif

static int sec_nfc_probe(struct i2c_client *client,
		const struct i2c_device_id *id)
{
	int ret = 0;

#ifdef CONFIG_NFC_S3FWRN5_I2C
	/*
	 * Yield once to s3fwrn5_i2c.  The second probe (after the deferred
	 * queue) reaches this point only when the NCI driver declined or
	 * failed, and the legacy transport then keeps the node working.
	 *
	 * The first pass can run before late_initcall (this tree defers I2C
	 * client probing until then), i.e. before s3fwrn5_i2c has registered:
	 * return -EPROBE_DEFER unconditionally, never -ENODEV here.  A delayed
	 * worker re-queues deferred probes after every built-in initcall, so
	 * the second pass happens with all drivers present.
	 */
	if (sec_nfc_nci_defer()) {
		NFC_LOG_INFO("yielding 7-0027 to s3fwrn5_i2c for one probe pass\n");
		pr_info("NUXEL sec_nfc: deferring to s3fwrn5_i2c\n");
		return -EPROBE_DEFER;
	}
#endif

	nfc_logger_init();

	ret = __sec_nfc_probe(&client->dev);
	if (ret)
		return ret;

	ret = sec_nfc_i2c_probe(client);
	if (ret) {
		__sec_nfc_remove(&client->dev);
		return ret;
	}

	return 0;
}

static int sec_nfc_remove(struct i2c_client *client)
{
	return __sec_nfc_remove(&client->dev);
}

static struct i2c_device_id sec_nfc_id_table[] = {
	{ SEC_NFC_DRIVER_NAME, 0 },
	{ }
};

/*
 * NUXEL: the S3NRN82 on this board runs NCI firmware, so s3fwrn5_i2c is the
 * preferred owner of 7-0027 when CONFIG_NFC_S3FWRN5_I2C is built.  But this
 * driver must not simply refuse the node: i2c_device_match() accepts the
 * OF compatible as a fallback, so an unconditional stand-down would leave
 * the controller with no driver at all if the NCI probe cannot run (firmware
 * missing, GPIO conflict, NCI driver not present in the boot image).
 *
 * sec_nfc_probe() below defers (-EPROBE_DEFER) only while the NCI driver is
 * registered and still has the I2C ID/OF match for this address, and then
 * lets the NCI driver claim the node.  If the NCI driver is absent or has no
 * match, this legacy raw transport binds instead, so NFC hardware never
 * silently disappears.
 */
static const struct of_device_id nfc_match_table[] = {
	{ .compatible = SEC_NFC_DRIVER_NAME,},
	{},
};

static struct i2c_driver sec_nfc_driver = {
	.probe = sec_nfc_probe,
	.id_table = sec_nfc_id_table,
	.remove = sec_nfc_remove,
	.driver = {
		.name = SEC_NFC_DRIVER_NAME,
#ifdef CONFIG_PM
		.pm = &sec_nfc_pm_ops,
#endif
		.of_match_table = nfc_match_table,
		.suppress_bind_attrs = true,
	},
};

static int __init sec_nfc_init(void)
{
	return SEC_NFC_INIT(&sec_nfc_driver);
}

static void __exit sec_nfc_exit(void)
{
	SEC_NFC_EXIT(&sec_nfc_driver);
}

module_init(sec_nfc_init);
module_exit(sec_nfc_exit);

MODULE_DESCRIPTION("Samsung sec_nfc driver");
MODULE_LICENSE("GPL");
