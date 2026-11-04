"use strict";
const $ = id => document.getElementById(id);
const state = {library: [], recordings:[], selected: new Set(), id: null, report: null, notes: [], checked: new Set(),
  alternative: null, profile: null, exercise: null, recording: null, reference:null};
const copy = value => JSON.parse(JSON.stringify(value));
let pianoEditor=null;
let recordingLibrary=null;
function element(tag, text, cls) {const e=document.createElement(tag); if(text!==undefined)e.textContent=text; if(cls)e.className=cls; return e;}
function status(text, error=false) {$('status').textContent=text; $('status').classList.toggle('error',error);}
async function api(path, data) {
  const response=await fetch('/api/'+path, data===undefined?{}:{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(data)});
  const result=await response.json(); if(!response.ok)throw new Error(result.error||'Request failed'); return result;
}
async function run(action) {try {await action();} catch(e) {status(e.message,true); console.error(e);}}
function tab(name) {document.querySelectorAll('.panel').forEach(e=>e.classList.toggle('hidden',e.id!==name));document.querySelectorAll('.tab').forEach(e=>e.classList.toggle('active',e.dataset.tab===name));draw();}
document.querySelectorAll('.tab').forEach(e=>e.onclick=()=>tab(e.dataset.tab));
function config() {return {estimator:$('estimator').value,fmin:+$('fmin').value,fmax:+$('fmax').value,
  confidence:+$('confidence').value,min_note_seconds:+$('minnote').value,transition_seconds:+$('hold').value,input_kind:$('kind').value};}
async function refresh() {
  const result=await api('state');state.library=result.analyses;state.recordings=result.recordings||[];
  recordingLibrary?.refreshFilters();renderLibrary();status(`${state.recordings.length} recordings · ${state.library.length} preserved analysis versions · corpus inclusion is explicit`);
}
function renderLibrary() {
  recordingLibrary?.render();
}
async function importAudio(file, attempt=false) {
  status(`Importing ${file.name}…`);
  const response=await fetch('/api/import?name='+encodeURIComponent(file.name),{method:'POST',headers:{'Content-Type':'application/octet-stream'},body:file});
  const upload=await response.json(); if(!response.ok)throw new Error(upload.error);
  status(`Analyzing ${file.name} with ${$('estimator').value}. CPU inference may take a few minutes…`);
  const result=await api('analyze',{upload_id:upload.upload_id,config:config(),metadata:{song:file.name,
    artist:$('artist').value,section:attempt?'practice':$('section').value,tags:attempt?['practice-attempt']:[]}});
  if(!attempt)state.selected.add(result.report.audio.content_sha256);await refresh();await load(result.id);
  if(attempt && state.exercise) {
    const feedback=await api('attempt',{id:result.id,exercise:state.exercise});$('feedback').textContent=JSON.stringify(feedback,null,2);tab('compose');
    status('Attempt recorded and transcribed. Constraint feedback is available; review the notes for transcription errors.');
  }
  return result;
}
$('files').onchange=()=>run(async()=>{for(const file of $('files').files)await importAudio(file);$('files').value='';});
$('attemptfile').onchange=()=>run(async()=>{if($('attemptfile').files[0])await importAudio($('attemptfile').files[0],true);});
$('refresh').onclick=()=>run(refresh);
async function load(id) {
  if(pianoEditor?.dirty&&!confirm('Discard unsaved edits before changing recordings?'))return false;
  pianoEditor?.stashView();
  pianoEditor?.audition.stop();
  const token=(state.loadToken||0)+1;state.loadToken=token;const report=await api('report?id='+encodeURIComponent(id));if(state.loadToken!==token)return false;
  state.id=id;state.report=report;state.notes=copy(state.report.notes);state.checked.clear();state.alternative=null;state.reference=null;
  const r=state.report;$('title').textContent=r.metadata.song||r.audio.source_path.split(/[\\/]/).pop();
  $('sourceinfo').textContent=`${r.audio.duration.toFixed(3)} s · source ${r.audio.original_sample_rate} Hz / ${r.audio.channels} channels · ${r.raw_pitch.model} → ${r.provenance.note_model.name} · ${r.provenance.correction_revision?'human revision active':'model prediction; review before interpretation'}`;
  $('audio').src='/api/source-audio?id='+encodeURIComponent(id);$('loopstart').value=0;$('loopend').value=r.audio.duration;$('loop').checked=false;$('viewstart').value=0;
  $('alternative').replaceChildren(new Option('None',''));
  state.library.filter(other=>other.id!==id && other.audio.content_sha256===r.audio.content_sha256).forEach(other=>$('alternative').add(new Option((other.estimator||'F0')+' → '+other.model.name+' / '+other.prediction_id.slice(0,8),other.id)));
  $('exports').replaceChildren();for(const [type,label] of [['midi','MIDI'],['csv','CSV'],['json','JSON']]) {
    const a=element('a',label,'download');a.href='/api/download?id='+id+'&type='+type;a.dataset.exportType=type;a.dataset.workingHref=a.href;$('exports').append(a);
  }
  $('provenance').textContent=JSON.stringify({provenance:r.provenance,warnings:r.warnings,flags:r.processed_pitch.flags},null,2);
  pianoEditor?.loaded();
  await refreshReferences();if(state.loadToken!==token)return false;referenceModeStatus();renderMetadata();renderNotes();renderLibrary();draw();tab('review');status('Audio, contour and note events are aligned in source seconds.');return true;
}
function renderMetadata() {
  $('metadata').replaceChildren();for(const key of ['artist','song','section','tempo','key','mode','language','genre','tags']) {
    const label=element('label',key);const input=element('input');input.id='meta-'+key;const value=state.report.metadata[key];input.value=Array.isArray(value)?value.join(', '):value??'';label.append(input);$('metadata').append(label);
  }
}
$('savemeta').onclick=()=>run(async()=>{
  if(!state.id)return;const metadata={};for(const key of ['artist','song','section','tempo','key','mode','language','genre','tags'])metadata[key]=key==='tags'?$('meta-'+key).value.split(',').map(s=>s.trim()).filter(Boolean):$('meta-'+key).value;
  state.report=await api('metadata',{id:state.id,metadata});await refresh();status('Recording metadata saved.');
});
function remember() {pianoEditor?.remember();}
function renderNotes() {
  $('notes').replaceChildren();state.notes.forEach((n,i)=>{
    const row=element('tr',undefined,state.checked.has(n.id)?'selected':'');const td=element('td');const check=element('input');check.type='checkbox';check.checked=state.checked.has(n.id);
    check.onchange=()=>{check.checked?state.checked.add(n.id):state.checked.delete(n.id);row.classList.toggle('selected',check.checked);draw();};td.append(check);row.append(td,element('td',i+1));
    for(const key of ['start','end','pitch','phrase']) {
      const cell=element('td');const input=element('input');input.type='number';input.step=key==='phrase'?1:.001;input.value=+n[key].toFixed(6);input.setAttribute('aria-label',`Note ${i+1} ${key}`);
      input.disabled=state.reference?.origin.kind==='published_human_dataset';
      let changing=false;
      const update=()=>{if(!changing){remember();changing=true;}n[key]=+input.value;n.duration=n.end-n.start;n.confidence=1;n.flags=['human_corrected'];draw();status('Unsaved edit. Boundaries and overlaps will be validated on save.');};
      input.oninput=update;input.onchange=()=>{update();changing=false;};cell.append(input);row.append(cell);
    }
    row.append(element('td',n.confidence.toFixed(2)),element('td',n.flags.join(', ')));$('notes').append(row);
  });
  pianoEditor?.render();
}
// All note-edit commands share MelodyEditor / MelodyEdits. Save keeps the existing API.
$('save').onclick=()=>run(async()=>{if(!state.id)return;if(state.reference){await saveReference();return;}state.report=await api('correct',{id:state.id,notes:state.notes,base_revision:state.report.provenance.correction_revision??null});state.notes=copy(state.report.notes);pianoEditor?.resetHistory();renderNotes();draw();await refresh();await pianoEditor?.revisions();status('Correction revision saved. Raw predictions and earlier revisions are preserved.');});
$('raw').onclick=()=>{if(state.report){pianoEditor?.openPanel('research');$('provenance').textContent=JSON.stringify({predicted_notes:state.report.predicted_notes,provenance:state.report.provenance},null,2);$('provenance').parentElement.open=true;$('provenance').scrollIntoView({behavior:'smooth'});}};
$('alternative').onchange=()=>run(async()=>{state.alternative=$('alternative').value?await api('report?id='+$('alternative').value):null;draw();});
['viewstart','viewlength'].forEach(id=>$(id).onchange=draw);
let geometry=null;
function drawTimeline(canvas,report,notes,playhead=0,windowStart=0,windowLength=null,alternative=null,reference=null) {
  if(!report||!canvas.clientWidth)return;
  const dpr=window.devicePixelRatio||1;const width=canvas.clientWidth,height=canvas.id==='timeline'?380:180;canvas.width=width*dpr;canvas.height=height*dpr;
  const ctx=canvas.getContext('2d');ctx.scale(dpr,dpr);ctx.clearRect(0,0,width,height);
  const start=Math.max(0,windowStart);const end=Math.min(report.audio.duration,start+(windowLength||report.audio.duration));if(end<=start)return;
  const all=notes.map(n=>n.pitch);if(report.raw_pitch)report.raw_pitch.f0_hz.forEach((f,i)=>{if(f&&report.raw_pitch.times[i]>=start&&report.raw_pitch.times[i]<=end)all.push(69+12*Math.log2(f/440));});const low=Math.min(60,...all)-2,high=Math.max(72,...all)+2;const top=canvas.id==='timeline'?100:15,bottom=height-30,left=43;
  const x=t=>left+(t-start)/(end-start)*(width-left-12);const y=p=>bottom-(p-low)/(high-low)*(bottom-top);
  ctx.font='10px system-ui';ctx.lineWidth=1;
  for(let p=Math.ceil(low);p<=high;p++) {ctx.strokeStyle=p%12===0?'#3a484b':'#243034';ctx.beginPath();ctx.moveTo(left,y(p));ctx.lineTo(width-10,y(p));ctx.stroke();if(p%2===0){ctx.fillStyle='#8ea09d';ctx.fillText(p,12,y(p)+3);}}
  const tick=Math.max(.5,Math.ceil((end-start)/10));for(let t=Math.ceil(start/tick)*tick;t<=end;t+=tick){ctx.strokeStyle='#263438';ctx.beginPath();ctx.moveTo(x(t),top);ctx.lineTo(x(t),bottom);ctx.stroke();ctx.fillStyle='#8ea09d';ctx.fillText(t.toFixed(1)+'s',x(t)-10,height-9);}
  ctx.save();ctx.beginPath();ctx.rect(left,0,width-left-10,bottom+1);ctx.clip();
  if(report.waveform && canvas.id==='timeline') {
    const w=report.waveform;ctx.strokeStyle='#617876';for(let i=0;i<w.min.length;i++){const t=i*w.hop_seconds;if(t<start||t>end)continue;ctx.beginPath();ctx.moveTo(x(t),43-w.max[i]*32);ctx.lineTo(x(t),43-w.min[i]*32);ctx.stroke();}
  }
  function drawNotes(ns,color) {for(const n of ns){if(n.end<start||n.start>end)continue;ctx.fillStyle=color||(state.checked.has(n.id)?'#d1e4aa':n.flags.length||n.confidence<.6?'#d9a16b':'#65aac2');ctx.globalAlpha=color?.55:.65;ctx.fillRect(x(n.start),y(n.pitch)-5,Math.max(2,x(n.end)-x(n.start)),10);ctx.globalAlpha=1;}}
  if(alternative)drawNotes(alternative.predicted_notes,'#adb3b0');
  if(reference){drawNotes(report.predicted_notes,'#e28373');drawNotes(notes,'#93d6a6');
    for(const region of reference.regions||[]){if(region.kind==='uncertain'){ctx.fillStyle='#e2bd7040';ctx.fillRect(x(region.start),top,x(region.end)-x(region.start),bottom-top);}}
  }else drawNotes(notes);
  if(report.raw_pitch && canvas.id==='timeline') {
    for(const [track,color] of [[alternative?.raw_pitch,'#879792'],[report.raw_pitch,'#c1dc82']]){if(!track)continue;ctx.strokeStyle=color;ctx.lineWidth=1.4;ctx.beginPath();let active=false;
    for(let i=0;i<track.times.length;i++){const t=track.times[i],f=track.f0_hz[i];if(t<start||t>end||!f){active=false;continue;}const p=69+12*Math.log2(f/440);if(!active)ctx.moveTo(x(t),y(p));else ctx.lineTo(x(t),y(p));active=true;}ctx.stroke();}
  }
  let phrase=null;for(const n of notes){if(n.phrase!==phrase){ctx.strokeStyle='#789779';ctx.setLineDash([3,5]);ctx.beginPath();ctx.moveTo(x(n.start),top);ctx.lineTo(x(n.start),bottom);ctx.stroke();ctx.setLineDash([]);phrase=n.phrase;}}
  if(playhead>=start&&playhead<=end){ctx.strokeStyle='#f5f4d8';ctx.beginPath();ctx.moveTo(x(playhead),0);ctx.lineTo(x(playhead),bottom);ctx.stroke();}ctx.restore();
  if(canvas.id==='timeline')geometry={left,width,start,end};
}
function draw(){if(pianoEditor){pianoEditor.render();return;}drawTimeline($('timeline'),state.report,state.notes,$('audio').currentTime,+$('viewstart').value,+$('viewlength').value,state.alternative,state.reference);}
$('timeline').onclick=event=>{if(pianoEditor||!geometry)return;const rect=$('timeline').getBoundingClientRect();const t=geometry.start+(event.clientX-rect.left-geometry.left)/(geometry.width-geometry.left-12)*(geometry.end-geometry.start);$('audio').currentTime=Math.max(0,Math.min(state.report.audio.duration,t));draw();};
window.addEventListener('resize',draw);
function animate(){const audio=$('audio');if(pianoEditor)pianoEditor.tick();else if(!audio.paused){const begin=+$('loopstart').value,end=+$('loopend').value;if($('loop').checked&&end>begin&&audio.currentTime>=end)audio.currentTime=begin;if(audio.currentTime>+$('viewstart').value + +$('viewlength').value)$('viewstart').value=Math.floor(audio.currentTime);draw();}requestAnimationFrame(animate);}animate();
function evidenceButton(label,hash,start,end) {const b=element('button',label,'evidence');b.onclick=()=>run(async()=>{const r=state.library.find(r=>r.audio.content_sha256===hash);if(!r)throw new Error('Evidence recording is unavailable.');await load(r.id);$('loopstart').value=start;$('loopend').value=end;$('loop').checked=true;$('viewstart').value=Math.max(0,start-.3);$('audio').currentTime=start;await $('audio').play();draw();});return b;}
function distribution(container,weights) {
  for(const [key,value] of Object.entries(weights).sort((a,b)=>+a[0]- +b[0])){const row=element('div',undefined,'barrow');const p=element('progress');p.max=1;p.value=value;row.append(element('span',key+' st'),p,element('span',(value*100).toFixed(1)+'%'));container.append(row);}
}
$('profile').onclick=()=>run(async()=>{if(!state.selected.size)throw new Error('Select at least one recording.');status('Building a recording-balanced profile…');state.profile=await api('profile',{ids:recordingLibrary.corpusIds(),artist:$('artist').value,allow_research:recordingLibrary.allowedResearch()});renderProfile();renderExercises();tab('style');status(state.profile.corpus_scope?.research_opt_in?'Explicit research corpus · dataset recordings included':'Style profile ready. Evidence and limited sample sizes are visible in every conclusion.');});
function renderProfile(){const p=state.profile,root=$('stylecontent');root.replaceChildren();const stats=element('div',undefined,'statgrid');for(const [v,label] of [[p.songs,`songs / ${p.recordings} recordings`],[p.phrases,'rest-delimited phrases'],[p.notes,'note events']]){const e=element('div',undefined,'stat');e.append(element('strong',v),element('span',label));stats.append(e);}root.append(stats);
  const intervals=element('div',undefined,'card');intervals.append(element('h3','Measured property · within-phrase interval distribution'),element('p','Recordings are averaged within each song; songs contribute equal weight. Transposition is normalized through relative intervals.','muted'));distribution(intervals,p.interval_weights);root.append(intervals);
  for(const c of p.conclusions){const card=element('div',undefined,'card');card.append(element('span','MEASURED MUSICAL PROPERTY','eyebrow'),element('h3',c.description),element('p',`${(c.equal_song_mean*100).toFixed(1)}% · ${c.support_songs} songs · ${c.support_recordings} recordings · ${c.support_notes} notes`));
    card.append(element('p',c.song_bootstrap_95_interval?`Song bootstrap interval: ${c.song_bootstrap_95_interval.map(v=>(v*100).toFixed(1)+'%').join(' – ')}`:'Too few recordings for a bootstrap interval.','muted'));
    for(const ev of c.evidence){card.append(element('p',`${ev.song}: ${ev.value===null?'no transitions':(ev.value*100).toFixed(1)+'%'}`));for(const ph of ev.phrases)card.append(evidenceButton(`${ph.start.toFixed(2)}–${ph.end.toFixed(2)} s · ${ph.notes} notes`,ev.source_hash,ph.start,ph.end));}
    const detail=element('details');detail.append(element('summary','Inspect support and exceptions'),element('pre',JSON.stringify(c,null,2)));card.append(detail);root.append(card);}
  const inference=element('div',undefined,'card');inference.append(element('span','STATISTICAL INFERENCE','eyebrow'),element('p',p.inferences[0].text),element('p',p.inferences[0].basis,'muted'));root.append(inference);
  for(const item of p.motif_families){for(const family of item.motifs.families||[]){const card=element('div',undefined,'card');card.append(element('h3','Candidate motif family · '+family.intervals.join(', ')+' semitones'));for(const occurrence of family.occurrences)card.append(evidenceButton(`${occurrence.variation} · ${occurrence.start.toFixed(2)} s`,item.source_hash,occurrence.start,occurrence.end));root.append(card);}}
  for(const family of p.cross_song_motifs?.families||[]){const card=element('div',undefined,'card');card.append(element('h3',`Cross-song motif candidate · ${family.support_songs} songs`));for(const o of family.occurrences)card.append(evidenceButton(`${o.song}: ${o.variation} · ${o.start.toFixed(2)} s`,o.source_hash,o.start,o.end));root.append(card);}
  const detail=element('details');detail.append(element('summary','Full profile, section comparisons and limitations'),element('pre',JSON.stringify(p,null,2)));root.append(detail);
}
for(const [i,name] of ['C','C♯','D','E♭','E','F','F♯','G','A♭','A','B♭','B'].entries())$('tonic').add(new Option(name,i));
$('generate').onclick=()=>run(async()=>{
  status('Searching for distinct scale- and range-constrained candidates…');
  const c={tonic:+$('tonic').value,scale:$('scale').value,tempo:+$('tempo').value,low:+$('low').value,high:+$('high').value,bars:+$('bars').value,density:+$('density').value,contour:$('contour').value,repetition:+$('repetition').value,section:$('section').value,subjective_direction:$('direction').value,syllables:$('syllables').value?+$('syllables').value:null,time_signature:$('timesig').value.split('/').map(Number),stress_notes:$('stress').value.split(',').filter(s=>s.trim()).map(Number),chords:JSON.parse($('chords').value),seed:+$('seed').value,candidates:3};
  const result=await api('compose',{ids:recordingLibrary.corpusIds(),artist:$('artist').value,allow_research:recordingLibrary.allowedResearch(),config:c});$('candidates').replaceChildren();
  result.candidates.forEach((candidate,i)=>{const card=element('div',undefined,'card');const resemblance=candidate.source_similarity.status==='assessed'?(candidate.source_similarity.similarity*100).toFixed(0)+'%':'not assessed';card.append(element('h3',`Candidate ${i+1}`),element('p',`Largest leap ${candidate.assessment.largest_leap_semitones} st · ${candidate.assessment.breath_gaps} breath gaps · maximum source resemblance ${resemblance}`,'muted'));
    if(candidate.source_similarity.status!=='assessed')card.append(element('p','Source resemblance was not assessed: fewer than six comparable notes.','muted'));
    const canvas=element('canvas');card.append(canvas);const a=element('a','Download original MIDI reference','download');a.href=`/api/candidate?id=${result.id}&index=${i}`;card.append(a);
    const preview=element('button','Play reference tones');preview.onclick=()=>run(()=>playReference(candidate.notes));card.append(preview);
    const detail=element('details');detail.append(element('summary','Editable note structure (seconds, MIDI pitch)'));const editor=element('textarea');editor.rows=7;editor.value=JSON.stringify(candidate.notes.map(n=>({start:n.start,end:n.end,pitch:n.pitch})),null,2);detail.append(editor);const play=element('button','Play edited reference');play.onclick=()=>run(()=>playReference(JSON.parse(editor.value)));detail.append(play,element('pre',JSON.stringify(candidate.assessment,null,2)));card.append(detail);$('candidates').append(card);
    drawTimeline(canvas,{audio:{duration:c.bars*c.time_signature[0]*4/c.time_signature[1]*60/c.tempo}},candidate.notes);
  });
  $('candidates').append(element('p',result.warnings.join(' '),'muted'));status(`${result.candidates.length} candidates found; ${result.rejected_source_matches} source matches rejected. Sing and revise a candidate yourself.`);
});
async function playReference(notes){
  if(!Array.isArray(notes)||notes.length>200)throw new Error('Use at most 200 reference notes.');
  const context=new AudioContext();const now=context.currentTime+.05;
  for(const n of notes){if(!Number.isFinite(n.start)||!Number.isFinite(n.end)||!Number.isFinite(n.pitch)||n.start<0||n.end<=n.start||n.end>180||n.pitch<0||n.pitch>127){await context.close();throw new Error('Invalid edited note.');}const osc=context.createOscillator(),gain=context.createGain();osc.type='sine';osc.frequency.value=440*2**((n.pitch-69)/12);gain.gain.setValueAtTime(0,now+n.start);gain.gain.linearRampToValueAtTime(.12,now+n.start+.01);gain.gain.setValueAtTime(.12,now+Math.max(n.start+.01,n.end-.02));gain.gain.linearRampToValueAtTime(0,now+n.end);osc.connect(gain).connect(context.destination);osc.start(now+n.start);osc.stop(now+n.end);}
  setTimeout(()=>context.close(),((Math.max(0,...notes.map(n=>n.end))+.2)*1000));
}
function renderExercises(){
  $('exercises').replaceChildren();for(const exercise of state.profile.exercises){const card=element('div',undefined,'card');card.append(element('span','PRACTICAL SONGWRITING SUGGESTION','eyebrow'),element('h3',exercise.title),element('p',exercise.why_selected),element('pre',JSON.stringify(exercise.constraint,null,2)),element('p',exercise.instructions));
    const editor=element('textarea');editor.rows=5;editor.value=JSON.stringify(exercise.structure,null,2);card.append(editor);const use=element('button','Practice this exercise');use.onclick=()=>run(async()=>{state.exercise=copy(exercise);state.exercise.structure=JSON.parse(editor.value);status(`Practice selected: ${exercise.title}. Record or import your own sung response.`);});card.append(use);$('exercises').append(card);}
  state.exercise=state.profile.exercises[0]||null;
}
$('record').onclick=()=>run(async()=>{
  const stream=await navigator.mediaDevices.getUserMedia({audio:true});const context=new AudioContext();const source=context.createMediaStreamSource(stream);const processor=context.createScriptProcessor(4096,1,1);const buffers=[];
  processor.onaudioprocess=e=>{buffers.push(new Float32Array(e.inputBuffer.getChannelData(0)));};source.connect(processor);processor.connect(context.destination);
  state.recording={stream,context,source,processor,buffers};$('record').disabled=true;$('stoprecord').disabled=false;status('Recording your sung attempt locally…');
});
$('stoprecord').onclick=()=>run(async()=>{
  const r=state.recording;if(!r)return;r.processor.disconnect();r.source.disconnect();r.stream.getTracks().forEach(t=>t.stop());const sr=r.context.sampleRate;await r.context.close();state.recording=null;$('record').disabled=false;$('stoprecord').disabled=true;
  const count=r.buffers.reduce((s,b)=>s+b.length,0);const data=new ArrayBuffer(44+count*2);const view=new DataView(data);let offset=0;const text=s=>{for(const c of s)view.setUint8(offset++,c.charCodeAt(0));};
  text('RIFF');view.setUint32(4,36+count*2,true);offset=8;text('WAVEfmt ');view.setUint32(16,16,true);view.setUint16(20,1,true);view.setUint16(22,1,true);view.setUint32(24,sr,true);view.setUint32(28,sr*2,true);view.setUint16(32,2,true);view.setUint16(34,16,true);offset=36;text('data');view.setUint32(40,count*2,true);offset=44;
  for(const buffer of r.buffers)for(const value of buffer){view.setInt16(offset,Math.round(Math.max(-1,Math.min(1,value))*32767),true);offset+=2;}
  await importAudio(new File([data],'sung-attempt-'+Date.now()+'.wav',{type:'audio/wav'}),true);
});
$('recheck').onclick=()=>run(async()=>{
  if(!state.id||!state.exercise)throw new Error('Select an analyzed attempt and a songwriting exercise first.');
  const result=await api('attempt',{id:state.id,exercise:state.exercise});
  $('feedback').textContent=JSON.stringify(result,null,2);status('Feedback refreshed from the saved note edition. Save any corrections before rechecking.');
});
async function refreshReferences(){
  $('reference-list').replaceChildren(new Option('Select an annotation',''));
  if(!state.id)return;
  const refs=await api('references?id='+state.id);
  for(const r of refs){const edition=r.origin.edition?' / '+r.origin.edition:'';
    $('reference-list').add(new Option(`${r.annotator}${edition} · ${r.excerpt.start.toFixed(2)}–${r.excerpt.end.toFixed(2)} s · ${r.review.status} · ${r.split}`,r.id));}
  if(state.reference)$('reference-list').value=state.reference.id;
}
function referenceModeStatus(){
  const r=state.reference;const published=r?.origin.kind==='published_human_dataset';
  $('reference-status').textContent=r?`${published?'Published human edition (read-only)':r.review.status==='reviewed'&&!pianoEditor?.dirty?'Reviewed human reference':'UNREVIEWED DRAFT — not accuracy evidence'} · ${r.excerpt.start.toFixed(3)}–${r.excerpt.end.toFixed(3)} source seconds · ${r.split}. Green bars: reference; red bars: raw prediction.`:'Working corrections mode. Reference revisions are independent from predictions and normal corrections.';
  $('save').textContent=r?'Save reference revision':'Save correction revision';
  for(const id of ['save','add','split','merge','delete','undo','reference-region'])$(id).disabled=!!published;
  $('reference-regions').disabled=!!published;
  for(const id of ['reference-annotator','reference-reviewer','reference-reviewed'])$(id).disabled=!!published;
  $('reference-split').disabled=!!r&&(published||r.split!=='unassigned');
  $('reference-group').disabled=!!published;
  $('reference-download').hidden=!r;
  if(r)$('reference-download').href=`/api/reference?reference_id=${r.id}&revision=${r.revision}`;
  for(const a of $('exports').querySelectorAll('a')){
    const type=a.dataset.exportType;a.hidden=!!r&&type!=='json';
    a.href=r?`/api/reference?reference_id=${r.id}&revision=${r.revision}`:a.dataset.workingHref;
    a.textContent=r?'Saved reference JSON':type==='midi'?'MIDI':type.toUpperCase();
    if(r)a.download='reference-'+r.id+'.json';else a.removeAttribute('download');
  }
}
function enterReference(r){
  if(r.audio.content_sha256!==state.report.audio.content_sha256)throw Error('Reference belongs to another source recording.');
  pianoEditor?.stashView();state.reference=r;state.notes=copy(r.notes);state.checked.clear();
  $('reference-list').value=r.id;
  $('reference-annotator').value=r.annotator;$('reference-reviewer').value=r.review.reviewer||'';
  $('reference-split').value=r.split;$('reference-group').value=r.song_group;
  $('reference-reviewed').checked=r.review.status==='reviewed'&&r.origin.kind!=='published_human_dataset';$('reference-regions').value=JSON.stringify(r.regions,null,2);
  $('loopstart').value=r.excerpt.start;$('loopend').value=r.excerpt.end;
  $('viewstart').value=r.excerpt.start;$('viewlength').value=Math.max(1,r.excerpt.end-r.excerpt.start);
  pianoEditor?.modeChanged();referenceModeStatus();renderNotes();draw();
}
async function createReference(seed){
  if(!state.id)throw new Error('Choose a recording first.');
  if(pianoEditor?.dirty&&!confirm('Discard unsaved edits before starting a separate reference? Cancel to keep editing.'))return;
  const annotator=$('reference-annotator').value.trim();if(!annotator){pianoEditor.openPanel('history');$('reference-annotator').focus();throw new Error('Enter your annotator name in History / revisions, then create a blank or model-assisted draft.');}
  const r=await api('reference-create',{id:state.id,start:+$('loopstart').value,end:+$('loopend').value,
    annotator,split:$('reference-split').value,song_group:$('reference-group').value||state.report.audio.content_sha256,seed});
  enterReference(r);await refreshReferences();status('Independent reference DRAFT created. Listen, correct notes, mark uncertainty and explicitly review before evaluation.');
}
$('reference-blank').onclick=()=>run(()=>createReference(false));
$('reference-seed').onclick=()=>run(()=>createReference(true));
$('reference-load').onclick=()=>run(async()=>{
  await openReference($('reference-list').value);
});
async function openReference(identifier){
  if(pianoEditor?.dirty&&!confirm('Discard unsaved edits and load the saved reference?'))return;
  if(!identifier)throw new Error('Select a reference edition first.');
  enterReference(await api('reference?reference_id='+identifier));status('Reference and raw prediction are aligned in original source seconds.');
}
$('reference-working').onclick=()=>{if(!state.report)return;if(pianoEditor?.dirty&&!confirm('Discard unsaved reference edits and return to working corrections?'))return;pianoEditor?.stashView();state.reference=null;state.notes=copy(state.report.notes);state.checked.clear();pianoEditor?.modeChanged();referenceModeStatus();renderNotes();draw();status('Working corrections restored. Saved reference editions remain separate.');};
$('reference-region').onclick=()=>run(async()=>{
  if(!state.reference)throw new Error('Create or load an editable reference first.');
  remember();
  const regions=JSON.parse($('reference-regions').value);regions.push({kind:$('region-kind').value,
    start:+$('loopstart').value,end:+$('loopend').value,reason:$('region-reason').value});
  state.reference.regions=regions;$('reference-regions').value=JSON.stringify(regions,null,2);$('reference-reviewed').checked=false;draw();status('Region added to unsaved reference. Uncertain intervals require a reason and are excluded with coverage reported.');
});
$('reference-regions').onchange=()=>run(async()=>{if(!state.reference)return;const regions=JSON.parse($('reference-regions').value);remember();state.reference.regions=regions;$('reference-reviewed').checked=false;draw();});
async function saveReference(){
  const r=state.reference;const reviewed=$('reference-reviewed').checked;
  const value=await api('reference-save',{reference_id:r.id,base_revision:r.revision,notes:state.notes,
    regions:JSON.parse($('reference-regions').value),annotator:$('reference-annotator').value,
    reviewer:$('reference-reviewer').value,reviewed,attestation:reviewed,
    split:$('reference-split').value,song_group:$('reference-group').value});
  enterReference(value);await refreshReferences();status(`Independent reference ${value.review.status} revision saved. No model prediction or normal correction was replaced.`);
}
$('reference-score').onclick=()=>run(async()=>{
  if(!state.reference)throw new Error('Select a saved human reference first.');
  const score=await api('reference-score',{id:state.id,reference_id:state.reference.id});
  $('reference-result').textContent=JSON.stringify(score,null,2);status(score.validation_status);
});
$('reference-export').onclick=()=>run(async()=>{
  const manifest=await api('reference-manifest',{});$('reference-result').textContent=JSON.stringify(manifest,null,2);
  status('Reviewed manifest saved at outputs/real-validation/reviewed.manifest.json. Exact annotation revisions and checksums are frozen.');
});
pianoEditor=new window.MelodyEditor({state,$,api,status,run,renderNotes,referenceModeStatus,enterReference});
recordingLibrary=new window.RecordingLibrary({state,$,api,status,run,load,openReference});
window.addEventListener('beforeunload',event=>{if(pianoEditor.dirty){event.preventDefault();event.returnValue='';}});
run(async()=>{await refresh();const params=new URLSearchParams(location.search),id=params.get('analysis'),ref=params.get('reference');if(id&&state.library.some(r=>r.id===id)){await load(id);if(ref)enterReference(await api('reference?reference_id='+encodeURIComponent(ref)));}});
