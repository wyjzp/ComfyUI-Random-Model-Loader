import { app } from "/scripts/app.js";

/*
 * 把「本次随机到的文件」直接显示在节点上，不需要再接 Show Text 之类的节点。
 *
 * 原理：后端返回 {"ui": {"text": [文件名]}, "result": (...)}，
 * 前端在节点执行完收到 executed 事件 → 调用节点的 onExecuted(message)，
 * 这里就把 message.text[0] 写进节点上的只读控件。
 */

/** 节点类型 → 显示框的名字 */
const LABELS = {
  RandomUNetLoader: "本次使用",
  RandomCheckpointLoader: "本次使用",
};

/** 「模型」下拉里这些值代表"随机"，不是具体文件 */
const COMBO_PLACEHOLDERS = ["（全部·随机）", "（全部）", "（根目录）"];

function labelOf(node) {
  const cls = node.comfyClass || node.type;
  return LABELS[cls];
}

function addPickedWidget(node, label) {
  if (node.__pickedWidget) return node.__pickedWidget;

  const w = node.addWidget("text", label, "", () => {}, { serialize: false });
  w.serialize = false;
  w.tooltip = "本次运行实际随机到的文件（自动更新，不用连节点）";
  node.__pickedWidget = w;

  // 加了一个控件，节点需要变高一点，否则会被裁掉
  try {
    const need = node.computeSize()[1];
    if (node.size[1] < need) node.setSize([node.size[0], need]);
  } catch (e) {
    /* 忽略：某些版本取尺寸会抛错，不影响功能 */
  }
  return w;
}

/** 只留文件名：去掉目录、去掉扩展名（后端已经处理过，这里兜一层，幂等） */
function prettyName(name) {
  const s = String(name ?? "").replace(/\\/g, "/");
  const base = s.split("/").pop() || s;
  const dot = base.lastIndexOf(".");
  return dot > 0 ? base.slice(0, dot) : base;
}

function setPicked(node, text) {
  const label = labelOf(node);
  if (!label) return;
  const w = addPickedWidget(node, label);
  const v = prettyName(text);
  if (w.value === v) return;
  w.value = v;
  node.setDirtyCanvas?.(true, true);
  app.graph?.setDirtyCanvas?.(true, true);
}

/** 「模型」下拉里选的是具体文件名时，先把名字填上（这种情况结果固定、可能被缓存不重跑） */
function syncFromCombo(node) {
  const combo = node.widgets?.find((w) => w.name === "模型");
  if (!combo || typeof combo.value !== "string") return;
  const v = combo.value;
  if (!v || v.startsWith("📁") || COMBO_PLACEHOLDERS.includes(v)) return;
  if (node.__pickedWidget?.value) return; // 已经有真实运行结果了就别覆盖
  setPicked(node, v);
}

function hookCombo(node) {
  const combo = node.widgets?.find((w) => w.name === "模型");
  if (!combo || combo.__pickedHooked) return;
  combo.__pickedHooked = true;
  const prev = combo.callback;
  combo.callback = function (...args) {
    const r = prev?.apply(this, args);
    syncFromCombo(node);
    return r;
  };
}

app.registerExtension({
  name: "RandomModelLoader.ShowPicked",

  async beforeRegisterNodeDef(nodeType, nodeData) {
    if (!LABELS[nodeData?.name]) return;

    const prevOnExecuted = nodeType.prototype.onExecuted;
    nodeType.prototype.onExecuted = function (message) {
      prevOnExecuted?.apply(this, arguments);
      const t = message?.text;
      if (Array.isArray(t) && t.length) setPicked(this, t[0]);
    };
  },

  /**
   * 加载完工作流之后修正：
   * 老工作流的 UNet / Checkpoint 节点存过「种子」，那个值会被按位置塞进显示框，清掉
   */
  async afterConfigureGraph() {
    for (const node of app.graph?._nodes ?? []) {
      const picked = node.__pickedWidget;
      if (!picked) continue;
      if (/^-?\d+(\.\d+)?$/.test(String(picked.value ?? "").trim())) {
        picked.value = "";
        node.setDirtyCanvas?.(true, true);
      }
    }
  },

  async nodeCreated(node) {
    const cls = node.comfyClass || node.type;
    const label = LABELS[cls];
    if (!label) return;
    addPickedWidget(node, label);
    hookCombo(node);
    syncFromCombo(node);
  },
});
