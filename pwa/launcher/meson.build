project('nuxel-pwa-launcher', 'c',
    version: '0.6.1-beta',
    license: 'MIT',
    default_options: [
        'c_std=c17',
        'warning_level=3',
        'buildtype=release',
        'b_pie=true',
        'b_lto=true',
    ]
)

# Dependencies
webkitgtk_dep = dependency('webkitgtk-6.0', version: '>=2.44')
gtk4_dep = dependency('gtk4', version: '>=4.14')
json_glib_dep = dependency('json-glib-1.0', version: '>=1.8')

# Compiler flags for hardening
add_project_arguments([
    '-fstack-protector-strong',
    '-D_FORTIFY_SOURCE=3',
    '-fno-omit-frame-pointer',
    '-fno-delete-null-pointer-checks',
    '-fno-strict-overflow',
    '-Werror=format-security',
    '-mbranch-protection=standard',
], language: 'c')

add_project_link_arguments([
    '-Wl,-z,relro,-z,now,-z,noexecstack',
    '-Wl,-z,separate-code',
    '-Wl,--as-needed',
], language: 'c')

# The PWA launcher binary
executable('nuxel-pwa-launcher',
    'nuxel-pwa-launcher.c',
    dependencies: [webkitgtk_dep, gtk4_dep, json_glib_dep],
    install: true,
    install_dir: '/app/bin',
)

# Install configuration template
configure_file(
    input: 'nuxel-pwa.conf.in',
    output: 'nuxel-pwa.conf',
    install_dir: '/app/etc',
    configuration: configuration_data(),
)
