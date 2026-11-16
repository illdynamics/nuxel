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

#ifndef __LOCAL_S3FWRN5_H_
#define __LOCAL_S3FWRN5_H_

#include <linux/nfc.h>
#include <linux/workqueue.h>

#include <net/nfc/nci_core.h>

#include "firmware.h"

enum s3fwrn5_mode {
	S3FWRN5_MODE_COLD,
	S3FWRN5_MODE_NCI,
	S3FWRN5_MODE_FW,
};

struct s3fwrn5_phy_ops {
	void (*set_wake)(void *id, bool sleep);
	void (*set_mode)(void *id, enum s3fwrn5_mode);
	enum s3fwrn5_mode (*get_mode)(void *id);
	int (*write)(void *id, struct sk_buff *skb);
	/*
	 * NUXEL: optional transport extensions.  write_bulk() sends one
	 * complete firmware frame in a single I2C transaction (the i2c core
	 * rejects the 260-byte frame the firmware protocol needs); the
	 * session hooks hold rail + reference clock across a whole NCI setup.
	 */
	int (*write_bulk)(void *id, const u8 *data, size_t len);
	/*
	 * NUXEL: consume a reply interrupt that was owed while the part
	 * switched from the bootloader to NCI (S3NRN82 holds the frame and
	 * NACKs the next command until it is read).
	 */
	int (*read_pending)(void *id);
	void (*session_begin)(void *id);
	void (*session_end)(void *id);
};

struct s3fwrn5_info {
	struct nci_dev *ndev;
	void *phy_id;
	struct device *pdev;

	const struct s3fwrn5_phy_ops *phy_ops;
	unsigned int max_payload;

	struct s3fwrn5_fw_info fw_info;

	struct mutex mutex;

	/* NUXEL: boot-time NCI runtime setup (firmware download + reset). */
	struct work_struct setup_work;
	struct delayed_work setup_retry;
	int setup_attempts;
	/* NUXEL: bootloader GET_BOOTINFO check, run from the setup worker. */
	int (*ctrl_ready_check)(void *id);
	/* NUXEL: download the image once even without a known revision. */
	bool force_fw_update;
};

static inline int s3fwrn5_set_mode(struct s3fwrn5_info *info,
	enum s3fwrn5_mode mode)
{
	if (!info->phy_ops->set_mode)
		return -ENOTSUPP;

	info->phy_ops->set_mode(info->phy_id, mode);

	return 0;
}

static inline enum s3fwrn5_mode s3fwrn5_get_mode(struct s3fwrn5_info *info)
{
	if (!info->phy_ops->get_mode)
		return -ENOTSUPP;

	return info->phy_ops->get_mode(info->phy_id);
}

static inline int s3fwrn5_set_wake(struct s3fwrn5_info *info, bool wake)
{
	if (!info->phy_ops->set_wake)
		return -ENOTSUPP;

	info->phy_ops->set_wake(info->phy_id, wake);

	return 0;
}

static inline int s3fwrn5_write(struct s3fwrn5_info *info, struct sk_buff *skb)
{
	if (!info->phy_ops->write)
		return -ENOTSUPP;

	return info->phy_ops->write(info->phy_id, skb);
}

static inline void s3fwrn5_set_ready_check(struct nci_dev *ndev,
					   int (*fn)(void *id))
{
	struct s3fwrn5_info *info = nci_get_drvdata(ndev);

	if (info)
		info->ctrl_ready_check = fn;
}

static inline void s3fwrn5_read_pending(struct s3fwrn5_info *info)
{
	if (info->phy_ops->read_pending)
		info->phy_ops->read_pending(info->phy_id);
}

static inline int s3fwrn5_session_begin(struct s3fwrn5_info *info)
{
	if (!info->phy_ops->session_begin)
		return -ENOTSUPP;

	info->phy_ops->session_begin(info->phy_id);

	return 0;
}

static inline void s3fwrn5_session_end(struct s3fwrn5_info *info)
{
	if (info->phy_ops->session_end)
		info->phy_ops->session_end(info->phy_id);
}

int s3fwrn5_probe(struct nci_dev **ndev, void *phy_id, struct device *pdev,
	const struct s3fwrn5_phy_ops *phy_ops, unsigned int max_payload);
void s3fwrn5_remove(struct nci_dev *ndev);

int s3fwrn5_recv_frame(struct nci_dev *ndev, struct sk_buff *skb,
	enum s3fwrn5_mode mode);

#endif /* __LOCAL_S3FWRN5_H_ */
