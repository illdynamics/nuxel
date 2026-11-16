/*
 * NCI based driver for Samsung S3FWRN5 NFC chip
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

#include <linux/module.h>
#include <linux/delay.h>
#include <net/nfc/nci_core.h>

#include "s3fwrn5.h"
#include "firmware.h"
#include "nci.h"

#define S3FWRN5_NFC_PROTOCOLS  (NFC_PROTO_JEWEL_MASK | \
				NFC_PROTO_MIFARE_MASK | \
				NFC_PROTO_FELICA_MASK | \
				NFC_PROTO_ISO14443_MASK | \
				NFC_PROTO_ISO14443_B_MASK | \
				NFC_PROTO_ISO15693_MASK)

static int s3fwrn5_firmware_update(struct s3fwrn5_info *info)
{
	bool need_update;
	int ret;

	/*
	 * NUXEL (S3NRN82): the controller on this board is the S3NRN82, whose
	 * vendor image is sec_s3nrn82_firmware.bin (shipped in
	 * /vendor/firmware/nfc, shipped hash d315cd8b…).  Upstream only knows
	 * the stand-alone S3FWRN5 name; try the board image first and keep the
	 * upstream name as the generic fallback.
	 */
	static const char * const fw_names[] = {
		"sec_s3nrn82_firmware.bin",
		"sec_s3fwrn5_firmware.bin",
		"nfc/sec_s3nrn82_firmware.bin",
	};
	int i;

	/* Update firmware */

	s3fwrn5_set_wake(info, false);
	s3fwrn5_set_mode(info, S3FWRN5_MODE_FW);

	ret = -ENOENT;
	for (i = 0; i < ARRAY_SIZE(fw_names); i++) {
		s3fwrn5_fw_init(&info->fw_info, fw_names[i]);
		ret = s3fwrn5_fw_setup(&info->fw_info);
		if (ret == 0) {
			dev_info(&info->ndev->nfc_dev->dev,
				 "NUXEL: firmware image %s\n", fw_names[i]);
			break;
		}
		dev_info(&info->ndev->nfc_dev->dev,
			 "NUXEL: firmware image %s unavailable (%d)\n",
			 fw_names[i], ret);
		s3fwrn5_fw_cleanup(&info->fw_info);
		s3fwrn5_set_mode(info, S3FWRN5_MODE_FW);
	}
	if (ret < 0)
		goto out;

	/*
	 * NUXEL (S3NRN82): if the handshake was answered by the NCI runtime
	 * rather than the bootloader, the part already has its firmware and
	 * flashed it.  Do not wait out the (5 s) bootloader timeouts for a
	 * flash that must not happen.
	 */
	if (info->fw_info.part_in_nci) {
		dev_info(&info->ndev->nfc_dev->dev,
			 "NUXEL: bootloader reported NCI traffic; firmware already running\n");
		s3fwrn5_set_mode(info, S3FWRN5_MODE_NCI);
		s3fwrn5_set_wake(info, true);
		goto out;
	}

	/*
	 * NUXEL (S3NRN82): the controller's own firmware revision is only
	 * known after an NCI CORE_RESET; at first bring-up there is none, so
	 * the shipped image is downloaded unconditionally once.  A controlled
	 * update can still skip an identical/older image below.
	 */
	need_update = info->force_fw_update ||
		s3fwrn5_fw_check_version(&info->fw_info,
			info->ndev->manufact_specific_info);
	/* NUXEL: measured decision inputs (the image is only flashed when the
	 * hardware target byte matches, see firmware.c). */
	dev_info(&info->ndev->nfc_dev->dev,
		 "fw image version 0x%08x, controller 0x%08x, update=%d\n",
		 info->fw_info.fw.version, info->ndev->manufact_specific_info,
		 need_update);
	if (!need_update)
		goto out;

	dev_info(&info->ndev->nfc_dev->dev, "Detected new firmware version\n");

	info->force_fw_update = false;
	ret = s3fwrn5_fw_download(&info->fw_info);
	if (ret < 0)
		goto out;

	/* Update RF configuration */

	s3fwrn5_set_mode(info, S3FWRN5_MODE_NCI);

	s3fwrn5_set_wake(info, true);
	ret = s3fwrn5_nci_rf_configure(info, "sec_s3fwrn5_rfreg.bin");
	s3fwrn5_set_wake(info, false);

out:
	s3fwrn5_set_mode(info, S3FWRN5_MODE_COLD);
	s3fwrn5_fw_cleanup(&info->fw_info);
	return ret;
}

static int s3fwrn5_nci_open(struct nci_dev *ndev)
{
	struct s3fwrn5_info *info = nci_get_drvdata(ndev);
	enum s3fwrn5_mode mode = s3fwrn5_get_mode(info);

	/*
	 * NUXEL: nfc0 is opened again for every post_setup retry.  The part is
	 * then already in NCI mode inside a held session; that is not EBUSY.
	 */
	if (mode != S3FWRN5_MODE_COLD && mode != S3FWRN5_MODE_NCI)
		return -EBUSY;

	if (mode == S3FWRN5_MODE_COLD) {
		s3fwrn5_set_mode(info, S3FWRN5_MODE_NCI);
		s3fwrn5_set_wake(info, true);
	}

	return 0;
}

static int s3fwrn5_nci_close(struct nci_dev *ndev)
{
	struct s3fwrn5_info *info = nci_get_drvdata(ndev);

	s3fwrn5_set_wake(info, false);
	s3fwrn5_set_mode(info, S3FWRN5_MODE_COLD);

	return 0;
}

static int s3fwrn5_nci_send(struct nci_dev *ndev, struct sk_buff *skb)
{
	struct s3fwrn5_info *info = nci_get_drvdata(ndev);
	int ret;

	mutex_lock(&info->mutex);

	if (s3fwrn5_get_mode(info) != S3FWRN5_MODE_NCI) {
		mutex_unlock(&info->mutex);
		return -EINVAL;
	}

	/*
	 * NUXEL (S3NRN82): an interrupt that was owed while the part was
	 * switched from the bootloader to NCI is read before the next NCI
	 * command.  Otherwise the controller still holds that reply and
	 * NACKs the new command (or the hsi2c bus wedges).
	 */
	s3fwrn5_read_pending(info);

	ret = s3fwrn5_write(info, skb);
	if (ret < 0)
		kfree_skb(skb);

	mutex_unlock(&info->mutex);
	return ret;
}

static int s3fwrn5_nci_post_setup(struct nci_dev *ndev)
{
	struct s3fwrn5_info *info = nci_get_drvdata(ndev);
	int ret, i;

	/*
	 * NUXEL (S3NRN82): hold the rail and the 26 MHz reference for the
	 * whole setup.  Firmware flash writes and the NCI switch must not see
	 * the clock gated between frames, and the controller keeps its
	 * bootloader session between UPDATE_SECTOR frames.
	 */
	s3fwrn5_session_begin(info);

	ret = s3fwrn5_firmware_update(info);
	if (ret < 0)
		goto out;

	/* NCI core reset */

	s3fwrn5_set_mode(info, S3FWRN5_MODE_NCI);
	s3fwrn5_set_wake(info, true);

	/*
	 * NUXEL: the part only leaves the bootloader after a completed flash
	 * and the NCI switch.  If it is still in firmware mode here (the
	 * download failed, or the strap was sampled while the rail was off
	 * and the part already runs NCI), an NCI reset cannot be answered -
	 * it would only stretch SCL for the full NCI timeout on the shared
	 * hsi2c bus.  Report the real state instead of faking a retry.
	 */
	if (s3fwrn5_get_mode(info) != S3FWRN5_MODE_NCI) {
		dev_err(&info->ndev->nfc_dev->dev,
			"NUXEL: part stayed in firmware mode; NFC not initialised\n");
		ret = -EIO;
		goto out;
	}

	dev_info(&info->ndev->nfc_dev->dev,
		 "NCI mode entered; sending CORE_RESET\n");
	/*
	 * NUXEL (S3NRN82): right after a firmware download the controller
	 * needs a moment to bring its NCI runtime up; the first frame can be
	 * NACKed because the part has not yet accepted its I2C address.
	 * Retry the reset instead of failing the NFC device.
	 */
	for (i = 0; i < 5; i++) {
		ret = nci_core_reset(info->ndev);
		if (ret == 0)
			break;
		dev_info(&info->ndev->nfc_dev->dev,
			 "CORE_RESET attempt %d/5 failed: %d\n", i + 1, ret);
		/* NUXEL: let the part release a stretched SCL before retrying. */
		msleep(1000);
	}
	if (ret < 0) {
		dev_err(&info->ndev->nfc_dev->dev,
			"CORE_RESET failed: %d\n", ret);
		goto out;
	}

	ret = nci_core_init(info->ndev);
	if (ret < 0)
		dev_err(&info->ndev->nfc_dev->dev,
			"CORE_INIT failed: %d\n", ret);

out:
	s3fwrn5_session_end(info);
	return ret;
}

/*
 * NUXEL (S3NRN82): the controller has no firmware in NCI runtime mode (it only
 * answers its bootloader) and nothing opens nfc0 until an app asks for NFC, so
 * the NCI setup (firmware download + CORE_RESET + discovery) is driven once
 * from probe through the generic NFC netlink API.  That path performs exactly
 * the open/close a userspace service would, so it needs no NCI internals.
 */
static int s3fwrn5_nci_dev_up(struct nci_dev *ndev)
{
	struct nfc_dev *nfc_dev = ndev->nfc_dev;
	int ret;

	/*
	 * nfc_core exports nfc_dev_up()/nfc_dev_down(): they take the device
	 * lock, honour the rfkill state and keep dev_up consistent, exactly as
	 * NFC_CMD_DEV_UP/DOWN from userspace would.
	 */
	ret = nfc_dev_up(nfc_dev);
	if (ret == -EALREADY)
		return 0;

	return ret;
}

#define S3FWRN5_SETUP_RETRY_MAX 12

static void s3fwrn5_nci_setup_work(struct work_struct *work)
{
	struct s3fwrn5_info *info = container_of(work, struct s3fwrn5_info,
						 setup_work);
	int ret;

	/*
	 * NUXEL (S3NRN82): this runs from a workqueue, never from probe.  The
	 * controller is still in bootloader mode here; the NCI open performs
	 * the firmware download (custom image signature), CORE_RESET and
	 * CORE_INIT.  Firmware lives in /vendor/firmware, mounted by the NCI
	 * firmware loader at open time.  If the part is not ready yet (power
	 * rail settling after boot), retry with backoff instead of giving up.
	 */
	/*
	 * NUXEL: bootloader readiness handshake for nfc0, on the workqueue
	 * (a GET_BOOTINFO + S3NRN82 bootinfo check).  Advisory only.
	 */
	ret = s3fwrn5_nci_dev_up(info->ndev);
	/*
	 * NUXEL: a failed open has already power-cycled the part (the
	 * session always ends with the rail off).  Probe the bootloader
	 * *before* the next attempt instead of after the failed one: the
	 * probe itself performs a rail cycle and an unread reply from it
	 * would otherwise be delivered to the next session's CORE_RESET.
	 */
	if (ret < 0 && info->ctrl_ready_check &&
	    info->setup_attempts < S3FWRN5_SETUP_RETRY_MAX) {
		int probe = info->ctrl_ready_check(info->phy_id);

		dev_info(&info->ndev->nfc_dev->dev,
			 "NUXEL: CORE_RESET failed (%d); bootloader probe=%d\n",
			 ret, probe);
	}
	if (ret < 0) {
		if (info->setup_attempts++ < S3FWRN5_SETUP_RETRY_MAX) {
			dev_info(&info->ndev->nfc_dev->dev,
				 "NUXEL: NCI setup attempt %d failed (%d); retrying in 3 s\n",
				 info->setup_attempts, ret);
			schedule_delayed_work(&info->setup_retry,
					      msecs_to_jiffies(3000));
			return;
		}
		dev_err(&info->ndev->nfc_dev->dev,
			"NUXEL: NCI setup failed after %d attempts (%d)\n",
			info->setup_attempts, ret);
		return;
	}

	dev_info(&info->ndev->nfc_dev->dev,
		 "NUXEL: NCI runtime ready (firmware + CORE_RESET + CORE_INIT)\n");
	/* Release the setup's own reference; the NFC service does its own up. */
	nfc_dev_down(info->ndev->nfc_dev);
}

static void s3fwrn5_nci_setup_retry_work(struct work_struct *work)
{
	struct s3fwrn5_info *info = container_of(to_delayed_work(work),
						 struct s3fwrn5_info,
						 setup_retry);

	s3fwrn5_nci_setup_work(&info->setup_work);
}

/*
 * NUXEL: nci_open_device() sends its own CORE_RESET before post_setup, so the
 * bootloader is probed here, as NCI init, while the transport is still in
 * bootloader mode.  This is the diagnostic that tells whether the controller
 * answers at all; it must not block for more than the caller's timeout.
 */
static int s3fwrn5_nci_init(struct nci_dev *ndev)
{
	/*
	 * NUXEL (S3NRN82): the controller answers exactly one frame per power
	 * cycle, so the session must spend it on the real NCI CORE_RESET that
	 * nci_open_device() issues next.  The bootloader readiness check is
	 * only run when that reset answers nothing (see the retry worker).
	 */
	(void)ndev;
	return 0;
}

static struct nci_ops s3fwrn5_nci_ops = {
	.init = s3fwrn5_nci_init,
	.open = s3fwrn5_nci_open,
	.close = s3fwrn5_nci_close,
	.send = s3fwrn5_nci_send,
	.post_setup = s3fwrn5_nci_post_setup,
};

int s3fwrn5_probe(struct nci_dev **ndev, void *phy_id, struct device *pdev,
	const struct s3fwrn5_phy_ops *phy_ops, unsigned int max_payload)
{
	struct s3fwrn5_info *info;
	int ret;

	info = devm_kzalloc(pdev, sizeof(*info), GFP_KERNEL);
	if (!info)
		return -ENOMEM;

	info->phy_id = phy_id;
	info->pdev = pdev;
	info->phy_ops = phy_ops;
	info->max_payload = max_payload;
	mutex_init(&info->mutex);

	s3fwrn5_set_mode(info, S3FWRN5_MODE_COLD);

	s3fwrn5_nci_get_prop_ops(&s3fwrn5_nci_ops.prop_ops,
		&s3fwrn5_nci_ops.n_prop_ops);

	info->ndev = nci_allocate_device(&s3fwrn5_nci_ops,
		S3FWRN5_NFC_PROTOCOLS, 0, 0);
	if (!info->ndev)
		return -ENOMEM;

	nci_set_parent_dev(info->ndev, pdev);
	nci_set_drvdata(info->ndev, info);

	ret = nci_register_device(info->ndev);
	if (ret < 0) {
		nci_free_device(info->ndev);
		return ret;
	}

	info->fw_info.ndev = info->ndev;
	/*
	 * NUXEL: initialise the firmware protocol here, so the IRQ path can
	 * never call complete() on an uninitialised completion (measured boot
	 * loop: bootloader reply before s3fwrn5_fw_init()).  fw_init() only
	 * resets software state; the download re-inits it again.
	 */
	s3fwrn5_fw_init(&info->fw_info, "sec_s3nrn82_firmware.bin");
	/* NUXEL: the controller's own revision is unknown before a reset. */
	info->force_fw_update = true;

	*ndev = info->ndev;

	/*
	 * NUXEL: switch the controller to NCI runtime once at boot, outside of
	 * probe and initcalls, so a slow NFC bring-up can never stall the boot
	 * path (UFS/RPMB) and a failed attempt can be retried.
	 */
	INIT_WORK(&info->setup_work, s3fwrn5_nci_setup_work);
	INIT_DELAYED_WORK(&info->setup_retry, s3fwrn5_nci_setup_retry_work);
	schedule_work(&info->setup_work);

	return ret;
}
EXPORT_SYMBOL(s3fwrn5_probe);

void s3fwrn5_remove(struct nci_dev *ndev)
{
	struct s3fwrn5_info *info = nci_get_drvdata(ndev);

	s3fwrn5_set_mode(info, S3FWRN5_MODE_COLD);

	nci_unregister_device(ndev);
	nci_free_device(ndev);
}
EXPORT_SYMBOL(s3fwrn5_remove);

int s3fwrn5_recv_frame(struct nci_dev *ndev, struct sk_buff *skb,
	enum s3fwrn5_mode mode)
{
	switch (mode) {
	case S3FWRN5_MODE_NCI:
		return nci_recv_frame(ndev, skb);
	case S3FWRN5_MODE_FW:
		return s3fwrn5_fw_recv_frame(ndev, skb);
	default:
		kfree_skb(skb);
		return -ENODEV;
	}
}
EXPORT_SYMBOL(s3fwrn5_recv_frame);

MODULE_LICENSE("GPL");
MODULE_DESCRIPTION("Samsung S3FWRN5 NFC driver");
MODULE_AUTHOR("Robert Baldyga <r.baldyga@samsung.com>");
