# C-Eval 评测报告

仅对文件中实际运行的题目计算分数。公开题集可能存在训练数据污染；不同提示、抽题和模型配置的结果不可直接比较。

## deepseek-flash · val

数据 SHA-256：`c34f1722fe977bd77907106fdddcf95386c032f96aa763fd8574779aa3a3702d`；提示版本：`ceval-answer-only-zero-shot-nonthinking-v2`。
有效回答 1346/1346；请求失败 0；无法提取选项 0。
按题目计正确率：1182/1346（87.8%）。
按学科等权平均：88.3%（覆盖 52 个学科）。
平均请求耗时：0.55 秒。
输入 token：167560；输出 token：1346。

| 类别 | 正确/有效 |
|---|---:|
| Humanities | 235/257 |
| Other | 331/384 |
| STEM | 367/430 |
| Social Science | 249/275 |

| 学科 | 正确/有效 | 请求失败 |
|---|---:|---:|
| 注册会计师 (`accountant`) | 43/49 | 0 |
| 高等数学 (`advanced_mathematics`) | 12/19 | 0 |
| 艺术学 (`art_studies`) | 30/33 | 0 |
| 基础医学 (`basic_medicine`) | 17/19 | 0 |
| 工商管理 (`business_administration`) | 25/33 | 0 |
| 中国语言文学 (`chinese_language_and_literature`) | 20/23 | 0 |
| 公务员 (`civil_servant`) | 40/47 | 0 |
| 临床医学 (`clinical_medicine`) | 19/22 | 0 |
| 大学化学 (`college_chemistry`) | 21/24 | 0 |
| 大学经济学 (`college_economics`) | 44/55 | 0 |
| 大学物理 (`college_physics`) | 18/19 | 0 |
| 大学编程 (`college_programming`) | 34/37 | 0 |
| 计算机组成 (`computer_architecture`) | 21/21 | 0 |
| 计算机网络 (`computer_network`) | 15/19 | 0 |
| 离散数学 (`discrete_mathematics`) | 12/16 | 0 |
| 教育学 (`education_science`) | 27/29 | 0 |
| 注册电气工程师 (`electrical_engineer`) | 28/37 | 0 |
| 环境影响评价工程师 (`environmental_impact_assessment_engineer`) | 26/31 | 0 |
| 注册消防工程师 (`fire_engineer`) | 24/31 | 0 |
| 高中生物 (`high_school_biology`) | 18/19 | 0 |
| 高中化学 (`high_school_chemistry`) | 15/19 | 0 |
| 高中语文 (`high_school_chinese`) | 16/19 | 0 |
| 高中地理 (`high_school_geography`) | 19/19 | 0 |
| 高中历史 (`high_school_history`) | 19/20 | 0 |
| 高中数学 (`high_school_mathematics`) | 10/18 | 0 |
| 高中物理 (`high_school_physics`) | 18/19 | 0 |
| 高中政治 (`high_school_politics`) | 19/19 | 0 |
| 思想道德修养与法律基础 (`ideological_and_moral_cultivation`) | 18/19 | 0 |
| 法学 (`law`) | 20/24 | 0 |
| 法律职业资格 (`legal_professional`) | 20/23 | 0 |
| 逻辑学 (`logic`) | 21/22 | 0 |
| 毛泽东思想和中国特色社会主义理论体系概论 (`mao_zedong_thought`) | 23/24 | 0 |
| 马克思主义基本原理 (`marxism`) | 18/19 | 0 |
| 注册计量师 (`metrology_engineer`) | 19/24 | 0 |
| 初中生物 (`middle_school_biology`) | 18/21 | 0 |
| 初中化学 (`middle_school_chemistry`) | 20/20 | 0 |
| 初中地理 (`middle_school_geography`) | 11/12 | 0 |
| 初中历史 (`middle_school_history`) | 22/22 | 0 |
| 初中数学 (`middle_school_mathematics`) | 18/19 | 0 |
| 初中物理 (`middle_school_physics`) | 18/19 | 0 |
| 初中政治 (`middle_school_politics`) | 21/21 | 0 |
| 近代史纲要 (`modern_chinese_history`) | 21/23 | 0 |
| 操作系统 (`operating_system`) | 17/19 | 0 |
| 医师资格 (`physician`) | 40/49 | 0 |
| 植物保护 (`plant_protection`) | 21/22 | 0 |
| 概率统计 (`probability_and_statistics`) | 13/18 | 0 |
| 导游资格 (`professional_tour_guide`) | 28/29 | 0 |
| 体育学 (`sports_science`) | 18/19 | 0 |
| 税务师 (`tax_accountant`) | 44/49 | 0 |
| 教师资格 (`teacher_qualification`) | 42/44 | 0 |
| 注册城乡规划师 (`urban_and_rural_planner`) | 39/46 | 0 |
| 兽医学 (`veterinary_medicine`) | 22/23 | 0 |
