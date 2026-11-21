/* SPDX-License-Identifier: GPL-2.0-only */
#ifndef S10_S5K_FW_H
#define S10_S5K_FW_H
#ifdef __KERNEL__
#include <linux/types.h>
#include <linux/errno.h>
#include <linux/string.h>
#else
#include <stdint.h>
#include <stddef.h>
#include <errno.h>
#include <string.h>
typedef uint8_t u8;
typedef uint16_t u16;
typedef uint32_t u32;
#endif

#define S5K_FW_HEADER 24
#define S5K_FW_MAX_SIZE (1024 * 1024)
struct s5k_fw_view {
	const u8 *data;
	size_t size;
	u16 tables, bursts;
};
static inline u16 s5k_fw_u16(const u8 *p)
{
	return (u16)p[0] | ((u16)p[1] << 8);
}
static inline u32 s5k_fw_u32(const u8 *p)
{
	return (u32)p[0] | ((u32)p[1] << 8) | ((u32)p[2] << 16) | ((u32)p[3] << 24);
}
static inline const u8 *s5k_fw_table(const struct s5k_fw_view *v, unsigned int i)
{
	return v->data + S5K_FW_HEADER + 12 * i;
}
static inline const u8 *s5k_fw_burst(const struct s5k_fw_view *v, unsigned int i)
{
	return v->data + S5K_FW_HEADER + 12 * v->tables + 8 * i;
}
/* Validate the entire container before allocating tables or touching a sensor.
 * Canonical contiguous offsets reject overlap, aliases, holes and trailing data.
 */
static inline int s5k_fw_validate(const u8 *p, size_t size, u16 model,
				u16 revision, unsigned int modes, int master,
				struct s5k_fw_view *view)
{
	struct s5k_fw_view v;
	size_t cursor, i, j;
	unsigned int tables;

	if (!view || !p || size < S5K_FW_HEADER || size > S5K_FW_MAX_SIZE ||
	    modes < 1 || modes > 2 || (master != 0 && master != 1))
		return -EINVAL;
	tables = 1 + modes + master;
	if (memcmp(p, "S10S5K1\0", 8) || s5k_fw_u16(p + 8) != 1 ||
	    s5k_fw_u16(p + 10) != model || s5k_fw_u16(p + 12) != revision ||
	    s5k_fw_u16(p + 14) != tables || s5k_fw_u16(p + 18) ||
	    s5k_fw_u32(p + 20) != size)
		return -EINVAL;
	v.data = p;
	v.size = size;
	v.tables = tables;
	v.bursts = s5k_fw_u16(p + 16);
	if (v.bursts > 16)
		return -EINVAL;
	cursor = S5K_FW_HEADER + 12 * tables + 8 * v.bursts;
	if (cursor > size)
		return -EINVAL;
	for (i = 0; i < tables; i++) {
		const u8 *d = s5k_fw_table(&v, i);
		u16 id = i == 0 ? 0 : i <= modes ? 0x100 + i - 1 : 1;
		u32 count = s5k_fw_u32(d + 8);

		if (s5k_fw_u16(d) != id || s5k_fw_u16(d + 2) ||
		    s5k_fw_u32(d + 4) != cursor || !count ||
		    count > (size - cursor) / 5)
			return -EINVAL;
		for (j = 0; j < count; j++) {
			const u8 *op = p + cursor + 5 * j;
			u16 reg = s5k_fw_u16(op), val = s5k_fw_u16(op + 2);
			u8 len = op[4];

			if (reg == 0xffff) {
				if (len || val > 65000)
					return -EINVAL;
			} else if (reg == 0xfffe) {
				if (len || val >= v.bursts)
					return -EINVAL;
			} else if ((len != 1 && len != 2) || (len == 1 && val > 255)) {
				return -EINVAL;
			}
		}
		cursor += count * 5;
	}
	for (i = 0; i < v.bursts; i++) {
		const u8 *d = s5k_fw_burst(&v, i);
		u32 bytes = s5k_fw_u32(d + 4);

		if (s5k_fw_u32(d) != cursor || bytes < 2 || bytes > 65535 ||
		    bytes > size - cursor)
			return -EINVAL;
		cursor += bytes;
	}
	if (cursor != size)
		return -EINVAL;
	*view = v;
	return 0;
}
#endif
