<a id="chinese"></a>

<p align="center">
  <b>中文</b> ｜ <a href="#english">English</a>
</p>

# ComfyUI 随机模型加载器

从文件夹里**随机挑一个模型**来加载，抽到哪个直接显示在节点上，不用再接 Show Text。

包含两个节点（分类：`模型/随机`）：

| 节点 | 读取目录 | 输出 |
|---|---|---|
| **随机 Checkpoint 加载器** | `models/checkpoints` | MODEL / CLIP / VAE |
| **随机 UNet 加载器** | `models/diffusion_models` | MODEL |

## 下拉里有什么

```
📁 分组名            → 在这个分组（含子文件夹）里随机抽
📁 （根目录）         → 只在根目录里的模型随机，不含子文件夹
（全部·随机）         → 所有模型里随便抽
具体的 xxx.safetensors → 固定用这一个，不随机
```

- 选分组 / 全部：**每次排队都会重新抽**，没有种子控件
- 选具体文件：跟普通加载器一样，固定加载

## 显示

节点上会直接显示本次抽到的文件名（不含文件夹、不含后缀），跑完自动更新。
前端的实现在 `web/random-model-loader.js`。

## 元数据

随机模式下（选 📁 分组 / 全部随机），节点执行时会把**真正抽到的文件**记下来，
`comfyui_image_metadata_extension` 读这张表写入 `Model:` / `Model hash:`，
所以上传 Civitai 时即使随机也能自动识别大模型。

## 安装

把 `random-model-loader` 文件夹放进 `ComfyUI/custom_nodes/`，重启 ComfyUI。

## 注意

⚠️ 随机 UNet 的 CLIP / VAE 是外接的，把不同架构的模型混在一个分组里随机会在采样时报错，
建议只让同一架构的模型进同一个分组。

## 历史

早年的版本里还有一个「Krea2专用随机LoRA加载器」，因为元数据/工作流兼容性问题已经移除。
现在随机 LoRA 建议直接在 `Load LoRA Tag` 的提示词里写 `<lora:名字:权重>`，
配合其它随机节点使用。

---

<a id="english"></a>

<p align="center">
  <a href="#chinese">中文</a> ｜ <b>English</b>
</p>

# ComfyUI Random Model Loader

Pick a **random model from a folder** and load it. The selected file name is shown right on the
node, so no extra Show Text node is needed.

Two nodes (category: `模型/随机` — Model/Random):

| Node | Reads from | Outputs |
|---|---|---|
| **Random Checkpoint Loader** | `models/checkpoints` | MODEL / CLIP / VAE |
| **Random UNet Loader** | `models/diffusion_models` | MODEL |

## Dropdown entries

```
📁 Folder name          → pick randomly from this folder (including subfolders)
📁 (Root)               → pick randomly from the top level only
（全部·随机）            → pick randomly from every model
xxx.safetensors         → always load this one (no randomness)
```

- Choosing a folder / all models: **a new model is drawn on every queue**, there is no seed widget.
- Choosing a specific file: behaves like the standard loader and always loads that file.

## Display

The node shows the picked file name (folder and extension stripped) and updates after each run.
The frontend part lives in `web/random-model-loader.js`.

## Metadata

In random mode (📁 folder / all models), the node records the file it actually picked while
executing. `comfyui_image_metadata_extension` reads that record and writes `Model:` / `Model hash:`,
so Civitai can still recognize the checkpoint when the model was chosen randomly.

## Install

Drop the `random-model-loader` folder into `ComfyUI/custom_nodes/` and restart ComfyUI.

## Notes

⚠️ The Random UNet Loader only outputs MODEL; CLIP and VAE are connected separately. Mixing
different architectures in one folder will break sampling — keep one architecture per folder.

## History

Older versions also shipped a "Krea2-only random LoRA loader". It has been removed because of
metadata/workflow compatibility issues. For random LoRAs, write `<lora:name:weight>` in the prompt
of a `Load LoRA Tag` node and combine it with any random node you already use.
