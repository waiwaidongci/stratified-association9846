import{reactive}from 'vue';import type{PairedStudy,PairedRun,PairedNote,PairedSnapshot}from '../types/domain';import*as studies from '../api/pairedStudies';import*as runs from '../api/pairedRuns';import*as notes from '../api/pairedNotes';
export const paired=reactive({studies:[]as PairedStudy[],runs:[]as PairedRun[],notes:[]as PairedNote[],snapshots:{}as Record<number,PairedSnapshot>});
export async function loadPaired(){const[s,r,n]=await Promise.all([studies.list(),runs.list(),notes.list()]);paired.studies=s;paired.runs=r;paired.notes=n;}
export async function loadSnapshot(id:number){paired.snapshots[id]=await studies.snapshot(id);return paired.snapshots[id];}
