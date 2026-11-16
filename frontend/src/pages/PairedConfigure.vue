<script setup lang="ts">
import{ref,onMounted}from 'vue';
import{useRouter}from 'vue-router';
import{paired,loadPaired,loadSnapshot}from '../stores/paired';
import{canEdit}from '../stores/auth';
import*as runs from '../api/pairedRuns';
import{useTask}from '../hooks/useTask';
import{usePolling}from '../hooks/usePolling';
import PageHeading from '../components/common/PageHeading.vue';
import ErrorNotice from '../components/common/ErrorNotice.vue';
import StatusBadge from '../components/common/StatusBadge.vue';
const selected=ref(0),name=ref('配对复测 · 整片交换精确核对'),alpha=ref(.05),layerCount=ref(0),pieceCount=ref(0),router=useRouter(),{error,busy,execute}=useTask();
function totalCombinations(n:number):string{return(BigInt(2)**BigInt(n)).toString(10);}
onMounted(()=>execute(async()=>{await loadPaired();selected.value=paired.studies[0]?.id||0;await syncMeta();}));
usePolling(()=>{if(paired.runs.some(r=>['queued','running'].includes(r.status)))execute(loadPaired)});
async function syncMeta(){if(!selected.value){layerCount.value=0;pieceCount.value=0;return;}const snap=await loadSnapshot(selected.value);layerCount.value=snap.layers.length;pieceCount.value=snap.pieces.length;}
function choose(id:number){selected.value=id;execute(syncMeta);}
function submit(){execute(async()=>{const r=await runs.create({name:name.value,study_id:selected.value,alpha:alpha.value});await loadPaired();router.push('/paired-results?run='+r.id)});}
</script>
<template>
 <PageHeading index="08" title="整片交换，再数证据。" text="零假设下每片在全部湿度层共同交换封装标签，共2^N个等可能配置；精确双侧保留跨层关联与并列，不模拟、不逐层独立。"/>
 <ErrorNotice :message="error" @retry="execute(syncMeta)"/>
 <div class="configure-grid">
  <form v-if="canEdit" @submit.prevent="submit">
   <label>配对研究
    <select :value="selected" @change="choose(Number(($event.target as HTMLSelectElement).value))">
     <option v-for="s in paired.studies" :key="s.id" :value="s.id">{{s.code}} {{s.name}}</option>
    </select>
   </label>
   <p class="margin-note" v-if="selected">已冻结底稿：{{pieceCount}}片 × {{layerCount}}层；总配置数将为 2^{{pieceCount}} = {{totalCombinations(pieceCount)}}。</p>
   <label>研究名称<input v-model="name" minlength="3" maxlength="160" required/></label>
   <label>预设探索阈值 alpha<input v-model.number="alpha" type="number" min=".001" max=".1" step=".001" required/></label>
   <p class="margin-note">内存预算约1 GiB：精确枚举预估或实际超限时任务明确失败，绝不回退到模拟或逐层独立近似。</p>
   <button class="primary" :disabled="busy||!selected">冻结并送入配对计算队列 →</button>
  </form>
  <aside>
   <p class="eyebrow">WHOLE-PIECE LABEL SWAP</p>
   <h2>关联留在片内。</h2>
   <p>交换作用于整片：同一试片在全部湿度层的封装标签一起翻转，跨层相关结构被完整保留。</p>
   <p>统计量 T = max_j |D_j|（各层配对率差绝对值的最大者）；任一层达到或超过其观察距离即入双侧尾，等距并列入尾。</p>
   <p>纯整数精确计数与有理数比较；输出尾部组合数、内部组合数与总组合数，可逐格核对。</p>
  </aside>
 </div>
 <section class="run-ledger">
  <h2>配对研究队列</h2>
  <article v-for="r in paired.runs" :key="r.id">
   <div><span>#{{r.id}}</span><h3>{{r.name}}</h3><small>底稿{{r.study_id}} · α{{r.alpha}}</small></div>
   <StatusBadge :status="r.status"/>
   <RouterLink :to="'/paired-results?run='+r.id">读取配对冻结研究 ↗</RouterLink>
  </article>
 </section>
</template>
