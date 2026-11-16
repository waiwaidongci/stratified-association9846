import{request}from './client';import type{PairedStudy,PairedSnapshot}from '../types/domain';
export const list=()=>request<PairedStudy[]>('/paired-studies');
export const snapshot=(id:number)=>request<PairedSnapshot>('/paired-studies/'+id+'/snapshot');
export const replace=(data:unknown)=>request<PairedSnapshot>('/paired-studies',{method:'PUT',body:JSON.stringify(data)});
