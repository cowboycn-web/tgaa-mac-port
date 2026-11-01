# 大逆转裁判 1&2 日版 Mac 移植工具

**中文** · [English](README.en.md) · [English build guide](docs/build-variants.en.md)

基于 [nxnative](https://github.com/seedds/nxnative) 的 Apple 芯片 Mac 移植实验，支持整理为原版（日语／英语）与汉化版两种独立构建，包含日版游戏配置、Mac 宿主与启动器源码补丁、辅助脚本及测试记录。

本仓库提供工具与文档。运行游戏需要使用者自行准备有权使用的游戏数据、所需密钥，以及可选的汉化 1.3 RomFS 覆盖层；这些内容与 App、DMG、个人存档均不随仓库提供。单独的汉化覆盖层不能替代完整游戏本体。本项目为非官方实验项目。

## 两种构建

- **原版 `original`**：使用干净日版资源，提供日语／英语选择，默认英文游戏和英文启动器，不加载汉化覆盖层。
- **汉化版 `chinese`**：在同一干净原版资源上叠加使用者提供的汉化，固定读取日语资源槽位。

两版共用宿主与图形功能，使用独立应用标识、偏好和存档目录。构建入口为 `scripts/build_variant.py`，参数、资源准备和打包命令见 [两种构建指南](docs/build-variants.md)。新入口已覆盖资源隔离和构建编排测试；原版英文模式仍需真实游戏验证。

## 支持范围与当前状态

目标为 Switch **日版本体 1.0.0**，Title ID 为 `0100D7F00FB1A000`。国际版 `010036E00FB20000` 使用不同的主程序，不能直接套用本项目的地址补丁。

| 项目 | 当前情况 |
| --- | --- |
| 运行平台 | Apple 芯片 Mac；Intel Mac 与其他平台未验证 |
| 基础运行 | 本地构建已验证启动、标题、第一部第一话部分剧情与法庭 |
| 汉化 | 已接入使用者提供的汉化 1.3 覆盖层，完整章节与译名适配待验证 |
| 分辨率 | 720p、1080p、1440p、原生 4K；高分辨率仅完成部分场景测试 |
| 帧率 | 默认 30 帧；60 帧为实验选项，剧情速度、音画同步与全章节稳定性待验证 |
| 显示 | 默认 SDR；EDR 为实验输出，不代表已完成原生 HDR 或色彩校准 |
| 输入 | 可改键、鼠标触控、手柄样式与实时图标切换；物理拔插等仍需人工测试 |
| 离线攻略 | 两部作品十话的分段提示；全部流程尚未实机通关核对 |
| 签名 | 本地构建采用临时签名，未完成开发者签名或公证 |

默认画质为 **1080p / 30 帧 / SDR**。4K、60 帧和 EDR 的组合已在第一话法庭短测，不能据此承诺全程性能或通关兼容性。

原版英文已完成启动、标题菜单、开场英文字幕与第一话开头对话的本机短测，详见 [2026-11-01 测试记录](docs/english-smoke-test-2026-11-01.md)；不代表完整通关验证。

## 仓库结构

| 路径 | 内容 |
| --- | --- |
| `profiles/0100D7F00FB1A000/` | 日版 1.0.0 配置与按 Build ID、原始字节检查的补丁 |
| `patches/nxnative-mac-customizations.patch` | 对 nxnative 的宿主、启动器和打包工具等源码改动 |
| `patches/nxnative-build-variants.patch` | 两种资源模式与独立数据目录的打包器补丁 |
| `patches/nxnative-launcher-languages.patch` | 启动器与宿主菜单的中英文支持 |
| `patches/tgaa-env.txt` | 默认高清触控环境配置 |
| `patches/*.json` | 分辨率与帧率实验配方 |
| `scripts/` | 本地构建、配置、诊断、打包与历史归档辅助脚本 |
| `scripts/vendor/bc7enc16/` | BC7 编码依赖源码及其许可证 |
| `guide/` | 离线攻略 JSON 与来源说明，含剧透 |
| `docs/` | 分阶段技术记录与测试范围 |

`local-data/`、`upstream/`、`release/` 为被 Git 忽略的本地工作目录，不会随克隆产生。文档中引用的本地日志、截图和测试存档也不在仓库内。

## 开发环境与复现边界

这是研发资料仓库，尚未整理成从空白环境一键构建的发行工具。以下是已知准备流程；提取、资源合并、着色器构建与打包仍需结合固定版本的 nxnative 文档操作。

准备 Apple 芯片 Mac、完整 Xcode 与 Metal 工具链、Git、Python 3.11 及以上，以及 nxnative 对应版本要求的 .NET 和其他依赖。本地记录使用 Xcode 27.1；这不是经过兼容性测试得出的最低版本要求。

已记录的源码基线：

- nxnative：`201dfd1280684e9d3ceac8b644236fdac11b6cc2`。
- hactool：本地提取记录为 `1d64a83`，用于已有游戏数据的提取。

### 1. 准备 nxnative 源码与项目配置

在本仓库根目录运行：

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

在干净检出上应用一次补丁；如果检查失败，先核对基线及工作区改动。不要直接跳过版本与字节检查。

### 2. 准备本地输入与工具链

将游戏数据与提取输出放在 `local-data/`，密钥放在本机私有位置。核对日版 1.0.0 的模块 Build ID，见 [提取与配置差异](docs/phase-2-extraction.md)。汉化资源应合并到原版资源的独立副本，保留原始输入。

`scripts/run_nxnative.py` 是本机工具链包装脚本，执行前需按本机安装位置检查其中的 `DEVELOPER_DIR`、`TOOLCHAINS`、`DOTNET_ROOT` 和 Python 环境路径。脚本会过滤特定格式异常的密钥来源条目，使用权限为 `0600` 的临时副本，并在正常退出或异常清理时删除副本；原始密钥文件保持不变。

查看其参数：

```sh
python3 scripts/run_nxnative.py --help
```

此脚本不是完整的汉化版构建流水线；历史实验和归档脚本还可能依赖未随仓库提供的 App、测试存档、目录清单或 NAS 环境。运行前应阅读脚本，不要批量执行 `scripts/` 下的全部文件。

### 3. 构建、配置与打包

新的两种构建优先使用 [build_variant.py 流程](docs/build-variants.md)，在打包阶段分离资源与存档。下列配置脚本属于历史体验版流程，不要再对新入口生成的最终 App 运行，避免改写应用与数据目录标识。

按固定版本的 nxnative 开发文档完成程序改写、资源镜像、着色器和 Mac 宿主构建，再使用其中的 `dm/mac/pack_app.py` 打包。宿主和启动器必须包含本项目的源码补丁。

- 日版高清补丁在 `patch_nso.py` 阶段应用。
- 打包器传入本仓库 `patches/tgaa-env.txt` 的路径，用于高清触控坐标映射。
- 如需离线攻略，传入 `--guide` 并指定本仓库的 `guide/guide.json`。
- `scripts/configure_resolutions.py` 用于同步分辨率设置；修改 App 后需要重新签名。
- `scripts/configure_fps_trial.py` 用于独立帧率体验配置。
- `scripts/configure_edr_trial.py` 额外依赖本地生成的 `local-data/hdr-test/unclamp-msl/720e88a17ae787f6_b.metal`，此着色器不随仓库提供，不能在刚克隆的环境中直接运行。相关实验见 [画质验证记录](docs/native-display-target.md)。

不要在环境配置中固定 `DM_TGAA_RESOLUTION`，否则可能覆盖跳过启动窗口时保存的用户选择。详细打包过程与历史结果见 [Mac 测试版记录](docs/phase-3-mac-prototype.md)。

## 本地构建后的使用

原版默认英文界面（`--ui-language en`）及英文游戏（`--language en-US`）；汉化版默认中文界面，游戏资源槽位固定 `ja`。界面语言与游戏语言可独立指定，例如 `--variant original --language ja --ui-language en`。英文设置、改键、存档选择、控制器选项及宿主菜单需要重新编译打过全部三份补丁的宿主和启动器，旧 App 不会自动更新。中文离线攻略不会随界面语言翻译，未附带攻略时隐藏其菜单。

启动设置提供分辨率、帧率、显示模式、按键与存档选择。若已跳过设置窗口，按住 Option（⌥）打开 App 可再次显示；游戏菜单中的“启动设置…”也可重新配置，重启前请保存进度。“恢复标准画质”恢复 1080p、30 帧、SDR，并保留存档和按键设置。

“新存档（从头开始）”使用独立的 `save-fresh/`，现有进度位于 `save/`。不要让多个 App 同时写入同一存档。独立实验配置使用不同的数据目录；仓库不附带历史测试存档。

### 默认键盘操作

点击游戏画面使其获得焦点。按键按物理位置识别，可在启动设置中修改；重复分配按键时会交换映射。

| Switch 操作 | Mac 键盘 |
| --- | --- |
| 左摇杆 | `W` `A` `S` `D` |
| 十字键 | 方向键 |
| A 确认 / B 返回 | `J` / `K` |
| X / Y | `U` / `I` |
| L / R | `Q` / `E` |
| ZL / ZR | `Z` / `C` |
| 按下左摇杆 / 右摇杆 | `F` / `G` |
| + / − | `Return` / `Tab` |
| 摇动手柄 | 按住 `Space` |

鼠标左键按下、拖动和松开对应触屏操作，需使用支持触控的掌机输入模式；电视模式不提供鼠标触控。手柄样式支持自动、Switch、Xbox／通用、PlayStation 和键盘。自动样式跟随实际输入切换图标，手动指定则保持固定；特定设备仍需人工验证。

应用菜单“攻略…”（⌘G）打开本地分段提示。攻略包含剧透，来源及验证范围见 [攻略说明](guide/README.md)。

## 测试记录与问题反馈

- [输入清点（早期记录）](docs/phase-1-inventory.md)
- [提取与配置差异](docs/phase-2-extraction.md)
- [Mac 测试版与输入修复](docs/phase-3-mac-prototype.md)
- [分辨率、60 帧与 EDR 实验](docs/native-display-target.md)

这些是按日期保留的研发记录，早期描述可能已被后续进展替代。性能采样只代表对应场景；全章节、长时间运行、音画同步、外接屏切换和手柄物理拔插仍需验证。

反馈问题时请提供芯片型号、macOS 版本、游戏版本与 Build ID、所用代码基线、画质设置、复现步骤和去除私密信息后的日志片段。不要附带密钥、完整游戏资源或个人存档。

## 许可证与第三方来源

- [nxnative](https://github.com/seedds/nxnative)：本项目基于其运行与构建工具，固定基线的许可证为 MIT；分发相关源码或补丁时应保留其版权与许可文本，见 [nxnative 许可证](THIRD_PARTY_NOTICES.md)。
- [hactool](https://github.com/SciresM/hactool)：本地提取工具，不随本仓库提供。
- BC7 编码依赖：原许可文本保留于 [scripts/vendor/bc7enc16/LICENSE](scripts/vendor/bc7enc16/LICENSE)。
- 离线攻略参考来源见 [guide/README.md](guide/README.md)。

本项目自身新增且有权授权的代码、脚本、配置与文档采用 [MIT 许可证](LICENSE)。使用、修改或再分发时，请保留对应版权与许可声明。第三方代码及素材仍适用各自的许可证，相关声明见 [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md)。

**本仓库不包含游戏本体和汉化资源。** 游戏程序、文本、图片、字体、音频、视频、汉化资源与解密密钥均不在本项目 MIT 许可的授权范围内，其权利归各自权利人；本许可证不授予这些内容的使用或分发权。使用者需自行准备有权使用的输入数据，本地生成或导入的资源与安装包也不因使用本工具而自动获得 MIT 授权。
