#!/usr/bin/env python3
"""Translate this game's generated Mac launcher labels without changing setting values."""

import argparse
import json
from pathlib import Path


SECTIONS = {"Game": "游戏", "Controls": "操作", "Performance": "性能"}
LABELS = {
    "DM_OPMODE": "主机模式",
    "DM_PRESENT_UPSCALE": "画面放大",
    "DM_LANG": "游戏语言",
    "DM_FULLSCREEN": "显示模式",
    "DM_RUMBLE": "游戏震动",
    "DM_RUMBLE_GAIN": "震动强度",
    "DM_RUMBLE_MIN": "震动触发阈值",
    "DM_METAL_HUD": "性能监视器",
}
NOTES = {
    "DM_PRESENT_UPSCALE": "会增加 GPU 负载和设备发热。",
}
OPTIONS = {
    "DM_OPMODE": {"1": "电视模式", "0": "掌机模式"},
    "DM_PRESENT_UPSCALE": {"off": "标准", "metalfx": "MetalFX"},
    "DM_LANG": {"en-US": "美式英语", "en-GB": "英式英语", "ja": "日语"},
    "DM_FULLSCREEN": {"0": "窗口", "1": "全屏"},
}


def localize(source: Path, destination: Path) -> None:
    data = json.loads(source.read_text(encoding="utf-8"))
    settings = data["settings"]
    if data.get("game") != "0100D7F00FB1A000" or {s["env"] for s in settings} != set(LABELS):
        raise ValueError("Unexpected game or settings; review the translations before applying")
    for setting in settings:
        env = setting["env"]
        setting["section"] = SECTIONS.get(setting["section"], setting["section"])
        setting["label"] = LABELS[env]
        if env in NOTES:
            setting["note"] = NOTES[env]
        if env in OPTIONS:
            for option in setting["options"]:
                option[1] = OPTIONS[env][option[0]]
    destination.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path, help="generated launcher.json")
    parser.add_argument("destination", type=Path, help="localized launcher.json")
    args = parser.parse_args()
    localize(args.source, args.destination)
