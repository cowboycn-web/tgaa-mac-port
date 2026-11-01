# The Great Ace Attorney Chronicles — Japanese-release Mac port tools

[中文](README.md) · **English** · [English build guide](docs/build-variants.en.md)

An unofficial Apple silicon Mac port experiment based on [nxnative](https://github.com/seedds/nxnative). This repository contains game profiles, source patches, build helpers, and development notes for two local builds:

- **Original:** unmodified Japanese-release game assets, with Japanese or English game text and voices. The launcher and menus default to English.
- **Chinese:** the same original assets plus a separately supplied Chinese fan-translation overlay. The launcher defaults to Simplified Chinese.

**No game files, fan-translation assets, keys, saves, ready-to-play apps, or installers are included.** Supply your own authorized inputs. A Chinese overlay alone is not a complete game.

## Supported game and project status

Both builds target the **Japanese Switch release, base version 1.0.0**, title ID `0100D7F00FB1A000`. Its original language data supports Japanese and English. An English-language build here still uses the Japanese-release executable. The international release (`010036E00FB20000`) has a different main program and is not supported by this build entry point.

This is a developer-oriented repository, not an end-to-end installer. Low-level extraction, executable rewriting, host compilation, and shader preparation still require the matching nxnative workflow. The new variant entry point packages those existing build inputs into separate apps.

| Area | Status |
| --- | --- |
| Platform | Apple silicon Mac; Intel Mac and other platforms have not been validated |
| Gameplay | Historical local builds reached the title screen and parts of Adventures, Episode 1, including courtroom scenes |
| English gameplay | Local smoke test reached English title/menus, opening movie subtitles, and the beginning of Adventures, Episode 1; a complete playthrough has not been validated |
| Chinese translation | A user-supplied CN1.3 overlay was tested locally; all chapters and translated names remain to be checked |
| Resolution | 720p, 1080p, 1440p, and native 4K; higher resolutions have limited scene coverage |
| Frame rate | 30 FPS by default; 60 FPS is experimental and still needs timing, input, and audio/video sync testing |
| Display | SDR by default; optional EDR is experimental and does not establish calibrated native HDR |
| Input | Remappable physical keyboard keys, mouse touch, and controller glyphs; physical hotplug still needs manual testing |
| Signing | Local ad-hoc signing; no Developer ID signing or notarization |

Defaults are **1080p / 30 FPS / SDR**. Short courtroom measurements do not establish full-game performance or compatibility. Automated build tests and native launcher compilation also do not replace gameplay or manual UI testing.

Local opening-flow evidence and limits are recorded in the [2026-11-01 English smoke test](docs/english-smoke-test-2026-11-01.md).

## Build locally

Read the [English build guide](docs/build-variants.en.md) for both variants, required inputs, language options, dry runs, and packaging commands. The corresponding [Chinese guide](docs/build-variants.md) is retained.

Requirements include an Apple silicon Mac, full Xcode with the required Metal toolchain, Git, **Python 3.11 or newer**, and the .NET/other dependencies required by the pinned nxnative revision. Historical local builds used Xcode 27.1; that is not a tested minimum requirement. Check the generated host's deployment target for macOS compatibility.

The recorded nxnative baseline is `201dfd1280684e9d3ceac8b644236fdac11b6cc2`. Apply all three repository patches, in this order, before building the host and launcher:

```sh
mkdir -p upstream local-data release
git clone https://github.com/seedds/nxnative.git upstream/nxnative
git -C upstream/nxnative checkout 201dfd1280684e9d3ceac8b644236fdac11b6cc2

git -C upstream/nxnative apply --check ../../patches/nxnative-mac-customizations.patch
git -C upstream/nxnative apply ../../patches/nxnative-mac-customizations.patch
git -C upstream/nxnative apply --check ../../patches/nxnative-build-variants.patch
git -C upstream/nxnative apply ../../patches/nxnative-build-variants.patch
git -C upstream/nxnative apply --check ../../patches/nxnative-launcher-languages.patch
git -C upstream/nxnative apply ../../patches/nxnative-launcher-languages.patch

mkdir -p upstream/nxnative/dm/games/0100D7F00FB1A000
cp profiles/0100D7F00FB1A000/game.tsv profiles/0100D7F00FB1A000/patches.py \
  upstream/nxnative/dm/games/0100D7F00FB1A000/
```

Apply each patch once to a clean checkout. Stop and inspect the revision or local changes if a check fails. Follow the development documentation in that pinned checkout for its build dependencies and pipeline. The local `scripts/run_nxnative.py` wrapper hardcodes toolchain paths and must be reviewed for your machine before use. It is not a complete variant-building pipeline. Do not run every script in `scripts/`: some are historical experiments or local archive maintenance tools.

## Launcher and game languages

The build helper accepts independent choices:

| Option | Original default | Chinese default |
| --- | --- | --- |
| `--language` (game assets) | `en-US` | `ja`, the resource slot replaced by the translation |
| `--ui-language` (launcher and menus) | `en` | `zh-Hans` |

For example, `--variant original --language ja --ui-language en` creates a Japanese-language game with an English launcher. Japanese and English remain selectable in the original build's settings. `en-US` and `en-GB` are system language codes; they do not promise different English translations.

English launcher support covers settings, save profiles, controller selection, keyboard bindings, buttons, environment-lock notes, and the in-game **Launch Settings…** menu and restart confirmation. Rebuild the host from the patched source as well as rebuilding the launcher; an older host still contains the older menu text.

The bundled walkthrough content is Chinese and contains spoilers. It is optional and is not translated by `--ui-language`. The Walkthrough menu appears only when a guide is included.

## Using a local build

Choose **Play** after configuring settings. Click the game window to give it keyboard focus. Hold **Option (⌥)** while opening the app to show a previously hidden settings window. During gameplay, **Launch Settings…** (⌘,) restarts the game and reopens settings; save your progress first.

**Restore standard graphics** restores 1080p, 30 FPS, SDR, and disables extra upscaling/performance overlays without resetting saves or key bindings. **New save (start over)** uses a separate `save-fresh/` folder; **Current save** uses `save/`. The two variants have separate preference domains and data directories. Existing trial-app saves are not imported.

| Switch action | Default keyboard key |
| --- | --- |
| Left stick | W / A / S / D |
| D-pad | Arrow keys |
| A (confirm) / B (back) | J / K |
| X / Y | U / I |
| L / R | Q / E |
| ZL / ZR | Z / C |
| Left / right stick press | F / G |
| + / − | Return / Tab |
| Shake controller | Hold Space |

Bindings use physical key positions. Reusing a key swaps the conflicting bindings. Mouse clicks and drags act as touch input in mouse/touch mode; TV mode does not provide mouse touch. Controller presets include Automatic, Switch, Xbox/Generic, PlayStation, and Keyboard. Automatic glyphs follow the active input source; device-specific behavior still needs hands-on testing.

## Repository layout and verification

- `profiles/`: version-specific profile and guarded executable patches.
- `patches/`: nxnative source patches and experimental graphics recipes.
- `scripts/build_variant.py`: isolated resource preparation and app packaging.
- `scripts/vendor/bc7enc16/`: bundled encoding dependency and its license.
- `guide/`: optional Chinese offline walkthrough and source notes.
- `docs/`: build guides and historical development records, primarily in Chinese.

`local-data/`, `upstream/`, and `release/` are ignored local directories. Referenced local logs, screenshots, shaders derived from game data, and saves are not part of the repository.

Run the resource isolation, language, and packaging orchestration tests without game data:

```sh
python3 -m unittest discover -s scripts -p test_build_variants.py -v
```

For bug reports, include your chip, macOS version, game version/build ID, source revision, language and graphics settings, reproduction steps, and a sanitized log excerpt. Do not attach keys, complete game assets, or personal saves. Historical evidence and outstanding checks are recorded in [extraction notes](docs/phase-2-extraction.md), [Mac prototype notes](docs/phase-3-mac-prototype.md), and [graphics experiments](docs/native-display-target.md); earlier entries may have been superseded.

## License and acknowledgments

Project-owned additions are licensed under the [MIT License](LICENSE). Retain applicable copyright and license notices. Third-party components retain their own licenses; see [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md), including nxnative's MIT notice and the [BC7 dependency license](scripts/vendor/bc7enc16/LICENSE). hactool was used locally for extraction and is not bundled. Walkthrough reference sources are listed in [guide/README.md](guide/README.md).

The MIT grant does **not** cover game executables, game text, images, fonts, audio, video, fan-translation resources, or decryption keys. Those remain with their respective rightsholders. Importing or processing them with these tools does not make the resulting resources or installers MIT-licensed.
