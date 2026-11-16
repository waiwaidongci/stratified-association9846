import{request}from './client';import type{PairedRun}from '../types/domain';
export const list=()=>request<PairedRun[]>('/paired-runs');
export const detail=(id:number)=>request<PairedRun>('/paired-runs/'+id);
export const create=(data:unknown)=>request<PairedRun>('/paired-runs',{method:'POST',body:JSON.stringify(data)});
