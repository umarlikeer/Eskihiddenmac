[app]
title = GA-GOA Elektr Tarmog'i
package.name = gagoelectrnetwork
package.domain = uz.research.powergrid
source.dir = .
source.include_exts = py,txt,md,csv
source.exclude_dirs = .git,.github,__pycache__,results
version = 1.0.0
requirements = python3,kivy,numpy
orientation = portrait
fullscreen = 0
android.archs = arm64-v8a, armeabi-v7a
android.minapi = 24
android.api = 35
android.ndk = 27c
android.accept_sdk_license = True
android.allow_backup = True

# Pin python-for-android to the develop branch: the stable/PyPI p4a release
# hits a known, still-open upstream bug on Python 3.14 recipes where its
# internal venv self-upgrades pip and corrupts itself (two pip versions end
# up coexisting in site-packages), raising:
#   ImportError: cannot import name 'BuildDependencyInstallError' from 'pip._internal.exceptions'
# See https://github.com/kivy/python-for-android/issues/3364 — community
# workaround confirmed by multiple projects is pinning p4a to develop.
p4a.branch = develop

[buildozer]
log_level = 2
warn_on_root = 1
