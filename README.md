# 大模型评测与对比

项目先用客观文本题验证模型调用、记录、评分和报告流程，再完成 C-Eval 与 MMLU-Pro 的学科评测。成绩分别衡量中文、英文选择题在各自协议下的表现，不代表模型的全方位能力。

完整的目标、维度、题库设计和实施阶段见[主流大模型全方位能力评测方案](评测方案.md)。

## 结果对比与可视化

- [Flash 与 V4 Pro 的优劣势总结](docs/ceval-flash-vs-pro.md)：总体、类别、学科差异及比较范围。
- [Eval Atlas 交互看板](dashboard/index.html)：模型选择、基准对比、类别图、学科 / 领域明细及运行配置。目前接入 C-Eval 的 Flash test、V4 Pro test、Flash val，以及 MMLU-Pro 的 Flash test 四次结果。
- [新增模型 / 评测集的数据接入说明](dashboard/README.md)：通过来源配置和统一汇总格式扩展，前端不固定模型数量或评测集。

在仓库根目录启动：

```sh
python3 build_dashboard.py
python3 -m http.server 8765 --bind 127.0.0.1 --directory dashboard
```

浏览器打开 `http://127.0.0.1:8765/`。静态服务仅提供看板目录。来源注册在 `dashboard/sources.json`，公开汇总目录为 `dashboard/data/catalog.json`；更换数据或加入新运行后重新生成并刷新页面。不同数据版本、分组、提示或生成参数会分开展示，不跨评测集计算一个总分。

## MMLU-Pro 英文学科评测

已于 2026-10-12 完成 `deepseek-flash` 的 test 全量评测：**12,032 题、14 个领域，答对 10,167 题，逐题正确率 84.50%，领域等权平均 84.04%**。账户模型目录显示服务名称为 **DeepSeek-V4.1-Flash**。

采用固定数据版本、5-shot CoT、非思考模式、温度 0 和 4,000 token 输出上限。全部题目最终取得成功响应；49 个无法提取最终选项的回答按错计分，58 个输出截断单列统计。中间失败请求已通过续跑补齐，成功回答未因答错、格式异常或截断而重新生成。

查看 [完整报告](results/mmlu-pro-flash.md)、[固定数据与评测协议](docs/mmlu-pro-method.md)。结果已通过归一化汇总接入看板，并标记为全量完成；不与 C-Eval 的零样本、短输出协议直接比较百分比分数。

重现评测和更新看板：

```sh
.venv/bin/python mmlu_pro.py prepare
python3 mmlu_pro.py run --workers 8
python3 mmlu_pro.py report --require-complete --markdown results/mmlu-pro-flash.md --aggregate aggregates/mmlu-pro-flash.json
python3 build_dashboard.py
```

原始题库与逐题回答留在本地，只跟踪归一化汇总和报告。重新运行同一命令会复用已保存的成功记录；新模型或新实验应使用独立结果文件。

## C-Eval 中文学科评测

已完成 `deepseek-flash` 在 `val` 验证集上的全量评测：52 学科、1,346 题，正确 1,182 题（逐题正确率 87.8%；学科等权平均 88.3%）。1,346 次请求全部成功，答案均可提取。详细报告见 `results/ceval-deepseek-v2.md`；含原始题目与答案的逐题记录 `results/ceval-deepseek-v2.jsonl` 只保存在本地。

使用 [C-Eval 官方数据](https://github.com/hkust-nlp/ceval) 的 `val` CSV，按官方零样本题目模板发题，另加一条系统指令要求仅输出 A/B/C/D，依据选项评分。DeepSeek 请求明确关闭思考模式、温度设为 0。项目已包含官方学科中文名称与类别映射。数据集受 [CC BY-NC-SA 4.0](https://creativecommons.org/licenses/by-nc-sa/4.0/) 约束；本项目只在本地使用题目，不将题目和标准答案提交到 Git。

题库压缩包已从 [OpenCompass 的 ModelScope 镜像](https://www.modelscope.cn/datasets/opencompass/ceval-exam)下载到项目 `data/ceval-exam.zip`。该文件的 SHA-256 是 `68786deeea68ff089c56563ee48fab8160da857b77b913437bb504d681fd8e20`。运行：

```sh
python3 ceval.py inspect --dataset data/ceval-exam.zip
python3 ceval.py run --dataset data/ceval-exam.zip --per-subject 0 --output results/ceval-deepseek-v2.jsonl
python3 ceval.py report results/ceval-deepseek-v2.jsonl --markdown results/ceval-deepseek-v2.md
```

上述命令选中验证集全部 1,346 题，已有结果会跳过。若只想抽样，设置 `--per-subject 5`，即可按固定随机种子从每个学科抽 5 题。旧镜像的 test CSV 没有答案列。逐题记录保存数据指纹、提示词、原始回答、抽取选项和用量；报告按学科和四大类别展示结果。

### C-Eval test 全量结果

官方 [Hugging Face 数据集](https://huggingface.co/datasets/ceval/ceval-exam) 已公开带答案的 `test` 文件。本项目固定数据版本为 `617524a00b307ff6f9933702f724131fe12ca7ce`，下载 52 个 Parquet 文件，并逐题比对旧镜像中的题干和选项后，转换为本地 CSV 压缩包 `data/ceval-test-labeled.zip`（SHA-256：`dfdc3ccdb31d98d9dc5d47dc1f661ad0b971a3a6c8de9a2d1a73fbdcda43e069`）。该包和逐题记录均不提交到 Git。

`deepseek-flash` 在 12,342 道 `test` 题中答对 10,861 题：逐题正确率 **88.0%**，52 学科等权平均 **88.2%**。全部请求成功，答案均可提取。详细报告见 `results/ceval-deepseek-test.md`。这是本项目独立运行的零样本结果；额外的系统消息要求只返回选项字母，不能直接当作官方榜单分数。

重现数据准备和评测（准备步骤需要 `pyarrow`，运行与报告仅用 Python 标准库）：

```sh
mkdir -p data
curl -fL 'https://www.modelscope.cn/datasets/opencompass/ceval-exam/resolve/master/ceval-exam.zip' -o data/ceval-exam.zip
python3 -m pip install pyarrow
python3 prepare_ceval_test.py
python3 ceval.py inspect --dataset data/ceval-test-labeled.zip --split test
python3 run_ceval_parallel.py --dataset data/ceval-test-labeled.zip --split test --workers 8 --output results/ceval-deepseek-test.jsonl
python3 ceval.py report results/ceval-deepseek-test.jsonl --markdown results/ceval-deepseek-test.md
```

`run_ceval_parallel.py` 为每个学科保留独立结果文件并支持续跑。完整验证集与测试集都是公开题目，成绩可能受训练数据污染影响；`dev` 的 260 题是开发示例，本次没有计入测试分数。

### DeepSeek V4 Pro 对照评测

已于 2026-10-12 完成 `deepseek-v4-pro` 的 test 全量评测：12,342 题中答对 **11,126 题（90.15%）**，学科等权平均 **90.10%**。相对仓库 Flash 历史结果（10,861 题正确，88.00%），多答对 **265 题**，逐题正确率提高 **2.15 个百分点**。最终请求失败 0；5 个无法提取为单一选项的回答按错误计分。详细报告及类别对照见 [Pro 评测报告](results/ceval-deepseek-v4-pro-test.md)。

使用官方 API 模型名 `deepseek-v4-pro`，沿用 Flash 的 test 全量数据、零样本提示、关闭思考模式、温度 0 和最大输出 32 token。Pro 使用独立分卷目录和结果文件，支持中断续跑：

```sh
python3 eval.py models
python3 run_ceval_parallel.py --dataset data/ceval-test-labeled.zip --split test --model deepseek-v4-pro --workers 8 --limit-per-subject 1 --parts-dir results/ceval-v4-pro-test-parts --output results/ceval-deepseek-v4-pro-smoke.jsonl
python3 ceval.py report results/ceval-deepseek-v4-pro-smoke.jsonl
python3 run_ceval_parallel.py --dataset data/ceval-test-labeled.zip --split test --model deepseek-v4-pro --workers 8 --parts-dir results/ceval-v4-pro-test-parts --output results/ceval-deepseek-v4-pro-test.jsonl
python3 ceval.py report results/ceval-deepseek-v4-pro-test.jsonl --markdown results/ceval-deepseek-v4-pro-test.md
```

先试跑每学科 1 题（共 52 题），确认 API 返回的模型、请求成功和选项提取正常后再运行全量；全量会复用这些试跑记录。API 返回的模型名称记录在逐题记录的 `api_model` 中，该名称未必是不可变版本；比较时也应核对数据指纹与提示版本。Flash 历史报告未提供可核实的模型快照。本次耗时含限流等待和重试，不直接与 Flash 历史耗时比较。

API 遇到 HTTP 429 时最多重试 5 次，逐步延长等待并参考 `Retry-After`（单次最多等待 60 秒）；持续失败仍保存错误记录，可用同一命令续跑。模型成功返回但未按格式回答的记录保留并按现有规则评分。

由于 C-Eval 题目已经公开，正式结论需结合较新题目和自建保留集，注意可能的训练数据污染。

## 准备

评测与报告使用 Python 3.10+，无需第三方依赖；准备官方 Parquet 测试数据需要 `pyarrow`。DeepSeek 的官方示例使用 `https://api.deepseek.com/chat/completions`，模型可用性以实际账号和官方模型列表为准。

在本机终端设置密钥：

```sh
export DEEPSEEK_API_KEY='你的密钥'
```

也可以在项目根目录创建本地 `.env` 文件，内容仅一行 `DEEPSEEK_API_KEY=你的密钥`。该文件已被 Git 忽略；不要把密钥发送到聊天中。

## 运行

```sh
python3 eval.py validate
python3 eval.py models
python3 eval.py run --model deepseek-flash --limit 6 --output results/pilot.jsonl
python3 eval.py report results/pilot.jsonl
```

小批量无误后运行全部题目：

```sh
python3 eval.py run --model deepseek-flash --repeat 2 --output results/deepseek-flash.jsonl
python3 eval.py report results/deepseek-flash.jsonl --markdown results/deepseek-flash.md
```

`run` 会在每次请求后追加一条 JSONL 记录；相同输出文件中已有的 `(模型, 题目, 重复序号)` 会跳过，便于中断续跑。若需全新实验，使用新的输出文件。`--thinking enabled --reasoning-effort high` 可测试推理模式，但应与非推理模式分开报告。

## 现阶段的测量范围

题库覆盖中文理解、指令遵循、逻辑与数学、给定材料事实核对、代码理解，以及信息抽取。大多数题要求短答案或 JSON，使用确定性规则评分。题库刻意包含公开的标准答案，因此**不是隐藏测试集**。它尚未覆盖开放式写作质量、真实代码修改、长文档、多模态、工具调用、安全性、时延与成本的系统比较。这些需要后续专项题库和人工复核。

报告分别展示每个维度的得分、请求错误与平均耗时；不会将网络错误当作能力失分。原始响应会保存在 `results/`，该目录默认被 Git 忽略。

## 数据格式

`cases/pilot.jsonl` 每行一题，字段为 `id`、`dimension`、`prompt`、`answer`、`grader`。当前评分器：`exact`（只忽略首尾空白）、`number`（数值完全相等）、`json`（JSON 结构与值相等）。评分前不对题目答案做语义推测。运行 `python3 -m unittest discover -s tests -v` 可检查评分与续跑流程。

## API 文档

- [DeepSeek 首次调用](https://api-docs.deepseek.com/)
- [DeepSeek 模型列表接口](https://api-docs.deepseek.com/api/list-models/)
