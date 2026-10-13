-- Nuxel WirePlumber voice-call profile
--
-- Installed into the WirePlumber conf.d directory:
--   /etc/wireplumber/wireplumber.conf.d/40-nuxel-voice-call.lua
-- (or ~/.config/wireplumber/wireplumber.conf.d/ on per-user setups).
--
-- WirePlumber is the JACK session manager for the phone; it must NOT be
-- replaced by a hardcoded route because the calls are dynamic. This script
-- instead provides the policy hooks that:
--   * label a dedicated "nuxel-call" virtual sink (voice path)
--   * apply "voice-call" priority / AEC hints
--   * crossfade ducking: when a call node appears, media sinks drop ~24 dB
--
-- Verbose hooks only; the actual UCM "VoiceCall" device selection is driven
-- by ALSA UCM (configs/alsa-ucm/GoogleMustang/VoiceCall.conf) triggered from
-- the PipeWire config fragment.

rule = {
  matches = {
    {
      { "node.name", "matches", "nuxel-call*" },
    },
    {
      { "node.name", "matches", "nuxel-.*-voice" },
    },
  },
  apply_properties = {
    ["media.class"] = "Audio/Sink",
    ["node.name"]   = "nuxel-call",
    ["audio.position"] = "FL,FR",
    ["node.description"] = "Nuxel phone call (voice path)",

    -- Voice-call routing hints consumed by Phosh / ModemManager.
    ["route.ucm-device"] = "VoiceCall",
    ["audio.echo-cancel"] = true,
    ["audio.focus"] = "voice-call",
  },
}

table.insert(alsa_monitor.rules, rule)
table.insert(bluez_monitor.rules, rule)
