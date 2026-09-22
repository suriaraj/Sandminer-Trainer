# Sandminer Trainer

Android save editor for **Sand Miner: Idle Mining Game** (`com.hcph.sandexplore`).

Validated save layout: **Sand Miner 3.6.1**.

## What it edits

Only this file is opened for editing:

`/sdcard/Android/data/com.hcph.sandexplore/files/save.dat`

Validated fields:

- Money: Int32 little-endian at decimal offset **3030** (`0xBD6`)
- Gems: Int32 little-endian at decimal offset **3047** (`0xBE7`)

## Level safety

`level_save_1.dat` is intentionally not referenced by the save service. The trainer does not read, write, rename, copy, restore, or delete the level save.

Before each edit the current `save.dat` is copied to:

`/sdcard/Download/SandminerTrainerBackups/`

The Restore button restores only the trainer's most recent `save.dat` backup.

The app refuses to edit:

- an unsupported Sand Miner version;
- a missing or unexpectedly small/large save;
- a save whose validated structure bytes do not match the known 3.6.1 layout;
- negative/out-of-range values.

## Shizuku

This build uses the official Shizuku API. On a non-rooted phone:

1. Install Shizuku.
2. Start Shizuku using Wireless debugging (Android 11+) or ADB.
3. Open Sandminer Trainer.
4. Grant the Shizuku permission requested by the trainer.
5. Tap **Refresh**.
6. Enter Money / Gems and tap **Apply safely**.

Shizuku may need to be started again after the phone reboots.

## Build

GitHub Actions builds the debug APK on pushes to `main`.

Open **Actions → Build Android APK**, then download the `Sandminer-Trainer` artifact.

## Notes

This project is intended for local save editing of the user's own game data. It does not alter server-side data or purchase validation.
