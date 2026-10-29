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
android.minapi = 23
android.api = 35
android.ndk = 27c
android.accept_sdk_license = True
android.allow_backup = True

[buildozer]
log_level = 2
warn_on_root = 1
