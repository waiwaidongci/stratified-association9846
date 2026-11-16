<script setup lang="ts">
import{ref,onMounted,computed}from 'vue';
import{useRoute}from 'vue-router';
import{paired,loadPaired}from '../stores/paired';
import*as runs from '../api/pairedRuns';
import type{PairedRun}from '../types/domain';
import{pct,fmt}from '../utils/format';
import{useTask}from '../hooks/useTask';
import{usePolling}from '../hooks/usePolling';
import PageHeading from '../components/common/PageHeading.vue';
import ErrorNotice from '../components/common/ErrorNotice.vue';
import StatusBadge from '../components/common/StatusBadge.vue';
const route=useRoute(),selected=ref(0),current=ref<PairedRun|null>(null),{error,execute}=useTask();
const r=computed(()=>current.value?.status==='completed'?current.value.result:null);
const ex=computed(()=>r.value?.paired_exact??null);
let seq=0;
async function switchRun(id:number){selected.value=id;current.value=null;const s=++seq;const data=await runs.detail(id);if(s===seq&&selected.value===id)current.value=data;}
function choose(id:number){execute(()=>switchRun(id));}
onMounted(()=>execute(async()=>{await loadPaired();const id=Number(route.query.run)||paired.runs.find(x=>x.status==='completed')?.id||paired.runs[0]?.id;if(id)await switchRun(id);}));
usePolling(()=>{if(current.value&&['queued','running'].includes(current.value.status))execute(async()=>{const id=selected.value;const data=await runs.detail(id);if(selected.value===id)current.value=data;await loadPaired();});});
function rate(num:number,den:number){return pct(num/den);}
</script>
<template>
 <PageHeading index="09" title="配对的证据，数组合而非四格。" text="整片共同交换下的精确双侧概率；尾部、内部与总组合数完整呈现，并列与跨层关联均保留。"/>
 <ErrorNotice :message="error" @retry="choose(selected)"/>
 <div class="run-select">
  <label>配对研究档案
   <select :value="selected" @change="choose(Number(($event.target as HTMLSelectElement).value))">
    <option v-for="x in paired.runs" :key="x.id" :value="x.id">#{{x.id}} {{x.name}}</option>
   </select>
  </label>
  <StatusBadge v-if="current" :status="current.status"/>
 </div>

 <div v-if="current?.status==='failed'" class="empty error"><h2>本次配对精确计算未完成</h2><p>{{current.error}}</p><RouterLink to="/paired-sources">回配对底稿修订 →</RouterLink></div>
 <div v-else-if="!r||!ex" class="empty"><h2>正在等待这份配对冻结研究</h2><p>队列完成后自动刷新；需先在配对底稿录入逐片明细并冻结。</p><RouterLink to="/paired-configure">打开配对冻结 →</RouterLink></div>

 <template v-if="r&&ex&&current">
  <div class="result-byline"><b>#{{current.id}} / {{current.name}}</b><span>{{r.input_snapshot.study.code}} · {{ex.piece_count}}片 × {{ex.layer_count}}层</span></div>
  <div class="result-totals paired-totals">
   <div><small>精确双侧 p（尾/总）</small><b class="p-value">{{ex.p_display}}</b></div>
   <div><small>总组合数 2^{{ex.total_combinations_bits}}</small><b class="bigint">{{ex.total_combinations}}</b></div>
   <div><small>尾部组合数（入双侧尾）</small><b class="bigint">{{ex.tail_combinations}}</b></div>
   <div><small>严格内部组合数</small><b class="bigint">{{ex.interior_combinations}}</b></div>
  </div>

  <div class="results-split">
   <section>
    <h2>各层配对率与阈值（逐片关联保留）</h2>
    <div class="table-wrap"><table class="paired-layer-table">
     <thead><tr><th>湿度层</th><th>A成功/片数</th><th>B成功/片数</th><th>A成功率</th><th>B成功率</th><th>率差 D（精确分数）</th><th>内部盒（严格，开区间）</th></tr></thead>
     <tbody>
      <tr v-for="o in ex.observed_layer_statistics" :key="o.code">
       <td>{{o.code}}<small>{{o.name}}</small></td>
       <td>{{o.a_success}}/{{ex.piece_count}}</td>
       <td>{{o.b_success}}/{{ex.piece_count}}</td>
       <td>{{rate(o.rate_a_numerator,o.rate_a_denominator)}}</td>
       <td>{{rate(o.rate_b_numerator,o.rate_b_denominator)}}</td>
       <td>{{fmt(o.difference,4)}}<small>{{o.difference_numerator}}/{{o.difference_denominator}}</small></td>
       <td><template v-for="t in ex.integer_thresholds.filter(x=>x.code===o.code)" :key="t.code">({{t.interior_lower_exclusive}}, {{t.interior_upper_exclusive}})<small>观察 S={{t.observed_s}}</small></template></td>
      </tr>
     </tbody>
    </table></div>
   </section>
   <aside class="evidence-note">
    <p class="eyebrow">EXACT / NO SIMULATION</p>
    <h2>{{ex.below_alpha?'达到预设探索阈值':'未达到预设探索阈值'}}</h2>
    <p>α = {{ex.alpha}}；最大绝对率差出现在 <b>{{ex.max_abs_layer}}</b>（{{fmt(ex.max_abs_difference,4)}}）。</p>
    <dl>
     <div><dt>活跃片 / 零向量片</dt><dd>{{ex.active_piece_count}} / {{ex.zero_vector_piece_count}}</dd></div>
     <div><dt>记忆状态 / 上限</dt><dd>{{ex.memo_states_used.toLocaleString()}} / {{ex.memo_state_cap.toLocaleString()}}</dd></div>
     <div><dt>预检状态上界</dt><dd>{{ex.preflight_state_bound.toLocaleString()}}</dd></div>
     <div><dt>尾+内 = 总</dt><dd>{{(BigInt(ex.tail_combinations)+BigInt(ex.interior_combinations)).toString(10)===ex.total_combinations?'成立':'不一致'}}</dd></div>
    </dl>
    <p>零向量片（每层两封装同成败）对所有配置贡献因子2，已剥离后乘回，不影响关联结构。</p>
   </aside>
  </div>

  <section class="distribution-sheet">
   <div class="section-heading"><h2>逐片冻结明细（可逐格核对）</h2><span>{{r.input_snapshot.pieces.length}}片 × {{r.input_snapshot.layers.length}}层</span></div>
   <details><summary>展开逐片 × 逐层 × 两种封装成败</summary>
    <div class="table-wrap exact-mass-table"><table class="paired-detail-table">
     <thead><tr><th>试片</th><th>来源</th><th v-for="l in r.input_snapshot.layers" :key="l.code">{{l.code}}<small>{{l.name}}</small></th></tr></thead>
     <tbody>
      <tr v-for="p in r.input_snapshot.pieces" :key="p.code">
       <td>{{p.code}}</td><td><small>{{p.source}}</small></td>
       <td v-for="c in p.cells" :key="c.layer_code"><span class="mini a">A:{{c.a_success?'成':'败'}}</span><span class="mini b">B:{{c.b_success?'成':'败'}}</span></td>
      </tr>
     </tbody>
    </table></div>
   </details>
  </section>

  <aside class="interpretation-boundary">
   <b>配对精确口径与边界</b>
   <p>{{r.interpretation}}</p>
   <p>{{ex.tail_rule}}</p>
   <p>{{ex.tie_handling}}</p>
   <p>{{ex.association}}</p>
   <RouterLink :to="'/paired-notes?run='+current.id">形成配对独立复验说明 →</RouterLink>
  </aside>
  <details class="fingerprint"><summary>冻结输入指纹与数值口径</summary>
   <code>{{r.fingerprint}}</code>
   <p>{{r.method_version}} / {{ex.numeric}}</p>
   <p>p = {{ex.p_numerator}} / {{ex.p_denominator}}；p log {{fmt(ex.p_log,10)}}{{ex.p_underflow?'；double 下溢，以科学计数文本与log保留':''}}。</p>
  </details>
 </template>
</template>
