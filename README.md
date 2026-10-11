# 大模型评测：DeepSeek 与 C-Eval

项目先用一组可客观判分的文本题验证模型调用、记录、评分和报告流程，然后完成 C-Eval 验证集与测试集的全量评测。这些成绩衡量中文单项选择题表现，不代表模型的全方位能力。

完整的目标、维度、题库设计和实施阶段见[主流大模型全方位能力评测方案](评测方案.md)。

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
