/* Integrated piano roll. Uses the existing application state and save/reference APIs. */
class MelodyEditor {
  constructor(hooks){
    this.h=hooks;this.s=hooks.state;this.$=hooks.$;this.M=MelodyEdits;this.history=new this.M.History();
    this.view={start:0,length:15,low:48,span:24};this.gesture=null;this.dirty=false;this.alternatives=[];this.queueKey='';this.lastPreviewPitch=null;
    this.roll=this.$('roll-viewport');this.canvas=this.$('timeline');
    this.audition=new VocalAudition(this.$('audio'),text=>{this.$('audition-status').textContent=text;this.$('audition-status').title=text;this.$('audio-timing').textContent=JSON.stringify(this.audition.timing(),null,2);});
    this.install();new ResizeObserver(()=>{cancelAnimationFrame(this.resizeFrame);this.resizeFrame=requestAnimationFrame(()=>this.render());}).observe(this.roll);
  }
  readonly(){return this.s.reference?.origin.kind==='published_human_dataset';}
  bounds(){return this.s.reference?[this.s.reference.excerpt.start,this.s.reference.excerpt.end]:[0,this.s.report?.audio.duration||0];}
  snapshot(){return {notes:this.M.clone(this.s.notes),regions:this.M.clone(this.s.reference?.regions||[]),checked:[...this.s.checked]};}
  remember(){this.history.push(this.snapshot());this.invalidate();}
  invalidate(){this.dirty=true;if(this.s.reference)this.$('reference-reviewed').checked=false;this.queueKey='';}
  resetHistory(){this.history.clear();this.dirty=false;this.queueKey='';}
  apply(value){
    this.s.notes=this.M.clone(value.notes);this.s.checked=new Set(value.checked.filter(id=>value.notes.some(n=>n.id===id)));
    if(this.s.reference){this.s.reference.regions=this.M.clone(value.regions);this.$('reference-regions').value=JSON.stringify(value.regions,null,2);}
    this.invalidate();this.h.renderNotes();this.h.referenceModeStatus();this.render();
  }
  commit(notes,before=this.snapshot()){
    if(this.readonly())throw Error('Published reference editions are read-only. Create a separate manual draft.');
    this.M.validate(notes,this.bounds());if(JSON.stringify(notes)===JSON.stringify(this.s.notes))return;
    this.history.push(before);this.s.notes=notes;this.invalidate();this.h.renderNotes();this.h.referenceModeStatus();this.render();
    this.h.status(this.s.reference?'Unsaved reference edits · original predictions retained':'Unsaved working corrections · save to retain this edition');
  }
  undo(){if(this.readonly())return;const value=this.history.back(this.snapshot());if(value)this.apply(value);}
  redo(){if(this.readonly())return;const value=this.history.forward(this.snapshot());if(value)this.apply(value);}
  selected(){return this.s.notes.filter(n=>this.s.checked.has(n.id));}
  selectionNote(){return this.selected()[0]||this.predictionSelection;}
  options(loop=false){return {pre:Math.max(0,+this.$('pre-roll').value||0),post:Math.max(0,+this.$('post-roll').value||0),loop};}
  updateURL(){if(!this.s.id)return;const u=new URL(location.href);u.searchParams.set('analysis',this.s.id);if(this.s.reference)u.searchParams.set('reference',this.s.reference.id);else u.searchParams.delete('reference');history.replaceState(null,'',u);}
  loaded(){
    this.audition.stop();this.resetHistory();this.alternatives=[];this.customRange=null;this.predictionSelection=null;
    this.view.start=+this.$('viewstart').value||0;this.view.length=Math.min(15,this.s.report.audio.duration);
    this.fitPitch();this.syncView();this.updateURL();this.render();this.h.run(()=>this.compareModels());this.h.run(()=>this.revisions());
  }
  modeChanged(){this.audition.stop();this.resetHistory();this.customRange=null;this.predictionSelection=null;this.view.start=+this.$('viewstart').value;this.view.length=+this.$('viewlength').value;this.fitPitch();this.syncView();this.updateURL();this.render();this.h.run(()=>this.revisions());}
  fitPitch(){const ns=this.s.notes.filter(n=>n.end>=this.view.start&&n.start<=this.view.start+this.view.length);if(!ns.length)return;
    const ps=ns.map(n=>n.pitch);this.view.span=this.M.clamp(Math.ceil(Math.max(...ps)-Math.min(...ps))+7,12,48);this.view.low=this.M.clamp((Math.max(...ps)+Math.min(...ps)-this.view.span)/2,-.5,127.5-this.view.span);}
  fit(){if(!this.s.report)return;const b=this.s.reference?this.bounds():this.selected().length?[Math.min(...this.selected().map(n=>n.start))-.2,Math.max(...this.selected().map(n=>n.end))+.2]:[0,this.s.report.audio.duration];this.view.start=Math.max(0,b[0]);this.view.length=Math.min(this.s.report.audio.duration,b[1])-this.view.start;this.fitPitch();this.syncView();this.render();}
  syncView(){if(!this.s.report)return;this.view.length=this.M.clamp(this.view.length,Math.min(.05,this.s.report.audio.duration),this.s.report.audio.duration);this.view.start=this.M.clamp(this.view.start,0,Math.max(0,this.s.report.audio.duration-this.view.length));this.view.span=this.M.clamp(this.view.span,4,60);this.view.low=this.M.clamp(this.view.low,-.5,127.5-this.view.span);this.$('viewstart').value=this.view.start;this.$('viewlength').value=this.view.length;}
  geometry(){const width=this.roll.clientWidth,height=this.roll.clientHeight,left=68,top=88,bottom=height-22;return {width,height,left,top,bottom,row:(bottom-top)/this.view.span};}
  x(t){const g=this.geometry();return g.left+(t-this.view.start)/this.view.length*(g.width-g.left);}
  y(p){const g=this.geometry();return g.bottom-(p-this.view.low)/this.view.span*(g.bottom-g.top);}
  time(x){const g=this.geometry();return this.M.clamp(this.view.start+(x-g.left)/(g.width-g.left)*this.view.length,0,this.s.report.audio.duration);}
  pitch(y){const g=this.geometry();return this.M.clamp(this.view.low+(g.bottom-y)/(g.bottom-g.top)*this.view.span,0,127);}
  point(e){const r=this.roll.getBoundingClientRect();return {x:e.clientX-r.left,y:e.clientY-r.top};}
  pitchReadout(p){this.$('pitch-label').textContent=`${this.M.pitchName(p)} · ${p.toFixed(3)} MIDI · ${this.M.hz(p).toFixed(2)} Hz`;}
  select(id,add=false){this.customRange=null;this.predictionSelection=null;if(add){this.s.checked.has(id)?this.s.checked.delete(id):this.s.checked.add(id);}else if(!this.s.checked.has(id)){this.s.checked=new Set([id]);}this.render();}
  async auditionSelected(){const n=this.selectionNote();if(!n)throw Error('Select a note first.');await this.audition.note(n,this.options(this.$('loop').checked));}
  seek(t){this.audition.cancelSegment();this.$('audio').currentTime=t;this.tick();}
  install(){
    const $=this.$,act=(id,fn)=>$(id).onclick=()=>this.h.run(fn);
    act('undo',()=>this.undo());act('redo',()=>this.redo());
    act('delete',()=>{if(this.s.checked.size)this.commit(this.s.notes.filter(n=>!this.s.checked.has(n.id)));});
    act('split',()=>this.commit(this.M.split(this.s.notes,this.s.checked,$('audio').currentTime,this.bounds(),crypto.randomUUID())));
    act('merge',()=>this.commit(this.M.merge(this.s.notes,this.s.checked,this.bounds())));
    act('add',()=>{if(!this.s.report)return;const start=$('audio').currentTime,b=this.bounds(),next=this.s.notes.find(n=>n.start>start);this.commit(this.M.add(this.s.notes,start,Math.min(start+.25,next?.start??b[1],b[1]),this.selected()[0]?.pitch||Math.round(this.view.low+this.view.span/2),b,crypto.randomUUID()));});
    act('pitch-up',()=>this.commit(this.M.move(this.s.notes,this.s.checked,0,1,this.bounds())));
    act('pitch-down',()=>this.commit(this.M.move(this.s.notes,this.s.checked,0,-1,this.bounds())));
    act('play',()=>this.audition.full());act('stop',()=>{this.audition.stop();if(this.s.report)$('audio').currentTime=+this.$('loopstart').value||0;});
    act('playrange',()=>this.playRange(false));act('loopselected',()=>this.loopSelection(false));act('loopphrase',()=>this.loopSelection(true));
    act('audition-selected',()=>this.auditionSelected());
    for(const [id,dp] of [['audition-below',-1],['audition-above',1]])act(id,()=>{const n=this.selectionNote();if(!n)throw Error('Select a note first.');return this.audition.piano(this.M.clamp(n.pitch+dp,0,127));});
    act('audition-ab',async()=>{const n=this.selectionNote();if(!n)throw Error('Select a note first.');await this.audition.note(n,{...this.options(),mode:'vocal'});if(this.audition.segment)this.audition.segment.thenPiano=n.pitch;});
    $('audition-mode').onchange=()=>{this.audition.stop();this.audition.mode=$('audition-mode').value;$('audition-status').textContent=`Click audition mode: ${$('audition-mode').selectedOptions[0].text}. The Play button always plays original audio.`;};
    for(const id of ['piano-volume','vocal-volume'])$(id).oninput=()=>this.audition.setVolumes(+$('piano-volume').value,+$('vocal-volume').value);
    $('speed').onchange=()=>this.h.run(()=>{try{this.audition.speed(+$('speed').value);this.h.status(`Playback ${$('speed').value}× · browser pitch preservation requested · annotations retain original source seconds`);}catch(e){$('speed').value='1';throw e;}});
    act('zoom-in',()=>this.zoomTime(.7));act('zoom-out',()=>this.zoomTime(1/.7));act('fit-view',()=>this.fit());
    for(const id of ['viewstart','viewlength'])$(id).oninput=()=>{this.view.start=+$('viewstart').value;this.view.length=+$('viewlength').value;this.syncView();this.render();};
    act('mark-uncertain',()=>this.markUncertain());act('confirm-note',()=>{if(!this.s.checked.size)throw Error('Select a note or a review item.');this.commit(this.s.notes.map(n=>this.s.checked.has(n.id)?{...n,flags:[...new Set([...(n.flags||[]),'review_confirmed'])]}:n));});
    act('refresh-review',()=>this.compareModels());act('restore-revision',()=>this.restoreRevision());
    act('finish-review',()=>{$('reference-tools').open=true;if(!this.s.reference){this.h.status('Choose an excerpt and start a reference draft before verifying it.');$('reference-annotator').focus();}else{$('reference-reviewer').focus();this.h.status('Listen to the whole excerpt, enter your name, and explicitly attest before saving a verified reference.');}});
    for(const key of ['pitch','start','end'])$(`inspect-${key}`).onchange=()=>this.h.run(()=>{const ns=this.M.clone(this.s.notes),n=ns.find(n=>this.s.checked.has(n.id));if(!n)return;n[key]=+$(`inspect-${key}`).value;n.duration=n.end-n.start;n.flags=[...new Set([...(n.flags||[]),'human_corrected'])];this.commit(ns);});
    this.roll.addEventListener('pointerdown',e=>this.h.run(()=>this.down(e)));
    this.roll.addEventListener('pointermove',e=>this.h.run(()=>this.movePointer(e)));
    this.roll.addEventListener('pointerup',e=>this.h.run(()=>this.up(e)));
    this.roll.addEventListener('pointercancel',()=>this.cancelGesture());
    this.roll.addEventListener('dblclick',e=>this.h.run(()=>{if(e.target.closest('.note-block,.piano-key')||this.readonly()||this.$('edit-tool').value!=='select')return;const p=this.point(e),g=this.geometry();if(p.x<g.left||p.y<g.top)return;const t=this.time(p.x),pitch=this.$('pitch-snap').checked?Math.round(this.pitch(p.y)):this.pitch(p.y);this.commit(this.M.add(this.s.notes,t,Math.min(t+.25,this.bounds()[1]),pitch,this.bounds(),crypto.randomUUID()));}));
    this.roll.addEventListener('wheel',e=>{if(!this.s.report)return;e.preventDefault();const p=this.point(e);if(e.ctrlKey)this.zoomTime(Math.exp(e.deltaY*.002),p.x);else if(e.altKey){const anchor=this.pitch(p.y),g=this.geometry(),ratio=(g.bottom-p.y)/(g.bottom-g.top);this.view.span=this.M.clamp(this.view.span*Math.exp(e.deltaY*.002),4,60);this.view.low=anchor-ratio*this.view.span;this.syncView();this.render();}else {if(e.shiftKey)this.view.start+=e.deltaY/600*this.view.length;else this.view.low-=e.deltaY/this.geometry().row*.3;this.syncView();this.render();}}, {passive:false});
    document.addEventListener('keydown',e=>{
      if(e.key==='Escape'){this.cancelGesture();return;}
      if(/INPUT|TEXTAREA|SELECT/.test(e.target.tagName)||this.$('review').classList.contains('hidden'))return;
      if(e.code==='Space'){e.preventDefault();this.h.run(()=>this.audition.full());}
      else if((e.ctrlKey||e.metaKey)&&e.key.toLowerCase()==='z'){e.preventDefault();e.shiftKey?this.redo():this.undo();}
      else if((e.ctrlKey||e.metaKey)&&e.key.toLowerCase()==='y'){e.preventDefault();this.redo();}
      else if(e.key==='Delete'||e.key==='Backspace'){e.preventDefault();$('delete').click();}
      else if(e.key==='ArrowUp'||e.key==='ArrowDown'){if(this.s.checked.size){e.preventDefault();$(e.key==='ArrowUp'?'pitch-up':'pitch-down').click();}}
    });
    $('audio').addEventListener('loadedmetadata',()=>this.tick());
    $('audio').addEventListener('error',()=>this.h.run(async()=>{
      if(!this.s.id||$('audio').src.includes('/api/audio?'))return;this.audition.stop();const id=this.s.id;
      const check=await fetch('/api/source-audio?id='+encodeURIComponent(id),{headers:{Range:'bytes=0-0'}});
      if(!check.ok){const error=await check.json();throw Error(error.error||'Original source audio could not be validated. Reanalyze before annotation.');}
      if(this.s.id!==id)return;$('audio').src='/api/audio?id='+encodeURIComponent(id);this.h.status('Browser cannot decode the original format. Using the existing mono/resampled playback copy with unchanged source seconds.',true);
    }));
    document.querySelectorAll('#editor-bottom>details').forEach(d=>d.addEventListener('toggle',()=>requestAnimationFrame(()=>this.render())));
  }
  zoomTime(factor,anchorX){if(!this.s.report)return;const g=this.geometry(),x=anchorX??(g.left+g.width)/2,t=this.time(x);this.view.length=this.M.clamp(this.view.length*factor,.05,this.s.report.audio.duration);this.view.start=t-(x-g.left)/(g.width-g.left)*this.view.length;this.syncView();this.render();}
  down(e){
    if(!this.s.report||e.target.closest('.piano-key')||e.button===2)return;
    const p=this.point(e),g=this.geometry();if(e.button!==0&&e.button!==1)return;e.preventDefault();this.roll.focus();this.roll.setPointerCapture(e.pointerId);
    if(e.button===1){this.gesture={kind:'pan',point:p,view:{...this.view}};return;}
    if(e.target.id==='playhead-handle'||p.y<g.top){this.audition.cancelSegment();this.gesture={kind:'seek'};this.$('audio').currentTime=this.time(p.x);this.tick();return;}
    const block=e.target.closest('.note-block');
    if(block){const id=block.dataset.noteId;this.select(id,e.shiftKey||e.ctrlKey||e.metaKey);const edge=e.target.dataset.edge;
      if(this.readonly()){this.gesture={kind:'click',id,point:p,moved:false};return;}this.gesture={kind:edge?'resize':'move',edge,id,point:p,before:this.snapshot(),moved:false};return;}
    if(p.x<g.left||p.y>g.bottom)return;
    const tool=this.$('edit-tool').value;
    if(tool==='select'&&!e.shiftKey){const t=this.time(p.x),prediction=this.s.report.predicted_notes.find(n=>n.start<=t&&n.end>=t&&Math.abs(this.y(n.pitch)-p.y)<=Math.max(4,g.row*.28));
      if(prediction){this.s.checked.clear();this.predictionSelection=prediction;this.gesture={kind:'prediction',note:prediction,point:p,moved:false};this.render();this.h.status('Raw model note selected for listening only · no reference note was created');return;}}
    this.gesture={kind:e.shiftKey?'marquee':tool==='draw'?'draw':tool==='range'||tool==='uncertain'?'range':'seek',tool,point:p,now:p,before:this.snapshot(),moved:false};
    if(this.gesture.kind==='seek'){this.s.checked.clear();this.predictionSelection=null;this.seek(this.time(p.x));this.render();}
  }
  movePointer(e){
    const d=this.gesture;if(!d)return;const p=this.point(e);d.now=p;
    if(d.kind==='seek'){this.$('audio').currentTime=this.time(p.x);this.tick();return;}
    if(d.kind==='pan'){const g=this.geometry();this.view.start=d.view.start-(p.x-d.point.x)/(g.width-g.left)*d.view.length;this.view.low=d.view.low+(p.y-d.point.y)/(g.bottom-g.top)*d.view.span;this.syncView();this.render();return;}
    d.moved=d.moved||Math.hypot(p.x-d.point.x,p.y-d.point.y)>3;
    if((d.kind==='move'||d.kind==='resize')&&d.moved){
      let ns;if(d.kind==='resize')ns=this.M.resize(d.before.notes,d.id,d.edge,this.time(p.x),this.bounds());
      else {const dp=this.pitch(p.y)-this.pitch(d.point.y),delta=this.$('pitch-snap').checked&&!e.altKey?Math.round(dp):dp;ns=this.M.move(d.before.notes,new Set(d.before.checked),this.time(p.x)-this.time(d.point.x),delta,this.bounds());}
      d.preview=ns;this.renderNotes(ns,true);const n=ns.find(n=>n.id===d.id);this.pitchReadout(n.pitch);
      if(d.kind==='move'&&this.$('drag-audition').checked&&Math.abs(n.pitch-(this.lastPreviewPitch??-999))>=.15){this.lastPreviewPitch=n.pitch;this.h.run(async()=>{await this.audition.ensure();this.audition.tone(n.pitch,.15);this.$('audition-status').textContent=`Drag preview: piano ${this.M.pitchName(n.pitch)} · vocal unchanged`;});}
    }else if(['draw','range','marquee'].includes(d.kind))this.drawGesture(d);
  }
  up(e){
    const d=this.gesture;if(!d)return;this.gesture=null;if(this.roll.hasPointerCapture(e.pointerId))this.roll.releasePointerCapture(e.pointerId);this.$('gesture-layer').replaceChildren();this.lastPreviewPitch=null;
    try {
      if(d.preview&&d.moved)this.commit(d.preview,d.before);
      else if(['move','click'].includes(d.kind)&&!d.moved&&this.$('auto-audition').checked){const n=this.s.notes.find(n=>n.id===d.id);if(n)this.h.run(()=>this.audition.note(n,this.options(this.$('loop').checked)));}
      else if(d.kind==='prediction'&&!d.moved&&this.$('auto-audition').checked)this.h.run(()=>this.audition.note(d.note,this.options(this.$('loop').checked)));
      else if(d.kind==='draw'&&!this.readonly()){
        const p=d.now||d.point,a=this.time(d.point.x),b=d.moved?this.time(p.x):Math.min(a+.25,this.bounds()[1]);
        const pitch=this.$('pitch-snap').checked?Math.round(this.pitch(d.point.y)):this.pitch(d.point.y),id=crypto.randomUUID();
        const ns=this.M.add(this.s.notes,a,b,pitch,this.bounds(),id);this.s.checked=new Set([id]);this.commit(ns,d.before);
      }else if(d.kind==='range'){
        const a=this.time(d.point.x),b=this.time((d.now||d.point).x);this.customRange=[Math.min(a,b),Math.max(a,b)];this.$('loopstart').value=this.customRange[0];this.$('loopend').value=this.customRange[1];
        if(d.tool==='uncertain')this.markUncertain();
      }else if(d.kind==='marquee'){
        const p=d.now||d.point,a=this.time(Math.min(p.x,d.point.x)),b=this.time(Math.max(p.x,d.point.x)),lo=this.pitch(Math.max(p.y,d.point.y)),hi=this.pitch(Math.min(p.y,d.point.y));
        this.s.checked=new Set(this.s.notes.filter(n=>n.start<b&&n.end>a&&n.pitch>=lo&&n.pitch<=hi).map(n=>n.id));
      }
    }finally{this.render();}
  }
  cancelGesture(){this.gesture=null;this.$('gesture-layer').replaceChildren();this.render();}
  drawGesture(d){const g=this.geometry(),p=d.now||d.point,box=document.createElement('div');box.className=d.kind==='marquee'?'marquee':'range-box'+(d.tool==='uncertain'?' uncertain':'');box.style.left=Math.max(g.left,Math.min(p.x,d.point.x))+'px';box.style.width=Math.abs(p.x-d.point.x)+'px';box.style.top=(d.kind==='marquee'?Math.min(p.y,d.point.y):g.top)+'px';box.style.height=(d.kind==='marquee'?Math.abs(p.y-d.point.y):g.bottom-g.top)+'px';this.$('gesture-layer').replaceChildren(box);}
  async playRange(loop){const a=+this.$('loopstart').value,b=+this.$('loopend').value;if(!this.s.report||!Number.isFinite(a)||!Number.isFinite(b)||a<0||b<=a||b>this.s.report.audio.duration)throw Error('Choose a valid source-time range.');await this.audition.range(a,b,loop||this.$('loop').checked);}
  async loopSelection(phrase){let ns=this.selected(),pool=this.s.notes;if(!ns.length&&this.predictionSelection){ns=[this.predictionSelection];pool=this.s.report.predicted_notes;}if(!ns.length)throw Error('Select a note first.');if(phrase){const ids=new Set(ns.map(n=>n.phrase));ns=pool.filter(n=>ids.has(n.phrase));}
    const a=Math.max(0,Math.min(...ns.map(n=>n.start))-this.options().pre),b=Math.min(this.s.report.audio.duration,Math.max(...ns.map(n=>n.end))+this.options().post);this.$('loopstart').value=a;this.$('loopend').value=b;this.$('loop').checked=true;
    if(!phrase&&ns.length===1)await this.audition.note(ns[0],{...this.options(true),mode:this.audition.mode==='piano'?'vocal':this.audition.mode});else await this.playRange(true);
  }
  markUncertain(){
    if(this.readonly())throw Error('Published labels are read-only.');const reason=this.$('uncertainty-reason').value.trim()||this.$('region-reason').value.trim();
    if(!reason){this.$('uncertainty-reason').focus();throw Error('Write what remains unclear, then mark the selected range uncertain.');}
    if(!this.s.reference){if(!this.s.checked.size)throw Error('Create a reference to label a time region, or select working notes to flag them.');this.commit(this.s.notes.map(n=>this.s.checked.has(n.id)?{...n,flags:[...new Set([...(n.flags||[]),'review_uncertain'])]}:n));return;}
    const ns=this.selected(),b=this.bounds(),r=this.customRange||(ns.length?[Math.min(...ns.map(n=>n.start)),Math.max(...ns.map(n=>n.end))]:[+this.$('loopstart').value,+this.$('loopend').value]);
    const start=Math.max(b[0],r[0]),end=Math.min(b[1],r[1]);if(!(end>start))throw Error('Choose a nonempty range inside the reference excerpt.');
    this.remember();this.s.reference.regions.push({kind:'uncertain',start,end,reason});this.$('reference-regions').value=JSON.stringify(this.s.reference.regions,null,2);this.render();this.h.referenceModeStatus();this.h.status('Unsaved uncertainty region · evaluation exclusions remain explicit');
  }
  async compareModels(){
    if(!this.s.id)return;const id=this.s.id,signature=r=>`${r.estimator||r.raw_pitch?.model}|${r.model?.name||r.provenance?.note_model.name}`;
    const base=signature({raw_pitch:this.s.report.raw_pitch,provenance:this.s.report.provenance}),seen=new Set([base]),candidates=[];
    for(const other of this.s.library){if(other.id===id||other.audio.content_sha256!==this.s.report.audio.content_sha256||seen.has(signature(other)))continue;seen.add(signature(other));candidates.push(other);}
    const reports=await Promise.all(candidates.slice(0,4).map(async other=>{const r=await this.h.api('report?id='+other.id);return {name:`${r.raw_pitch.model} → ${r.provenance.note_model.name}`,notes:r.predicted_notes};}));
    if(this.s.id!==id)return;this.alternatives=reports;this.queueKey='';this.renderQueue();
  }
  async revisions(){
    if(!this.s.id)return;const id=this.s.id,ref=this.s.reference?.id;
    const rows=await this.h.api(ref?'reference-history?reference_id='+ref:'correction-history?id='+id);
    if(this.s.id!==id||this.s.reference?.id!==ref)return;this.$('revision-list').replaceChildren();
    for(const r of rows){const option=new Option(`${r.saved_at||r.revision} · ${r.notes.length} notes${r.review?' · '+r.review.status:''}`,r.revision);this.$('revision-list').add(option);}
    if(!rows.length)this.$('revision-list').add(new Option('No saved corrections yet',''));
  }
  async restoreRevision(){
    const revision=this.$('revision-list').value;if(!revision)throw Error('Choose a saved revision first.');if(this.readonly())throw Error('Published references are read-only.');
    if(this.dirty&&!confirm('Replace unsaved edits with this saved edition?'))return;
    if(this.s.reference){const r=await this.h.api('reference-restore',{reference_id:this.s.reference.id,revision,base_revision:this.s.reference.revision});this.h.enterReference(r);}
    else {this.s.report=await this.h.api('restore-correction',{id:this.s.id,revision,base_revision:this.s.report.provenance.correction_revision??null});this.s.notes=this.M.clone(this.s.report.notes);this.s.checked.clear();this.resetHistory();this.h.renderNotes();this.render();}
    await this.revisions();this.h.status('Restored as a new revision. Earlier saved revisions and raw predictions remain intact.');
  }
  render(){if(!this.s.report)return;this.syncView();this.paint();this.renderNotes(this.s.notes);this.inspector();this.renderQueue();this.renderRegions();this.tick();
    this.$('undo').disabled=this.readonly()||!this.history.undo.length;this.$('redo').disabled=this.readonly()||!this.history.redo.length;
    this.$('mode-badge').textContent=this.s.reference?`${this.s.reference.origin.kind==='published_human_dataset'?'Published reference':this.dirty||this.s.reference.review.status!=='reviewed'?'UNREVIEWED reference draft':'Reviewed reference'}${this.dirty?' · unsaved':''}`:`Working corrections${this.dirty?' · unsaved':''}`;
    this.$('guide').textContent=this.s.reference?`${this.bounds()[0].toFixed(3)}–${this.bounds()[1].toFixed(3)} source seconds · ${this.s.reference.origin.kind==='model_assisted_draft'?'Model-assisted labels require your listening and correction.':'Inspect the edition by ear.'} Finish review requires your explicit attestation.`:'Choose 5–12 source seconds → listen → blank or model-assisted draft → visual correction → uncertainty → listen again → attest & save.';
    this.$('view-readout').textContent=`${this.view.start.toFixed(2)}–${(this.view.start+this.view.length).toFixed(2)} s · ${this.view.span.toFixed(1)} semitones`;
  }
  paint(){
    const g=this.geometry(),dpr=devicePixelRatio||1,c=this.canvas,ctx=c.getContext('2d');if(g.width<1||g.height<1)return;c.width=Math.round(g.width*dpr);c.height=Math.round(g.height*dpr);ctx.scale(dpr,dpr);ctx.clearRect(0,0,g.width,g.height);
    ctx.fillStyle='#10191b';ctx.fillRect(0,0,g.width,g.height);ctx.font='10px system-ui';ctx.fillStyle='#9db1ad';ctx.fillText('source s',4,14);
    const tick=this.view.length>20?5:this.view.length>8?1:this.view.length>2?.5:this.view.length>.5?.1:.01;
    for(let t=Math.ceil(this.view.start/tick)*tick;t<=this.view.start+this.view.length;t+=tick){const x=this.x(t);ctx.strokeStyle='#283639';ctx.beginPath();ctx.moveTo(x,18);ctx.lineTo(x,g.bottom);ctx.stroke();ctx.fillStyle='#a8bdb7';ctx.fillText(t.toFixed(tick<.1?2:1),x+3,13);}
    for(let p=Math.ceil(this.view.low);p<this.view.low+this.view.span;p++){const y=this.y(p+.5);ctx.fillStyle=[1,3,6,8,10].includes(p%12)?'#162124':'#1b292b';ctx.fillRect(g.left,y,g.width-g.left,g.row);ctx.strokeStyle=p%12===0?'#51716d':'#2b3e3f';ctx.beginPath();ctx.moveTo(g.left,y);ctx.lineTo(g.width,y);ctx.stroke();}
    ctx.save();ctx.beginPath();ctx.rect(g.left,18,g.width-g.left,g.bottom-18);ctx.clip();
    const w=this.s.report.waveform;if(w){ctx.strokeStyle='#6e9290';for(let i=0;i<w.min.length;i++){const t=i*w.hop_seconds;if(t<this.view.start||t>this.view.start+this.view.length)continue;const x=this.x(t);ctx.beginPath();ctx.moveTo(x,53-w.max[i]*26);ctx.lineTo(x,53-w.min[i]*26);ctx.stroke();}}
    ctx.save();ctx.beginPath();ctx.rect(g.left,g.top,g.width-g.left,g.bottom-g.top);ctx.clip();
    const preds=(ns,color,thick)=>{ctx.strokeStyle=color;ctx.lineWidth=thick;for(const n of ns){if(n.end<this.view.start||n.start>this.view.start+this.view.length)continue;ctx.beginPath();ctx.moveTo(this.x(n.start),this.y(n.pitch));ctx.lineTo(this.x(n.end),this.y(n.pitch));ctx.stroke();}};
    if(this.s.alternative)preds(this.s.alternative.predicted_notes,'#b3bcc7',3);
    preds(this.s.report.predicted_notes,'#df8274',3);
    for(const r of this.s.reference?.regions||[]){if(r.kind==='uncertain'){ctx.fillStyle='#e0b34739';ctx.fillRect(this.x(r.start),g.top,this.x(r.end)-this.x(r.start),g.bottom-g.top);}}
    ctx.save();ctx.beginPath();ctx.rect(g.left,g.top,g.width-g.left,g.bottom-g.top);ctx.clip();
    const track=this.s.report.raw_pitch;ctx.strokeStyle='#d1e891';ctx.lineWidth=1.25;ctx.beginPath();let active=false;
    for(let i=0;i<track.times.length;i++){const t=track.times[i],f=track.f0_hz[i];if(!f||t<this.view.start||t>this.view.start+this.view.length){active=false;continue;}const x=this.x(t),y=this.y(69+12*Math.log2(f/440));if(active)ctx.lineTo(x,y);else ctx.moveTo(x,y);active=true;}ctx.stroke();ctx.restore();ctx.restore();
    ctx.strokeStyle='#6f8d80';ctx.setLineDash([3,5]);let phrase=null;for(const n of this.s.notes){if(n.phrase!==phrase){ctx.beginPath();ctx.moveTo(this.x(n.start),g.top);ctx.lineTo(this.x(n.start),g.bottom);ctx.stroke();phrase=n.phrase;}}ctx.setLineDash([]);ctx.restore();
    this.renderKeyboard();
  }
  renderKeyboard(){const g=this.geometry(),parent=this.$('piano-keys');parent.replaceChildren();
    for(let p=Math.max(0,Math.ceil(this.view.low-.5));p<=Math.min(127,Math.floor(this.view.low+this.view.span+.5));p++){
      const button=document.createElement('button');button.type='button';button.className='piano-key'+([1,3,6,8,10].includes(p%12)?' black':'');button.dataset.pitch=p;button.textContent=this.M.pitchName(p);button.setAttribute('aria-label',`Piano ${this.M.pitchName(p)} · ${this.M.hz(p).toFixed(2)} Hz`);button.title=button.getAttribute('aria-label');button.style.top=(this.y(p)-g.top-g.row/2)+'px';button.style.height=g.row+'px';
      button.onclick=()=>this.h.run(async()=>{this.pitchReadout(p);const ns=this.predictionSelection?[this.predictionSelection,...this.s.notes]:this.s.notes,ids=this.predictionSelection?new Set([this.predictionSelection.id]):this.s.checked;await this.audition.keyboard(p,ids,ns,this.options(this.$('loop').checked));});parent.append(button);
    }
  }
  renderNotes(ns,preview=false){const g=this.geometry(),layer=this.$('note-layer');layer.replaceChildren();
    for(const n of ns){if(n.end<this.view.start||n.start>this.view.start+this.view.length||n.pitch<this.view.low-.5||n.pitch>this.view.low+this.view.span+.5)continue;
      const block=document.createElement('button');block.type='button';block.className='note-block'+(!this.s.reference?' working':'')+(this.s.checked.has(n.id)?' selected':'')+(n.confidence<.35||n.flags?.some(f=>/review|confidence_unavailable/.test(f))?' flagged':'')+(preview?' preview':'');block.dataset.noteId=n.id;block.dataset.pitch=n.pitch;block.dataset.start=n.start;block.dataset.end=n.end;
      const title=`Note ${this.M.pitchName(n.pitch)} · ${n.start.toFixed(6)}–${n.end.toFixed(6)} source seconds`;block.setAttribute('aria-label',title);block.setAttribute('aria-pressed',this.s.checked.has(n.id));block.title=title;block.style.left=(this.x(n.start)-g.left)+'px';block.style.top=(this.y(n.pitch)-g.top-g.row*.36)+'px';block.style.width=Math.max(3,this.x(n.end)-this.x(n.start))+'px';block.style.height=Math.max(7,g.row*.72)+'px';
      const label=document.createElement('span');label.className='note-name';label.textContent=this.M.pitchName(n.pitch);block.append(label);
      if(!this.readonly())for(const edge of ['start','end']){const handle=document.createElement('span');handle.className='note-edge '+edge;handle.dataset.edge=edge;handle.setAttribute('aria-label',`Resize ${edge}`);block.append(handle);}
      // Enter/keyboard activation remains available without using pointer gestures.
      block.onclick=e=>{if(e.detail===0){this.select(n.id,e.shiftKey);if(this.$('auto-audition').checked)this.h.run(()=>this.audition.note(n,this.options(this.$('loop').checked)));}};layer.append(block);
    }
  }
  inspector(){const ns=this.selected(),n=this.selectionNote(),rawOnly=!ns.length&&!!this.predictionSelection;this.$('selection-summary').textContent=rawOnly?'Raw model prediction · listen only; reference labels stay separate':ns.length?`${ns.length} selected · drag body to move, edges to resize`:'Shift-click / Shift-drag to multi-select. Draw tool adds notes.';
    for(const key of ['pitch','start','end']){const input=this.$('inspect-'+key);if(document.activeElement!==input)input.value=n?n[key]:'';input.disabled=!n||rawOnly||this.readonly();}
    if(n){this.pitchReadout(n.pitch);this.$('inspect-duration').textContent=`Duration ${(n.end-n.start).toFixed(6)} s · phrase ${n.phrase}`;
      this.$('inspect-confidence').textContent=n.flags?.includes('confidence_unavailable')?'Note-model confidence unavailable. F0 confidence is separate.':`Estimator confidence ${n.confidence.toFixed(3)} · not a correctness probability`;
    }else {this.$('pitch-label').textContent='Select a note or piano key';this.$('inspect-duration').textContent='';this.$('inspect-confidence').textContent='';}
    for(const id of ['confirm-note','pitch-up','pitch-down'])this.$(id).disabled=!ns.length||this.readonly();
  }
  renderQueue(){
    if(!this.s.report)return;const bounds=this.bounds(),key=JSON.stringify([this.s.notes,bounds,this.alternatives.map(a=>a.name)]);if(key===this.queueKey)return;this.queueKey=key;
    // Alternative-only windows must stay inside the active reference excerpt.
    const scoped=this.alternatives.map(a=>({...a,notes:a.notes.filter(n=>n.end>bounds[0]&&n.start<bounds[1]).map(n=>({...n,start:Math.max(bounds[0],n.start),end:Math.min(bounds[1],n.end)}))}));
    this.queue=this.M.reviewQueue(this.s.notes,this.s.report.processed_pitch,scoped);this.$('review-count').textContent=`(${this.queue.filter(r=>!r.confirmed).length} to inspect · ${this.alternatives.length} alternatives)`;
    const parent=this.$('review-queue');parent.replaceChildren();
    for(const item of this.queue){const button=document.createElement('button');button.className='review-item'+(item.confirmed?' confirmed':'');button.textContent=`${item.confirmed?'Confirmed · ':''}${item.start.toFixed(3)}–${item.end.toFixed(3)} s · ${item.reasons.join(' · ')}`;
      button.onclick=()=>this.h.run(async()=>{this.s.checked=new Set(item.note_id?[item.note_id]:[]);this.customRange=[item.start,item.end];this.view.start=Math.max(0,item.start-.35);this.view.length=Math.max(1,item.end-item.start+.7);this.syncView();this.fitPitch();this.render();if(this.$('queue-loop').checked){const note=this.s.notes.find(n=>n.id===item.note_id);if(note)await this.audition.note(note,{...this.options(true),mode:this.audition.mode==='piano'?'vocal':this.audition.mode});else await this.audition.range(Math.max(0,item.start-this.options().pre),Math.min(this.s.report.audio.duration,item.end+this.options().post),true);}});parent.append(button);
    }
    if(!this.queue.length)parent.textContent='No rules flagged these notes. This does not establish accuracy.';
  }
  renderRegions(){const parent=this.$('region-list');parent.replaceChildren();for(const [index,r] of (this.s.reference?.regions||[]).entries()){
    const row=document.createElement('div');row.className='region-item';const text=document.createElement('span');text.textContent=`${r.kind} ${r.start.toFixed(3)}–${r.end.toFixed(3)} s · ${r.reason||''}`;row.append(text);
    if(!this.readonly()){const remove=document.createElement('button');remove.textContent='Remove';remove.onclick=()=>{this.remember();this.s.reference.regions.splice(index,1);this.$('reference-regions').value=JSON.stringify(this.s.reference.regions,null,2);this.render();};row.append(remove);}parent.append(row);
  }}
  tick(){
    const audio=this.$('audio');this.audition.tick();if(!this.s.report)return;
    if(!audio.paused&&!this.audition.segment&&this.$('loop').checked&&audio.currentTime>=+this.$('loopend').value&&+this.$('loopend').value>+this.$('loopstart').value)audio.currentTime=+this.$('loopstart').value;
    const x=this.x(audio.currentTime);this.$('playhead').style.left=x+'px';this.$('playhead').hidden=x<68||x>this.geometry().width;
    this.$('transport-time').textContent=audio.currentTime.toFixed(3)+' s';this.$('play').textContent=audio.paused?'▶ Play':'❚❚ Pause';
  }
}
window.MelodyEditor=MelodyEditor;
