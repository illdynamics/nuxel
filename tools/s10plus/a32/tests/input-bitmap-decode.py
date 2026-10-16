#!/usr/bin/env python3
"""Decode the /proc/bus/input/devices KEY bitmap exactly as the kernel prints it.

Fixture = the LIVE gpio_keys line read from the S10+ this cycle:
    B: KEY=8000000000000000 0 0 0 0 0 0 0 0 1c000000000000 0
Expected: VOLUMEDOWN 114, VOLUMEUP 115, POWER 116, assistant/Bixby 703.
This is the same decode the mission (section 10) requires before any keycode is
assumed, and the manager's own EVIOCGBIT output must agree with it.
"""
import sys

WORDS = 11  # kernel prints ceil(KEY_CNT/64) words for KEY_MAX=0x2ff


def decode(line):
    hexwords = line.split("KEY=")[1].split()
    words = [int(w, 16) for w in hexwords]
    keys = set()
    for idx, w in enumerate(words):
        word_index = len(words) - 1 - idx          # first printed word is the HIGHEST
        for bit in range(64):
            if w & (1 << bit):
                keys.add(word_index * 64 + bit)
    return sorted(keys)


def main():
    fixture = "B: KEY=8000000000000000 0 0 0 0 0 0 0 0 1c000000000000 0"
    got = decode(fixture)
    want = [114, 115, 116, 703]
    print("decoded keys: %s" % got)
    failures = 0
    if got != want:
        print("FAIL expected %s" % want); failures += 1
    else:
        print("PASS gpio_keys key set matches the measured EVIOCGBIT output")
    names = {114: "VOLUMEDOWN", 115: "VOLUMEUP", 116: "POWER", 703: "assistant/Bixby"}
    for k in want:
        if k in got:
            print("PASS key %d = %s present" % (k, names[k]))
        else:
            print("FAIL key %d = %s missing" % (k, names[k])); failures += 1
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
