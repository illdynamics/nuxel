/*
 * I2C Link Layer for Samsung S3FWRN5 NCI based Driver
 *
 * Copyright (C) 2015 Samsung Electrnoics
 * Robert Baldyga <r.baldyga@samsung.com>
 *
 * This program is free software; you can redistribute it and/or modify it
 * under the terms and conditions of the GNU General Public License,
 * version 2 or later, as published by the Free Software Foundation.
 *
 * This program is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
 * GNU General Public License for more details.
 *
 * You should have received a copy of the GNU General Public License
 * along with this program; if not, see <http://www.gnu.org/licenses/>.
 */

#include <linux/i2c.h>
#include <linux/gpio.h>
#include <linux/delay.h>
#include <linux/of_gpio.h>
#include <linux/of_irq.h>
#include <linux/module.h>
#include <linux/clk.h>
#include <linux/completion.h>
#include <linux/regulator/consumer.h>

#include <net/nfc/nfc.h>

#include "s3fwrn5.h"
#include "firmware.h"

#define S3FWRN5_I2C_DRIVER_NAME "s3fwrn5_i2c"

#define S3FWRN5_I2C_MAX_PAYLOAD 32
#define S3FWRN5_EN_WAIT_TIME 150
/* NUXEL: vendor sec_nfc SEC_NFC_VEN_WAIT_TIME on this board is 20 ms. */
#define S3FWRN5_BOARD_VEN_WAIT_MS 20
/*
 * NUXEL: the firmware strap is only sampled once the part has been stable
 * with rail + reference clock (vendor NPT: VEN on, clock on, 20 ms, FIRM).
 */
#define S3FWRN5_BOARD_FIRM_HOLD_MS 30

struct s3fwrn5_i2c_phy {
	struct i2c_client *i2c_dev;
	struct nci_dev *ndev;

	int gpio_en;
	int gpio_fw_wake;
	/* NUXEL: input GPIO behind client->irq, sampled by the handshake. */
	int irq_gpio;
	/* NUXEL: pins use the vendor active-low VEN / FIRM=bootloader wiring. */
	bool board_pins;
	/* NUXEL: optional 26 MHz "oscclk_nfc" the controller requests. */
	struct clk *clk;
	/* NUXEL: vendor "VDD_NFC_1P8" rail (sec-nfc,nfc_pvdd). */
	struct regulator *pvdd;
	/*
	 * NUXEL (S3NRN82): a "hold" is one power/clock session that spans a
	 * whole NCI setup (bootloader firmware download + NCI switch), not
	 * just one mode switch.  The clk_req IRQ is kept disabled while held
	 * because this part NACKs the next I2C read if its 26 MHz reference
	 * is gated between frames (measured: write ACK, then -EREMOTEIO).
	 */
	int hold;
	bool clk_on;
	/* NUXEL: signalled by the IRQ thread when it has consumed a frame. */
	struct completion irq_done;
	/* NUXEL: true once the firmware protocol is ready for IRQ frames. */
	bool ndev_ready;
	/* NUXEL: a NCI session owed a reply interrupt that was dropped. */
	bool nci_pending;

	struct mutex mutex;

	enum s3fwrn5_mode mode;
	unsigned int irq_skip:1;
};

static void s3fwrn5_i2c_set_wake(void *phy_id, bool wake)
{
	struct s3fwrn5_i2c_phy *phy = phy_id;

	/*
	 * NUXEL (beyond2lte): FIRM high selects the bootloader, so it must
	 * NEVER be used as a wake line.  The stand-alone S3FWRN5 has a
	 * dedicated FW_WAKE pin and uses this path.  Driving it after a
	 * set_mode(NCI) would drop the part back into FW mode (visible as
	 * "CORE_RESET never answered" when testing this board).
	 */
	if (phy->board_pins)
		return;

	mutex_lock(&phy->mutex);
	gpio_set_value(phy->gpio_fw_wake, wake);
	msleep(S3FWRN5_EN_WAIT_TIME/2);
	mutex_unlock(&phy->mutex);
}

static void s3fwrn5_i2c_set_mode(void *phy_id, enum s3fwrn5_mode mode)
{
	struct s3fwrn5_i2c_phy *phy = phy_id;

	mutex_lock(&phy->mutex);

	if (phy->mode == mode)
		goto out;

	/*
	 * NUXEL: leaving NCI with an unread reply discards it (the rail is
	 * dropped below or the part is reconfigured), so a pending marker
	 * must not outlive the transaction that produced it.
	 */
	phy->nci_pending = false;
	if (phy->hold && phy->board_pins) {
		/*
		 * NUXEL: inside a session the rail and the 26 MHz reference
		 * stay on, so the bootloader strap (FIRM) is latched by the
		 * part with power and clock present.  Deciding the strap
		 * *while the rail is off* is what the vendor NPT avoids: the
		 * S3NRN82 then keeps answering the firmware protocol after
		 * the driver has switched to NCI (measured: NCI CORE_RESET is
		 * NACKed, then the bootloader replies to the probe).
		 */
		gpio_set_value(phy->gpio_fw_wake, mode == S3FWRN5_MODE_FW);
		msleep(S3FWRN5_BOARD_FIRM_HOLD_MS);
	}
	phy->mode = mode;

	/*
	 * NUXEL: a session holds the rail and reference clock across modes.
	 * COLD must still really power the part down, otherwise the next
	 * session's bootloader entry is not a reset (the vendor NPT needs the
	 * rail to drop).  IRQ frames are ignored during the session anyway
	 * (see the clk-held check in the IRQ handler).
	 */
	if (phy->hold)
		goto held;

	if (phy->board_pins) {
		/*
		 * NUXEL (beyond2lte): vendor wiring has VEN active-low
		 * (0 = rail on) and FIRM high = bootloader mode.  Sequence
		 * copied from sec_nfc_set_mode(): rail off, FIRM, wait the
		 * vendor 20 ms, rail on, wait 20 ms.  The part's rail is cut
		 * between sessions so the next bootloader entry is a real
		 * reset.
		 */
		/*
		 * COLD is the exception: the vendor NPT ("NFC OFF mode NPT")
		 * drops VEN with FIRM still low, so the part is never powered
		 * up with a bootloader strap.  That is the state the reader
		 * must come back from at the start of every session.
		 */
		gpio_set_value(phy->gpio_en, 1);
		if (mode != S3FWRN5_MODE_COLD) {
			gpio_set_value(phy->gpio_fw_wake,
				       mode == S3FWRN5_MODE_FW);
			msleep(S3FWRN5_BOARD_VEN_WAIT_MS);
			gpio_set_value(phy->gpio_en, 0);
			msleep(S3FWRN5_BOARD_VEN_WAIT_MS);
		} else {
			gpio_set_value(phy->gpio_fw_wake, 0);
		}
	} else {
		gpio_set_value(phy->gpio_en, 1);
		gpio_set_value(phy->gpio_fw_wake, 0);
		if (mode == S3FWRN5_MODE_FW)
			gpio_set_value(phy->gpio_fw_wake, 1);

		if (mode != S3FWRN5_MODE_COLD) {
			msleep(S3FWRN5_EN_WAIT_TIME);
			gpio_set_value(phy->gpio_en, 0);
			msleep(S3FWRN5_EN_WAIT_TIME/2);
		}
	}

	phy->irq_skip = true;
	goto out;

held:
	/* NUXEL: rail and reference clock stay up for the whole session. */
	if (phy->board_pins)
		gpio_set_value(phy->gpio_fw_wake, mode == S3FWRN5_MODE_FW);
	else
		gpio_set_value(phy->gpio_fw_wake, 0);

	phy->irq_skip = true;

out:
	mutex_unlock(&phy->mutex);
}

/*
 * NUXEL (S3NRN82): session power/clock control.
 *
 * The controller is powered and clocked for a whole NCI setup (bootloader
 * firmware download -> NCI switch -> CORE_RESET), not per mode switch.  The
 * reference clock is kept enabled for the session: the clk_req line toggles
 * per I2C frame and this part NACKs the next read when the 26 MHz is gated
 * between frames.  The clock is only turned off when the session ends and the
 * part is in COLD mode.
 */
/*
 * NUXEL: wake the controller from COLD for a session.  A warm part stays
 * in NCI runtime, so switching back to NCI has to be a real reset: the rail
 * is dropped first.  Called by the session code before set_mode(), with the
 * same lock ordering as set_mode() itself (never while holding it).
 */
static void s3fwrn5_i2c_power_cycle(struct s3fwrn5_i2c_phy *phy)
{
	if (!phy->board_pins)
		return;

	mutex_lock(&phy->mutex);
	gpio_set_value(phy->gpio_en, 1);	/* rail off (VEN active-low) */
	gpio_set_value(phy->gpio_fw_wake, 0);
	msleep(S3FWRN5_BOARD_VEN_WAIT_MS);
	phy->mode = S3FWRN5_MODE_COLD;
	mutex_unlock(&phy->mutex);
}

static void s3fwrn5_i2c_session_begin(struct s3fwrn5_i2c_phy *phy)
{
	mutex_lock(&phy->mutex);
	phy->hold++;

	if (phy->clk && !phy->clk_on) {
		int ret = clk_prepare_enable(phy->clk);

		if (ret) {
			dev_err(&phy->i2c_dev->dev,
				"NUXEL: enabling oscclk_nfc failed: %d\n", ret);
		} else {
			phy->clk_on = true;
			dev_info(&phy->i2c_dev->dev,
				 "NUXEL: oscclk_nfc on for session\n");
		}
	}

	if (phy->pvdd) {
		int ret = regulator_enable(phy->pvdd);

		if (ret == 0 || ret == -EALREADY)
			dev_info(&phy->i2c_dev->dev,
				 "NUXEL: VDD_NFC_1P8 on (%d)\n", ret);
		else
			dev_info(&phy->i2c_dev->dev,
				 "NUXEL: VDD_NFC_1P8 enable failed (%d)\n", ret);
	}

	/*
	 * NUXEL (S3NRN82): vendor NPT entry, exactly:
	 *   VEN on (rail), reference clock on, 20 ms, THEN FIRM high.
	 * The strap is sampled by the part with rail and clock present; the
	 * previous sequence set FIRM 20 ms before the rail came on, and the
	 * part kept answering as if it were in the NCI runtime: every
	 * firmware command was then sent while the transport said NCI (or was
	 * NACKed because the strap was sampled without power).  Keep the
	 * transport in FW mode afterwards - this is the mode the part is in.
	 */
	if (phy->board_pins) {
		/*
		 * NUXEL (S3NRN82): measured window.  This part only ACKs its
		 * I2C address for a short time after the rail comes up; the
		 * bootloader reply arrived ~1 ms after power-up.  Vendor NPT
		 * (VEN on, 20 ms, FIRM) leaves the part silent by the time the
		 * first frame is sent - 20 ms + 30 ms later every command was
		 * NACKed and no IRQ fired.  Power on with the bootloader strap
		 * already asserted and send the first frame immediately.
		 */
		gpio_set_value(phy->gpio_fw_wake, 1);	/* bootloader strap */
		gpio_set_value(phy->gpio_en, 0);	/* rail on (active-low) */
		usleep_range(1000, 2000);
	}
	phy->mode = S3FWRN5_MODE_FW;
	phy->irq_skip = true;
	mutex_unlock(&phy->mutex);
}

static void s3fwrn5_i2c_session_end(struct s3fwrn5_i2c_phy *phy)
{
	mutex_lock(&phy->mutex);
	if (phy->hold > 0)
		phy->hold--;
	mutex_unlock(&phy->mutex);

	/* Only idle the part when no outer session is still using it. */
	if (phy->hold)
		return;

	s3fwrn5_i2c_set_mode(phy, S3FWRN5_MODE_COLD);
	if (phy->clk && phy->clk_on) {
		clk_disable_unprepare(phy->clk);
		phy->clk_on = false;
	}
	if (phy->pvdd)
		regulator_disable(phy->pvdd);
}

static enum s3fwrn5_mode s3fwrn5_i2c_get_mode(void *phy_id)
{
	struct s3fwrn5_i2c_phy *phy = phy_id;
	enum s3fwrn5_mode mode;

	mutex_lock(&phy->mutex);

	mode = phy->mode;

	mutex_unlock(&phy->mutex);

	return mode;
}

static int s3fwrn5_i2c_write(void *phy_id, struct sk_buff *skb)
{
	struct s3fwrn5_i2c_phy *phy = phy_id;
	int ret;

	mutex_lock(&phy->mutex);

	phy->irq_skip = false;

	ret = i2c_master_send(phy->i2c_dev, skb->data, skb->len);
	if (ret == -EREMOTEIO) {
		/* Retry, chip was in standby */
		usleep_range(110000, 120000);
		ret  = i2c_master_send(phy->i2c_dev, skb->data, skb->len);
	}

	mutex_unlock(&phy->mutex);

	if (ret < 0)
		return ret;

	if (ret != skb->len)
		return -EREMOTEIO;

	return 0;
}

/*
 * NUXEL (S3NRN82): write one complete firmware-protocol frame (header +
 * payload) as a single I2C transfer.  The per-frame skb path is fine for NCI
 * and for the short bootloader commands, but the kernel's i2c core rejects a
 * 260-byte message on this adapter, which is the size of a 256-byte firmware
 * data packet.  The controller only starts processing a frame when it has been
 * received completely, so the frame is sent in one transaction.
 *
 * Returns the number of bytes written (frame length) or a negative errno.
 */
static int s3fwrn5_i2c_write_bulk(void *phy_id, const u8 *data, size_t len)
{
	struct s3fwrn5_i2c_phy *phy = phy_id;
	int ret;

	if (len == 0 || len > U16_MAX)
		return -EINVAL;

	mutex_lock(&phy->mutex);
	ret = i2c_master_send(phy->i2c_dev, data, len);
	mutex_unlock(&phy->mutex);

	if (ret == -EREMOTEIO) {
		/* The part may still be in standby from the previous frame. */
		usleep_range(20000, 25000);
		mutex_lock(&phy->mutex);
		ret = i2c_master_send(phy->i2c_dev, data, len);
		mutex_unlock(&phy->mutex);
	}
	if (ret < 0) {
		dev_err_ratelimited(&phy->i2c_dev->dev,
				    "NUXEL fw: %zu-byte frame write failed %d (mode=%d)\n",
				    len, ret, phy->mode);
		return ret;
	}
	dev_info_ratelimited(&phy->i2c_dev->dev,
			     "NUXEL tx %zu: %*ph (mode=%d)\n", len,
			     (int)min_t(size_t, len, 16), data, phy->mode);
	if ((size_t)ret != len)
		return -EREMOTEIO;

	return ret;
}

static int s3fwrn5_i2c_read(struct s3fwrn5_i2c_phy *phy);

/*
 * NUXEL (S3NRN82): read the reply the IRQ thread could not consume while the
 * part was being switched to NCI.  Called from the NCI send path before a new
 * command; a failure here is not fatal for the session (the sender reports
 * the real I2C outcome).
 */
static int s3fwrn5_i2c_read_pending(void *phy_id)
{
	struct s3fwrn5_i2c_phy *phy = phy_id;
	int ret = 0;

	mutex_lock(&phy->mutex);
	if (phy->nci_pending) {
		/*
		 * NUXEL (S3NRN82): the bootloader reply is still latched in
		 * the controller (it answers exactly one frame per rail
		 * cycle).  Once the transport is in FW mode for the download,
		 * that frame must be consumed as a firmware response; reading
		 * it while the transport says NCI hands it to the NCI core,
		 * which drops the type byte instead of the bootloader waiter.
		 */
		phy->nci_pending = false;
		ret = s3fwrn5_i2c_read(phy);
		dev_info_ratelimited(&phy->i2c_dev->dev,
				     "NUXEL: read pending bootloader reply (%d)\n",
				     ret);
	}
	mutex_unlock(&phy->mutex);
	return ret;
}

static const struct s3fwrn5_phy_ops i2c_phy_ops = {
	.set_wake = s3fwrn5_i2c_set_wake,
	.set_mode = s3fwrn5_i2c_set_mode,
	.get_mode = s3fwrn5_i2c_get_mode,
	.write = s3fwrn5_i2c_write,
	.write_bulk = s3fwrn5_i2c_write_bulk,
	.read_pending = s3fwrn5_i2c_read_pending,
	.session_begin = s3fwrn5_i2c_session_begin,
	.session_end = s3fwrn5_i2c_session_end,
};

/*
 * NUXEL (S3NRN82): decide which protocol a received frame belongs to.
 *
 * The controller answers the bootloader handshake with a 4-byte firmware
 * header of type RSP (0x01|parity), and the bootloader is still reachable
 * right after a rail cycle.  If such a frame arrives once the transport
 * believes it is in NCI mode it must go to the firmware protocol, not be
 * parsed as an NCI header (which would hand garbage to nci_recv_frame and
 * leave the firmware waiter without its reply).
 */
static int nuxel_frame_mode(struct s3fwrn5_i2c_phy *phy, const char *hdr)
{
	const u8 *h = (const u8 *)hdr;

	if (phy->mode == S3FWRN5_MODE_FW)
		return S3FWRN5_MODE_FW;
	/*
	 * The protocol is selected by the bit7 (parity) flag, exactly as the
	 * driver builds every command frame with it:
	 *   FW   data/command : 0x00 | 0x80 (1st), 0x00 (2nd)
	 *   FW   response     : 0x01 (no flag)  <- measured GET_BOOTINFO reply
	 *   81 00 0e 00 ...
	 *   NCI  control      : 0x40..0x7f (RSP_NTF 0x40/0x60, RSP_ACK 0x7f)
	 * A response (type 1, no flag) overlaps NCI data MT=0, so a 4-byte
	 * header of type RSP must be treated as a firmware response: handing it
	 * to nci_recv_frame() made the NCI core discard it and the bootloader
	 * waiter timed out with the reply sitting unread in the latched frame.
	 */
	if (h[0] < 0x40 && (h[0] & 0x7f) == S3FWRN5_FW_MSG_RSP)
		return S3FWRN5_MODE_FW;
	/*
	 * Everything else is NCI: data packets are 0x00..0x3f and control
	 * packets (RSP_NTF/RSP_ACK) are 0x40..0x7f.  FW data frames (parity
	 * flag set, bit7) never belong in NCI mode - the firmware protocol is
	 * only active when the transport was put in FW mode.
	 */
	return S3FWRN5_MODE_NCI;
}

static int s3fwrn5_i2c_read(struct s3fwrn5_i2c_phy *phy)
{
	struct sk_buff *skb;
	size_t hdr_size;
	size_t data_len;
	char hdr[4];
	int ret, frame_mode, retries;

	/*
	 * NUXEL: the frame is already latched in the controller, so the read
	 * must not race a mode switch.  A hsi2c timeout means the bus, not
	 * the reply, needs a moment; retry a few times before giving up.
	 *
	 * DIAG: the first transaction right after power-up is the one that
	 * mattered (reply seen at +1 ms, then bootinfo timed out), so time
	 * every step of this call in ms since the rail came on.
	 */
	for (retries = 0; retries < 3; retries++) {
		hdr_size = (phy->mode == S3FWRN5_MODE_NCI) ?
			NCI_CTRL_HDR_SIZE : S3FWRN5_FW_HDR_SIZE;
		ret = i2c_master_recv(phy->i2c_dev, hdr, hdr_size);
		if (ret == hdr_size)
			break;
		usleep_range(2000, 3000);
	}
	if (ret < 0) {
		dev_info_ratelimited(&phy->i2c_dev->dev,
				     "NUXEL nci read: header recv failed %d (mode=%d)\n",
				     ret, phy->mode);
		return ret;
	}

	if (ret < hdr_size)
		return -EBADMSG;

	frame_mode = nuxel_frame_mode(phy, hdr);
	data_len = (frame_mode == S3FWRN5_MODE_NCI) ?
		((struct nci_ctrl_hdr *)hdr)->plen :
		((struct s3fwrn5_fw_header *)hdr)->len;

	skb = alloc_skb(hdr_size + data_len, GFP_KERNEL);
	if (!skb)
		return -ENOMEM;

	skb_put_data(skb, hdr, hdr_size);

	if (data_len == 0)
		goto out;

	ret = i2c_master_recv(phy->i2c_dev, skb_put(skb, data_len), data_len);
	if (ret != data_len) {
		kfree_skb(skb);
		return -EBADMSG;
	}

out:
	dev_info_ratelimited(&phy->i2c_dev->dev,
			     "NUXEL nci rx: %*ph  mode=%d frame=%d\n",
			     (int)min_t(size_t, skb->len, 16), skb->data,
			     phy->mode, frame_mode);
	return s3fwrn5_recv_frame(phy->ndev, skb, frame_mode);
}

static irqreturn_t s3fwrn5_i2c_irq_thread_fn(int irq, void *phy_id)
{
	struct s3fwrn5_i2c_phy *phy = phy_id;
	int ret = 0;

	if (!phy || !phy->ndev) {
		WARN_ON_ONCE(1);
		return IRQ_NONE;
	}

	mutex_lock(&phy->mutex);

	if (phy->irq_skip) {
		/* A mode/rail switch is in progress; the line is not a frame. */
		dev_dbg(&phy->i2c_dev->dev, "NUXEL irq: skipped (mode=%d)\n",
			phy->mode);
		goto out;
	}

	switch (phy->mode) {
	case S3FWRN5_MODE_NCI:
	case S3FWRN5_MODE_FW:
		/*
		 * NUXEL: until the first s3fwrn5_fw_init() has run (the probe
		 * readiness check runs before it), the firmware completion is
		 * not initialised and s3fwrn5_fw_recv_frame() would BUG_ON().
		 */
		if (!phy->ndev_ready) {
			dev_info_ratelimited(&phy->i2c_dev->dev,
					     "NUXEL irq: ignored before firmware setup (mode=%d)\n",
					     phy->mode);
			break;
		}
		/*
		 * NUXEL (S3NRN82): a session always ends with the part powered
		 * off, which discards an unread frame.  An interrupt that is
		 * still owed when the part was switched to NCI must be read
		 * here: skipping the read leaves the controller holding the
		 * reply, and the next transaction (CORE_RESET) is NACKed or
		 * the hsi2c bus wedges ("SDA check timeout AT READ").
		 */
		if (phy->hold && phy->mode == S3FWRN5_MODE_NCI)
			phy->nci_pending = true;
		ret = s3fwrn5_i2c_read(phy);
		if (ret < 0)
			dev_info_ratelimited(&phy->i2c_dev->dev,
					     "NUXEL irq: read failed %d (mode=%d)\n",
					     ret, phy->mode);
		break;
	case S3FWRN5_MODE_COLD:
		dev_info_ratelimited(&phy->i2c_dev->dev,
				     "NUXEL irq in COLD mode ignored\n");
		break;
	}

out:
	mutex_unlock(&phy->mutex);
	complete(&phy->irq_done);

	return IRQ_HANDLED;
}

static int s3fwrn5_i2c_parse_dt(struct i2c_client *client,
				struct s3fwrn5_i2c_phy *phy)
{
	struct device_node *np = client->dev.of_node;
	int ret;

	if (!np)
		return -ENODEV;

	phy->gpio_en = of_get_named_gpio(np, "s3fwrn5,en-gpios", 0);
	if (!gpio_is_valid(phy->gpio_en)) {
		phy->gpio_en = of_get_named_gpio(np, "sec-nfc,ven-gpio", 0);
		/* VEN on this wiring is active-low: mark the board style. */
		phy->board_pins = gpio_is_valid(phy->gpio_en);
	}
	if (!gpio_is_valid(phy->gpio_en))
		return -ENODEV;

	phy->gpio_fw_wake = of_get_named_gpio(np, "s3fwrn5,fw-gpios", 0);
	if (!gpio_is_valid(phy->gpio_fw_wake)) {
		phy->gpio_fw_wake = of_get_named_gpio(np, "sec-nfc,firm-gpio", 0);
		/*
		 * NUXEL: on this vendor wiring FIRM is the bootloader strap and
		 * the IRQ line (sec-nfc,irq-gpio) is a separate input GPIO.
		 * s3fwrn5_i2c_set_wake() must never toggle FIRM; keep the board
		 * flag tied to this node shape.
		 */
		if (gpio_is_valid(phy->gpio_fw_wake))
			phy->board_pins = true;
	}
	if (!gpio_is_valid(phy->gpio_fw_wake))
		return -ENODEV;

	ret = of_get_named_gpio(np, "sec-nfc,irq-gpio", 0);
	if (!gpio_is_valid(ret))
		ret = of_get_named_gpio(np, "s3fwrn5,irq-gpios", 0);
	phy->irq_gpio = ret;

	/*
	 * NUXEL (beyond2lte): the controller's reference clock is the SoC
	 * "oscclk_nfc" output (DT clocks/clock-names), gated by hardware on the
	 * clk_req line (sec-nfc,clk_req-gpio).  The vendor driver enables the
	 * gate interrupt on every mode switch; without the clock the part never
	 * answers NCI.  A board without these properties (plain S3FWRN5) keeps
	 * clk == NULL and this is a no-op.
	 */
	/*
	 * NUXEL: the vendor node also names its 1.8 V NFC rail
	 * (sec-nfc,nfc_pvdd = "VDD_NFC_1P8"); sec_nfc enables it around every
	 * mode switch.  Keep it enabled while the transport owns the part.
	 */
	if (of_find_property(np, "sec-nfc,ldo_control", NULL)) {
		const char *name = NULL;

		of_property_read_string(np, "sec-nfc,nfc_pvdd", &name);
		if (name && *name) {
			phy->pvdd = regulator_get(NULL, name);
			if (IS_ERR(phy->pvdd)) {
				dev_info(&client->dev,
					 "NUXEL: nfc rail %s unavailable (%ld)\n",
					 name, PTR_ERR(phy->pvdd));
				phy->pvdd = NULL;
			}
		}
	}

	phy->clk = devm_clk_get(&client->dev, "oscclk_nfc");
	if (IS_ERR(phy->clk)) {
		if (PTR_ERR(phy->clk) == -ENOENT || PTR_ERR(phy->clk) == -ENODEV) {
			phy->clk = NULL;
		} else {
			dev_err(&client->dev, "NUXEL: oscclk_nfc unavailable: %ld\n",
				PTR_ERR(phy->clk));
			return PTR_ERR(phy->clk);
		}
	}

	return 0;
}

/*
 * NUXEL: bootloader readiness handshake.
 *
 * This probes the part with GET_BOOTINFO and verifies the reply carries the
 * measured S3NRN82 hardware tag and plausible sector/page sizes.  It runs on
 * a workqueue after probe: doing it inside the device_initcall starved the
 * UFS/RPMB worker and boot-looped the phone.
 */
static int s3fwrn5_i2c_nci_ready(void *phy_id)
{
	struct s3fwrn5_i2c_phy *phy = phy_id;
	struct s3fwrn5_fw_header req = {
		.type = S3FWRN5_FW_MSG_CMD,
		.code = S3FWRN5_FW_CMD_GET_BOOTINFO,
		.len = 0,
	};
	struct sk_buff *skb;
	int ret, i;

	/*
	 * NUXEL: the S3NRN82 answers exactly one frame per power cycle, so a
	 * real reset must precede the probe: drop the rail, then enter the
	 * bootloader (VENDOR NPT order: VEN, wait, FIRM).
	 */
	s3fwrn5_i2c_power_cycle(phy);
	s3fwrn5_i2c_set_mode(phy, S3FWRN5_MODE_FW);
	s3fwrn5_i2c_set_wake(phy, false);
	msleep(S3FWRN5_BOARD_VEN_WAIT_MS);

	skb = alloc_skb(sizeof(req), GFP_KERNEL);
	if (!skb) {
		ret = -ENOMEM;
		goto out_mode;
	}
	skb_put_data(skb, &req, sizeof(req));
	reinit_completion(&phy->irq_done);
	ret = s3fwrn5_i2c_write(phy, skb);
	kfree_skb(skb);
	if (ret < 0) {
		dev_info(&phy->i2c_dev->dev,
			 "NUXEL: GET_BOOTINFO write failed (%d)\n", ret);
		goto out_mode;
	}
	/*
	 * NUXEL: read the reply as soon as the IRQ handler has taken the
	 * frame.  The controller releases SCL only briefly after answering,
	 * so the probe must not add its own delay before the read.
	 */

	/*
	 * NUXEL: wait on the IRQ, not only on the level of the line.  The
	 * level drops before the handler reads the frame, so polling the line
	 * alone can miss a reply that is already being delivered (measured:
	 * the bootinfo was logged, yet the probe timed out).
	 */
	reinit_completion(&phy->irq_done);
	for (i = 0; i < 200; i++) {
		if (wait_for_completion_timeout(&phy->irq_done,
						msecs_to_jiffies(10)) ||
		    gpio_get_value(phy->irq_gpio))
			break;
	}
	if (i == 200) {
		dev_info(&phy->i2c_dev->dev,
			 "NUXEL: bootloader did not answer GET_BOOTINFO (irq line=%d, ven=%d firm=%d)\n",
			 gpio_get_value(phy->irq_gpio),
			 gpio_get_value(phy->gpio_en),
			 gpio_get_value(phy->gpio_fw_wake));
		ret = -ENXIO;
	} else {
		ret = 0;
	}

out_mode:
	s3fwrn5_i2c_set_mode(phy, S3FWRN5_MODE_COLD);
	s3fwrn5_i2c_set_wake(phy, false);
	return ret;
}

static int s3fwrn5_i2c_probe(struct i2c_client *client,
				  const struct i2c_device_id *id)
{
	struct s3fwrn5_i2c_phy *phy;
	int ret;

	phy = devm_kzalloc(&client->dev, sizeof(*phy), GFP_KERNEL);
	if (!phy)
		return -ENOMEM;

	mutex_init(&phy->mutex);
	init_completion(&phy->irq_done);
	phy->mode = S3FWRN5_MODE_COLD;
	phy->irq_skip = true;

	phy->i2c_dev = client;
	i2c_set_clientdata(client, phy);

	dev_info(&client->dev, "NUXEL s3fwrn5_i2c probe begin\n");

	ret = s3fwrn5_i2c_parse_dt(client, phy);
	if (ret < 0) {
		dev_err(&client->dev, "NUXEL s3fwrn5_i2c parse_dt failed: %d\n", ret);
		return ret;
	}
	dev_info(&client->dev, "NUXEL s3fwrn5_i2c gpio en=%d fw=%d irq=%d\n",
		 phy->gpio_en, phy->gpio_fw_wake, phy->i2c_dev->irq);

	/*
	 * NUXEL: the board node is the vendor sec-nfc@27 node.  Its EN line is
	 * the NFC rail enable (not the upstream reset), and the bootloader can
	 * leave it high.  Start both pins low so set_mode() owns every edge.
	 */
	/*
	 * NUXEL: on the vendor wiring VEN starts de-asserted (rail off) and
	 * FIRM low; set_mode() then sequences them.  The upstream defaults
	 * (EN high = asserted, which is rail-off here) are kept for other
	 * boards.
	 */
	ret = devm_gpio_request_one(&phy->i2c_dev->dev, phy->gpio_en,
		GPIOF_OUT_INIT_HIGH, "s3fwrn5_en");
	if (ret < 0)
		return ret;

	ret = devm_gpio_request_one(&phy->i2c_dev->dev, phy->gpio_fw_wake,
		GPIOF_OUT_INIT_LOW, "s3fwrn5_fw_wake");
	if (ret < 0)
		return ret;

	if (gpio_is_valid(phy->irq_gpio)) {
		ret = devm_gpio_request_one(&phy->i2c_dev->dev, phy->irq_gpio,
					    GPIOF_IN, "s3fwrn5_irq");
		if (ret < 0)
			return ret;
	}

	if (phy->pvdd) {
		ret = regulator_enable(phy->pvdd);
		dev_info(&client->dev, "NUXEL: nfc rail enabled (%d)\n", ret);
		if (ret)
			phy->pvdd = NULL;
	}

	if (phy->clk) {
		/*
		 * NUXEL (beyond2lte): "oscclk_nfc" is CAL vclk OSC_NFC, a CLKOUT
		 * whose source is selected in the PMU (VCLK_CLKOUT1).  It has no
		 * settable rate: cal_clk_setrate() answers "Un-support clk type"
		 * (-EINVAL) and cal_vclk_set_rate() then returns -EAGAIN, while
		 * cal_vclk_recalc_rate() reports no rate at all.  Prepare/enable
		 * runs ra_enable_clkout(), which is the whole operation.  No
		 * set_rate here, and the reported rate is not a health signal.
		 */
		ret = clk_prepare_enable(phy->clk);
		if (ret) {
			dev_err(&client->dev,
				"NUXEL: enabling oscclk_nfc failed: %d\n", ret);
			return ret;
		}
		dev_info(&client->dev, "NUXEL: oscclk_nfc prepared/enabled\n");
	}

	ret = s3fwrn5_probe(&phy->ndev, phy, &phy->i2c_dev->dev, &i2c_phy_ops,
		S3FWRN5_I2C_MAX_PAYLOAD);
	if (ret < 0) {
		dev_err(&client->dev, "NUXEL s3fwrn5_probe failed: %d\n", ret);
		return ret;
	}
	/*
	 * NUXEL: s3fwrn5_probe() has now initialised the firmware protocol
	 * (completion included), so firmware-protocol frames must reach it
	 * from here on.  Before this point the IRQ handler leaves them alone.
	 */
	phy->ndev_ready = true;
	s3fwrn5_set_ready_check(phy->ndev, s3fwrn5_i2c_nci_ready);

	/*
	 * NUXEL (beyond2lte): the vendor transport waits for a RISING edge on
	 * the same IRQ (sec_nfc.c: IRQF_TRIGGER_RISING).  The board DT carries
	 * "interrupts = <2 0 0>" and the controller pulses the line per frame,
	 * so a level-triggered handler never fires for the second frame (the
	 * line is already low again).  Matches the vendor behaviour.
	 */
	ret = devm_request_threaded_irq(&client->dev, phy->i2c_dev->irq, NULL,
		s3fwrn5_i2c_irq_thread_fn,
		IRQF_TRIGGER_RISING | IRQF_ONESHOT,
		S3FWRN5_I2C_DRIVER_NAME, phy);
	if (ret) {
		dev_err(&client->dev, "NUXEL s3fwrn5_i2c request_irq failed: %d\n", ret);
		s3fwrn5_remove(phy->ndev);
		return ret;
	}
	phy->irq_skip = true;

	/*
	 * NUXEL: probe never fails because of the controller.  /dev/nfc0 must
	 * exist for the NFC service; the bootloader handshake runs on a
	 * workqueue (never in this initcall) and its result is advisory.
	 */
	dev_info(&client->dev, "NUXEL s3fwrn5_i2c probe success\n");

	return ret;
}

static int s3fwrn5_i2c_remove(struct i2c_client *client)
{
	struct s3fwrn5_i2c_phy *phy = client->dev.driver_data;

	s3fwrn5_remove(phy->ndev);

	return 0;
}

static struct i2c_device_id s3fwrn5_i2c_id_table[] = {
	{S3FWRN5_I2C_DRIVER_NAME, 0},
	{}
};
MODULE_DEVICE_TABLE(i2c, s3fwrn5_i2c_id_table);

static const struct of_device_id of_s3fwrn5_i2c_match[] = {
	{ .compatible = "samsung,s3fwrn5-i2c", },
	/*
	 * NUXEL (beyond2lte): the board DTS names the S3NRN82 node "sec-nfc@27"
	 * with compatible "sec-nfc" and Samsung's sec-nfc,ven/firm-gpio property
	 * spelling.  That node is this NCI controller; the legacy raw driver
	 * (sec_nfc.c) cannot speak NCI and leaves the chip unregistered from
	 * the kernel NFC stack.  Binding it here gives the standard
	 * /sys/class/nfc + /dev/nfc0 ABI.
	 */
	{ .compatible = "sec-nfc", },
	{}
};
MODULE_DEVICE_TABLE(of, of_s3fwrn5_i2c_match);

static struct i2c_driver s3fwrn5_i2c_driver = {
	.driver = {
		.owner = THIS_MODULE,
		.name = S3FWRN5_I2C_DRIVER_NAME,
		.of_match_table = of_match_ptr(of_s3fwrn5_i2c_match),
	},
	.probe = s3fwrn5_i2c_probe,
	.remove = s3fwrn5_i2c_remove,
	.id_table = s3fwrn5_i2c_id_table,
};

/*
 * NUXEL registration.
 *
 * This driver must (a) be registered after net/nfc's nfc_init() has
 * registered the "nfc" class (nci_register_device() -> device_add() ->
 * get_device_parent() dereferences nfc_class's parent, which only exists
 * after class_register(); booting earlier panicked at 0.65 s with a NULL
 * deref in _raw_spin_lock/get_device_parent) and (b) be registered before
 * the legacy sec_nfc driver so it is the preferred match for the vendor
 * "sec-nfc" node.
 *
 * This tree's module_init() is subsys_initcall() (level 4) - the same level
 * as nfc_init - and drivers/nfc links before net/nfc, so a plain module_init()
 * here loses that race (measured: panic in nfc_register_device at 0.65 s).
 * Registration therefore happens at device_initcall (level 6), after every
 * subsys_initcall has run, and sec_nfc defers one probe pass (-EPROBE_DEFER,
 * sec_nfc.c) so the NCI transport still owns 7-0027.
 */
static int __init s3fwrn5_i2c_init(void)
{
	int ret;

	ret = i2c_add_driver(&s3fwrn5_i2c_driver);
	pr_info("NUXEL s3fwrn5_i2c: driver registered (rc=%d)\n", ret);
	return ret;
}
device_initcall(s3fwrn5_i2c_init);

static void __exit s3fwrn5_i2c_exit(void)
{
	i2c_del_driver(&s3fwrn5_i2c_driver);
}
module_exit(s3fwrn5_i2c_exit);

MODULE_LICENSE("GPL");
MODULE_DESCRIPTION("I2C driver for Samsung S3FWRN5");
MODULE_AUTHOR("Robert Baldyga <r.baldyga@samsung.com>");
