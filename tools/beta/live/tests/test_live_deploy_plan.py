#!/usr/bin/env python3
"""Offline tests for the EXTENDED deploy manifest and its guards (briq-01).

Run:  python3 tools/beta/live/tests/test_live_deploy_plan.py

Nothing here touches the phone: the deploy plan, the manifest contract and the
framebuffer-owner assertion are all proven against the repository and against a
synthetic /proc tree.  The tests answer, in order:

  * does the plan still build for the CURRENT manifest, with the seven core groups
    byte-identical (briq-10b's unrun plan must stay valid)?
  * does the extension block really cover the rest of the built programme, with
    everything left out either in non_deployable[] or named as a procedure?
  * are the invariants enforced — a raw-partition / .img / non-userspace target, a
    source outside the repository, a missing source, an unknown risk class, an
    extension group whose risk goes backwards, a group with no rollback /
    health_check / restart-or-reload, flash tooling in a pre/post/reload command,
    and a non_deployable entry that tries to claim a promoted state?
  * does the framebuffer-owner assertion really distinguish one owner from none,
    from two, and from the wrong one?
"""

from __future__ import annotations

import fnmatch
import hashlib
import json
import os
import subprocess
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from harness import load_live  # noqa: E402

nl = load_live()
REPO = nl.repo_root_from_here()
MANIFEST = os.path.join(REPO, "tools", "beta", "live", "deploy-manifest.json")

#: sha256 of json.dumps(core_groups, sort_keys=True, separators=(",",":")) — the
#: seven core groups as present in the supplied v0.6.1-beta archive before extending the
#: manifest.  If this changes, the unrun core plan changed, which is forbidden.
CORE_GROUPS_DIGEST = "013c055c3e347d8e10afb950cf9d83a1d49401f45b99cf3517d9ee8b5229eb83"
CORE_GROUP_IDS = ["launcher-pwa", "status-bar-safe-zones", "session-units",
                  "animation-handoff", "touch-and-buttons", "audio-and-network-config",
                  "console-and-kernel-side-followups"]
EXTENSION_GROUP_IDS = ["pwa-app-suite", "pwa-shared-runtime", "app-registry-consumers",
                       "configs-nuxel-remaining", "s10plus-a33-runtime", "services-runtime",
                       "native-shell-sources", "boot-animation-runtime", "packages-reconcile",
                       "nuxel-branding-sounds-and-icons"]


def manifest():
    with open(MANIFEST) as fh:
        return json.load(fh)


#: The mirror root the manifest is *authored* against.  The plan remaps it onto
#: the device's real root (/usr/share/nuxel — measured on the S10+), so coverage
#: assertions must be made against the remapped root, not the authored one.
MIRROR = "/home/nuxel/nuxel"


def device_root():
    return nl.remap_path(MIRROR, nl.resolve_root_map(manifest()))


def plan_of(man):
    return nl.build_deploy_plan(man, REPO)


def valid_group(gid="unit-group", **over):
    group = {"id": gid, "component": "unit test group", "priority": 1, "risk": "low",
             "restart_service": None, "declared_reload": "systemctl daemon-reload",
             "pre": [], "health_check": "true", "rollback": "restore <target>.nuxel-rollback",
             "files": [{"source": "README.md", "target": "/etc/nuxel/unit-test.conf"}]}
    group.update(over)
    return group


def tracked(prefix):
    out = subprocess.check_output(["git", "-C", REPO, "ls-files", prefix]).decode()
    return [l for l in out.split("\n") if l.strip()]


class TestCorePlanIsFrozen(unittest.TestCase):
    def test_seven_core_groups_are_byte_compatible(self):
        man = manifest()
        core = man["groups"][:7]
        self.assertEqual([g["id"] for g in core], CORE_GROUP_IDS)
        canon = json.dumps(core, sort_keys=True, separators=(",", ":"))
        self.assertEqual(hashlib.sha256(canon.encode()).hexdigest(), CORE_GROUPS_DIGEST,
                         "the core briq-10b groups must stay byte-identical")

    def test_core_plan_still_has_its_38_steps_and_4_blocks(self):
        plan = plan_of(manifest())
        core_steps = [s for s in plan["steps"] if s["group"] in CORE_GROUP_IDS]
        self.assertEqual(len(core_steps), 38,
                         "the uploaded current core plan is 7 groups / 38 file steps")
        self.assertEqual([s["group"] for s in plan["skipped"]],
                         ["console-and-kernel-side-followups"])
        self.assertTrue(plan["skipped"][0]["verdict"] == "BLOCKED_KERNEL")


class TestExtendedPlanBuilds(unittest.TestCase):
    def test_plan_builds_without_a_single_violation(self):
        plan = plan_of(manifest())
        self.assertEqual(plan["violations"], [],
                         "the shipped manifest must produce a clean plan: %s"
                         % json.dumps(plan["violations"])[:400])
        self.assertGreater(len(plan["steps"]), 37)
        for gid in EXTENSION_GROUP_IDS:
            self.assertTrue(any(s["group"] == gid for s in plan["steps"]),
                            "extension group %s plans no steps" % gid)

    def test_every_group_declares_the_full_contract(self):
        man = manifest()
        for group in man["groups"]:
            gid = group["id"]
            if group.get("state") in ("blocked_kernel", "blocked_firmware"):
                continue
            self.assertIn(group["risk"], nl.RISK_CLASSES, gid)
            self.assertTrue(str(group.get("health_check") or "").strip(), gid)
            self.assertTrue(str(group.get("rollback") or "").strip(), gid)
            self.assertTrue(
                group.get("restart_service")
                or nl.group_reload(group, man),
                "%s must declare a restart_service or a deliberate reload" % gid)

    def test_extension_risk_order_is_ascending(self):
        man = manifest()
        seq = [(g["id"], g["priority"], nl.risk_rank(g["risk"]))
               for g in man["groups"] if g["id"] in EXTENSION_GROUP_IDS]
        self.assertEqual(len(seq), len(EXTENSION_GROUP_IDS))
        ranks = [r for _, _, r in seq]
        prios = [p for _, p, _ in seq]
        self.assertEqual(ranks, sorted(ranks), "risk must never go backwards: %s" % seq)
        self.assertEqual(prios, sorted(prios), "priority must never go backwards: %s" % seq)
        self.assertEqual(ranks[0], 0, "the extension starts with a low-risk group")

    def test_no_extension_target_is_written_twice(self):
        plan = plan_of(manifest())
        seen = {}
        for step in plan["steps"]:
            if step["group"] in CORE_GROUP_IDS:
                continue
            seen.setdefault(step["target"], []).append(step["group"])
        dups = {t: g for t, g in seen.items() if len(g) > 1}
        self.assertEqual(dups, {}, "an extension target is staged twice: %s" % dups)

    def test_core_vs_extension_overlap_is_documented(self):
        man = manifest()
        plan = plan_of(man)
        core = {f["target"] for g in man["groups"][:7] for f in g.get("files", [])}
        ext = {s["target"] for s in plan["steps"] if s["group"] in EXTENSION_GROUP_IDS}
        documented = {o["target"] for o in man["target_overrides"]}
        overlap = core & ext
        self.assertTrue(overlap <= documented | {"/etc/nuxel/statusbar-safezones.json"},
                        "undocumented target overlap: %s" % (overlap - documented))

    def test_every_non_deployable_entry_is_honest(self):
        for entry in manifest()["non_deployable"]:
            self.assertIn(entry["terminal_state"], nl.VALID_VERDICTS, entry["path"])
            self.assertNotIn(entry["terminal_state"], nl.PROMOTING_TERMINAL_STATES,
                             "%s claims a promoted state" % entry["path"])
            self.assertTrue(str(entry.get("reason") or "").strip(), entry["path"])
            proc = entry.get("procedure")
            if proc:
                self.assertTrue(os.path.isfile(os.path.join(REPO, proc)),
                                "procedure missing for %s" % entry["path"])

    def test_referenced_install_procedures_exist_and_are_indexed(self):
        man = manifest()
        index = {p["path"] for p in man["install_procedures"]}
        self.assertTrue(index)
        for group in man["groups"]:
            proc = group.get("install_procedure")
            if proc:
                self.assertTrue(os.path.isfile(os.path.join(REPO, proc)), proc)
                self.assertIn(proc, index, "%s is not in install_procedures[]" % proc)
        for entry in man["non_deployable"]:
            if entry.get("procedure"):
                self.assertIn(entry["procedure"], index, entry["procedure"])

    def test_step_carries_pre_post_and_the_declared_reload(self):
        plan = plan_of(manifest())
        by_group = {}
        for step in plan["steps"]:
            by_group.setdefault(step["group"], step)
        self.assertEqual(by_group["session-units"]["pre"], ["systemctl daemon-reload"],
                         "the core group's declared pre step must not be dropped")
        self.assertEqual(by_group["session-units"]["declared_reload"],
                         "systemctl daemon-reload")
        self.assertEqual(by_group["configs-nuxel-remaining"]["declared_reload"],
                         "systemctl daemon-reload")
        self.assertTrue(by_group["boot-animation-runtime"]["pre"])
        self.assertTrue(by_group["boot-animation-runtime"]["post"])
        script = nl.install_script(by_group["boot-animation-runtime"])
        self.assertIn("nuxel-fb-owner-assert.sh", script)
        self.assertIn("/usr/local/bin/nuxel-fb-owner-assert.sh --expect nuxel-wl-fb", script)


class TestCoverageOfTheBuiltProgramme(unittest.TestCase):
    """The extension must cover what the mission says was unreachable."""

    def _targets(self):
        plan = plan_of(manifest())
        return {s["source"] for s in plan["steps"]}

    def _plan_sets(self):
        """(sources, targets) — a derived artefact is covered by its TARGET."""
        plan = plan_of(manifest())
        return ({s["source"] for s in plan["steps"]},
                {s["target"] for s in plan["steps"]})

    def _non_deployable(self):
        return [e["path"] for e in manifest()["non_deployable"]]

    def _covered(self, rel, sources, nd, targets=()):
        """Is `rel` either planned, or named as non-deployable?

        A non_deployable[] entry may be an exact path, a directory prefix (with or
        without a trailing slash) or a glob; the `*` in a glob matches across
        separators here because the entry is a repository-tree marker, not a shell
        pattern.
        """
        if rel in sources or rel in targets or (device_root() + "/" + rel) in targets:
            return True
        for pat in nd:
            base = pat.rstrip("/")
            if rel == base or rel.startswith(base + "/"):
                return True
            if fnmatch.fnmatch(rel, pat) or fnmatch.fnmatch(rel, base + "/*"):
                return True
        return False

    def test_every_pwa_app_file_is_deployed(self):
        sources, targets = self._plan_sets()
        nd = self._non_deployable()
        missing = [f for f in tracked("pwa/nuxel-apps")
                   if not self._covered(f, sources, nd, targets)]
        self.assertEqual(missing, [], "uncovered PWA app files: %s" % missing[:8])

    def test_shared_pwa_runtime_and_launcher_leftovers_are_deployed(self):
        sources, targets = self._plan_sets()
        for rel in ("pwa/nuxel-common/bridge.js", "pwa/nuxel-common/app-registry.json",
                    "pwa/nuxel-home/icons/icon-192.png",
                    "pwa/nuxel-home/assets/nuxel-boot-animation.mp4"):
            self.assertIn(rel, sources, "%s must be deployable" % rel)
        # the per-PWA wallpaper copies are DERIVED (gitignored, single-sourced in
        # assets/): they are covered by their TARGET, installed from the tracked
        # canonical source — the A31 404 this closes.
        for tgt in (device_root() + "/pwa/nuxel-home/assets/nuxel-background.png",
                    device_root() + "/pwa/nuxel-apps/calendar/assets/nuxel-background.png"):
            self.assertIn(tgt, targets, "%s must be installed from assets/" % tgt)
        self.assertIn("assets/nuxel-background.png", sources)

    def test_registry_consumers_are_deployed(self):
        sources = self._targets()
        for rel in ("pwa/nuxel-common/app-registry.json",
                    "shell/nuxel-home-native/nuxel_home/app_registry.json",
                    "tools/s10plus/a33/verify-app-registry.py"):
            self.assertIn(rel, sources, rel)

    def test_services_are_deployed(self):
        sources, targets = self._plan_sets()
        nd = self._non_deployable()
        missing = [f for f in tracked("services")
                   if not self._covered(f, sources, nd, targets)]
        self.assertEqual(missing, [], "uncovered services files: %s" % missing[:8])

    def test_configs_nuxel_are_deployed_or_named(self):
        sources, targets = self._plan_sets()
        nd = self._non_deployable()
        missing = [f for f in tracked("configs/nuxel")
                   if not self._covered(f, sources, nd, targets)]
        self.assertEqual(missing, [], "uncovered configs/nuxel files: %s" % missing[:8])
        # the guard refuses /etc/nuxel/modem/**, so those must be in non_deployable
        self.assertTrue(any("configs/nuxel/modem/modem.json" == p for p in nd))
        self.assertTrue(any(p.startswith("configs/nuxel/modem/") for p in nd))

    def test_shell_and_a33_sources_are_deployed_or_named(self):
        sources, targets = self._plan_sets()
        nd = self._non_deployable()
        for prefix in ("shell/nuxel-shell", "tools/s10plus/a33"):
            missing = [f for f in tracked(prefix)
                       if not self._covered(f, sources, nd, targets)]
            self.assertEqual(missing, [], "uncovered %s files: %s" % (prefix, missing[:8]))

    def test_boot_animation_and_packages_groups_have_their_subjects(self):
        sources = self._targets()
        for rel in ("services/nuxel-animation/bin/nuxel-animation-claim",
                    "services/nuxel-animation/systemd/nuxel-animation.service",
                    "assets/nuxel-boot-animation.mp4",
                    "tools/beta/live/nuxel-fb-owner-assert.sh",
                    "images/s10plus/packages-manifest.json",
                    "tools/s10plus/a33/verify-packages.py"):
            self.assertIn(rel, sources, "%s must be deployable" % rel)

    def test_non_deployable_sources_never_enter_the_plan(self):
        sources = self._targets()
        for group in manifest()["groups"]:
            for entry in group.get("files", []):
                self.assertNotIn(entry["source"], manifest()["non_deployable"],
                                 "%s is listed as non-deployable AND planned"
                                 % entry["source"])
        self.assertNotIn("boot/initramfs/init.sh", sources)

    def test_gitignored_artefacts_are_never_sources(self):
        """build/ is gitignored: nothing may be staged from it."""
        for step in plan_of(manifest())["steps"]:
            self.assertFalse(step["source"].startswith("build/"),
                             "staged from a gitignored path: %s" % step["source"])


class TestGuardRefusals(unittest.TestCase):
    def test_raw_partition_target_is_refused(self):
        man = {"groups": [valid_group(files=[{"source": "README.md",
                                             "target": "/dev/block/by-name/BOOT"}])]}
        plan = plan_of(man)
        self.assertFalse(plan["steps"])
        self.assertTrue(any(v["kind"] == "guard" for v in plan["violations"]))

    def test_flashed_image_target_is_refused(self):
        for tgt in ("/usr/local/bin/nuxel-boot.img",
                    "/home/nuxel/nuxel/nuxel-beyond2lte-boot-merged.img",
                    "/etc/nuxel/recovery.img"):
            man = {"groups": [valid_group(files=[{"source": "README.md", "target": tgt}])]}
            plan = plan_of(man)
            self.assertFalse(plan["steps"], tgt)
            self.assertTrue(any(v["kind"] == "guard" for v in plan["violations"]), tgt)

    def test_non_userspace_root_target_is_refused(self):
        for tgt in ("/opt/nuxel/nuxel-anim-player", "/etc/NetworkManager/conf.d/x.conf",
                    "/lib/modules/4.14.253/x.ko", "/root/thing", "/etc/tor/torrc"):
            man = {"groups": [valid_group(files=[{"source": "README.md", "target": tgt}])]}
            plan = plan_of(man)
            self.assertFalse(plan["steps"], tgt)
            self.assertTrue(any(v["kind"] == "guard" for v in plan["violations"]), tgt)

    def test_source_outside_the_repository_is_refused(self):
        for src in ("/etc/passwd", "../../../etc/passwd", "docs/../../outside.txt"):
            man = {"groups": [valid_group(files=[{"source": src,
                                                 "target": "/etc/nuxel/x.conf"}])]}
            plan = plan_of(man)
            self.assertFalse(plan["steps"], src)
            self.assertTrue(any(v["kind"] == "source_escape" for v in plan["violations"]),
                            "a source outside the repo must be refused: %s" % src)

    def test_missing_source_is_refused_not_dropped(self):
        man = {"groups": [valid_group(files=[{"source": "does/not/exist.conf",
                                             "target": "/etc/nuxel/x.conf"}])]}
        plan = plan_of(man)
        self.assertFalse(plan["steps"])
        self.assertTrue(any(v["kind"] == "missing_source" for v in plan["violations"]))

    def test_unknown_risk_class_is_refused(self):
        man = {"groups": [valid_group(risk="critical")]}
        plan = plan_of(man)
        self.assertTrue(any(v["kind"] == "manifest" for v in plan["violations"]),
                        plan["violations"])

    def test_group_without_rollback_health_or_reload_is_refused(self):
        for over in ({"rollback": ""}, {"health_check": ""},
                     {"declared_reload": "", "restart_service": None},
                     {"files": [{"source": "README.md"}]}):
            man = {"groups": [valid_group(**over)]}
            plan = plan_of(man)
            self.assertTrue(any(v["kind"] == "manifest" for v in plan["violations"]),
                            "manifest violation expected for %s" % over)

    def test_flash_tooling_in_a_group_command_is_refused(self):
        for over in ({"pre": ["heimdall flash --BOOT boot.img"]},
                     {"post": ["fastboot reboot"]},
                     {"declared_reload": "odin4 -b BL"},
                     {"health_check": "dd if=/dev/block/mmcblk0 of=/tmp/x"}):
            man = {"groups": [valid_group(**over)]}
            plan = plan_of(man)
            self.assertTrue(any(v["kind"] == "command_guard" for v in plan["violations"]),
                            "command guard expected for %s" % over)

    def test_extension_risk_going_backwards_is_refused(self):
        man = manifest()
        groups = [dict(g) for g in man["groups"]]
        # swap the last two extension groups: high before medium
        idx = [i for i, g in enumerate(groups) if g["id"] in EXTENSION_GROUP_IDS]
        a, b = groups[idx[-2]], groups[idx[-1]]
        groups[idx[-2]], groups[idx[-1]] = b, a
        man["groups"] = groups
        man["extension"] = dict(man["extension"],
                                groups=[EXTENSION_GROUP_IDS[-1], EXTENSION_GROUP_IDS[-2]])
        plan = plan_of(man)
        self.assertTrue(any(v["kind"] == "ordering" for v in plan["violations"]),
                        "a backwards risk step must be refused")

    def test_extension_group_missing_from_the_block_is_refused(self):
        man = manifest()
        man["extension"] = dict(man["extension"], groups=EXTENSION_GROUP_IDS[:-1])
        plan = plan_of(man)
        self.assertTrue(any(v["kind"] == "ordering" for v in plan["violations"]))

    def test_non_deployable_claiming_a_promoted_state_is_refused(self):
        for state in ("VERIFIED_ON_S10PLUS", "DEPLOYED_UNVERIFIED", "NOT_A_VERDICT"):
            man = {"groups": [valid_group()],
                   "non_deployable": [{"path": "x", "reason": "y",
                                       "terminal_state": state}]}
            plan = plan_of(man)
            self.assertTrue(any(v["kind"] == "manifest" for v in plan["violations"]), state)

    def test_non_deployable_referencing_a_missing_procedure_is_refused(self):
        man = {"groups": [valid_group()],
               "non_deployable": [{"path": "x", "reason": "y",
                                   "terminal_state": "INSTALL_PROCEDURE_REQUIRED",
                                   "procedure": "docs/does-not-exist.md"}]}
        plan = plan_of(man)
        self.assertTrue(any(v["kind"] == "procedure_missing" for v in plan["violations"]))

    def test_group_install_procedure_must_exist(self):
        man = {"groups": [valid_group(install_procedure="docs/nope.md")]}
        plan = plan_of(man)
        self.assertTrue(any(v["kind"] == "procedure_missing" for v in plan["violations"]))


class TestFramebufferOwnerAssertion(unittest.TestCase):
    """The mission's [FRAMEBUFFER] rule, as an executable check."""

    SCRIPT = os.path.join(REPO, "tools", "beta", "live", "nuxel-fb-owner-assert.sh")

    def _fixture(self, holders):
        """holders: list of (pid, comm) that hold /dev/fb0."""
        root = tempfile.mkdtemp(prefix="nxl-proc-")
        for pid, comm in holders:
            d = os.path.join(root, str(pid))
            os.makedirs(os.path.join(d, "fd"), exist_ok=True)
            with open(os.path.join(d, "comm"), "w") as fh:
                fh.write(comm + "\n")
            os.symlink("/dev/fb0", os.path.join(d, "fd", "3"))
        # a process that holds something else, to prove the scan is real
        d = os.path.join(root, "9999")
        os.makedirs(os.path.join(d, "fd"), exist_ok=True)
        with open(os.path.join(d, "comm"), "w") as fh:
            fh.write("unrelated\n")
        os.symlink("/dev/null", os.path.join(d, "fd", "3"))
        return root

    def _run(self, root, *args):
        p = subprocess.run(["sh", self.SCRIPT, "--proc-root", root] + list(args),
                           stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
        return p.returncode, p.stdout.strip()

    def test_single_correct_owner_passes(self):
        rc, out = self._run(self._fixture([(101, "nuxel-wl-fb")]), "--expect", "nuxel-wl-fb")
        self.assertEqual(rc, 0, out)
        self.assertIn("FB_OWNER_ASSERT=PASS", out)
        self.assertIn("owner=nuxel-wl-fb", out)
        self.assertIn("count=1", out)

    def test_no_writer_fails_and_allow_zero_is_explicit(self):
        root = self._fixture([])
        rc, out = self._run(root)
        self.assertEqual(rc, 1, out)
        self.assertIn("reason=zero", out)
        rc, out = self._run(root, "--allow-zero")
        self.assertEqual(rc, 0, out)
        self.assertIn("count=0", out)

    def test_two_writers_are_the_failure_this_exists_to_catch(self):
        rc, out = self._run(self._fixture([(101, "nuxel-wl-fb"), (202, "nuxel-ui")]))
        self.assertEqual(rc, 2, out)
        self.assertIn("reason=multiple", out)
        self.assertIn("count=2", out)

    def test_wrong_owner_is_reported_separately(self):
        rc, out = self._run(self._fixture([(101, "nuxel-ui")]), "--expect", "nuxel-wl-fb")
        self.assertEqual(rc, 3, out)
        self.assertIn("reason=wrong-owner", out)

    def test_unknown_argument_is_a_usage_error(self):
        rc, out = self._run(self._fixture([(101, "nuxel-wl-fb")]), "--flash")
        self.assertEqual(rc, 4, out)

    def test_the_script_never_writes_or_flashes_anything(self):
        text = open(self.SCRIPT).read()
        for bad in ("heimdall", "odin", "fastboot", "twrp", "dd if=", "mkfs"):
            self.assertNotIn(bad, text, "the assertion helper must not contain %r" % bad)
        self.assertIn("/proc", text)


if __name__ == "__main__":
    unittest.main(verbosity=2)
