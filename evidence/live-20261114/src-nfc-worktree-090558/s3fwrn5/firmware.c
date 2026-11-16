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

#include <linux/completion.h>
#include <linux/delay.h>
#include <linux/firmware.h>
#include <crypto/hash.h>
#include <crypto/sha.h>

#include "s3fwrn5.h"
#include "firmware.h"

struct s3fwrn5_fw_version {
	__u8 major;
	__u8 build1;
	__u8 build2;
	__u8 target;
};

static int s3fwrn5_fw_wait_reply(struct s3fwrn5_fw_info *fw_info,
	struct sk_buff **rsp)
{
	long ret;

	/*
	 * NUXEL: keep the upstream 1 s for the fast commands, but allow more
	 * time while the controller is writing flash (S3NRN82 bootloader).
	 */
	ret = wait_for_completion_interruptible_timeout(
		&fw_info->completion,
		msecs_to_jiffies(fw_info->custom_format ?
				 S3FWRN5_FW_CUSTOM_REPLY_TIMEOUT_MS : 1000));
	if (ret < 0)
		return ret;
	else if (ret == 0)
		return -ENXIO;

	if (!fw_info->rsp) {
		return -EINVAL;
	}

	/*
	 * NUXEL: the bootloader reply is a firmware-protocol frame (its
	 * header type is RSP).  Anything else means the part already runs the
	 * NCI firmware and is not answering this protocol (measured: an NCI
	 * control frame leaks into the handshake when the strap was sampled
	 * with the rail off).  Drop it instead of failing on a forged
	 * firmware header.
	 */
	if (((u8)fw_info->rsp->data[0] & 0x7f) != S3FWRN5_FW_MSG_RSP) {
		dev_info_ratelimited(&fw_info->ndev->nfc_dev->dev,
			"NUXEL: non-firmware reply to the bootloader (0x%02x); part is in NCI\n",
			(u8)fw_info->rsp->data[0]);
		/*
		 * NUXEL: the latched bootloader response (0x01 00 0e 00 ...) is
		 * the answer to the GET_BOOTINFO sent during the failed NCI
		 * reset.  It is a valid bootloader response, not NCI traffic:
		 * accept it so fw_setup() can proceed instead of failing the
		 * whole session on the part's single-frame-per-cycle behaviour.
		 */
		if (fw_info->rsp->len >= S3FWRN5_FW_HDR_SIZE &&
		    ((u8)fw_info->rsp->data[0] & 0x7f) == S3FWRN5_FW_MSG_RSP &&
		    (u8)fw_info->rsp->data[1] == S3FWRN5_FW_RET_SUCCESS) {
			dev_info(&fw_info->ndev->nfc_dev->dev,
				 "NUXEL: accepting latched bootloader response\n");
			*rsp = fw_info->rsp;
			fw_info->rsp = NULL;
			return 0;
		}
		kfree_skb(fw_info->rsp);
		fw_info->rsp = NULL;
		fw_info->part_in_nci = true;
		return -EPROTO;
	}

	*rsp = fw_info->rsp;
	fw_info->rsp = NULL;

	return 0;
}

static int s3fwrn5_fw_send_msg(struct s3fwrn5_fw_info *fw_info,
	struct sk_buff *msg, struct sk_buff **rsp)
{
	struct s3fwrn5_info *info =
		container_of(fw_info, struct s3fwrn5_info, fw_info);
	int ret;

	reinit_completion(&fw_info->completion);

	ret = s3fwrn5_write(info, msg);
	if (ret < 0)
		return ret;

	return s3fwrn5_fw_wait_reply(fw_info, rsp);
}

/*
 * NUXEL: send one firmware frame built in a single buffer.  Transports that
 * can transfer the whole frame in one transaction get the byte stream (a
 * 256-byte data packet is 260 bytes, which this board's i2c core refuses to
 * queue as a msg); others get the historical skb path.
 */
static int s3fwrn5_fw_send_frame(struct s3fwrn5_fw_info *fw_info, u8 type,
	u8 code, const void *data, u16 len)
{
	struct s3fwrn5_info *info = nci_get_drvdata(fw_info->ndev);
	u8 *frame;
	int ret;

	if (!info->phy_ops->write_bulk)
		return -ENOTSUPP;

	frame = kmalloc(S3FWRN5_FW_HDR_SIZE + len, GFP_KERNEL);
	if (!frame)
		return -ENOMEM;

	frame[0] = type | fw_info->parity;
	fw_info->parity ^= 0x80;
	frame[1] = code;
	frame[2] = len & 0xff;
	frame[3] = len >> 8;
	if (len)
		memcpy(frame + S3FWRN5_FW_HDR_SIZE, data, len);

	reinit_completion(&fw_info->completion);
	ret = info->phy_ops->write_bulk(info->phy_id, frame,
					S3FWRN5_FW_HDR_SIZE + len);
	kfree(frame);

	return ret < 0 ? ret : 0;
}

static int s3fwrn5_fw_prep_msg(struct s3fwrn5_fw_info *fw_info,
	struct sk_buff **msg, u8 type, u8 code, const void *data, u16 len)
{
	struct s3fwrn5_fw_header hdr;
	struct sk_buff *skb;

	hdr.type = type | fw_info->parity;
	fw_info->parity ^= 0x80;
	hdr.code = code;
	hdr.len = len;

	skb = alloc_skb(S3FWRN5_FW_HDR_SIZE + len, GFP_KERNEL);
	if (!skb)
		return -ENOMEM;

	skb_put_data(skb, &hdr, S3FWRN5_FW_HDR_SIZE);
	if (len)
		skb_put_data(skb, data, len);

	*msg = skb;

	return 0;
}

static int s3fwrn5_fw_get_bootinfo(struct s3fwrn5_fw_info *fw_info,
	struct s3fwrn5_fw_cmd_get_bootinfo_rsp *bootinfo)
{
	struct sk_buff *msg, *rsp = NULL;
	struct s3fwrn5_fw_header *hdr;
	int ret;

	/* Send GET_BOOTINFO command */

	ret = s3fwrn5_fw_prep_msg(fw_info, &msg, S3FWRN5_FW_MSG_CMD,
		S3FWRN5_FW_CMD_GET_BOOTINFO, NULL, 0);
	if (ret < 0)
		return ret;

	ret = s3fwrn5_fw_send_msg(fw_info, msg, &rsp);
	kfree_skb(msg);
	if (ret < 0)
		return ret;

	hdr = (struct s3fwrn5_fw_header *) rsp->data;
	if (hdr->code != S3FWRN5_FW_RET_SUCCESS) {
		ret = -EINVAL;
		goto out;
	}

	{
		/*
		 * NUXEL: copy the whole measured reply body (23 bytes) into the
		 * zeroed struct; only fields that fit are taken, so a shorter
		 * upstream reply stays valid.
		 */
		size_t body = hdr->len > 0 ? hdr->len : 0;

		memset(bootinfo, 0, sizeof(*bootinfo));
		if (body > sizeof(*bootinfo))
			body = sizeof(*bootinfo);
		memcpy(bootinfo, rsp->data + S3FWRN5_FW_HDR_SIZE, body);
	}

out:
	kfree_skb(rsp);
	return ret;
}

static int s3fwrn5_fw_enter_update_mode(struct s3fwrn5_fw_info *fw_info,
	const void *hash_data, u16 hash_size,
	const void *sig_data, u16 sig_size)
{
	struct s3fwrn5_fw_cmd_enter_updatemode args;
	struct sk_buff *msg, *rsp = NULL;
	struct s3fwrn5_fw_header *hdr;
	int ret;

	/* Send ENTER_UPDATE_MODE command */

	args.hashcode_size = hash_size;
	args.signature_size = sig_size;

	ret = s3fwrn5_fw_prep_msg(fw_info, &msg, S3FWRN5_FW_MSG_CMD,
		S3FWRN5_FW_CMD_ENTER_UPDATE_MODE, &args, sizeof(args));
	if (ret < 0)
		return ret;

	ret = s3fwrn5_fw_send_msg(fw_info, msg, &rsp);
	kfree_skb(msg);
	if (ret < 0)
		return ret;

	hdr = (struct s3fwrn5_fw_header *) rsp->data;
	if (hdr->code != S3FWRN5_FW_RET_SUCCESS) {
		ret = -EPROTO;
		goto out;
	}

	kfree_skb(rsp);

	/* Send hashcode data */

	ret = s3fwrn5_fw_send_frame(fw_info, S3FWRN5_FW_MSG_DATA, 0,
				    hash_data, hash_size);
	if (ret == -ENOTSUPP) {
		ret = s3fwrn5_fw_prep_msg(fw_info, &msg, S3FWRN5_FW_MSG_DATA,
			0, hash_data, hash_size);
		if (ret < 0)
			return ret;
		ret = s3fwrn5_fw_send_msg(fw_info, msg, &rsp);
		kfree_skb(msg);
	} else if (ret == 0) {
		ret = s3fwrn5_fw_wait_reply(fw_info, &rsp);
	}
	if (ret < 0)
		return ret;

	hdr = (struct s3fwrn5_fw_header *) rsp->data;
	if (hdr->code != S3FWRN5_FW_RET_SUCCESS) {
		ret = -EPROTO;
		goto out;
	}

	kfree_skb(rsp);

	/* Send signature data */

	ret = s3fwrn5_fw_send_frame(fw_info, S3FWRN5_FW_MSG_DATA, 0,
				    sig_data, sig_size);
	if (ret == -ENOTSUPP) {
		ret = s3fwrn5_fw_prep_msg(fw_info, &msg, S3FWRN5_FW_MSG_DATA,
			0, sig_data, sig_size);
		if (ret < 0)
			return ret;
		ret = s3fwrn5_fw_send_msg(fw_info, msg, &rsp);
		kfree_skb(msg);
	} else if (ret == 0) {
		ret = s3fwrn5_fw_wait_reply(fw_info, &rsp);
	}
	if (ret < 0)
		return ret;

	hdr = (struct s3fwrn5_fw_header *) rsp->data;
	if (hdr->code != S3FWRN5_FW_RET_SUCCESS)
		ret = -EPROTO;

	/*
	 * NUXEL (S3NRN82): the controller acknowledges the signature frame
	 * before it has committed it to flash.  Give it time before the
	 * first sector update, otherwise the bootloader silently ignores the
	 * UPDATE_SECTOR frames that follow (measured: stale reply frames).
	 */
	if (ret == 0)
		msleep(S3FWRN5_FW_UPDATE_SETTLE_MS);

out:
	kfree_skb(rsp);
	return ret;
}

static int s3fwrn5_fw_update_sector(struct s3fwrn5_fw_info *fw_info,
	u32 base_addr, const void *data)
{
	struct s3fwrn5_fw_cmd_update_sector args;
	struct sk_buff *msg, *rsp = NULL;
	struct s3fwrn5_fw_header *hdr;
	int ret, i;

	/* Send UPDATE_SECTOR command */

	args.base_address = base_addr;

	ret = s3fwrn5_fw_prep_msg(fw_info, &msg, S3FWRN5_FW_MSG_CMD,
		S3FWRN5_FW_CMD_UPDATE_SECTOR, &args, sizeof(args));
	if (ret < 0)
		return ret;

	ret = s3fwrn5_fw_send_msg(fw_info, msg, &rsp);
	kfree_skb(msg);
	if (ret < 0)
		return ret;

	hdr = (struct s3fwrn5_fw_header *) rsp->data;
	if (hdr->code != S3FWRN5_FW_RET_SUCCESS) {
		ret = -EPROTO;
		goto err;
	}

	kfree_skb(rsp);

	/* Send data split into 256-byte packets */

	for (i = 0; i < 16; ++i) {
		ret = s3fwrn5_fw_send_frame(fw_info, S3FWRN5_FW_MSG_DATA, 0,
					    data + 256 * i, 256);
		if (ret == -ENOTSUPP) {
			ret = s3fwrn5_fw_prep_msg(fw_info, &msg,
				S3FWRN5_FW_MSG_DATA, 0, data + 256 * i, 256);
			if (ret < 0)
				break;

			ret = s3fwrn5_fw_send_msg(fw_info, msg, &rsp);
			kfree_skb(msg);
		} else if (ret == 0) {
			ret = s3fwrn5_fw_wait_reply(fw_info, &rsp);
		}
		if (ret < 0)
			break;

		hdr = (struct s3fwrn5_fw_header *) rsp->data;
		if (hdr->code != S3FWRN5_FW_RET_SUCCESS) {
			ret = -EPROTO;
			goto err;
		}

		kfree_skb(rsp);
	}

	/*
	 * NUXEL (S3NRN82): the ACK of the last 256-byte packet is sent when
	 * the controller has accepted the packet into its 4 KiB flash buffer,
	 * not when the sector write completes.  Pace the next command; the
	 * bootloader otherwise answers with the previous frame (measured as
	 * a stale 14-byte bootinfo reply on every following UPDATE_SECTOR).
	 */
	msleep(S3FWRN5_FW_SECTOR_SETTLE_MS);

	return ret;

err:
	kfree_skb(rsp);
	return ret;
}

static int s3fwrn5_fw_complete_update_mode(struct s3fwrn5_fw_info *fw_info)
{
	struct sk_buff *msg, *rsp = NULL;
	struct s3fwrn5_fw_header *hdr;
	int ret;

	/* Send COMPLETE_UPDATE_MODE command */

	ret = s3fwrn5_fw_prep_msg(fw_info, &msg, S3FWRN5_FW_MSG_CMD,
		S3FWRN5_FW_CMD_COMPLETE_UPDATE_MODE, NULL, 0);
	if (ret < 0)
		return ret;

	ret = s3fwrn5_fw_send_msg(fw_info, msg, &rsp);
	kfree_skb(msg);
	if (ret < 0)
		return ret;

	hdr = (struct s3fwrn5_fw_header *) rsp->data;
	if (hdr->code != S3FWRN5_FW_RET_SUCCESS)
		ret = -EPROTO;

	kfree_skb(rsp);

	return ret;
}

/*
 * Firmware header stucture:
 *
 * 0x00 - 0x0B : Date and time string (w/o NUL termination)
 * 0x10 - 0x13 : Firmware version
 * 0x14 - 0x17 : Signature address
 * 0x18 - 0x1B : Signature size
 * 0x1C - 0x1F : Firmware image address
 * 0x20 - 0x23 : Firmware sectors count
 * 0x24 - 0x27 : Custom signature address
 * 0x28 - 0x2B : Custom signature size
 */

#define S3FWRN5_FW_IMAGE_HEADER_SIZE 44

static int s3fwrn5_fw_request_firmware(struct s3fwrn5_fw_info *fw_info)
{
	struct s3fwrn5_fw_image *fw = &fw_info->fw;
	u32 sig_off;
	u32 image_off;
	u32 custom_sig_off;
	int ret;

	fw->fw = NULL;
	/*
	 * NUXEL: the NFC setup runs from a workqueue during boot, before any
	 * udev/rootfs firmware helper exists.  request_firmware() would fall
	 * back to a userspace helper and wait for it (measured: the first
	 * setup at ~1.3 s stalled for a minute on the missing helper).  Use
	 * the direct loader: it honours firmware_class.path (/vendor/firmware,
	 * set by the bootloader cmdline) and /lib/firmware without userspace.
	 */
	ret = request_firmware_direct(&fw->fw, fw_info->fw_name,
				      &fw_info->ndev->nfc_dev->dev);
	if (ret < 0) {
		/* NUXEL: keep cleanup/release_firmware(NULL) safe on retries. */
		fw->fw = NULL;
		return ret;
	}

	if (fw->fw->size < S3FWRN5_FW_IMAGE_HEADER_SIZE) {
		release_firmware(fw->fw);
		return -EINVAL;
	}

	memcpy(fw->date, fw->fw->data + 0x00, 12);
	fw->date[12] = '\0';

	memcpy(&fw->version, fw->fw->data + 0x10, 4);

	memcpy(&sig_off, fw->fw->data + 0x14, 4);
	fw->sig = fw->fw->data + sig_off;
	memcpy(&fw->sig_size, fw->fw->data + 0x18, 4);

	memcpy(&image_off, fw->fw->data + 0x1C, 4);
	fw->image = fw->fw->data + image_off;
	memcpy(&fw->image_sectors, fw->fw->data + 0x20, 4);

	memcpy(&custom_sig_off, fw->fw->data + 0x24, 4);
	fw->custom_sig = fw->fw->data + custom_sig_off;
	memcpy(&fw->custom_sig_size, fw->fw->data + 0x28, 4);

	return 0;
}

static void s3fwrn5_fw_release_firmware(struct s3fwrn5_fw_info *fw_info)
{
	if (fw_info->fw.fw)
		release_firmware(fw_info->fw.fw);
	fw_info->fw.fw = NULL;
}

static const struct {
	u8 version[4];
	u32 base_addr;
} s3fwrn5_hw_match[] = {
	{{0x05, 0x00, 0x00, 0x00}, 0x00005000},
	{{0x05, 0x00, 0x00, 0x01}, 0x00003000},
	{{0x05, 0x00, 0x00, 0x02}, 0x00003000},
	{{0x05, 0x00, 0x00, 0x03}, 0x00003000},
	{{0x05, 0x00, 0x00, 0x05}, 0x00003000},
	/*
	 * NUXEL (SM-G975F, S3NRN82): measured GET_BOOTINFO reply
	 * 82.00.01.00, sector=4096 page=512 frame=262 buf=65535.  The
	 * S3NRN82 is an S3FWRN5-family part with the same firmware protocol,
	 * but its bootloader reports this vendor hardware tag.  The base
	 * address is the same 0x3000 as the upstream 05.00.00.0x entries (the
	 * image header of the shipped sec_s3nrn82_firmware.bin, byte-identical
	 * to the pinned vendor blob, carries the same 0x25-sector layout).
	 */
	{{0x82, 0x00, 0x01, 0x00}, 0x00003000},
};

static int s3fwrn5_fw_get_base_addr(
	struct s3fwrn5_fw_cmd_get_bootinfo_rsp *bootinfo, u32 *base_addr)
{
	int i;

	for (i = 0; i < ARRAY_SIZE(s3fwrn5_hw_match); ++i)
		if (bootinfo->hw_version[0] == s3fwrn5_hw_match[i].version[0] &&
			bootinfo->hw_version[1] == s3fwrn5_hw_match[i].version[1] &&
			bootinfo->hw_version[3] == s3fwrn5_hw_match[i].version[3]) {
			*base_addr = s3fwrn5_hw_match[i].base_addr;
			return 0;
		}

	return -EINVAL;
}

static inline bool
s3fwrn5_fw_is_custom(struct s3fwrn5_fw_cmd_get_bootinfo_rsp *bootinfo)
{
	return !!bootinfo->hw_version[2];
}

int s3fwrn5_fw_setup(struct s3fwrn5_fw_info *fw_info)
{
	struct s3fwrn5_fw_cmd_get_bootinfo_rsp bootinfo;
	int ret;

	/* Get firmware data */

	ret = s3fwrn5_fw_request_firmware(fw_info);
	if (ret < 0) {
		dev_err(&fw_info->ndev->nfc_dev->dev,
			"Failed to get fw file, ret=%02x\n", ret);
		return ret;
	}

	/* Get bootloader info */

	ret = s3fwrn5_fw_get_bootinfo(fw_info, &bootinfo);
	if (ret < 0) {
		dev_err(&fw_info->ndev->nfc_dev->dev,
			"Failed to get bootinfo, ret=%02x\n", ret);
		goto err;
	}
	dev_info(&fw_info->ndev->nfc_dev->dev,
		 "bootinfo hw=%02x.%02x.%02x.%02x sector=%u page=%u frame=%u buf=%u\n",
		 bootinfo.hw_version[0], bootinfo.hw_version[1],
		 bootinfo.hw_version[2], bootinfo.hw_version[3],
		 bootinfo.sector_size, bootinfo.page_size,
		 bootinfo.frame_max_size, bootinfo.hw_buffer_size);

	/* Match hardware version to obtain firmware base address */

	ret = s3fwrn5_fw_get_base_addr(&bootinfo, &fw_info->base_addr);
	if (ret < 0) {
		/* NUXEL: report the raw boot info so the accept table can be
		 * extended from measurement instead of guessing. */
		dev_err(&fw_info->ndev->nfc_dev->dev,
			"Unknown hardware version %02x.%02x.%02x.%02x (sector=%u page=%u frame=%u buf=%u)\n",
			bootinfo.hw_version[0], bootinfo.hw_version[1],
			bootinfo.hw_version[2], bootinfo.hw_version[3],
			bootinfo.sector_size, bootinfo.page_size,
			bootinfo.frame_max_size, bootinfo.hw_buffer_size);
		goto err;
	}

	fw_info->sector_size = bootinfo.sector_size;

	/*
	 * NUXEL (S3NRN82): a custom-format image is signed with its CUSTOM
	 * signature only; sending the standard signature as well makes the
	 * controller reject the update.  Standard parts keep the historical
	 * behaviour (both signatures are derived from the same header fields
	 * there, so this is byte-identical for them).
	 */
	/*
	 * The bootloader's own GET_BOOTINFO is authoritative for the format:
	 * hw_version[2] is non-zero exactly when the controller runs a custom
	 * image.  This matches the image header flags at offsets 0x10/0x11 of
	 * the firmware file (standard/custom), which the S3NRN82 blob sets to
	 * 0x45/0x09.
	 */
	fw_info->custom_format = bootinfo.hw_version[2] != 0;
	if (fw_info->custom_format) {
		fw_info->sig = fw_info->fw.custom_sig;
		fw_info->sig_size = fw_info->fw.custom_sig_size;
	} else {
		fw_info->sig = fw_info->fw.sig;
		fw_info->sig_size = fw_info->fw.sig_size;
	}
	dev_info(&fw_info->ndev->nfc_dev->dev,
		 "fw image: %s format, image_off=0x%x sectors=%u sig=%u custom_sig=%u\n",
		 fw_info->custom_format ? "custom" : "standard",
		 (unsigned int)((const u8 *)fw_info->fw.image -
				(const u8 *)fw_info->fw.fw->data),
		 fw_info->fw.image_sectors, fw_info->fw.sig_size,
		 fw_info->fw.custom_sig_size);

	return 0;

err:
	s3fwrn5_fw_release_firmware(fw_info);
	return ret;
}

bool s3fwrn5_fw_check_version(struct s3fwrn5_fw_info *fw_info, u32 version)
{
	struct s3fwrn5_fw_version *new = (void *) &fw_info->fw.version;
	struct s3fwrn5_fw_version *old = (void *) &version;

	if (new->major > old->major)
		return true;
	if (new->build1 > old->build1)
		return true;
	if (new->build2 > old->build2)
		return true;

	return false;
}

int s3fwrn5_fw_download(struct s3fwrn5_fw_info *fw_info)
{
	struct s3fwrn5_fw_image *fw = &fw_info->fw;
	u8 hash_data[SHA1_DIGEST_SIZE];
	struct crypto_shash *tfm;
	u32 image_size, off;
	int ret;

	/*
	 * NUXEL: fw_setup() releases the image it parsed (upstream frees it
	 * after setup because it historically downloaded straight away).
	 * Reload it here so the sector loop below has the actual bytes.
	 */
	if (!fw->fw) {
		ret = s3fwrn5_fw_request_firmware(fw_info);
		if (ret < 0) {
			dev_err(&fw_info->ndev->nfc_dev->dev,
				"Cannot reload firmware image (code=%d)\n", ret);
			goto out;
		}
	}

	image_size = fw_info->sector_size * fw->image_sectors;

	/* Compute SHA of firmware data */

	tfm = crypto_alloc_shash("sha1", 0, 0);
	if (IS_ERR(tfm)) {
		ret = PTR_ERR(tfm);
		dev_err(&fw_info->ndev->nfc_dev->dev,
			"Cannot allocate shash (code=%d)\n", ret);
		goto out;
	}

	{
		SHASH_DESC_ON_STACK(desc, tfm);

		desc->tfm = tfm;
		desc->flags = CRYPTO_TFM_REQ_MAY_SLEEP;

		ret = crypto_shash_digest(desc, fw->image, image_size,
					  hash_data);
		shash_desc_zero(desc);
	}

	crypto_free_shash(tfm);
	if (ret) {
		dev_err(&fw_info->ndev->nfc_dev->dev,
			"Cannot compute hash (code=%d)\n", ret);
		goto out;
	}

	/* Firmware update process */

	dev_info(&fw_info->ndev->nfc_dev->dev,
		"Firmware update: %s\n", fw_info->fw_name);

	ret = s3fwrn5_fw_enter_update_mode(fw_info, hash_data,
		SHA1_DIGEST_SIZE, fw_info->sig, fw_info->sig_size);
	if (ret < 0) {
		dev_err(&fw_info->ndev->nfc_dev->dev,
			"Unable to enter update mode\n");
		goto out;
	}

	for (off = 0; off < image_size; off += fw_info->sector_size) {
		ret = s3fwrn5_fw_update_sector(fw_info,
			fw_info->base_addr + off, fw->image + off);
		if (ret < 0) {
			dev_err(&fw_info->ndev->nfc_dev->dev,
				"Firmware update error (code=%d)\n", ret);
			goto out;
		}
	}

	ret = s3fwrn5_fw_complete_update_mode(fw_info);
	if (ret < 0) {
		dev_err(&fw_info->ndev->nfc_dev->dev,
			"Unable to complete update mode\n");
		goto out;
	}

	dev_info(&fw_info->ndev->nfc_dev->dev,
		"Firmware update: success\n");

out:
	return ret;
}

void s3fwrn5_fw_init(struct s3fwrn5_fw_info *fw_info, const char *fw_name)
{
	fw_info->parity = 0x00;
	fw_info->rsp = NULL;
	fw_info->fw.fw = NULL;
	strcpy(fw_info->fw_name, fw_name);
	init_completion(&fw_info->completion);
}

void s3fwrn5_fw_cleanup(struct s3fwrn5_fw_info *fw_info)
{
	s3fwrn5_fw_release_firmware(fw_info);
}

int s3fwrn5_fw_recv_frame(struct nci_dev *ndev, struct sk_buff *skb)
{
	struct s3fwrn5_info *info = nci_get_drvdata(ndev);
	struct s3fwrn5_fw_info *fw_info = &info->fw_info;

	/*
	 * NUXEL: a late or duplicate bootloader frame must never panic the
	 * phone (measured: the S3NRN82 replays its GET_BOOTINFO reply when a
	 * request is re-sent after an I2C recovery).  The newer reply replaces
	 * the unconsumed one; the waiter below takes exactly one skb.
	 */
	if (fw_info->rsp) {
		kfree_skb(fw_info->rsp);
		fw_info->rsp = NULL;
	}

	fw_info->rsp = skb;

	complete(&fw_info->completion);

	return 0;
}
