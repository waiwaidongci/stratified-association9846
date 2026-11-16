<script setup lang="ts">
import{ref,onMounted}from 'vue';
import{useRoute}from 'vue-router';
import{paired,loadPaired}from '../stores/paired';
import{canEdit,isAdmin}from '../stores/auth';
import*as notes from '../api/pairedNotes';
import{useTask}from '../hooks/useTask';
import PageHeading from '../components/common/PageHeading.vue';
import ErrorNotice from '../components/common/ErrorNotice.vue';
import StatusBadge from '../components/common/StatusBadge.vue';
const route=useRoute(),run=ref(Number(route.query.run)||0),title=ref('配对复测整片交换复验说明'),
 interpretation=ref('核对整片共同交换下的精确双侧证据：尾部/内部/总组合数与逐片冻结明细，确认跨层关联与等距并列已保留，未使用模拟或逐层独立近似。'),
 action=ref('保持按整片交换的配对设计，补充同片多湿度层复测并逐格记录两种封装成败。'),
 comment=ref('配对精确双侧定义、组合数恒等与逐片明细已核对，按预设方案开展独立复验。'),
 notice=ref(''),{error,execute}=useTask();
onMounted(()=>execute(async()=>{await loadPaired();run.value=run.value||paired.runs.find(r=>r.status==='completed')?.id||0;}));
function create(){execute(async()=>{await notes.create({title:title.value,run_id:run.value,interpretation:interpretation.value,action:action.value});notice.value='配对复验说明已建立，等待负责人审阅';await loadPaired();});}
function review(id:number,decision:string){execute(async()=>{await notes.review(id,decision,comment.value);await loadPaired();notice.value='审阅状态已保存';});}
function exportNote(id:number){execute(()=>notes.exportNote(id));}
</script>
<template>
 <PageHeading index="10" title="配对证据，落到独立复验。" text="研究员起草、负责人审阅、阅读者仅下载已批准说明；导出附尾部/总组合数、逐层阈值与逐片冻结明细及指纹。"/>
 <ErrorNotice :message="error" @retry="execute(loadPaired)"/>
 <p v-if="notice" class="success" role="status">{{notice}}</p>
 <div class="notes-layout">
  <form v-if="canEdit" @submit.prevent="create">
   <p class="eyebrow">NEW PAIRED VERIFICATION NOTE</p>
   <label>关联配对研究
    <select v-model="run" aria-label="关联配对研究">
     <option v-for="x in paired.runs.filter(x=>x.status==='completed')" :key="x.id" :value="x.id">#{{x.id}} {{x.name}}</option>
    </select>
   </label>
   <label>说明名称<input v-model="title" required minlength="3"/></label>
   <label>复验解释<textarea v-model="interpretation" rows="5" required minlength="8"></textarea></label>
   <label>复验动作<textarea v-model="action" rows="4" required minlength="5"></textarea></label>
   <button class="primary" :disabled="!run">保存配对复验说明 →</button>
  </form>
  <section>
   <div class="section-title"><h2>配对复验档案</h2><span>{{paired.notes.length}}份</span></div>
   <label v-if="isAdmin">审阅意见<textarea v-model="comment" rows="2"></textarea></label>
   <article v-for="n in paired.notes" class="observation-note" :key="n.id">
    <div><p class="eyebrow">NOTE {{n.id}} / PAIRED RUN {{n.run_id}}</p><StatusBadge :status="n.status"/></div>
    <h2>{{n.title}}</h2><p>{{n.interpretation}}</p><p class="action-note">{{n.action}}</p>
    <p v-if="n.review_comment" class="review-comment">{{n.approved_by}} · {{n.review_comment}}</p>
    <div class="actions">
     <button v-if="isAdmin&&n.status==='draft'" class="primary" @click="review(n.id,'approved')">批准说明</button>
     <button v-if="isAdmin&&n.status==='draft'" class="outline" @click="review(n.id,'rejected')">退回</button>
     <button v-if="n.status==='approved'" class="outline" @click="exportNote(n.id)">下载获批CSV ↗</button>
    </div>
   </article>
  </section>
 </div>
</template>
