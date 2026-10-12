# Eval Atlas · 模型评测观测台

纯 HTML/CSS/JavaScript 的静态看板，无前端构建、第三方 CDN 或运行时 API 密钥。当前包含两个模型、两个评测集和四次运行：C-Eval 的 Flash test、V4 Pro test、Flash val，以及 MMLU-Pro Flash test 全量结果。

## 预览与更新

在仓库根目录执行：

```sh
python3 build_dashboard.py
python3 -m http.server 8765 --bind 127.0.0.1 --directory dashboard
```

打开 <http://127.0.0.1:8765/>。服务只提供 `dashboard/`，不会提供仓库根目录的 `.env`、本地题库或逐题记录。按 Ctrl+C 停止。

`build_dashboard.py` 从 `sources.json` 读取来源并生成 `data/catalog.json`。新增或更新结果后再次运行，再刷新浏览器。提交源码、来源配置、汇总报告和生成的目录即可重现页面。

`dashboard/` 可直接作为静态网站根目录托管。页面通过相对地址读取 JSON，兼容部署在站点子路径。双击 `index.html` 可能被浏览器的本地文件访问策略限制，应使用 HTTP 服务打开。

## 可用功能

- 按评测集、split、可比较配置和指标筛选。
- 任意数量的模型与运行勾选；同一模型多次运行单独展示，默认选取最新有日期的运行。
- 整体得分、类别条形图、相对基准的维度胜负和主要差距。
- 明细搜索、类别筛选、差值或得分排序；缺失指标显示 `—`，不当作 0 分。
- 运行参数、数据指纹、来源路径、失败与格式异常统计、模型版本说明。
- 导出当前评测集和所选运行的汇总 JSON（不包含搜索过滤，不导出逐题记录）。

## 数据组织与比较边界

```text
评测集 benchmarks
  ├─ 指标定义：名称、单位、范围、比较方向
  └─ 运行 runs
       ├─ 模型 model_id / 运行 ID / 日期
       ├─ split / 数据指纹 / 评测协议
       ├─ 总体 metrics / counts
       ├─ categories：类别汇总
       └─ dimensions：学科或其他维度
```

模型 ID 表示调用名称；每次运行有独立 ID 和日期。历史结果日期未知时用 `null`，不伪造测量日期。`notes` 中记录不可变模型快照、数据污染、运行异常等说明。

比较组由 `benchmark_id`、`split`、`dataset_fingerprint` 和完整 `protocol` 共同生成。以下任一字段变化都会分组，不能混成一个排名：提示版本、few-shot 数、思考模式、温度、输出上限、题目选择标识。模型不同不是分组依据。

运行还可声明 `status: "incomplete"` 和 `counts.expected_total`，用于展示已尝试样本和成功响应 / 计划总数。阶段结果会醒目标记，并与 `completed` 的完整运行分组，不能冒充全量成绩；未声明状态的历史完整来源默认为 `completed`。

`dataset_fingerprint` 应覆盖题目、选项、标准答案及维度映射的版本；`protocol.selection` 对全量使用 `full`，对抽样必须使用选中题目 ID、顺序和抽样配置的指纹。不同分组内的得分不合并，也不计算跨评测集的总分。

如果评测还受其他协议参数影响（例如 reasoning effort、工具集或执行环境），应把这些参数纳入 `prompt_version` 的协议版本标识，或扩展导出器的协议字段与分组签名后再接入。不能使用相同版本标识代表不同评测协议。

## 新增 C-Eval 模型或运行

1. 用现有评测命令生成独立 JSONL 和 Markdown 汇总报告。
2. 在 `sources.json` 的 `sources` 中新增条目，使用唯一运行 ID、真实模型信息和独立来源路径。
3. 运行 `python3 build_dashboard.py`。模型卡片、类别图、明细列和基准选项自动增加，无需改页面代码。

例如：

```json
{
  "id": "ceval-test-new-model-20261020",
  "format": "ceval-report",
  "path": "results/ceval-new-model-test.md",
  "benchmark_id": "ceval",
  "model": {"id": "实际模型名称", "name": "显示名称", "provider": "提供方"},
  "date": "2026-10-20",
  "protocol": {"shots": 0, "thinking": "disabled", "temperature": 0, "max_tokens": 32, "selection": "full"},
  "notes": ["记录实际模型快照及运行限制"]
}
```

示例不代表已完成评测。报告解析器只读取主结果块，并从正确数/有效数重算精确得分，不使用报告中已经四舍五入的百分比；总分、学科与类别计数必须一致。

## 新增评测集或自定义指标

其他评测集通过 `normalized` JSON 接入，不必修改前端，也不必模拟 C-Eval 的 Markdown 格式。

首先在 `sources.json` 的 `benchmarks` 中注册评测集和指标。例如：

```json
{
  "id": "custom-benchmark",
  "name": "自建保留集",
  "description": "真实任务 · 保留题目",
  "metrics": [
    {"id": "score", "name": "得分", "unit": "分", "range": [0, 10], "higher_is_better": true},
    {"id": "duration_ms", "name": "耗时", "unit": "ms", "higher_is_better": false}
  ]
}
```

只有测量条件一致的指标才应注册为可比较指标。当前 C-Eval 的运行耗时因为包含重试而只保存在 `operational`，不放入评分选择器。指标范围可选；缺少范围时，图表根据当前数据自动定范围。每个指标声明 `higher_is_better`，支持越低越好的指标。

然后准备汇总结果 JSON（下方是格式示例，不是实测数据）：

```json
{
  "split": "heldout",
  "dataset_fingerprint": "数据内容与标准答案的版本指纹",
  "protocol": {
    "prompt_version": "custom-protocol-v1",
    "shots": 0,
    "thinking": "disabled",
    "temperature": 0,
    "max_tokens": 1024,
    "selection": "full"
  },
  "counts": {"total": 100},
  "metrics": {"score": 7.5, "duration_ms": 200},
  "categories": [
    {"id": "reasoning", "name": "推理", "metrics": {"score": 7.5, "duration_ms": 200}}
  ],
  "dimensions": [
    {"id": "logic", "name": "逻辑", "category_id": "reasoning", "metrics": {"score": 7.5, "duration_ms": null}}
  ]
}
```

最后在 `sources` 注册：

```json
{
  "id": "custom-model-a-run-1",
  "format": "normalized",
  "path": "aggregates/custom-model-a.json",
  "benchmark_id": "custom-benchmark",
  "model": {"id": "model-a", "name": "Model A", "provider": "提供方"},
  "date": "2026-10-20",
  "notes": ["真实运行说明"]
}
```

源文件可以存放于仓库内的任意目录；默认被忽略的 `results/` 内文件需要显式允许跟踪。各运行以稳定的类别 / 维度 ID 对齐；指标缺失使用 `null` 或省略，不填 0。类别、维度数组允许为空；没有明细时展示空状态。

导出器只允许汇总字段，排除原始题目、标准答案、提示正文、回答和密钥等任意附加字段。不要在名称、notes、协议标识等公开元数据中填写敏感信息。

## 检查

```sh
python3 -m unittest discover -s tests -v
node --test tests/dashboard_metrics.test.mjs
node --check dashboard/app.mjs
```

Python 测试核对实测结果、汇总一致性、数据重建、不同配置隔离、自定义评测集和导出边界。JavaScript 测试覆盖实测差值、三模型排名、低值更优指标和缺失值处理。
