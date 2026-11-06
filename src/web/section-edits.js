/* Pure transactional section edits; source seconds and stable IDs are preserved. */
(function(root){
 const EPS=1e-6,SNAP=.03,clone=v=>JSON.parse(JSON.stringify(v));
 function valid(s,duration){if(!s.id||![s.start,s.end].every(Number.isFinite)||s.start<0||s.end>duration||s.end-s.start<.000001)throw Error('Enter positive section bounds inside the source recording.');}
 const overlap=(a,b)=>a.start<b.end-EPS&&b.start<a.end-EPS;
 function name(type,sections,id){const title=type[0].toUpperCase()+type.slice(1);let count=0,highest=0;for(const s of sections)if(s.id!==id&&s.type===type){count++;const m=String(s.name||'').match(new RegExp('^'+title+' (\\d+)$','i'));if(m)highest=Math.max(highest,+m[1]);}return title+' '+(Math.max(count,highest)+1);}
 function plan(sections,candidate,duration,{resolution=null,shared=false}={}){
  let rows=clone(sections),s=clone(candidate),old=rows.find(o=>o.id===s.id);valid(s,duration);
  const others=rows.filter(o=>o.id!==s.id);s.layer=s.layer||'structure';
  if(shared&&old&&(old.layer||'structure')==='structure'&&s.layer==='structure'){for(const edge of ['start','end']){const opposite=edge==='start'?'end':'start';if(s[edge]!==old[edge])for(const o of others)if((o.layer||'structure')==='structure'&&Math.abs(o[opposite]-old[edge])<=EPS){o[opposite]=s[edge];valid(o,duration);}}}
  if(s.layer==='structure')for(const o of others.filter(o=>(o.layer||'structure')==='structure')){if(Math.abs(s.start-o.end)<=SNAP)s.start=o.end;if(Math.abs(s.end-o.start)<=SNAP)s.end=o.start;}
  valid(s,duration);const conflicts=others.filter(o=>(o.layer||'structure')==='structure'&&s.layer==='structure'&&overlap(o,s));
  if(conflicts.length&&!resolution)return {conflicts,candidate:s};
  if(resolution==='analysis'){s.layer='analysis';s.overlap_policy='allow';}
  if(s.layer==='analysis')s.overlap_policy='allow';
  if(resolution==='shared'){
   if(conflicts.length!==1)throw Error('Choose one adjacent neighbour for a shared boundary, or keep an analytical overlap.');
   const o=conflicts[0];if(s.start>o.start&&s.end>=o.end)o.end=s.start;else if(s.end<o.end&&s.start<=o.start)o.start=s.end;else throw Error('A nested region has two boundaries. Keep an analytical overlap or explicitly trim the existing section.');valid(o,duration);
  }
  if(resolution==='trim'){
   rows=others.flatMap(o=>{if(!conflicts.includes(o))return [o];const parts=[];if(o.start<s.start)parts.push({...o,end:s.start});if(o.end>s.end)parts.push({...o,start:s.end,id:parts.length?crypto.randomUUID():o.id,...(parts.length?{derived_from:o.id}: {})});return parts;});
  }else rows=others;
  rows.push(s);const structural=rows.filter(o=>(o.layer||'structure')==='structure').sort((a,b)=>a.start-b.start);
  for(let i=0;i<structural.length;i++)for(let j=i+1;j<structural.length;j++)if(overlap(structural[i],structural[j]))throw Error('Shared boundary would overlap another structural section.');
  rows.forEach(o=>valid(o,duration));return {rows:rows.sort((a,b)=>a.start-b.start||a.end-b.end||a.id.localeCompare(b.id)),candidate:s,conflicts:[]};
 }
 const api={EPS,SNAP,overlap,name,plan};root.SectionEdits=api;if(typeof module!=='undefined')module.exports=api;
})(typeof window==='undefined'?globalThis:window);
