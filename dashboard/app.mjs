import {isNumber, orderedRuns, compareDimensions, unionDimensions, metricScale, barWidth} from './metrics.mjs';

const $ = id => document.getElementById(id);
const escape = value => String(value ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const integer = value => isNumber(value) ? value.toLocaleString('zh-CN') : '—';
const palette = ['#377b64', '#94ad55', '#6b86ac', '#bd8a69', '#956e9e', '#72a1a6', '#b2a348', '#73737c'];
let catalog, selected = new Set();
const benchmark = () => catalog.benchmarks.find(b => b.id === $('benchmark').value);
const metric = () => benchmark().metrics.find(m => m.id === $('metric').value);
const allRuns = () => catalog.runs.filter(r => r.benchmark_id === $('benchmark').value && r.split === $('split').value && r.comparison_group === $('group').value);
const runs = () => allRuns().filter(r => selected.has(r.id));
const baseline = () => runs().find(r => r.id === $('baseline').value);
const target = () => runs().find(r => r.id === $('target').value);
const model = run => catalog.models.find(m => m.id === run.model_id);
const color = run => palette[catalog.models.findIndex(m => m.id === run.model_id) % palette.length];
const label = run => `${model(run)?.name ?? run.model_id}${allRuns().filter(r => r.model_id === run.model_id).length > 1 ? ' · ' + (run.date ?? run.id) : ''}`;
const score = (value, m = metric()) => isNumber(value) ? value.toFixed(2) + (m.unit ?? '') : '—';
const delta = (value, m = metric()) => isNumber(value) ? `${value > 0 ? '+' : ''}${value.toFixed(2)}${m.unit === '%' ? ' 个百分点' : m.unit ? ' ' + m.unit : ''}` : '—';
const directionClass = value => !isNumber(value) || Math.abs(value) < 1e-9 ? 'neutral' : value * (metric().higher_is_better ? 1 : -1) > 0 ? 'positive' : 'negative';
const comparableDelta = () => baseline() && target() && isNumber(baseline().metrics[metric().id]) && isNumber(target().metrics[metric().id]) ? target().metrics[metric().id] - baseline().metrics[metric().id] : null;

function options(id, values, current) {
  const select = $(id);
  select.replaceChildren(...values.map(v => new Option(v.name, v.id)));
  if (values.some(v => v.id === current)) select.value = current;
}
function setupBenchmark(reset = false) {
  if (reset) options('benchmark', catalog.benchmarks.map(b => ({id:b.id,name:b.name})));
  const splits = [...new Set(catalog.runs.filter(r => r.benchmark_id === $('benchmark').value).map(r => r.split))];
  options('split', splits.map(s => ({id:s,name:s === 'test' ? 'test · 测试集' : s === 'val' ? 'val · 验证集' : s})));
  options('metric', benchmark().metrics.map(m => ({id:m.id,name:m.name})), benchmark().metrics[0]?.id);
  setupGroups();
}
function setupGroups() {
  const entries = new Map();
  for (const r of catalog.runs.filter(r => r.benchmark_id === $('benchmark').value && r.split === $('split').value)) if (!entries.has(r.comparison_group)) entries.set(r.comparison_group, r);
  options('group', [...entries.values()].map(r => {
    const p = r.protocol;
    const base = `${p.thinking === 'disabled' ? '非思考' : p.thinking === 'enabled' ? '思考' : p.thinking} · ${p.shots === 0 ? '零样本' : p.shots + '-shot'} · T=${p.temperature} · ${p.max_tokens} token`;
    return {id:r.comparison_group,name:base + (r.status==='incomplete' ? ' · 阶段结果' : '') + (entries.size > 1 ? ` · ${r.comparison_group.slice(0, 6)}` : '')};
  }));
  setupSelection();
}
function setupSelection() {
  // Multiple dates of a model are independent runs; default to its most recently dated run.
  const defaults = new Map();
  for (const r of allRuns()) if (!defaults.has(r.model_id) || (r.date ?? '') > (defaults.get(r.model_id).date ?? '')) defaults.set(r.model_id, r);
  selected = new Set([...defaults.values()].map(r => r.id));
  $('search').value = '';
  $('sort').value = 'delta-desc';
  setupComparison();
  render();
}
function setupComparison() {
  options('baseline', runs().map(r => ({id:r.id,name:label(r)})), $('baseline').value);
  setupTarget();
}
function setupTarget() {
  options('target', runs().filter(r => r.id !== $('baseline').value).map(r => ({id:r.id,name:label(r)})), $('target').value);
  $('target').disabled = runs().length < 2;
}
function renderKpis() {
  const m = metric(), list = runs(), best = orderedRuns(list, m).find(r => isNumber(r.metrics[m.id]));
  const d = comparableDelta();
  const totals = [...new Set(list.map(r => r.counts.total).filter(isNumber))];
  const dimensions = unionDimensions(list).length;
  const cards = [
    {label:list.some(r=>r.status==='incomplete') ? '阶段最高成绩' : '当前最佳成绩',value:best ? score(best.metrics[m.id]) : '—',foot:best ? label(best) : '该指标暂无数据',icon:'↗'},
    {label:'相对基准变化',value:isNumber(d) ? `${d > 0 ? '+' : ''}${d.toFixed(2)}` : '—',unit:isNumber(d) ? (m.unit === '%' ? '百分点' : m.unit ?? '') : '',foot:target() ? `${label(target())} vs ${label(baseline())}` : '选择两个运行后查看',class:directionClass(d),icon:'↔'},
    {label:list.some(r=>r.status==='incomplete') ? '已尝试样本数（阶段）' : '每次运行样本数',value:totals.length === 1 ? integer(totals[0]) : totals.length > 1 ? '不同' : '—',foot:`覆盖 ${dimensions} 个学科 / 维度`,icon:'▦'},
    {label:'参与对比的运行',value:list.length,unit:'次',foot:`${new Set(list.map(r => r.model_id)).size} 个模型 · 同配置分组`,icon:'◫'}
  ];
  $('kpis').innerHTML = cards.map(c => `<article class="kpi"><div class="kpi-label">${escape(c.label)}<span aria-hidden="true">${c.icon}</span></div><div class="kpi-value ${c.class ?? ''}">${escape(c.value)}${c.unit ? `<small>${escape(c.unit)}</small>` : ''}</div><div class="kpi-foot">${escape(c.foot)}</div></article>`).join('');
}
function renderModels() {
  const m = metric(), list = allRuns(), scale = metricScale(m, list.map(r => r.metrics[m.id]));
  const best = orderedRuns(runs(), m).find(r => isNumber(r.metrics[m.id]));
  $('models').innerHTML = list.map(r => {
    const value = r.metrics[m.id];
    return `<article class="model-card ${selected.has(r.id) ? '' : 'off'}" style="--series:${color(r)}"><div class="model-top"><label class="model-check"><input type="checkbox" data-run="${escape(r.id)}" ${selected.has(r.id) ? 'checked' : ''}><span class="color-dot" style="background:${color(r)}"></span>${escape(label(r))}</label>${r.status==='incomplete' ? '<span class="tag">阶段结果</span>' : best?.id === r.id ? '<span class="tag">当前最佳</span>' : ''}</div><div class="model-score">${isNumber(value) ? value.toFixed(2) : '—'}<small>${isNumber(value) ? escape(m.unit ?? '') : ''}</small></div><div class="track" aria-hidden="true"><span style="width:${barWidth(value, scale)}%"></span></div><div class="model-bottom"><span>${r.counts.correct !== undefined ? `${integer(r.counts.correct)} / ${integer(r.counts.valid ?? r.counts.total)} 有效题正确` : `${integer(r.counts.total)} 个样本`}</span><span>${escape(r.date ?? '历史记录')}</span></div></article>`;
  }).join('');
}
function renderCategories() {
  const m = metric(), list = runs(), cats = new Map();
  for (const r of list) for (const c of r.categories) if (!cats.has(c.id)) cats.set(c.id,c);
  $('legend').innerHTML = list.map(r => `<span><i class="color-dot" style="background:${color(r)}"></i>${escape(label(r))}</span>`).join('');
  $('chart-unit').textContent = `${m.name} ${m.higher_is_better ? '↑ 越高越好' : '↓ 越低越好'}`;
  const scale = metricScale(m, list.flatMap(r => r.categories.map(c => c.metrics[m.id])));
  $('category-chart').classList.toggle('many-categories', cats.size > 6);
  $('category-chart').innerHTML = cats.size ? [...cats.values()].map(c => {
    const counts = [...new Set(list.map(r => r.categories.find(d => d.id === c.id)?.counts.valid).filter(isNumber))];
    return `<div class="category-row"><div class="category-name">${escape(c.name)}<small>${counts.length === 1 ? integer(counts[0]) + ' 题 / 运行' : ''}</small></div>${list.map(r => {const v = r.categories.find(d => d.id === c.id)?.metrics[m.id];return `<div class="bar-row" aria-label="${escape(`${c.name}，${label(r)}，${score(v)}`)}"><div class="bar-track" style="--series:${color(r)}" aria-hidden="true"><span style="width:${barWidth(v,scale)}%"></span></div><span class="bar-value">${escape(score(v))}</span></div>`;}).join('')}</div>`;
  }).join('') + `<div class="axis" aria-hidden="true"><span>${escape(score(scale[0]))}</span><span>${escape(score((scale[0]+scale[1])/2))}</span><span>${escape(score(scale[1]))}</span></div>` : '<div class="empty-state">此评测尚未提供类别明细。</div>';
}
function renderComparison() {
  const b = baseline(), t = target(), m = metric();
  if (!b || !t) {
    $('comparison-summary').textContent = '当前只有一个运行。接入或勾选第二个同配置运行后，可查看优势与差距。';
    $('delta-chart').innerHTML = '<div class="empty-state">暂无可比较的第二个运行</div>';
    return;
  }
  const rows = compareDimensions(b,t,m), wins = rows.filter(r => r.advantage > 1e-9).length, losses = rows.filter(r => r.advantage < -1e-9).length;
  const change = comparableDelta();
  $('comparison-summary').innerHTML = `<strong>${escape(label(t))}</strong> 相对基准 ${escape(delta(change))}<br>共有 ${rows.length} 个可比维度：<strong>${wins} 领先</strong> · ${rows.length-wins-losses} 持平 · ${losses} 落后`;
  const winning = rows.filter(r => r.advantage > 1e-9).sort((a,b) => b.advantage-a.advantage).slice(0,4);
  const losing = rows.filter(r => r.advantage < -1e-9).sort((a,b) => a.advantage-b.advantage).slice(0,3);
  const max = Math.max(1e-9, ...[...winning,...losing].map(r => Math.abs(r.delta)));
  const renderRows = (items, caption, cls) => items.length ? `<div class="delta-caption">${caption}</div>${items.map(r => `<div class="delta-row ${cls}" title="${escape(`${r.name}：${score(r.baseline)} → ${score(r.target)}；${delta(r.delta)}`)}"><span class="delta-name">${escape(r.name)}</span><div class="delta-track" aria-hidden="true"><span style="width:${Math.abs(r.delta)/max*100}%"></span></div><span class="delta-value">${r.delta > 0 ? '+' : ''}${r.delta.toFixed(2)}</span></div>`).join('')}` : `<div class="delta-caption">${caption}：无</div>`;
  $('delta-chart').innerHTML = rows.length ? renderRows(winning,'领先最多','positive') + renderRows(losing,'落后最多','negative') + `<p class="table-note">差值单位：${escape(m.unit === '%' ? '百分点' : m.unit ?? '分')} · ${m.higher_is_better ? '越高越好' : '越低越好'} · 条形长度表示差值绝对值</p>` : '<div class="empty-state">两个运行暂无共同的维度指标。</div>';
}
function setupCategories() {
  const cats = new Map();
  for (const r of runs()) for (const c of r.categories) cats.set(c.id,c.name);
  options('category',[{id:'all',name:'全部类别'},...[...cats].map(([id,name])=>({id,name}))],$('category').value);
}
function renderTable() {
  const m = metric(), list = runs(), b = baseline(), t = target();
  const comparisons = new Map(compareDimensions(b,t,m).map(d=>[d.id,d]));
  const lookup = new Map(list.map(r=>[r.id,new Map(r.dimensions.map(d=>[d.id,d]))]));
  const categories = new Map(list.flatMap(r=>r.categories.map(c=>[c.id,c.name])));
  const query = $('search').value.trim().toLowerCase();
  let rows = unionDimensions(list).filter(d=>(!query || `${d.id} ${d.name}`.toLowerCase().includes(query)) && ($('category').value === 'all' || d.category_id === $('category').value));
  const targetScore = d=>lookup.get((t ?? b)?.id)?.get(d.id)?.metrics[m.id];
  const sorter = $('sort').value;
  rows.sort((a,b)=>{
    if (sorter === 'name') return a.name.localeCompare(b.name,'zh-CN');
    const av = sorter.startsWith('delta') ? comparisons.get(a.id)?.advantage : targetScore(a);
    const bv = sorter.startsWith('delta') ? comparisons.get(b.id)?.advantage : targetScore(b);
    if (!isNumber(av)) return isNumber(bv) ? 1 : 0;
    if (!isNumber(bv)) return -1;
    return (av-bv)*(sorter.endsWith('asc') ? 1 : -1) || a.name.localeCompare(b.name,'zh-CN');
  });
  const scale = metricScale(m,list.flatMap(r=>r.dimensions.map(d=>d.metrics[m.id])));
  $('dimension-count').textContent = `${rows.length} / ${unionDimensions(list).length} 个维度`;
  $('table-head').innerHTML = `<tr><th>学科 / 维度</th><th>类别</th>${list.map(r=>`<th><span class="color-dot" style="background:${color(r)}"></span> ${escape(label(r))}</th>`).join('')}<th>${escape(t ? label(t)+' − 基准' : '对比差值')}</th></tr>`;
  $('table-body').innerHTML = rows.length ? rows.map(d=>`<tr><td class="name-cell">${escape(d.name)}<small>${escape(d.id)}</small></td><td><span class="count-tag">${escape(categories.get(d.category_id) ?? '—')}</span></td>${list.map(r=>{const item=lookup.get(r.id).get(d.id), v=item?.metrics[m.id];return `<td class="score-cell" style="--series:${color(r)}"><div class="cell-score"><span>${escape(score(v))}</span><small>${item?.counts.correct !== undefined ? integer(item.counts.correct)+'/'+integer(item.counts.valid) : ''}</small></div><div class="cell-bar" aria-hidden="true"><span style="width:${barWidth(v,scale)}%"></span></div></td>`;}).join('')}<td class="${directionClass(comparisons.get(d.id)?.delta)}">${escape(delta(comparisons.get(d.id)?.delta))}</td></tr>`).join('') : `<tr><td colspan="${3+list.length}" class="empty-state">没有匹配的学科 / 维度，请调整搜索或类别筛选。</td></tr>`;
  $('table-note').textContent = `${m.name}；差值为对比运行减基准。缺失指标显示“—”，不按 0 分处理。未覆盖的维度不参与胜负统计。`;
}
function renderMethod() {
  const list = runs(), r = list[0], p = r?.protocol;
  if (!r) {
    $('protocol-details').replaceChildren();
    $('run-table').replaceChildren();
    $('run-notes').textContent = '此筛选下暂未接入运行结果。';
    return;
  }
  const details = [['评测集 / 分组',`${benchmark().name} / ${r.split}`],['提示版本',p.prompt_version],['模式 / 样本',`${p.thinking === 'disabled' ? '非思考模式' : p.thinking} · ${p.shots}-shot`],['生成配置',`temperature=${p.temperature} · max_tokens=${p.max_tokens}`],['题目选择标识',p.selection],['数据指纹',r.dataset_fingerprint]];
  $('protocol-details').innerHTML = details.map(([key,value])=>`<div><dt>${escape(key)}</dt><dd>${escape(value)}</dd></div>`).join('');
  $('run-table').innerHTML = list.map(r=>`<tr><td>${escape(label(r))}<br><span class="count-tag">${escape(r.date ?? '历史记录 · 日期未提供')}</span></td><td>${integer(r.counts.total)} / ${integer(r.counts.correct)}</td><td>${integer(r.counts.failed)} / ${integer(r.counts.unparsed)}</td><td>${escape(r.source)}</td></tr>`).join('');
  $('run-notes').innerHTML = list.map(r=>`<strong>${escape(label(r))}</strong><ul>${r.notes.map(n=>`<li>${escape(n)}</li>`).join('')}</ul>`).join('');
}
function render() {
  const list = runs();
  $('export').disabled = !list.length;
  const incomplete=list.filter(r=>r.status==='incomplete');
  $('scope-note').classList.toggle('incomplete-note',incomplete.length>0);
  $('scope-note').textContent = (incomplete.length ? `阶段结果 · 尚未完成：${incomplete.map(r=>`${label(r)} 成功响应 ${integer(r.counts.valid)}/${integer(r.counts.expected_total ?? r.counts.total)}`).join('；')}。` : '') + `${benchmark().description ?? benchmark().name} · ${$('split').value} · ${allRuns().length} 次可选运行。不同数据指纹、提示、生成参数和抽样范围分开展示。`;
  const dated = list.map(r=>r.date).filter(Boolean).sort();
  $('run-date').textContent = dated.length ? `所选运行最新日期 / ${dated.at(-1)}` : '所选结果 / 历史记录';
  $('footer-count').textContent = `${catalog.models.length} 个模型 · ${catalog.benchmarks.length} 个评测集 · ${catalog.runs.length} 次运行`;
  renderKpis(); renderModels(); renderCategories(); renderComparison(); setupCategories(); renderTable(); renderMethod();
  $('announcement').textContent = `已显示 ${benchmark().name} ${$('split').value}，${list.length} 次运行，${metric().name}。`;
}
function download() {
  const data = {schema_version:catalog.schema_version,benchmark:benchmark(),metric:metric(),baseline_run_id:baseline()?.id ?? null,target_run_id:target()?.id ?? null,models:catalog.models.filter(m=>runs().some(r=>r.model_id===m.id)),runs:runs()};
  const url = URL.createObjectURL(new Blob([JSON.stringify(data,null,2)],{type:'application/json'}));
  const anchor = document.createElement('a'); anchor.href=url; anchor.download=`eval-${benchmark().id}-${$('split').value}.json`;anchor.click();setTimeout(()=>URL.revokeObjectURL(url),1000);
}
async function init() {
  try {
    const response = await fetch('./data/catalog.json');
    if (!response.ok) throw new Error('HTTP '+response.status);
    catalog = await response.json();
    if (catalog.schema_version !== 1 || !catalog.runs.length || !catalog.benchmarks.length) throw new Error('数据目录为空或版本不兼容');
    $('benchmark').addEventListener('change',()=>setupBenchmark());
    $('split').addEventListener('change',setupGroups);
    $('group').addEventListener('change',setupSelection);
    $('metric').addEventListener('change',render);
    $('baseline').addEventListener('change',()=>{setupTarget();renderKpis();renderComparison();renderTable();});
    $('target').addEventListener('change',()=>{renderKpis();renderComparison();renderTable();});
    $('models').addEventListener('change',event=>{
      const input=event.target, id=input.dataset.run;
      if (!id) return;
      if (!input.checked && selected.size===1){input.checked=true;$('announcement').textContent='请至少保留一个运行。';return;}
      input.checked ? selected.add(id) : selected.delete(id); setupComparison(); render();
      [...$('models').querySelectorAll('input')].find(el=>el.dataset.run===id)?.focus();
    });
    for (const id of ['search','category','sort']) $(id).addEventListener(id==='search'?'input':'change',renderTable);
    $('reset').addEventListener('click',()=>setupBenchmark(true));
    $('export').addEventListener('click',download);
    $('method-toggle').addEventListener('click',()=>{const expanded=$('method-toggle').getAttribute('aria-expanded')==='true';$('method-toggle').setAttribute('aria-expanded',String(!expanded));$('method-toggle').textContent=expanded?'展开配置 ↓':'收起配置 ↑';$('method-details').hidden=expanded;});
    $('catalog-count').textContent=`${catalog.models.length} 个模型 / ${catalog.runs.length} 次运行`;
    setupBenchmark(true);$('app-content').hidden=false;$('load-state').hidden=true;
  } catch (error) {
    $('load-state').innerHTML=`<strong>暂时无法读取评测数据</strong><p>请先在仓库根目录生成数据，再以 HTTP 服务打开此页面。</p><code>python3 build_dashboard.py<br>python3 -m http.server 8765 --bind 127.0.0.1 --directory dashboard</code><p>浏览器地址：http://127.0.0.1:8765/</p><small>${escape(error.message)}</small>`;
  }
}
init();
