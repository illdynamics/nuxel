project('nuxel-home-native',
    version: '0.7.3-beta',
    meson_version: '>= 0.53.0',
)

python3 = import('python3')
python3_dep = python3.dependency()

# Install Python package
install_subdir('nuxel_home',
    install_dir: python3.sysconfig_path('purelib'),
)

# Install desktop file
install_data('data/org.nuxel.Home.desktop',
    install_dir: join_paths(get_option('datadir'), 'applications'),
)

# Install AppStream metainfo
install_data('data/org.nuxel.Home.metainfo.xml',
    install_dir: join_paths(get_option('datadir'), 'metainfo'),
)

# Install app icon
install_data('data/icons/org.nuxel.Home.svg',
    install_dir: join_paths(get_option('datadir'), 'icons', 'hicolor', 'scalable', 'apps'),
)

# Install launcher script
install_data('nuxel-home-launcher',
    install_dir: get_option('prefix') / 'bin',
    install_mode: 'rwxr-xr-x',
    rename: 'nuxel-home',
)
