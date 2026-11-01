# 第二阶段：日版提取与配置差异

记录日期：2026-10-28。所有游戏内容仅存于 Git 忽略的 `local-data/`；以下只记录技术事实，不记录密钥值。

## 工具与输入

- 从官方仓库取得 `hactool`（`SciresM/hactool`，检出 `1d64a83`）和 `nxnative`（`seedds/nxnative`，检出 `201dfd1`），源码存于 Git 忽略的 `upstream/`。
- 本机 Xcode 27.1 在 `/Applications/Xcode.app`；默认 `xcode-select` 指向 Command Line Tools，后续命令需设置 `DEVELOPER_DIR=/Applications/Xcode.app/Contents/Developer`。
- `prod.keys` 有 231 个十六进制条目，其中 33 个 `master_kek_source_*` / `mariko_master_kek_source_*` 条目为 17 字节；`hactool` 对这类条目预期 16 字节，直接加载会中止。将这 33 项暂时排除后，其余密钥足以读取和提取此 XCI。原文件未修改，临时副本已删除。**不要用未加 `--disablekeywarns` 的 `hactool` 直接处理此密钥文件：其旧版警告会显示未识别的密钥值。**

## 已验证

| 项目 | 结果 |
| --- | --- |
| 原版 XCI Secure 分区 | 5 个 NCA，总计 4,229,808,640 字节 |
| 内部 Title ID | `0100D7F00FB1A000`，与标红文件名一致 |
| 控制数据版本 | `1.0.0` |
| ExeFS | `main`、`subsdk0`、`sdk`、`rtld`、`main.npdm` 已提取 |
| RomFS | 5,152 个文件，总计 4,205,383,975 字节 |
| 汉化补丁路径 | 137 个文件中，106 个与原版路径重合，31 个为新增路径 |

## Build ID 对照

| 模块 | 日版 1.0.0 | 与 `nxnative` 国际版配置相同 |
| --- | --- | --- |
| `main` | `d871b992e95b71c541ddc834f63c664b` | 否 |
| `subsdk0` | `84e50460493a12f26100e5150fbff271` | 是 |
| `sdk` | `d9add76fc264863d85fbbd1d70076c76` | 是 |

日版需建立自己的游戏配置，不能把国际版 `main` 的地址或 Build ID 直接套入。共用的两个 SDK 模块及 `nativeNXx64/sa/NX_64/root.arc` 路径提供复用基础；着色器表仍需由日版资源验证。

## 后续进展

`nxnative` 的 survey、日版独立 profile、原版 Mac 启动和汉化覆盖层的首段剧情测试均已完成。详见[Mac 测试版记录](phase-3-mac-prototype.md)。31 个新增路径已纳入资源镜像；各章节是否用到它们仍待完整试玩。
