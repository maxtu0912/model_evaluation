#!/usr/bin/env python3
"""Prepare, run and aggregate MMLU-Pro using the official 5-shot CoT template."""
import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
import datetime as dt
import hashlib
import io
import json
from pathlib import Path
import random
import re
import statistics
import threading
import time
from urllib.request import urlopen

from eval import ROOT, DEFAULT_BASE_URL, api_json, get_key, read_jsonl

REVISION = 'b189ec765aa7ed75c8acfea42df31fdae71f97be'
PROMPT_VERSION = 'mmlu-pro-official-5shot-cot-nonthinking-v1'
LETTERS = 'ABCDEFGHIJ'
NAMES = {'math':'数学','physics':'物理','chemistry':'化学','law':'法律','engineering':'工程',
         'other':'其他','economics':'经济学','health':'健康与医学','psychology':'心理学',
         'business':'商业','biology':'生物','philosophy':'哲学','computer science':'计算机科学','history':'历史'}


def digest(value):
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':')).encode()).hexdigest()


def prepare(args):
    import pyarrow.parquet as pq
    args.dataset.parent.mkdir(parents=True, exist_ok=True)
    dataset = {'revision':args.revision, 'source':'TIGER-Lab/MMLU-Pro', 'file_sha256':{}}
    for split in ('test','validation'):
        url=f'https://huggingface.co/datasets/TIGER-Lab/MMLU-Pro/resolve/{args.revision}/data/{split}-00000-of-00001.parquet'
        with urlopen(url,timeout=60) as response:
            content=response.read()
        dataset['file_sha256'][split]=hashlib.sha256(content).hexdigest()
        rows=pq.read_table(io.BytesIO(content)).to_pylist()
        dataset[split]=[]
        for row in rows:
            raw=row['options']; idx=row['answer_index']; options=[o for o in raw if o != 'N/A']
            if not 0 <= idx < len(raw) or LETTERS[idx] != row['answer'] or raw[idx]=='N/A':
                raise ValueError(f'{split}:{row["question_id"]} 标准答案不合法')
            if sum(o!='N/A' for o in raw[:idx]) != idx:
                raise ValueError('移除 N/A 后答案位置改变，须核对官方协议')
            if not 2 <= len(options) <= 10:
                raise ValueError('选项数量不合法')
            dataset[split].append({k:row[k] for k in ('question_id','question','category','answer','answer_index','cot_content')} | {'options':options})
        if len({r['question_id'] for r in dataset[split]}) != len(rows):
            raise ValueError('题目 ID 重复')
        print(f'{split}: {len(rows)} 题',flush=True)
    if len(dataset['test'])!=12032 or len(dataset['validation'])!=70:
        raise ValueError('固定版本的题目数与预期不符')
    cats={r['category'] for r in dataset['test']}
    if cats != set(NAMES) or any(sum(r['category']==cat for r in dataset['validation'])!=5 for cat in cats):
        raise ValueError('每领域必须提供 5 个验证集示例')
    dataset['dataset_sha256']=digest({k:dataset[k] for k in ('revision','file_sha256','test','validation')})
    args.dataset.write_text(json.dumps(dataset,ensure_ascii=False)+'\n')
    print(f'数据指纹：{dataset["dataset_sha256"]}')


def load_dataset(path):
    data=json.loads(path.read_text())
    if data['dataset_sha256'] != digest({k:data[k] for k in ('revision','file_sha256','test','validation')}):
        raise ValueError('本地题库指纹不一致')
    return data


def choose_questions(data, per_category, seed):
    rng=random.Random(seed)
    groups={cat:[r for r in data['test'] if r['category']==cat] for cat in sorted({r['category'] for r in data['test']})}
    for rows in groups.values():
        rng.shuffle(rows)
        if per_category:
            del rows[per_category:]
    return [rows[i] for i in range(max(map(len,groups.values()))) for rows in groups.values() if i<len(rows)]


def format_example(row, demonstration=False):
    text=f'Question: {row["question"]}\nOptions: '
    text+=''.join(f'{LETTERS[i]}. {option}\n' for i,option in enumerate(row['options']))
    cot=row['cot_content'] if demonstration else "Let's think step by step."
    if cot.startswith('A: '):
        cot=cot[3:]
    return text+'Answer: '+cot+'\n\n'


def make_prompt(question, data):
    category=question['category']
    demos=[r for r in data['validation'] if r['category']==category]
    if len(demos)!=5:
        raise ValueError('缺少 5-shot 示例')
    instruction=(f'The following are multiple choice questions (with answers) about {category}. Think step by'
                 ' step and then output the answer in the format of "The answer is (X)" at the end.\n\n')
    return instruction+''.join(format_example(r,True) for r in demos)+format_example(question)


def extract_answer(text, option_count):
    # Prefer the last explicit final answer; never fall back to arbitrary letters in the reasoning.
    text=text.replace('**','')
    matches=re.findall(r'(?i:\b(?:the\s+)?answer\s+is\s*)(?:\(([A-Ja-j])\)|([A-J]))(?=\s|[.,;!]|$)',text)
    if not matches:
        matches=re.findall(r'(?i:\banswer\s*:\s*)(?:\(([A-Ja-j])\)|([A-J]))(?=\s|[.,;!]|$)',text)
    if matches:
        answer=(matches[-1][0] or matches[-1][1]).upper()
    else:
        match=re.fullmatch(r'\s*\(?([A-J])\)?[.!]?\s*',text,re.I)
        answer=match[1].upper() if match else None
    return answer if answer is not None and answer in LETTERS[:option_count] else None


def request_payload(args, prompt):
    return {'model':args.model, 'messages':[{'role':'user','content':prompt}], 'temperature':0,
            'thinking':{'type':'disabled'}, 'max_tokens':args.max_tokens, 'top_p':1,
            'frequency_penalty':0, 'presence_penalty':0, 'stream':False}


def request_key(args, data, question, prompt):
    return digest({'dataset_sha256':data['dataset_sha256'], 'prompt_version':PROMPT_VERSION,
                   'question_id':question['question_id'], 'payload':request_payload(args,prompt)})


def run(args):
    data=load_dataset(args.dataset)
    selected=choose_questions(data,args.per_category,args.seed)
    key=get_key()
    if not args.service_name:
        models=api_json(args.base_url,'/models',key,timeout=args.timeout)
        args.service_name=next((m.get('name',m['id']) for m in models.get('data',[]) if m['id']==args.model),args.model)
    args.output.parent.mkdir(parents=True,exist_ok=True)
    done={r['request_fingerprint'] for r in read_jsonl(args.output) if 'error' not in r} if args.output.exists() else set()
    work=[]
    for question in selected:
        prompt=make_prompt(question,data)
        fingerprint=request_key(args,data,question,prompt)
        if fingerprint not in done:
            work.append((question,prompt,fingerprint))
    print(f'{args.model}: 选中 {len(selected)} 题，待运行 {len(work)}，并发 {args.workers}',flush=True)
    stop=threading.Event()
    def ask(item):
        if stop.is_set():
            return None
        q,prompt,fingerprint=item
        row={'time_utc':dt.datetime.now(dt.timezone.utc).isoformat(), 'benchmark':'MMLU-Pro','split':'test',
             'model':args.model,'model_service_name':args.service_name,'dataset_revision':data['revision'],
             'dataset_sha256':data['dataset_sha256'],'prompt_version':PROMPT_VERSION,'shots':5,'thinking':'disabled',
             'temperature':0,'max_tokens':args.max_tokens,'seed':args.seed,'request_fingerprint':fingerprint,
             'question_id':str(q['question_id']),'category':q['category'],'option_count':len(q['options']),
             'prompt':prompt,'expected':q['answer']}
        start=time.monotonic()
        try:
            result=api_json(args.base_url,'/chat/completions',key,request_payload(args,prompt),args.timeout)
            choice=result['choices'][0]
            row.update(latency_seconds=round(time.monotonic()-start,3),response=choice['message'].get('content') or '',
                       api_model=result.get('model'),finish_reason=choice.get('finish_reason'),usage=result.get('usage',{}))
            row['extracted']=extract_answer(row['response'],len(q['options']))
            row['correct']=row['extracted']==q['answer']
        except (RuntimeError,KeyError,IndexError,TypeError) as exc:
            row['error']=str(exc)
            if any(code in str(exc) for code in ('HTTP 401','HTTP 402','HTTP 403','HTTP 404')):
                stop.set()
        return row
    with args.output.open('a',encoding='utf-8') as output, ThreadPoolExecutor(max_workers=args.workers) as pool:
        futures=[pool.submit(ask,item) for item in work]
        errors=0
        for i,future in enumerate(as_completed(futures),1):
            row=future.result()
            if row is None:
                continue
            output.write(json.dumps(row,ensure_ascii=False)+'\n'); output.flush()
            errors+='error' in row
            if i%50==0 or i==len(work) or 'error' in row:
                print(f'本次完成 {i}/{len(work)}；请求失败 {errors}',flush=True)
    if stop.is_set():
        raise RuntimeError('鉴权、余额或模型访问错误，已停止；已保存结果可续跑')
    if errors:
        raise RuntimeError(f'{errors} 题请求失败，请用原命令续跑')
    print('评测完成',flush=True)


def aggregate(args):
    data=load_dataset(args.dataset)
    latest={}
    for row in read_jsonl(args.output):
        if row['model']!=args.model or row['dataset_sha256']!=data['dataset_sha256'] or row['prompt_version']!=PROMPT_VERSION or row['max_tokens']!=args.max_tokens:
            continue
        latest[row['question_id']]=row
    expected={str(q['question_id']):q for q in data['test']}
    if not latest or set(latest)-set(expected):
        raise ValueError('结果为空或有未知题目')
    valid=[r for r in latest.values() if 'error' not in r]
    if not valid:
        raise ValueError('没有成功响应，无法生成报告')
    if args.require_complete and (set(latest)!=set(expected) or len(valid)!=len(expected)):
        raise ValueError(f'结果尚未完整：{len(valid)}/{len(expected)}')
    for r in valid:
        q=expected[r['question_id']]
        if r['category']!=q['category'] or r['expected']!=q['answer'] or r['extracted']!=extract_answer(r['response'],len(q['options'])) or r['correct']!=(r['extracted']==q['answer']):
            raise ValueError('逐题记录与标准答案或提取规则不一致')
        if r['request_fingerprint']!=request_key(args,data,q,make_prompt(q,data)):
            raise ValueError('记录的请求配置与当前协议不一致')
    def counts(rows):
        ok=[r for r in rows if 'error' not in r]
        return {'total':len(rows),'valid':len(ok),'correct':sum(r['correct'] for r in ok),'failed':len(rows)-len(ok),
                'unparsed':sum(r['extracted'] is None for r in ok)}
    dimensions=[]
    for category in sorted({r['category'] for r in latest.values()}):
        subset=[r for r in latest.values() if r['category']==category]
        c=counts(subset); value=c['correct']/c['valid']*100 if c['valid'] else None
        dimensions.append({'id':category,'name':NAMES.get(category,category),'category_id':category,'counts':c,
                           'metrics':{'accuracy':value,'macro_accuracy':value}})
    c=counts(list(latest.values()))
    c['expected_total']=len(expected)
    complete=set(latest)==set(expected) and len(valid)==len(expected)
    selection='full' if set(latest)==set(expected) else 'question-ids:'+digest(sorted(latest))
    result={'split':'test','dataset_fingerprint':data['dataset_sha256'],'status':'completed' if complete else 'incomplete',
            'protocol':{'prompt_version':PROMPT_VERSION,'shots':5,'thinking':'disabled','temperature':0,'max_tokens':args.max_tokens,'selection':selection},
            'counts':c,'metrics':{'accuracy':c['correct']/c['valid']*100 if c['valid'] else None,
                                 'macro_accuracy':statistics.mean(d['metrics']['accuracy'] for d in dimensions if d['metrics']['accuracy'] is not None)},
            'categories':[{k:v for k,v in d.items() if k!='category_id'} for d in dimensions],'dimensions':dimensions,
            'operational':{'latency_seconds':statistics.mean(r['latency_seconds'] for r in valid),
                           'input_tokens':sum(r['usage'].get('prompt_tokens',0) for r in valid),
                           'output_tokens':sum(r['usage'].get('completion_tokens',0) for r in valid),'latency_comparable':False}}
    if args.aggregate:
        args.aggregate.parent.mkdir(parents=True,exist_ok=True)
        args.aggregate.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
    truncated=sum(r['finish_reason']=='length' for r in valid)
    truncated_unparsed=sum(r['finish_reason']=='length' and r['extracted'] is None for r in valid)
    truncated_correct=sum(r['finish_reason']=='length' and r['correct'] for r in valid)
    lines=['# MMLU-Pro 评测报告','',f'## {args.model} · test','',
           '完整性：全量完成。' if complete else f'**阶段结果，尚未完成：成功响应 {len(valid)}/{len(expected)}，已尝试 {len(latest)}/{len(expected)}。以下成绩不是全量成绩。**', '',
           f'账户模型服务名称：{sorted({str(r.get("model_service_name")) for r in valid})}；响应模型名称：{sorted({str(r.get("api_model")) for r in valid})}。',
           f'数据版本：`{data["revision"]}`；数据指纹：`{data["dataset_sha256"]}`。',
           f'提示版本：`{PROMPT_VERSION}`；5-shot CoT；非思考模式；温度 0；max_tokens={args.max_tokens}；top_p=1。',
           f'选题范围：`{selection}`；覆盖 {len(dimensions)} 个领域。',
           f'有效响应 {c["valid"]}/{c["total"]}；请求失败 {c["failed"]}；无法提取选项 {c["unparsed"]}；输出截断 {truncated}。',
           f'提取失败中有 {truncated_unparsed} 个为截断响应；截断响应中 {truncated-truncated_unparsed} 个仍能提取答案，其中 {truncated_correct} 个正确。',
           f'逐题正确率：{c["correct"]}/{c["valid"]}（{result["metrics"]["accuracy"]:.2f}%）；领域等权平均：{result["metrics"]["macro_accuracy"]:.2f}%。',
           f'平均请求耗时（含重试）：{result["operational"]["latency_seconds"]:.2f} 秒。',
           f'输入 token：{result["operational"]["input_tokens"]}；输出 token：{result["operational"]["output_tokens"]}。','',
           '| 领域 | 正确 / 有效 | 正确率 | 请求失败 |','|---|---:|---:|---:|']
    for d in dimensions:
        value=d['metrics']['accuracy']; v=f'{value:.2f}%' if value is not None else '—'
        lines.append(f'| {d["name"]} (`{d["id"]}`) | {d["counts"]["correct"]}/{d["counts"]["valid"]} | {v} | {d["counts"]["failed"]} |')
    lines+=['','## 方法与边界','',
            '- 固定官方数据版本，移除 N/A 填充选项；验证集的每领域 5 个示例只用于提示，测试题的 cot_content 和标准答案不进入请求。',
            '- 使用官方 5-shot CoT 提示模板；API 内部思考模式关闭，但允许回答正文包含逐步推理。',
            '- 按最后一个明确的最终答案提取选项，缺失或超出本题选项范围按错计分，不随机补答案。不采用官方脚本的任意字母兜底，因此属于本项目独立协议。',
            '- 成功回答不因答错、格式异常或截断而重新生成；仅补跑请求失败。',
            '- 截断响应若能提取有效答案则按该答案评分，否则计错；截断与答案提取失败分别统计。',
            '- 公开题集可能存在训练数据污染；未使用搜索或工具。结果不与 C-Eval 直接横比。',
            '- 模型服务名称与请求日期记录于本地逐题文件；API 别名不是不可变模型快照。','',
            '来源：[官方数据集](https://huggingface.co/datasets/TIGER-Lab/MMLU-Pro)、[官方评测代码](https://github.com/TIGER-AI-Lab/MMLU-Pro/blob/main/evaluate_from_api.py)。','']
    if args.markdown:
        args.markdown.write_text('\n'.join(lines))
    print(json.dumps({'counts':c,'metrics':result['metrics'],'truncated':truncated,'usage':result['operational']},ensure_ascii=False))
    return result


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    sub=parser.add_subparsers(dest='command',required=True)
    for name in ('prepare','run','report'):
        p=sub.add_parser(name)
        p.add_argument('--dataset',type=Path,default=ROOT/'data/mmlu-pro/dataset.json')
        if name=='prepare':
            p.add_argument('--revision',default=REVISION)
        else:
            p.add_argument('--model',default='deepseek-flash')
            p.add_argument('--service-name',help='留空则查询账户模型目录并记录真实服务名称')
            p.add_argument('--output',type=Path,default=ROOT/'results/mmlu-pro-flash.jsonl')
            p.add_argument('--max-tokens',type=int,default=4000)
            if name=='run':
                p.add_argument('--per-category',type=int,default=0)
                p.add_argument('--seed',type=int,default=20261012)
                p.add_argument('--workers',type=int,default=16)
                p.add_argument('--timeout',type=int,default=180)
                p.add_argument('--base-url',default=DEFAULT_BASE_URL)
            else:
                p.add_argument('--markdown',type=Path)
                p.add_argument('--aggregate',type=Path)
                p.add_argument('--require-complete',action='store_true')
    args=parser.parse_args()
    if args.command=='run' and (args.workers<1 or args.per_category<0 or args.max_tokens<1):
        parser.error('并发和输出上限必须为正，抽样数量不能为负')
    {'prepare':prepare,'run':run,'report':aggregate}[args.command](args)


if __name__=='__main__':
    main()
