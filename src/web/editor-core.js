/* Pure source-time editing and review rules. Shared by the workspace and tests. */
(function(root,factory){const api=factory();if(typeof module==='object')module.exports=api;else root.MelodyEdits=api;})(globalThis,()=>{
  'use strict';
  const clone=v=>JSON.parse(JSON.stringify(v));
  const clamp=(x,a,b)=>Math.max(a,Math.min(b,x));
  const hz=p=>440*2**((p-69)/12);
  const names=['C','C♯','D','D♯','E','F','F♯','G','G♯','A','A♯','B'];
  function pitchName(p){const q=Math.round(p),cents=(p-q)*100;return `${names[((q%12)+12)%12]}${Math.floor(q/12)-1}${Math.abs(cents)>.05?` ${cents>0?'+':''}${cents.toFixed(1)}¢`:''}`;}
  function validate(notes,bounds){
    const ns=[...notes].sort((a,b)=>a.start-b.start);const ids=new Set();
    for(let i=0;i<ns.length;i++){
      const n=ns[i];if(ids.has(n.id))throw Error('Duplicate note ID');ids.add(n.id);
      if(![n.start,n.end,n.pitch].every(Number.isFinite)||n.start<bounds[0]-1e-9||n.end>bounds[1]+1e-9||n.end-n.start<1e-9||n.pitch<0||n.pitch>127)throw Error('Keep notes inside the source excerpt with positive duration.');
      if(i&&n.start<ns[i-1].end-1e-6)throw Error('Notes cannot overlap. Resize a neighbour first.');
    }
    return ns;
  }
  const touched=n=>({...n,duration:n.end-n.start,flags:[...new Set([...(n.flags||[]),'human_corrected'])]});
  function lowerBound(values,value){let a=0,b=values.length;while(a<b){const m=(a+b)>>1;if(values[m]<value)a=m+1;else b=m;}return a;}
  function move(notes,ids,dt,dp,bounds){
    const selected=notes.filter(n=>ids.has(n.id));if(!selected.length)return clone(notes);
    let lo=bounds[0]-Math.min(...selected.map(n=>n.start)),hi=bounds[1]-Math.max(...selected.map(n=>n.end));
    for(const n of selected)for(const other of notes){if(ids.has(other.id))continue;
      if(other.end<=n.start+1e-6)lo=Math.max(lo,other.end-n.start);
      if(other.start>=n.end-1e-6)hi=Math.min(hi,other.start-n.end);
    }
    dt=clamp(dt,lo,hi);dp=clamp(dp,-Math.min(...selected.map(n=>n.pitch)),127-Math.max(...selected.map(n=>n.pitch)));
    return validate(notes.map(n=>ids.has(n.id)?touched({...n,start:n.start+dt,end:n.end+dt,pitch:n.pitch+dp}):clone(n)),bounds);
  }
  function resize(notes,id,edge,time,bounds){
    const ns=clone(notes).sort((a,b)=>a.start-b.start),i=ns.findIndex(n=>n.id===id);if(i<0)return ns;
    const n=ns[i],epsilon=.000001;
    if(edge==='start')n.start=clamp(time,i?ns[i-1].end:bounds[0],n.end-epsilon);
    else n.end=clamp(time,n.start+epsilon,i+1<ns.length?ns[i+1].start:bounds[1]);
    ns[i]=touched(n);return validate(ns,bounds);
  }
  function add(notes,start,end,pitch,bounds,id){
    if(end<start)[start,end]=[end,start];start=clamp(start,...bounds);end=clamp(end,...bounds);
    const n=touched({id,start,end,pitch:clamp(pitch,0,127),confidence:1,phrase:0,frame_start:0,frame_end:0,flags:['human_inserted']});
    return validate([...clone(notes),n],bounds);
  }
  function split(notes,ids,t,bounds,id){
    const i=notes.findIndex(n=>n.start<t&&t<n.end&&(!ids.size||ids.has(n.id)));if(i<0)throw Error('Place the playhead inside the selected note.');
    const ns=clone(notes),n=ns[i];ns.splice(i,1,touched({...n,end:t}),touched({...n,id,start:t}));return validate(ns,bounds);
  }
  function merge(notes,ids,bounds){
    const ns=clone(notes).sort((a,b)=>a.start-b.start),indices=ns.flatMap((n,i)=>ids.has(n.id)?[i]:[]);
    if(indices.length<2||indices.at(-1)-indices[0]+1!==indices.length)throw Error('Select adjacent notes to merge.');
    const selected=indices.map(i=>ns[i]);
    if(Math.max(...selected.map(n=>n.pitch))-Math.min(...selected.map(n=>n.pitch))>1)throw Error('Merge expects compatible pitches within one semitone. Change pitch first if these are fragments.');
    const duration=selected.reduce((s,n)=>s+n.end-n.start,0);
    const pitch=selected.reduce((s,n)=>s+n.pitch*(n.end-n.start),0)/duration;
    ns.splice(indices[0],indices.length,touched({...selected[0],end:selected.at(-1).end,pitch}));return validate(ns,bounds);
  }
  class History{
    constructor(limit=100){this.undo=[];this.redo=[];this.limit=limit;}
    push(value){this.undo.push(clone(value));if(this.undo.length>this.limit)this.undo.shift();this.redo=[];}
    back(value){if(!this.undo.length)return null;this.redo.push(clone(value));return this.undo.pop();}
    forward(value){if(!this.redo.length)return null;this.undo.push(clone(value));return this.redo.pop();}
    clear(){this.undo=[];this.redo=[];}
  }
  function reviewQueue(notes,track,alternatives=[]){
    const queue=[];
    for(let j=0;j<notes.length;j++){
      const n=notes[j],reasons=[];let priority=0;
      const frames=[];if(track?.times)for(let i=lowerBound(track.times,n.start),end=lowerBound(track.times,n.end);i<end;i++)frames.push(i);
      const ps=frames.filter(i=>track.voiced[i]&&track.f0_hz[i]).map(i=>69+12*Math.log2(track.f0_hz[i]/440));
      const confidences=frames.map(i=>track.confidence[i]).filter(Number.isFinite);
      if(n.flags?.includes('confidence_unavailable')){reasons.push('Note-model correctness confidence unavailable');priority+=1;}
      if(confidences.length&&confidences.reduce((a,b)=>a+b,0)/confidences.length<.35){reasons.push('Low mean F0/voicing confidence (<0.35)');priority+=2;}
      if(!frames.length||!ps.length){reasons.push('No reliable voiced contour inside event');priority+=3;}
      if(ps.length>3){const sorted=[...ps].sort((a,b)=>a-b);if(sorted[Math.floor(.9*sorted.length)]-sorted[Math.floor(.1*sorted.length)]>1.5){reasons.push('Wide F0 spread (>150 cents): inspect bend/vibrato/instability');priority+=2;}}
      const before=notes[j-1],after=notes[j+1];
      if(before&&Math.abs(n.pitch-before.pitch)>=11.5){reasons.push('Large transition (≥11.5 semitones): possible octave error or genuine leap');priority+=3;}
      if(n.end-n.start<.12){reasons.push('Short event (<120 ms): possible fragment or expressive target');priority+=2;}
      if(before&&Math.abs(n.pitch-before.pitch)<.5&&n.start-before.end<.08){reasons.push('Adjacent repeated pitch: inspect separate attack versus fragmentation');priority+=2;}
      if(n.end-n.start>.5&&ps.length>4){let changes=0;for(let k=1;k<ps.length;k++)if(Math.abs(ps[k]-ps[k-1])>.7)changes++;
        if(changes>2){reasons.push('Multiple contour transitions inside one event: inspect missing boundaries/possible melisma; lyric confirmation required');priority+=2;}}
      if(after&&after.start-n.end<.02&&Math.abs(after.pitch-n.pitch)>.5){reasons.push('Legato boundary: inspect onset/offset without silence');priority+=1;}
      for(const alternative of alternatives){
        const overlapping=alternative.notes.filter(a=>a.start<n.end&&a.end>n.start);
        const best=overlapping.sort((a,b)=>Math.abs(a.start-n.start)-Math.abs(b.start-n.start))[0];
        if(!best||Math.abs(best.pitch-n.pitch)>.5||Math.abs(best.start-n.start)>.05||Math.abs(best.end-n.end)>.08){
          reasons.push(`Disagreement with ${alternative.name}: pitch >50c or boundary >50/80ms, or missing event`);priority+=3;
        }
      }
      if(reasons.length)queue.push({note_id:n.id,start:n.start,end:n.end,priority,reasons,confirmed:n.flags?.includes('review_confirmed')||false});
    }
    const missing=[];
    for(const alternative of alternatives)for(const n of alternative.notes){
      const duration=n.end-n.start;if(duration<=0)continue;
      const covered=notes.some(a=>Math.max(0,Math.min(a.end,n.end)-Math.max(a.start,n.start))>=duration*.25);
      if(!covered&&!missing.some(r=>Math.abs(r.start-n.start)<.05&&Math.abs(r.end-n.end)<.08)){
        missing.push({note_id:null,start:n.start,end:n.end,priority:3,confirmed:false,
          reasons:[`Possible missing event: ${alternative.name} has a note here; current edition overlaps less than 25%. Listen before adding.`]});
      }
    }
    return [...queue,...missing].sort((a,b)=>b.priority-a.priority||a.start-b.start);
  }
  function segment(note,pre,post,duration){return [Math.max(0,note.start-pre),Math.min(duration,note.end+post)];}
  return {clone,clamp,hz,pitchName,validate,move,resize,add,split,merge,History,reviewQueue,segment};
});
