-- Nuxel WirePlumber JACK session-manager toggle
--
-- Installed into:
--   /etc/wireplumber/wireplumber.conf.d/50-nuxel-jack-session.lua
-- (or ~/.config/wireplumber/wireplumber.conf.d/ on per-user setups).
--
-- The JACK session manager is a WirePlumber concern, NOT a PipeWire context
-- property. PipeWire has no `wireplumber.jack-session` context property;
-- the setting belongs here. WirePlumber composes its session manager from the
-- component list in `conf.wireplumber.profiles.location.default`. Appending
-- the JACK session-manager script tells WirePlumber to act as the JACK
-- *session* manager so wlroots/Phosh can grab the voice stream; jackd is NOT
-- required. JACK-aware apps pull the stream via libpipewire-module-jack from
-- the PipeWire fragment (configs/pipewire/nuxel-phone.conf.part).

conf = conf or {}
conf.wireplumber = conf.wireplumber or {}
conf.wireplumber.profiles = conf.wireplumber.profiles or {}
conf.wireplumber.profiles.location = conf.wireplumber.profiles.location or {}
conf.wireplumber.profiles.location.default =
  conf.wireplumber.profiles.location.default or {}

-- Append the JACK session-manager component to the active default profile.
table.insert(conf.wireplumber.profiles.location.default, {
  v = 2,
  protocol = "jack",
  scripts = {
    -- JACK session manager shipped by WirePlumber (policy module).
    "policy-90-jack-session-manager",
  },
})
