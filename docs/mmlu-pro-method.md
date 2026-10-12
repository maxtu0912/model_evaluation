# MMLU-Pro 评测协议

本轮先评测 `deepseek-flash`。2026-10-12 查询账户模型目录，该名称对应 `DeepSeek-V4.1-Flash`，不把它标记成旧的 V4 Flash 快照。API 返回名称和请求日期逐题保存在本地记录中；别名可能变化，不代表不可变版本。

## 数据与提示

- 官方来源：[TIGER-Lab/MMLU-Pro](https://huggingface.co/datasets/TIGER-Lab/MMLU-Pro)。
- 固定数据版本：`b189ec765aa7ed75c8acfea42df31fdae71f97be`。
- test 为 12,032 题、14 个领域；validation 为 70 题，每个领域 5 个示例。
- 数据指纹：`0eb01609592342afa69dbc7ea376a79aa795f1937ac05e1069fb1abda8ec612d`。指纹涵盖版本、原始文件校验值及处理后的 test/validation 数据。
- 按官方脚本去除 `N/A` 填充选项，并核对标准答案的位置没有改变。
- 使用[官方 5-shot CoT 提示模板](https://github.com/TIGER-AI-Lab/MMLU-Pro/blob/main/evaluate_from_api.py)。每题只使用本领域 validation 的 5 个示例；测试题的答案和 `cot_content` 不进入请求。
- 请求仅有一条 user 消息，不增加要求只返回字母的系统指令。

## 模型配置与计分

`thinking=disabled`、`temperature=0`、`max_tokens=4000`、`top_p=1`、`frequency_penalty=0`、`presence_penalty=0`。非思考模式仍允许回答正文包含逐步推理；这与 API 内部思考模式是两个不同概念。

提示版本为 `mmlu-pro-official-5shot-cot-nonthinking-v1`。答案优先提取最后一个明确的 `The answer is (X)`，其次明确的 `Answer: X`，或纯选项回答；仅接受本题实际选项范围内的字母。不会从普通推理文字里捡取任意字母，也不随机补答案。该规则与官方脚本的宽松兜底不同，因此结果属于本项目独立运行，不能直接当作官方榜单分数。

正常返回但无法提取选项的回答按错误计分；输出截断单列统计，成功响应不会因答错、格式异常或截断而重新生成。API 请求失败不当作能力错误，支持退避重试及续跑。

截断响应若已包含符合上述规则的明确答案，仍按该答案评分；若未包含有效答案，则计错。报告分别列出截断数量和无法提取选项数量，两者不一定相等。

逐题正确率按所有成功响应计算；领域等权平均按各领域正确率的算术平均计算。最终发布前核对全部题目 ID、标准答案、评分和请求指纹。数学、物理等领域题量不同，两种平均值分别展示。

## 执行与续跑

准备需要已安装 `pyarrow` 的虚拟环境；运行与报告只使用 Python 标准库。

```sh
.venv/bin/python mmlu_pro.py prepare
python3 mmlu_pro.py run --per-category 10 --workers 16
python3 mmlu_pro.py report --markdown results/mmlu-pro-flash-pilot.md
python3 mmlu_pro.py run --workers 16
python3 mmlu_pro.py report --require-complete --markdown results/mmlu-pro-flash.md --aggregate aggregates/mmlu-pro-flash.json
python3 build_dashboard.py
```

试跑每领域 10 题，共 140 题；固定抽样种子为 20261012。试跑与全量收到相同题目时，请求指纹相同，因此复用成功记录。换模型、提示、数据或输出预算后会生成不同的请求指纹，不错误复用旧回答。用相同 run 命令续跑，只补请求失败或尚未完成的题目。

本地题库和逐题记录不提交。可公开产物为 Markdown 报告和 `aggregates/` 中的归一化汇总 JSON，看板使用已有的 normalized 接入方式。抽样结果必须使用题目 ID 指纹标记范围，不能冒充 full 结果。

## 比较范围

没有搜索、工具或额外训练。公开题集可能存在训练数据污染；英文题与中文 C-Eval 同时改变了语言、内容与协议，分数不能跨评测集直接比较。之后新增 Pro 时，应固定相同数据版本、示例、提示与生成参数，保留两个模型同题的逐题记录，以便做配对比较。
