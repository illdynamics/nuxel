project('nuxel-shell', 'c',
  version: '0.3.2-alpha',
  meson_version: '>= 0.60.0',
  default_options: ['warning_level=2', 'c_std=c11'],
)

fs = import('fs')

# Core UI toolkit dependencies (required for the GTK4 apps).
gtk4_dep = dependency('gtk4', required: false)
adwaita_dep = dependency('libadwaita-1', required: false)
glib_dep = dependency('glib-2.0', required: false)
gio_dep = dependency('gio-2.0', required: false)

# Optional dependencies.
#  - ModemManager client library is only needed by nuxel-dialer and only when a
#    matching dev package is present on the sysroot. The apps otherwise use
#    plain GDBus at runtime and degrade to the bridge mock in the VM.
#  - json-glib is used by nuxel-permissions when present.
mm_glib_dep = dependency('ModemManager', required: false)
json_glib_dep = dependency('json-glib-1.0', required: false)
libcap_dep = dependency('libcap', required: false)

# sandbox: pure C launcher using Linux namespaces, seccomp + Landlock.
if libcap_dep.found()
  executable('nuxel-sandbox',
    'nuxel-sandbox/sandbox.c',
    dependencies: [libcap_dep],
    include_directories: include_directories('nuxel-sandbox'),
    install: true,
    install_dir: get_option('bindir'),
  )
else
  warning('libcap not found — nuxel-sandbox will be built via gcc directly in build-native-apps.sh')
endif

# Native GTK4 C apps (the 5 phone apps). The Python home launcher is not
# compiled here — it is byte-compiled by build-native-apps.sh.
apps = {
  'nuxel-dialer': 'nuxel-dialer/main.c',
  'nuxel-contacts': 'nuxel-contacts/main.c',
  'nuxel-messages': 'nuxel-messages/main.c',
  'nuxel-settings': 'nuxel-settings/main.c',
  'nuxel-permissions': 'nuxel-permissions/main.c',
}

if gtk4_dep.found() and adwaita_dep.found()
  # Base deps shared by every GTK4 app. Deps are added on a per-app basis.
  foreach app_name, src : apps
    if not fs.exists(src)
      warning('Source file missing for ' + app_name + ': ' + src)
      continue
    endif

    deps = [gtk4_dep, adwaita_dep]
    if glib_dep.found()
      deps += glib_dep
    endif
    if gio_dep.found()
      deps += gio_dep
    endif

    extra_c_args = []

    # ModemManager client library: only for the dialer and only when the dev
    # package is present. The dialer guards that header behind HAVE_MM_GLIB.
    if app_name == 'nuxel-dialer'
      if mm_glib_dep.found()
        deps += mm_glib_dep
        extra_c_args += '-DHAVE_MM_GLIB'
      else
        extra_c_args += '-DNUXEL_NO_MM=1'
      endif
    endif

    # nuxel-contacts and nuxel-permissions both parse/store JSON via
    # json-glib, so link them against json-glib when it is present in the
    # sysroot (json-glib-devel). Declared required: false so a sysroot without
    # json-glib still configures; the crt source must then be adapted.
    if (app_name == 'nuxel-contacts' or app_name == 'nuxel-permissions') \
       and json_glib_dep.found()
      deps += json_glib_dep
    endif

    executable(app_name, src,
      dependencies: deps,
      c_args: extra_c_args,
      install: true,
      install_dir: get_option('bindir'),
    )
  endforeach
else
  warning('GTK4/libadwaita not found — skipping GTK4 native C app build. '
          + 'Install gtk4-devel and libadwaita-devel for native builds.')
endif

# Install shared desktop entries (used by the Phosh app drawer).
# The canonical .desktop files live in shell/config/; reference them via a
# relative path (../config/...) so meson setup does not abort on a missing
# shell/nuxel-shell/config/ directory.
install_data(
  [
    '../config/nuxel-home.desktop',
    '../config/nuxel-dialer.desktop',
    '../config/nuxel-contacts.desktop',
    '../config/nuxel-messages.desktop',
    '../config/nuxel-settings.desktop',
    '../config/nuxel-permissions.desktop',
  ],
  install_dir: get_option('datadir') / 'applications',
)
