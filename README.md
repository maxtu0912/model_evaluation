# 大模型评测：DeepSeek 试运行

这是全方位评测的第一步：用一组可客观判分的**文本题**验证模型调用、记录、评分和报告流程。当前题库规模很小，成绩只能用于检查评测流程，不能作为模型排名或全面能力结论。

完整的目标、维度、题库设计和实施阶段见[主流大模型全方位能力评测方案](评测方案.md)。

## C-Eval 中文学科评测

已完成 `deepseek-flash` 在 `val` 验证集上的全量评测：52 学科、1,346 题，正确 1,182 题（逐题正确率 87.8%；学科等权平均 88.3%）。1,346 次请求全部成功，答案均可提取。详细报告见 `results/ceval-deepseek-v2.md`；含原始题目与答案的逐题记录 `results/ceval-deepseek-v2.jsonl` 只保存在本地。这个成绩来自公开验证集，不代表 C-Eval `test` 官方榜单成绩。

使用 [C-Eval 官方数据](https://github.com/hkust-nlp/ceval) 的 `val` CSV，按官方零样本题目模板发题，另加一条系统指令要求仅输出 A/B/C/D，依据选项评分。DeepSeek 请求明确关闭思考模式、温度设为 0。项目已包含官方学科中文名称与类别映射。数据集受 [CC BY-NC-SA 4.0](https://creativecommons.org/licenses/by-nc-sa/4.0/) 约束；本项目只在本地使用题目，不将题目和标准答案提交到 Git。

题库压缩包已从 [OpenCompass 的 ModelScope 镜像](https://www.modelscope.cn/datasets/opencompass/ceval-exam)下载到项目 `data/ceval-exam.zip`。该文件的 SHA-256 是 `68786deeea68ff089c56563ee48fab8160da857b77b913437bb504d681fd8e20`。运行：

```sh
python3 ceval.py inspect --dataset data/ceval-exam.zip
python3 ceval.py run --dataset data/ceval-exam.zip --per-subject 0 --output results/ceval-deepseek-v2.jsonl
python3 ceval.py report results/ceval-deepseek-v2.jsonl --markdown results/ceval-deepseek-v2.md
```

上述命令选中验证集全部 1,346 题，已有结果会跳过。若只想抽样，设置 `--per-subject 5`，即可按固定随机种子从每个学科抽 5 题。当前镜像的 test CSV 没有答案列，因此本地计分只使用 val 分组。逐题记录保存数据指纹、提示词、原始回答、抽取选项和用量；报告按学科和四大类别展示结果。该自运行零样本配置应作为本项目结果，不能直接与使用其他提示、参数或抽题方式的官方榜单分数混为一谈。

由于 C-Eval 题目已经公开，正式结论需结合较新题目和自建保留集，注意可能的训练数据污染。

## 准备

使用 Python 3.10+，无需第三方依赖。DeepSeek 的官方示例使用 `https://api.deepseek.com/chat/completions`，模型可用性以实际账号和官方模型列表为准。

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
