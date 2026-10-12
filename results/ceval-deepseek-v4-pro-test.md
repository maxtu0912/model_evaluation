# C-Eval 评测报告

仅对文件中实际运行的题目计算分数。公开题集可能存在训练数据污染；不同提示、抽题和模型配置的结果不可直接比较。

## deepseek-v4-pro · test

数据 SHA-256：`a17ff4dcf2c4a49ee744bd9ee0b0b8501fec889d269129b4e6ef7d86196270e0`；提示版本：`ceval-answer-only-zero-shot-nonthinking-v2`。
有效回答 12342/12342；请求失败 0；无法提取选项 5。
按题目计正确率：11126/12342（90.1%）。
按学科等权平均：90.1%（覆盖 52 个学科）。
平均请求耗时：1.04 秒。
输入 token：1524372；输出 token：12344。

| 类别 | 正确/有效 |
|---|---:|
| Humanities | 2126/2364 |
| Other | 3183/3493 |
| STEM | 3483/3965 |
| Social Science | 2334/2520 |

| 学科 | 正确/有效 | 请求失败 |
|---|---:|---:|
| 注册会计师 (`accountant`) | 416/443 | 0 |
| 高等数学 (`advanced_mathematics`) | 125/173 | 0 |
| 艺术学 (`art_studies`) | 279/298 | 0 |
| 基础医学 (`basic_medicine`) | 160/175 | 0 |
| 工商管理 (`business_administration`) | 267/301 | 0 |
| 中国语言文学 (`chinese_language_and_literature`) | 186/209 | 0 |
| 公务员 (`civil_servant`) | 406/429 | 0 |
| 临床医学 (`clinical_medicine`) | 182/200 | 0 |
| 大学化学 (`college_chemistry`) | 179/224 | 0 |
| 大学经济学 (`college_economics`) | 422/497 | 0 |
| 大学物理 (`college_physics`) | 166/176 | 0 |
| 大学编程 (`college_programming`) | 301/342 | 0 |
| 计算机组成 (`computer_architecture`) | 171/193 | 0 |
| 计算机网络 (`computer_network`) | 161/171 | 0 |
| 离散数学 (`discrete_mathematics`) | 116/153 | 0 |
| 教育学 (`education_science`) | 240/270 | 0 |
| 注册电气工程师 (`electrical_engineer`) | 262/339 | 0 |
| 环境影响评价工程师 (`environmental_impact_assessment_engineer`) | 247/281 | 0 |
| 注册消防工程师 (`fire_engineer`) | 260/282 | 0 |
| 高中生物 (`high_school_biology`) | 168/175 | 0 |
| 高中化学 (`high_school_chemistry`) | 164/172 | 0 |
| 高中语文 (`high_school_chinese`) | 145/178 | 0 |
| 高中地理 (`high_school_geography`) | 171/178 | 0 |
| 高中历史 (`high_school_history`) | 162/182 | 0 |
| 高中数学 (`high_school_mathematics`) | 127/166 | 0 |
| 高中物理 (`high_school_physics`) | 164/175 | 0 |
| 高中政治 (`high_school_politics`) | 162/176 | 0 |
| 思想道德修养与法律基础 (`ideological_and_moral_cultivation`) | 155/172 | 0 |
| 法学 (`law`) | 195/221 | 0 |
| 法律职业资格 (`legal_professional`) | 172/215 | 0 |
| 逻辑学 (`logic`) | 186/204 | 0 |
| 毛泽东思想和中国特色社会主义理论体系概论 (`mao_zedong_thought`) | 216/219 | 0 |
| 马克思主义基本原理 (`marxism`) | 171/179 | 0 |
| 注册计量师 (`metrology_engineer`) | 193/219 | 0 |
| 初中生物 (`middle_school_biology`) | 188/192 | 0 |
| 初中化学 (`middle_school_chemistry`) | 183/185 | 0 |
| 初中地理 (`middle_school_geography`) | 106/108 | 0 |
| 初中历史 (`middle_school_history`) | 200/207 | 0 |
| 初中数学 (`middle_school_mathematics`) | 164/177 | 0 |
| 初中物理 (`middle_school_physics`) | 177/178 | 0 |
| 初中政治 (`middle_school_politics`) | 188/193 | 0 |
| 近代史纲要 (`modern_chinese_history`) | 198/212 | 0 |
| 操作系统 (`operating_system`) | 148/179 | 0 |
| 医师资格 (`physician`) | 420/443 | 0 |
| 植物保护 (`plant_protection`) | 179/199 | 0 |
| 概率统计 (`probability_and_statistics`) | 125/166 | 0 |
| 导游资格 (`professional_tour_guide`) | 248/266 | 0 |
| 体育学 (`sports_science`) | 156/180 | 0 |
| 税务师 (`tax_accountant`) | 409/443 | 0 |
| 教师资格 (`teacher_qualification`) | 391/399 | 0 |
| 注册城乡规划师 (`urban_and_rural_planner`) | 348/418 | 0 |
| 兽医学 (`veterinary_medicine`) | 201/210 | 0 |

## 与仓库 Flash 历史结果对照

两次均使用 test 全量 12,342 题、52 学科，数据指纹和提示版本一致；均为零样本、关闭思考模式、温度 0、最大输出 32 token。Flash 数据来源为仓库的 `results/ceval-deepseek-test.md`，本次未重新请求 Flash。

| 指标 | Flash（历史结果） | V4 Pro（本次） | Pro − Flash |
|---|---:|---:|---:|
| 正确题数 | 10,861 | 11,126 | +265 |
| 逐题正确率 | 88.00% | 90.15% | +2.15 个百分点 |
| 学科等权平均 | 88.22% | 90.10% | +1.87 个百分点 |
| 最终请求失败 | 0 | 0 | 0 |
| 无法提取选项 | 0 | 5 | — |

### 四大类别正确率

| 类别 | Flash | V4 Pro | Pro − Flash |
|---|---:|---:|---:|
| Humanities | 88.71% | 89.93% | +1.23 个百分点 |
| Other | 87.60% | 91.13% | +3.52 个百分点 |
| STEM | 86.05% | 87.84% | +1.79 个百分点 |
| Social Science | 90.95% | 92.62% | +1.67 个百分点 |

### 运行与计分说明

- 本次响应的 `api_model` 均为 `deepseek-v4-pro`。Flash 历史报告只记录 API 名称 `deepseek-flash`，未提供可核实的不可变模型快照；对照结果应按两次实际运行理解。
- 运行中遇到 HTTP 429，已通过退避重试及续跑补齐；最终合并文件每题只保留一条成功响应。中间失败记录仍保存在本地分卷中。
- 本次平均请求耗时包含限流等待与重试，不适合直接与 Flash 历史耗时比较。
- 仅重试请求失败的题目。成功返回但不符合单选格式的回答按错误计分，不重新生成答案。

### 无法提取选项的原始回答

| 题目 ID | 回答 | 结束原因 |
|---|---|---|
| `ideological_and_moral_cultivation:74` | `"ACD"` | `stop` |
| `college_economics:255` | `"ABD"` | `stop` |
| `college_economics:59` | `"AC"` | `stop` |
| `college_economics:361` | `"BD"` | `stop` |
| `college_economics:131` | `"ABCD"` | `stop` |
