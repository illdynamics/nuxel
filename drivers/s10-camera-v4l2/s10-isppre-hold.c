// SPDX-License-Identifier: GPL-2.0-only
/*
 * Keep the ISPPRE power domain powered for as long as the system is up.
 * Adapted from s10-linux s10-isppre-hold.c for beyond2lte (Exynos 9820).
 *
 * Once ISPPRE has been powered off through exynos-pd and back on, every
 * access to the ISPPRE CMU (0x17000000) raises a synchronous external abort.
 * Samsung's downstream PMU code saves/restores CMU state around a power cycle;
 * mainline's exynos-pd does not. Keep the domain on until proper support
 * exists. This module has no exit function on purpose.
 */
#include <linux/module.h>
#include <linux/of.h>
#include <linux/platform_device.h>
#include <linux/pm_runtime.h>

#include "s10-compat.h"

static int hold_probe(struct platform_device *pdev)
{
	int ret;

	/* beyond2lte reports "samsung,exynos9820" as its machine compatible. */
	if (!of_machine_is_compatible("samsung,exynos9820"))
		return -ENODEV;
	pm_runtime_enable(&pdev->dev);
	ret = pm_runtime_resume_and_get(&pdev->dev);
	if (ret < 0) {
		pm_runtime_disable(&pdev->dev);
		return ret;
	}
	dev_info(&pdev->dev, "ISPPRE power domain held on (this module cannot be unloaded)\n");
	return 0;
}

static const struct of_device_id hold_match[] = {
	{ .compatible = "samsung,exynos9820-isppre-hold-test" }, { }
};
MODULE_DEVICE_TABLE(of, hold_match);
static struct platform_driver hold_driver = {
	.probe = hold_probe,
	.driver = { .name = "s10-isppre-hold", .of_match_table = hold_match,
		    .suppress_bind_attrs = true },
};

static int __init hold_init(void)
{
	return platform_driver_register(&hold_driver);
}
module_init(hold_init);
MODULE_LICENSE("GPL");
MODULE_DESCRIPTION("Keep the S10+ ISPPRE power domain on (bring-up aid)");
