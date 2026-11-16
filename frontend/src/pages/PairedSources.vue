<script setup lang="ts">
import{ref,reactive,onMounted,computed}from 'vue';
import{load}from '../stores/research';
import{paired,loadPaired,loadSnapshot}from '../stores/paired';
import{canEdit}from '../stores/auth';
import*as api from '../api/pairedStudies';
import{useTask}from '../hooks/useTask';
import PageHeading from '../components/common/PageHeading.vue';
import ErrorNotice from '../components/common/ErrorNotice.vue';
import type{PairedLayer,PairedPiece,PairedCell}from '../types/domain';

const selected=ref(0),notice=ref(''),{error,execute}=useTask();
const studyMeta=reactive({code:'CN-PAIR-NEW',name:'新配对复测研究',period:'2026-11',description:'同一试片在多个湿度层复测；封装标签按整片共同交换。'});
const layers=reactive([]as PairedLayer[]);
const pieces=reactive([]as PairedPiece[]);
const layerName=ref(''),newLayerCode=ref('');
const pieceCount=ref(60);

function blankCell(layer_code:string):PairedCell{return{layer_code,a_success:1,a_failure:0,b_success:1,b_failure:0};}
function blankPiece(i:number):PairedPiece{return{code:'P'+String(i+1).padStart(2,'0'),source:'CN_配对复测.csv',cells:layers.map(l=>blankCell(l.code))};}

function rebuildPieces(count:number){
 const keep=pieces.slice(0,count);
 while(keep.length<count)keep.push(blankPiece(keep.length));
 pieces.splice(0,pieces.length,...keep);
}
function addLayer(){
 const code=newLayerCode.value.trim().toUpperCase();
 if(!code||layers.some(l=>l.code===code)){notice.value='层编号为空或重复';return;}
 const seq=layers.length;
 layers.push({code,name:layerName.value||('湿度层'+(seq+1)),sequence:seq,description:'预先声明的复测湿度层'});
 newLayerCode.value='';layerName.value='';
 pieces.forEach(p=>p.cells.push(blankCell(code)));
}
function removeLayer(code:string){
 const idx=layers.findIndex(l=>l.code===code);if(idx<0)return;
 layers.splice(idx,1);layers.forEach((l,i)=>l.sequence=i);
 pieces.forEach(p=>{const j=p.cells.findIndex(c=>c.layer_code===code);if(j>=0)p.cells.splice(j,1);});
}
function setOutcome(cell:PairedCell,which:'a'|'b',success:number){
 if(which==='a'){cell.a_success=success;cell.a_failure=1-success;}
 else{cell.b_success=success;cell.b_failure=1-success;}
}

async function refresh(){
 if(!selected.value)return;
 const snap=await loadSnapshot(selected.value);
 layers.splice(0,layers.length,...snap.layers.map(l=>({...l})));
 pieces.splice(0,pieces.length,...snap.pieces.map(p=>({...p,cells:p.cells.map(c=>({...c}))})));
 pieceCount.value=pieces.length;
 Object.assign(studyMeta,{code:snap.study.code,name:snap.study.name,period:snap.study.period,description:snap.study.description});
}
async function chooseStudy(id:number){selected.value=id;await execute(refresh);}
onMounted(()=>execute(async()=>{await Promise.all([load(),loadPaired()]);selected.value=paired.studies[0]?.id||0;if(selected.value)await refresh();else rebuildPieces(pieceCount.value);}));

const valid=computed(()=>{
 if(!studyMeta.code||!studyMeta.name||!studyMeta.period)return false;
 if(layers.length<2||layers.length>8||pieces.length<1||pieces.length>60)return false;
 const codes=new Set(layers.map(l=>l.code));
 return pieces.every(p=>p.cells.length===codes.size&&p.cells.every(c=>
   c.a_success+c.a_failure===1&&c.b_success+c.b_failure===1));
});
function payload(){return{study:{...studyMeta},layers:layers.map(l=>({...l})),pieces:pieces.map(p=>({...p,cells:p.cells.map(c=>({...c}))}))};}
async function save(){await execute(async()=>{const snap=await api.replace(payload());notice.value='逐片明细已冻结保存；已有冻结计算的研究不可改写';await loadPaired();selected.value=(paired.studies.find(s=>s.code===studyMeta.code)?.id)||selected.value;});}
function onPieceCount(n:number){pieceCount.value=n;rebuildPieces(n);}
const aRate=(j:number)=>pieces.length?pieces.reduce((acc,p)=>acc+p.cells[j].a_success,0)/pieces.length:0;
const bRate=(j:number)=>pieces.length?pieces.reduce((acc,p)=>acc+p.cells[j].b_success,0)/pieces.length:0;
</script>

<template>
 <PageHeading index="07" title="同一片，各层一起换标签。" text="逐片录入每个湿度层两种封装成败；冻结后整片共同交换，跨层关联不再被四格汇总拆散。"/>
 <ErrorNotice :message="error" @retry="execute(refresh)"/>
 <p v-if="notice" role="status" class="success">{{notice}}</p>
 <div class="paired-head">
  <label>配对研究底稿
   <select :value="selected" @change="chooseStudy(Number(($event.target as HTMLSelectElement).value))">
    <option :value="0">＋ 新建配对研究</option>
    <option v-for="s in paired.studies" :key="s.id" :value="s.id">{{s.code}} {{s.name}}</option>
   </select>
  </label>
  <div class="paired-key"><b>A封装</b><span>成功1/失败0</span><b>B封装</b><span>成功1/失败0</span><p>每片每层每种封装恰一次成败记录。</p></div>
 </div>

 <form v-if="canEdit" class="paired-meta" @submit.prevent="save">
  <div class="four-counts">
   <label>研究编号<input v-model="studyMeta.code" pattern="[A-Z0-9-]+" required/></label>
   <label>研究名称<input v-model="studyMeta.name" required minlength="3"/></label>
   <label>试验期间<input v-model="studyMeta.period" required/></label>
   <label>试片数量<input type="number" min="1" max="60" step="1" :value="pieceCount" @change="onPieceCount(Number(($event.target as HTMLInputElement).value))"/></label>
  </div>
  <label>研究批注<textarea v-model="studyMeta.description" rows="2" maxlength="1600"></textarea></label>
  <div class="layer-builder">
   <div class="layer-chips"><span v-for="l in layers" :key="l.code" class="layer-chip">{{l.code}} {{l.name}}
     <button type="button" class="text-button" @click="removeLayer(l.code)">✕</button></span></div>
   <div class="layer-add">
    <input v-model="newLayerCode" placeholder="层编号 H1" pattern="[A-Z0-9-]+"/>
    <input v-model="layerName" placeholder="层名称 低湿度层"/>
    <button type="button" class="outline" @click="addLayer" :disabled="layers.length>=8">添加湿度层（{{layers.length}}/8）</button>
   </div>
  </div>

  <div class="table-wrap paired-matrix-wrap">
   <table class="paired-matrix">
    <thead><tr><th>试片</th><th>来源</th><th v-for="(l,j) in layers" :key="l.code">
     {{l.code}}<small>{{l.name}}</small><small>A率 {{(aRate(j)*100).toFixed(1)}}% / B率 {{(bRate(j)*100).toFixed(1)}}%</small>
    </th></tr></thead>
    <tbody>
     <tr v-for="p in pieces" :key="p.code">
      <td><input v-model="p.code" class="cell-code" aria-label="试片编号"/></td>
      <td><input v-model="p.source" class="cell-source" aria-label="来源"/></td>
      <td v-for="c in p.cells" :key="c.layer_code" class="pair-cell">
       <div class="outcome"><span>A</span>
        <button type="button" :class="{on:c.a_success===1}" @click="setOutcome(c,'a',1)">成</button>
        <button type="button" :class="{on:c.a_success===0}" @click="setOutcome(c,'a',0)">败</button></div>
       <div class="outcome"><span>B</span>
        <button type="button" :class="{on:c.b_success===1}" @click="setOutcome(c,'b',1)">成</button>
        <button type="button" :class="{on:c.b_success===0}" @click="setOutcome(c,'b',0)">败</button></div>
      </td>
     </tr>
    </tbody>
   </table>
  </div>
  <p class="margin-note">提交即冻结逐片明细（{{pieces.length}}片 × {{layers.length}}层 × 两种封装）。冻结计算后该研究明细不可改写；整体写入保证片内各层关联不丢失。</p>
  <button class="primary" :disabled="!valid">保存并冻结逐片明细 →</button>
 </form>
 <div v-else class="empty">研究阅读者为只读；逐片明细请由分析员录入。</div>
</template>
