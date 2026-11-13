# -*- coding: utf-8 -*-
"""随机模型加载器

两个节点（都在「模型/随机」分类下）：
  · 随机 Checkpoint 加载器 —— 从 models/checkpoints 里选/随机，
    输出 MODEL / CLIP / VAE（跟 CheckpointLoaderSimple 一样，最安全）
  · 随机 UNet 加载器 —— 从 models/diffusion_models 里选/随机，
    只输出 MODEL，CLIP / VAE 要在外面自己接

两个节点都会把「本次随机到哪个」直接显示在节点上（见 web/random-model-loader.js），
不需要再接 Show Text。

「模型」下拉里同时列出【分组】和【单个文件】：
  📁 分组名          → 在这个分组里随机抽
  📁 （根目录）       → 只在根目录（不带子文件夹）的模型里随机
  （全部·随机）       → 所有模型里随便抽
  具体的 xxx.safetensors → 固定用这一个（不随机）

选了分组/全部就是每次排队重新抽，没有种子控件。

⚠️ 随机 UNet 要小心：CLIP / VAE 是外接的，混着不同架构的模型随机会在采样时炸。
   建议只在同一架构的分组里随机。
"""
import os
import random

import folder_paths
import comfy.sd
import comfy.utils
import torch


FOLDER_PREFIX = "📁 "
ALL_LABEL = "（全部·随机）"
ROOT_LABEL = "（根目录）"


# ---------------------------------------------------------------- 工具

def _files(key):
    try:
        return list(folder_paths.get_filename_list(key))
    except Exception:
        return []


def _dir_of(name):
    d = os.path.dirname(name.replace("\\", "/"))
    return d if d else ROOT_LABEL


def _options(key):
    """下拉选项 = 全部·随机 + 各分组 + 每个具体文件"""
    files = _files(key)
    folders = sorted({_dir_of(f) for f in files})
    opts = [ALL_LABEL] + [FOLDER_PREFIX + d for d in folders] + sorted(files)
    return opts or [ALL_LABEL]


def _resolve(key, sel):
    """把用户的选择解析成具体文件名。"""
    files = _files(key)
    if not files:
        raise RuntimeError("随机加载器：%s 目录下没有任何模型文件。" % key)

    name = (sel or "").strip()
    if name.startswith(FOLDER_PREFIX):
        name = name[len(FOLDER_PREFIX):].strip()

    # 1) 直接选了某个具体文件
    if name in files:
        return name

    # 2) 选了分组 / 全部
    if name in ("", ALL_LABEL, "（全部）"):
        pool = list(files)
    elif name == ROOT_LABEL:
        pool = [f for f in files if _dir_of(f) == ROOT_LABEL]
    else:
        target = name.replace("\\", "/")
        pool = [f for f in files if _dir_of(f).replace("\\", "/") == target]

    if not pool:
        raise RuntimeError(
            "随机加载器：%s 的「%s」下面没有模型文件。换个分组或先放模型进去。"
            % (key, sel)
        )

    return random.choice(sorted(pool))


def _dtype(name):
    return {
        "default": None,
        "fp8_e4m3fn": torch.float8_e4m3fn,
        "fp8_e4m3fn_fast": torch.float8_e4m3fn,
        "fp8_e5m2": torch.float8_e5m2,
    }.get(name)


def _is_concrete(key, sel):
    return (sel or "").replace(FOLDER_PREFIX, "").strip() in _files(key)


def _display(name):
    """节点上只显示文件名本身：去掉目录、去掉扩展名。"""
    base = os.path.basename((name or "").replace("\\", "/"))
    stem = os.path.splitext(base)[0]
    return stem or base


# ---------------------------------------------------------------- 节点

class 随机Checkpoint加载器:
    @classmethod
    def INPUT_TYPES(s):
        return {
            "required": {
                "模型": (_options("checkpoints"), {
                    "tooltip": "选📁分组=在该组随机抽；选具体文件名=固定用它"}),
            },
            "optional": {
                "排除关键词": ("STRING", {"default": "",
                                        "tooltip": "文件名里含这些字就跳过（多个用逗号分隔）"}),
            },
        }

    RETURN_TYPES = ("MODEL", "CLIP", "VAE")
    RETURN_NAMES = ("模型", "CLIP", "VAE")
    FUNCTION = "load"
    CATEGORY = "模型/随机"
    DESCRIPTION = "从 checkpoints 里选或随机取一个完整模型，同时出 MODEL / CLIP / VAE。"
    OUTPUT_NODE = False

    @classmethod
    def IS_CHANGED(s, 模型=ALL_LABEL, 排除关键词=""):
        # 选了具体文件 → 结果固定，不需要每次重跑；否则每次都重新随机
        if _is_concrete("checkpoints", 模型):
            return "%s|%s" % (模型, 排除关键词)
        return float("nan")

    def load(self, 模型, 排除关键词=""):
        name = _resolve("checkpoints", 模型)
        bad = [x.strip() for x in (排除关键词 or "").split(",") if x.strip()]
        if bad and any(b.lower() in name.lower() for b in bad):
            pool = [f for f in _files("checkpoints")
                    if not any(b.lower() in f.lower() for b in bad)]
            if pool:
                name = random.choice(sorted(pool))
        path = folder_paths.get_full_path_or_raise("checkpoints", name)
        print("[随机Checkpoint] 本次使用：%s" % name)
        out = comfy.sd.load_checkpoint_guess_config(
            path, output_vae=True, output_clip=True,
            embedding_directory=folder_paths.get_folder_paths("embeddings"))
        # ui.text 由 web/random-model-loader.js 显示在节点上
        return {"ui": {"text": [_display(name)]}, "result": (out[0], out[1], out[2])}


class 随机UNet加载器:
    @classmethod
    def INPUT_TYPES(s):
        return {
            "required": {
                "模型": (_options("diffusion_models"), {
                    "tooltip": "选📁分组=在该组随机抽；选具体文件名=固定用它"}),
                "权重精度": (["default", "fp8_e4m3fn", "fp8_e4m3fn_fast", "fp8_e5m2"],),
            },
        }

    RETURN_TYPES = ("MODEL",)
    RETURN_NAMES = ("模型",)
    FUNCTION = "load"
    CATEGORY = "模型/随机"
    DESCRIPTION = ("从 diffusion_models 里选或随机取一个 UNET。"
                   "⚠️ 只输出 MODEL，CLIP/VAE 要外接；不同架构混抽会炸。")

    @classmethod
    def IS_CHANGED(s, 模型=ALL_LABEL, 权重精度="default"):
        # 选了具体文件 → 结果固定，不需要每次重跑；否则每次都重新随机
        if _is_concrete("diffusion_models", 模型):
            return "%s|%s" % (模型, 权重精度)
        return float("nan")

    def load(self, 模型, 权重精度):
        name = _resolve("diffusion_models", 模型)
        opts = {}
        dt = _dtype(权重精度)
        if dt is not None:
            opts["dtype"] = dt
        if 权重精度 == "fp8_e4m3fn_fast":
            opts["fp8_optimizations"] = True
        path = folder_paths.get_full_path_or_raise("diffusion_models", name)
        print("[随机UNet] 本次使用：%s" % name)
        model = comfy.sd.load_diffusion_model(path, model_options=opts)
        # ui.text 由 web/random-model-loader.js 显示在节点上
        return {"ui": {"text": [_display(name)]}, "result": (model,)}


NODE_CLASS_MAPPINGS = {
    "RandomCheckpointLoader": 随机Checkpoint加载器,
    "RandomUNetLoader": 随机UNet加载器,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "RandomCheckpointLoader": "随机 Checkpoint 加载器",
    "RandomUNetLoader": "随机 UNet 加载器",
}

WEB_DIRECTORY = "./web"

__all__ = ["NODE_CLASS_MAPPINGS", "NODE_DISPLAY_NAME_MAPPINGS", "WEB_DIRECTORY"]
