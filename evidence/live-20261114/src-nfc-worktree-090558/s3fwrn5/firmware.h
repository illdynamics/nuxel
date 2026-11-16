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

#ifndef __LOCAL_S3FWRN5_FIRMWARE_H_
#define __LOCAL_S3FWRN5_FIRMWARE_H_

/* FW Message Types */
#define S3FWRN5_FW_MSG_CMD			0x00
#define S3FWRN5_FW_MSG_RSP			0x01
#define S3FWRN5_FW_MSG_DATA			0x02

/* FW Return Codes */
#define S3FWRN5_FW_RET_SUCCESS			0x00
#define S3FWRN5_FW_RET_MESSAGE_TYPE_INVALID	0x01
#define S3FWRN5_FW_RET_COMMAND_INVALID		0x02
#define S3FWRN5_FW_RET_PAGE_DATA_OVERFLOW	0x03
#define S3FWRN5_FW_RET_SECT_DATA_OVERFLOW	0x04
#define S3FWRN5_FW_RET_AUTHENTICATION_FAIL	0x05
#define S3FWRN5_FW_RET_FLASH_OPERATION_FAIL	0x06
#define S3FWRN5_FW_RET_ADDRESS_OUT_OF_RANGE	0x07
#define S3FWRN5_FW_RET_PARAMETER_INVALID	0x08

/* ---- FW Packet structures ---- */
#define S3FWRN5_FW_HDR_SIZE 4

struct s3fwrn5_fw_header {
	__u8 type;
	__u8 code;
	__u16 len;
};

/*
 * NUXEL: flash-pipeline settling times.  The S3NRN82 bootloader ACKs a
 * frame before the write behind it is committed; without these waits the
 * following UPDATE_SECTOR command gets the stale previous reply.
 */
#define S3FWRN5_FW_UPDATE_SETTLE_MS		20
#define S3FWRN5_FW_SECTOR_SETTLE_MS		20
#define S3FWRN5_FW_CUSTOM_REPLY_TIMEOUT_MS	5000

#define S3FWRN5_FW_CMD_RESET			0x00

#define S3FWRN5_FW_CMD_GET_BOOTINFO		0x01

/*
 * NUXEL: measured reply body on the S3NRN82 bootloader (23 bytes):
 *   hw=82.00.01.00 sector=1000 page=0200 frame=0106 01 ... buffer=ffff
 * The 10-byte upstream layout (u16 fields) does not describe this part; the
 * full body is captured so the firmware decision can be made from this
 * measurement (the dump is printed when the hardware is not in the flash
 * table).  Field order: 4-byte hw tag, u32 sector, u16 page, u16 frame,
 * u8, 4 bytes, u16 buffer (zero-extended into u32), 4 bytes.
 */
struct s3fwrn5_fw_cmd_get_bootinfo_rsp {
	__u8 hw_version[4];
	__u32 sector_size;
	__u16 page_size;
	__u16 frame_max_size;
	__u8 reserved0;
	__u8 reserved1[4];
	__u32 hw_buffer_size;
	__u8 reserved2[4];
};
#define S3FWRN5_FW_BOOTINFO_SIZE sizeof(struct s3fwrn5_fw_cmd_get_bootinfo_rsp)

#define S3FWRN5_FW_CMD_ENTER_UPDATE_MODE	0x02

struct s3fwrn5_fw_cmd_enter_updatemode {
	__u16 hashcode_size;
	__u16 signature_size;
};

#define S3FWRN5_FW_CMD_UPDATE_SECTOR		0x04

struct s3fwrn5_fw_cmd_update_sector {
	__u32 base_address;
};

#define S3FWRN5_FW_CMD_COMPLETE_UPDATE_MODE	0x05

struct s3fwrn5_fw_image {
	const struct firmware *fw;

	char date[13];
	u32 version;
	const void *sig;
	u32 sig_size;
	const void *image;
	u32 image_sectors;
	const void *custom_sig;
	u32 custom_sig_size;
};

struct s3fwrn5_fw_info {
	struct nci_dev *ndev;
	struct s3fwrn5_fw_image fw;
	char fw_name[NFC_FIRMWARE_NAME_MAXSIZE + 1];

	const void *sig;
	u32 sig_size;
	u32 sector_size;
	u32 base_addr;
	/*
	 * NUXEL: the bootloader reports its firmware format in the
	 * GET_BOOTINFO hw_version[2] byte (0 = standard, non-zero = custom).
	 * A custom image (the S3NRN82 reports 0x01) is verified by the
	 * controller against the CUSTOM signature inside the image, so the
	 * standard signature must not be sent for it.
	 */
	bool custom_format;
	/*
	 * NUXEL: set when a reply shows NCI traffic instead of a bootloader
	 * response; the part is already running its NCI firmware.
	 */
	bool part_in_nci;

	struct completion completion;
	struct sk_buff *rsp;
	char parity;
};

void s3fwrn5_fw_init(struct s3fwrn5_fw_info *fw_info, const char *fw_name);
int s3fwrn5_fw_setup(struct s3fwrn5_fw_info *fw_info);
bool s3fwrn5_fw_check_version(struct s3fwrn5_fw_info *fw_info, u32 version);
int s3fwrn5_fw_download(struct s3fwrn5_fw_info *fw_info);
void s3fwrn5_fw_cleanup(struct s3fwrn5_fw_info *fw_info);

int s3fwrn5_fw_recv_frame(struct nci_dev *ndev, struct sk_buff *skb);

#endif /* __LOCAL_S3FWRN5_FIRMWARE_H_ */
