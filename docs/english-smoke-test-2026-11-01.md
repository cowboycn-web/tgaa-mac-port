# Original English local smoke test — 2026-11-01

[English README](../README.en.md) · [中文 README](../README.md)

独立原版英文测试版已在本机打包并进行短测；没有覆盖现有汉化版，也未上传 GitHub。下面记录的是开头流程验证，不代表全章节通关或完整兼容性验收。

## Build and isolation

- Apple silicon Mac, macOS 27.0.1; local Xcode toolchain.
- Japanese Switch base game 1.0.0, title ID `0100D7F00FB1A000`.
- English launcher/menu UI (`en`) and English game resources (`en-US`).
- 1920 × 1080, 30 FPS, SDR. EDR and higher frame rates were not tested in this run.
- Newly compiled host and launcher; no Chinese overlay or offline walkthrough.
- The complete original RomFS image was recovered from local iCloud placeholders. The packaged image was checked byte-for-byte by SHA-256 against that original.
- Program modules were copied read-only from the previously built Japanese executable modules, which contain the verified graphics trampoline. Translation is a resource overlay, not a change to those modules.
- Bundle ID `org.nxnative.tgaa.japan.original`; default data ID `0100D7F00FB1A000-original`. Acceptance runs used separate, initially empty QA save/temp directories. Personal saves were not imported.
- The installed Chinese app's launcher, host, and Info.plist hashes matched the before-test snapshot afterward.

Original RomFS SHA-256: `a29429a7b91a1d020db3541186dcc818b1826ddf2dc0f1903a1822b59b7d33fd`.

## Observed runtime behavior

The actual packaged app displayed an English launch window with save profile, controller, language, window mode, resolution, frame-rate, and graphics reset labels. Play and Quit worked. The title and primary buttons fit the tested 560-point-wide window; longer content uses the scrollable form. Expanded keyboard/advanced layout and physical rebinding remain manual follow-ups; accessibility disclosure actions were not treated as proof that those sections expanded.

The clean original package reached the English system-save and auto-save notices, accepted mouse touch, rendered the full English title/menu backgrounds, entered Adventures / New Game, played the opening movie with English subtitles, and displayed English dialogue at the beginning of Episode 1. Keyboard/controller-style glyphs appeared in the game UI. A late opening-scene sample before restarting recorded frame-time p50 33.33 ms and p95 33.61 ms, approximately the default 30 FPS target; this is scene-specific evidence.

The game's Launch Settings menu showed an English restart warning and returned to the English launch settings after confirmation. The walkthrough menu was absent because no guide was bundled.

During automated capture, the game normally paused when it lost focus. Some bounded captures used the existing focus-test hook with a deliberately unreachable readback frame. That hook is not baked into the app or its default settings, and it does not enable HDR.

## Issue found and fixed

The Switch/original button-overlay branch originally returned failure when there was no cleaned Chinese message file. An untranslated build legitimately has no such file. This caused a misleading error log even though the game continued running.

The branch now accepts a valid empty overlay after removing stale font/message overrides, checks that its output directory exists, and still reports real output failures. Logging mentions a hidden translation version tag only when a cleaned message exists. The fix is retained in `patches/nxnative-launcher-languages.patch`; the launcher and local package were rebuilt afterward.

Verification covered 10 variant/localization tests, three native synthetic-resource overlay regression tests, application of all three source patches to the pinned clean baseline, local signatures, and DMG container/mounted-program identity. The corrected release startup run was checked separately for the overlay diagnostic.

## Local artifacts and limits

- `release/The Great Ace Attorney Chronicles - English Test.app`
- `release/The Great Ace Attorney Chronicles - English Test.dmg`
- `release/The Great Ace Attorney Chronicles - English Test.dmg.sha256`

The corrected DMG is 3351582480 bytes; SHA-256 `740abf2c9304505eb3c9799bc2f26e1ba13417441db535c28aa8f021530542da`. It was mounted read-only, and its app signature, executables, and metadata were checked against the final app. It contains user-supplied game assets and is a local test artifact, not an MIT source release. App and DMG remain ignored by Git. The signature is ad-hoc; no Developer ID signing or notarization was performed.

Full gameplay save/load, English audio listening/synchronization, physical controller hotplug, Japanese switching, investigation/courtroom interactions beyond the opening, all chapters, and long-session stability remain unverified by this run. Raw logs, accessibility captures, and screenshots stay in the ignored `local-data/english-test/` directory; they are not published with source.
