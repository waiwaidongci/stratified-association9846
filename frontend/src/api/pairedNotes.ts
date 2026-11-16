import{request}from './client';import{download}from './client';import type{PairedNote}from '../types/domain';
export const list=()=>request<PairedNote[]>('/paired-notes');
export const create=(data:unknown)=>request<PairedNote>('/paired-notes',{method:'POST',body:JSON.stringify(data)});
export const review=(id:number,decision:string,comment:string)=>request<PairedNote>('/paired-notes/'+id+'/review',{method:'PATCH',body:JSON.stringify({decision,comment})});
export const exportNote=(id:number)=>download('/paired-notes/'+id+'/export','cenan-paired-observation-'+id+'.csv');
