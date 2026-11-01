# 原版与汉化版构建

**中文** · [English](build-variants.en.md) · [English README](../README.en.md)

两种构建共用日版 1.0.0（`0100D7F00FB1A000`）的程序、宿主和图形补丁，通过独立资源树与应用标识区分。这里的“原版”指不加载汉化的游戏资源，仍包含移植所需的程序修改。日版原始控制数据声明日语及英语支持，原版构建提供日语、英语语言选择；国际版游戏程序不在此构建流程的支持范围内。

## 两种输出

| 项目 | 原版 `original` | 汉化版 `chinese` |
| --- | --- | --- |
| 游戏资源 | 完整、未汉化的日版 RomFS | 同一干净 RomFS 加使用者提供的汉化覆盖层 |
| 游戏语言 | `ja`、`en-US`、`en-GB`，默认 `en-US` | 固定 `ja`，读取被汉化替换的日语资源 |
| 启动器／菜单语言 | 默认英文 `en` | 默认简体中文 `zh-Hans` |
| 应用标识 | `org.nxnative.tgaa.japan.original` | `org.nxnative.tgaa.japan.cn13` |
| 数据目录 ID | `0100D7F00FB1A000-original` | `0100D7F00FB1A000-cn13` |
| 汉化版本标签清理 | 不执行 | 仅匹配已知标签时执行 |
| 按键图标 | 从原版日英字体档案派生 | 从合并后的日英字体档案派生，保留汉化字体 |
| 离线攻略 | 默认不包含，可显式加入 | 默认不包含，可显式加入中文攻略 |

数据目录位于 `~/Library/Application Support/nxnative/<数据目录 ID>/`。两版拥有独立偏好、存档与临时覆盖层，不导入历史体验版的个人存档；新游戏存档仍使用各自目录中的 `save-fresh/`。`en-US` / `en-GB` 是系统语言代码，不代表游戏有两套不同的英文翻译。

启动器的语言与游戏内容语言独立：用 `--ui-language en` 或 `--ui-language zh-Hans` 选择界面语言，用 `--language` 选择游戏语言。原版默认英文游戏和英文界面；例如 `--language ja --ui-language en` 可用英文启动器玩日文。汉化版也可显式选择英文界面，但游戏语言必须为 `ja`。原版应用显示名随界面语言使用英文或中文；输出文件名可自定。

英文界面覆盖启动设置、存档、手柄、改键、按钮、环境锁定提示、宿主的“Launch Settings…”菜单与重启确认。界面语言在构建时确定，游戏语言仍可在原版启动设置中切换。离线攻略正文仍为中文，不会自动翻译；未附带攻略时隐藏菜单。

## 源码准备

先按根目录 README 检出固定的 nxnative 基线，应用 `nxnative-mac-customizations.patch` 并复制日版 profile。随后在仓库根目录按顺序应用第二、第三份补丁：

```sh
git -C upstream/nxnative apply --check ../../patches/nxnative-build-variants.patch
git -C upstream/nxnative apply ../../patches/nxnative-build-variants.patch
git -C upstream/nxnative apply --check ../../patches/nxnative-launcher-languages.patch
git -C upstream/nxnative apply ../../patches/nxnative-launcher-languages.patch
```

第二份补丁给 Mac 打包器增加 `--resource-variant` 和 `--data-id`，并限制汉化专用清理只在 `chinese` 模式执行。第三份补丁增加界面语言、菜单和重启提示的翻译；要更新游戏内菜单，必须重新编译宿主，不能只改 JSON 或复用旧宿主。已应用的补丁不应重复应用。之前只传入资源的旧打包命令现在默认按原版处理；要保留旧汉化版本标签清理行为，需显式传入 `--resource-variant chinese`。

## 输入准备

构建脚本需要 Python 3.11 及以上。需要先使用固定版本的 nxnative 及本项目 profile 生成匹配的宿主、改写模块、着色器、配置表与字体替代文件。这一脚本不替代原有提取和底层编译流程，也不下载游戏或密钥。

以下路径是示例布局，需替换成自己的实际输入：

| 输入 | 示例路径 | 要求 |
| --- | --- | --- |
| 干净原版 RomFS | `local-data/original-romfs/` | 直接包含 `nativeNXx64/`；完整提取且未合并汉化 |
| 汉化覆盖层 | `local-data/cn13/romfs/` | 直接包含 `nativeNXx64/`；不是已经合并的整个游戏 |
| 启动设置 | `local-data/build/launcher.json` | 对应本作生成的 JSON，包含 `DM_LANG` |
| Mac 宿主 | `local-data/build/dmhost` | 包含本项目宿主修改 |
| 改写模块 | `local-data/build/patched/` | 本作改写程序及 fixups 表 |
| 着色器 | `local-data/build/msl/` | 含编译后的 `.metallib` |
| 配置表 | `local-data/build/tables/` | 对应本作的 shader_map 等配置 |
| 字体替代文件 | `local-data/build/font/` | nxnative 构建生成的 `.ttf` |

`--base-romfs` 接受解包后的目录，不接受 `RomFS.img`。若手头只有镜像，请先使用匹配工具导出为目录。不得拿现有汉化 App 的资源作为原版输入：移除汉化标记或切换 `DM_LANG` 都不能恢复已被覆盖的原始资源。

脚本会检查资源布局、符号链接、大小写冲突，并拒绝已知汉化 1.3 字体作为干净基线。但该检查不能证明任意输入都未经修改，使用者仍需确认原版来源与版本。输入资源保持不变；每次构建使用新资源树，禁止复用上一次合并后的树。完整复制资源需要额外磁盘空间。

## 先检查，不写入文件

原版（示例以英语为默认语言）：

```sh
python3 scripts/build_variant.py \
  --variant original --language en-US --ui-language en \
  --base-romfs local-data/original-romfs \
  --settings local-data/build/launcher.json \
  --prepare-only local-data/variants/original --dry-run
```

汉化版：

```sh
python3 scripts/build_variant.py \
  --variant chinese \
  --base-romfs local-data/original-romfs \
  --overlay-romfs local-data/cn13/romfs \
  --settings local-data/build/launcher.json \
  --prepare-only local-data/variants/chinese --dry-run
```

去掉 `--dry-run` 即生成资源树、设置与构建清单，不编译 App。输出目录必须尚不存在。汉化版必须提供覆盖层并使用 `ja`；原版拒绝覆盖层。原版运行时可在启动设置中切换日语与英语。

## 打包两种 App

在仓库根目录执行，按上表调整路径：

```sh
python3 scripts/build_variant.py \
  --variant original --language en-US --ui-language en \
  --base-romfs local-data/original-romfs \
  --settings local-data/build/launcher.json \
  --host local-data/build/dmhost \
  --patched local-data/build/patched \
  --msl local-data/build/msl --tables local-data/build/tables \
  --font local-data/build/font \
  --output 'release/大逆转裁判 1&2 原版.app'
```

```sh
python3 scripts/build_variant.py \
  --variant chinese \
  --base-romfs local-data/original-romfs \
  --overlay-romfs local-data/cn13/romfs \
  --settings local-data/build/launcher.json \
  --host local-data/build/dmhost \
  --patched local-data/build/patched \
  --msl local-data/build/msl --tables local-data/build/tables \
  --font local-data/build/font \
  --guide guide/guide.json \
  --output 'release/大逆转裁判 1&2 汉化版.app'
```

完整打包命令也接受 `--dry-run`，检查参数与打包器支持情况，但不编译或签名。默认画质为 1080p / 30 帧 / SDR，分辨率与 60 帧选项共用。脚本会编译打包器的启动器、进行本地临时签名并执行 `codesign --verify --deep --strict`，成功后才生成最终 App；已有输出会被拒绝，不会覆盖已安装的 App。

每个 App 内的 `Contents/Resources/build-variant.json` 记录构建类型、游戏／界面语言默认值、应用／数据 ID 及汉化覆盖文件的 SHA-256，不含密钥或个人存档。资源树和 App 都仅供本地使用，被 Git 忽略；勿将生成物或其游戏资源当作 MIT 源码发布。

### 可选 EDR 实验

两种构建都可额外传入：

```sh
--edr-shader local-data/hdr-test/unclamp-msl/720e88a17ae787f6_b.metal
```

该输入必须是针对日版相同构建生成的实验着色器。没有提供时不复制着色器、不显示 EDR 选项。提供时默认仍为 SDR，EDR 为可选实验模式。旧的 `configure_fps_trial.py` / `configure_edr_trial.py` 会改写应用标识，不应再对这里的最终输出运行。

## 验证范围

不依赖游戏数据的资源隔离、语言约束、输入保护与打包编排测试：

```sh
python3 -m unittest discover -s scripts -p test_build_variants.py -v
python3 -m unittest discover -s scripts -p test_original_button_overlay.py -v
```

原生覆盖层测试需 macOS 和已打补丁的 nxnative 源码，使用合成文件验证原版空覆盖层与汉化消息处理。构建编排测试使用人工构造的资源与模拟打包器，不代表实际游戏可运行。历史游戏测试范围仍以根 README 和研发记录为准。新的原版英文模式还需在英文 macOS 环境人工检查界面布局、跳过设置窗口后的语言、Option 重开、宿主菜单和重启确认，并在真实 App 中验证标题、剧情、字体、输入、存读档及语言切换；两版的全章节与增强画质也仍需实际游玩验证。
