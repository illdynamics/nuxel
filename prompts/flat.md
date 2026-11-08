Yes, it usually means your software manager is filtering the main Flathub repository or Flathub isn't fully enabled system-wide.

Distros using GNOME Software or Discover often restrict "proprietary" or non-free apps by default, or ship with a filtered OS-specific Flatpak remote (like NixOS, Fedora, or openSUSE) that hides packages like official Discord (`com.discordapp.Discord`) while still showing community ones like Vesktop.

---

### Step 1: Check your active remotes

Run this in your terminal to see what sources Flatpak is currently looking at:

```bash
flatpak remotes

```

If `flathub` isn't listed, or if it says `flathub (filtered)`, your software manager won't show the full catalog.

---

### Step 2: Add full Flathub access

Enable the official, unfiltered Flathub repository directly:

```bash
flatpak remote-add --if-not-exists flathub https://dl.flathub.org/repo/flathub.flatpakrepo

```

If it was already added but filtered, unfilter it:

```bash
flatpak remote-modify --no-filter flathub

```

---

### Step 3: Install official Discord via CLI

Once the remote is added, refresh your software store or install the official Flatpak directly:

```bash
flatpak install flathub com.discordapp.Discord

```

*(Note: If you run into the Wayland audio/screenshare limitation on the official Discord build, stick with **Vesktop** since it already has PipeWire audio patch routing out of the box).*
