# C-Eval 评测报告

仅对文件中实际运行的题目计算分数。公开题集可能存在训练数据污染；不同提示、抽题和模型配置的结果不可直接比较。

## deepseek-flash · test

数据 SHA-256：`a17ff4dcf2c4a49ee744bd9ee0b0b8501fec889d269129b4e6ef7d86196270e0`；提示版本：`ceval-answer-only-zero-shot-nonthinking-v2`。
有效回答 12342/12342；请求失败 0；无法提取选项 0。
按题目计正确率：10861/12342（88.0%）。
按学科等权平均：88.2%（覆盖 52 个学科）。
平均请求耗时：0.77 秒。
输入 token：1536714；输出 token：12342。

| 类别 | 正确/有效 |
|---|---:|
| Humanities | 2097/2364 |
| Other | 3060/3493 |
| STEM | 3412/3965 |
| Social Science | 2292/2520 |

| 学科 | 正确/有效 | 请求失败 |
|---|---:|---:|
| 注册会计师 (`accountant`) | 394/443 | 0 |
| 高等数学 (`advanced_mathematics`) | 117/173 | 0 |
| 艺术学 (`art_studies`) | 280/298 | 0 |
| 基础医学 (`basic_medicine`) | 160/175 | 0 |
| 工商管理 (`business_administration`) | 251/301 | 0 |
| 中国语言文学 (`chinese_language_and_literature`) | 182/209 | 0 |
| 公务员 (`civil_servant`) | 383/429 | 0 |
| 临床医学 (`clinical_medicine`) | 188/200 | 0 |
| 大学化学 (`college_chemistry`) | 175/224 | 0 |
| 大学经济学 (`college_economics`) | 412/497 | 0 |
| 大学物理 (`college_physics`) | 158/176 | 0 |
| 大学编程 (`college_programming`) | 291/342 | 0 |
| 计算机组成 (`computer_architecture`) | 174/193 | 0 |
| 计算机网络 (`computer_network`) | 154/171 | 0 |
| 离散数学 (`discrete_mathematics`) | 117/153 | 0 |
| 教育学 (`education_science`) | 235/270 | 0 |
| 注册电气工程师 (`electrical_engineer`) | 254/339 | 0 |
| 环境影响评价工程师 (`environmental_impact_assessment_engineer`) | 237/281 | 0 |
| 注册消防工程师 (`fire_engineer`) | 228/282 | 0 |
| 高中生物 (`high_school_biology`) | 167/175 | 0 |
| 高中化学 (`high_school_chemistry`) | 161/172 | 0 |
| 高中语文 (`high_school_chinese`) | 141/178 | 0 |
| 高中地理 (`high_school_geography`) | 169/178 | 0 |
| 高中历史 (`high_school_history`) | 164/182 | 0 |
| 高中数学 (`high_school_mathematics`) | 113/166 | 0 |
| 高中物理 (`high_school_physics`) | 160/175 | 0 |
| 高中政治 (`high_school_politics`) | 162/176 | 0 |
| 思想道德修养与法律基础 (`ideological_and_moral_cultivation`) | 157/172 | 0 |
| 法学 (`law`) | 185/221 | 0 |
| 法律职业资格 (`legal_professional`) | 166/215 | 0 |
| 逻辑学 (`logic`) | 177/204 | 0 |
| 毛泽东思想和中国特色社会主义理论体系概论 (`mao_zedong_thought`) | 211/219 | 0 |
| 马克思主义基本原理 (`marxism`) | 171/179 | 0 |
| 注册计量师 (`metrology_engineer`) | 197/219 | 0 |
| 初中生物 (`middle_school_biology`) | 188/192 | 0 |
| 初中化学 (`middle_school_chemistry`) | 182/185 | 0 |
| 初中地理 (`middle_school_geography`) | 106/108 | 0 |
| 初中历史 (`middle_school_history`) | 197/207 | 0 |
| 初中数学 (`middle_school_mathematics`) | 154/177 | 0 |
| 初中物理 (`middle_school_physics`) | 176/178 | 0 |
| 初中政治 (`middle_school_politics`) | 187/193 | 0 |
| 近代史纲要 (`modern_chinese_history`) | 195/212 | 0 |
| 操作系统 (`operating_system`) | 149/179 | 0 |
| 医师资格 (`physician`) | 407/443 | 0 |
| 植物保护 (`plant_protection`) | 180/199 | 0 |
| 概率统计 (`probability_and_statistics`) | 127/166 | 0 |
| 导游资格 (`professional_tour_guide`) | 253/266 | 0 |
| 体育学 (`sports_science`) | 150/180 | 0 |
| 税务师 (`tax_accountant`) | 385/443 | 0 |
| 教师资格 (`teacher_qualification`) | 388/399 | 0 |
| 注册城乡规划师 (`urban_and_rural_planner`) | 348/418 | 0 |
| 兽医学 (`veterinary_medicine`) | 198/210 | 0 |
