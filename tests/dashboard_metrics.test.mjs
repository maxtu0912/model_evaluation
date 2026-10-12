import test from 'node:test';
import assert from 'node:assert/strict';
import {readFile} from 'node:fs/promises';
import {orderedRuns, compareDimensions, unionDimensions, metricScale, barWidth} from '../dashboard/metrics.mjs';

const catalog = JSON.parse(await readFile(new URL('../dashboard/data/catalog.json', import.meta.url), 'utf8'));
const [flash, pro, val] = catalog.runs;
const accuracy = catalog.benchmarks[0].metrics[0];

test('real report comparison preserves all 52 dimensions and expected differences', () => {
  const rows = compareDimensions(flash, pro, accuracy);
  assert.equal(rows.length, 52);
  assert.equal(rows.filter(r => r.advantage > 0).length, 35);
  assert.equal(rows.filter(r => r.advantage < 0).length, 11);
  assert.equal(rows.filter(r => r.advantage === 0).length, 6);
  assert.equal(orderedRuns([flash,pro], accuracy)[0].id, pro.id);
  assert.ok(Math.abs(rows.find(r=>r.id==='clinical_medicine').delta + 3) < 1e-10);
  assert.equal(unionDimensions([flash,pro]).length, 52);
});
test('different splits cannot accidentally be compared', () => {
  assert.deepEqual(compareDimensions(val,pro,accuracy), []);
});
test('three models, lower-is-better metrics, and missing values remain meaningful', () => {
  const metric = {id:'time',higher_is_better:false};
  const model = (id, value) => ({id,comparison_group:'g',metrics:{time:value},dimensions:[{id:'task',metrics:{time:value}}]});
  const a=model('a',100), b=model('b',80), c=model('c',null);
  assert.deepEqual(orderedRuns([a,b,c],metric).map(r=>r.id), ['b','a','c']);
  assert.equal(compareDimensions(a,b,metric)[0].delta,-20);
  assert.equal(compareDimensions(a,b,metric)[0].advantage,20);
  assert.deepEqual(compareDimensions(a,c,metric),[]);
  assert.deepEqual(compareDimensions(a,undefined,metric),[]);
});
test('charts use declared scales and never treat missing metrics as scores', () => {
  assert.deepEqual(metricScale(accuracy,[88,90]),[0,100]);
  assert.deepEqual(metricScale({id:'score'},[-2,5,null]),[-2,5]);
  assert.equal(barWidth(90,[0,100]),90);
  assert.equal(barWidth(null,[0,100]),0);
  assert.equal(barWidth(7.5,[0,10]),75);
});
