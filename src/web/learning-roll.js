/* Shared listening/composition roll. Editing delegates to existing MelodyEdits. */
class LearningRoll {
  constructor(node,h={}){this.node=node;this.h=h;this.notes=[];this.start=0;this.end=8;this.low=48;this.high=76;this.selected=new Set();this.highlight=new Set();this.history=new MelodyEdits.History();this.report=null;this.cursor=null;this.canvas=document.createElement('canvas');this.layer=document.createElement('div');this.layer.className='learning-note-layer';node.append(this.canvas,this.layer);node.tabIndex=0;
    new ResizeObserver(()=>this.render()).observe(node);
    node.onpointerdown=e=>this.down(e);node.onpointermove=e=>this.move(e);node.onpointerup=e=>this.up(e);node.onpointercancel=()=>{this.drag=null;this.render();};
    node.onkeydown=e=>{if(!h.editable||/INPUT|SELECT|TEXTAREA/.test(e.target.tagName))return;if(e.key==='Delete'||e.key==='Backspace'){e.preventDefault();this.remove();}if((e.ctrlKey||e.metaKey)&&e.key==='z'){e.preventDefault();e.shiftKey?this.redo():this.undo();}};
  }
  geom(){const w=this.node.clientWidth,height=this.node.clientHeight,top=this.report?76:30;return {w,h:height,left:58,top,bottom:height-20,row:(height-20-top)/(this.high-this.low)};}
  x(t){const g=this.geom();return g.left+(t-this.start)/(this.end-this.start)*(g.w-g.left-6);}
  y(p){const g=this.geom();return g.bottom-(p-this.low)/(this.high-this.low)*(g.bottom-g.top);}
  time(x){const g=this.geom();return MelodyEdits.clamp(this.start+(x-g.left)/(g.w-g.left-6)*(this.end-this.start),this.start,this.end);}
  pitch(y){const g=this.geom();return MelodyEdits.clamp(this.low+(g.bottom-y)/(g.bottom-g.top)*(this.high-this.low),0,127);}
  point(e){const r=this.node.getBoundingClientRect();return {x:e.clientX-r.x,y:e.clientY-r.y};}
  set(notes,start,end,{report=null,low=null,high=null,reset=false}={}){this.notes=MelodyEdits.clone(notes);this.start=start;this.end=end;this.report=report;
    const p=notes.map(n=>n.pitch);this.low=low??(p.length?Math.floor(Math.min(...p))-3:48);this.high=high??(p.length?Math.ceil(Math.max(...p))+3:76);if(this.high-this.low<10){const center=(this.low+this.high)/2;this.low=center-5;this.high=center+5;}this.low=Math.max(-.5,this.low);this.high=Math.min(127.5,this.high);if(reset){this.history.clear();this.selected.clear();}this.render();}
  commit(notes){MelodyEdits.validate(notes,[this.start,this.end]);this.history.push(this.notes);this.notes=MelodyEdits.clone(notes);this.h.change?.(this.notes);this.render();}
  restore(notes){if(notes){this.notes=notes;this.h.change?.(this.notes);this.render();}}
  undo(){this.restore(this.history.back(this.notes));}redo(){this.restore(this.history.forward(this.notes));}
  remove(){if(this.selected.size)this.commit(this.notes.filter(n=>!this.selected.has(n.id)));}
  down(e){if(e.button!==0)return;const p=this.point(e),g=this.geom(),block=e.target.closest('.learning-note');e.preventDefault();this.node.focus();this.node.setPointerCapture(e.pointerId);
    if(p.x<g.left&&p.y>=g.top){this.h.pitch?.(Math.round(this.pitch(p.y)));return;}
    if(block){const n=this.notes.find(n=>n.id===block.dataset.noteId);if(!n)return;if(e.shiftKey)this.selected.has(n.id)?this.selected.delete(n.id):this.selected.add(n.id);else if(!this.selected.has(n.id))this.selected=new Set([n.id]);this.h.select?.(n);this.drag={kind:this.h.editable?(e.target.dataset.edge?'resize':'move'):'listen',id:n.id,edge:e.target.dataset.edge,point:p,before:MelodyEdits.clone(this.notes),moved:false};this.render();return;}
    if(p.x<g.left)return;this.drag={kind:this.h.editable?(this.h.tool?.()==='select'?'select-empty':'draw'):'range',point:p,before:MelodyEdits.clone(this.notes),moved:false};
  }
  move(e){if(!this.drag)return;const d=this.drag,p=this.point(e);d.now=p;d.moved ||= Math.hypot(p.x-d.point.x,p.y-d.point.y)>3;
    if(this.h.editable&&['move','resize'].includes(d.kind)&&d.moved){const n=d.before.find(n=>n.id===d.id),snap=v=>e.altKey?v:Math.round(v*4)/4;
      try{d.preview=d.kind==='move'?MelodyEdits.move(d.before,this.selected,snap(this.time(p.x)-this.time(d.point.x)),e.altKey?this.pitch(p.y)-this.pitch(d.point.y):Math.round(this.pitch(p.y)-this.pitch(d.point.y)),[this.start,this.end]):MelodyEdits.resize(d.before,n.id,d.edge,snap(this.time(p.x)),[this.start,this.end]);this.h.preview?.(d.preview.find(n=>n.id===d.id));}catch(error){this.h.error?.(error.message);}}
    this.render();}
  up(e){const d=this.drag;if(!d)return;this.drag=null;const p=this.point(e);if(this.node.hasPointerCapture(e.pointerId))this.node.releasePointerCapture(e.pointerId);
    try{if(d.preview&&d.moved)this.commit(d.preview);
      else if(d.kind==='draw'){const snap=v=>e.altKey?v:Math.round(v*4)/4;let a=snap(this.time(d.point.x)),b=d.moved?snap(this.time(p.x)):Math.min(this.end,a+.5);if(a>b)[a,b]=[b,a];if(b-a<.05)b=Math.min(this.end,a+.25);const id=crypto.randomUUID();this.commit(MelodyEdits.add(this.notes,a,b,Math.round(this.pitch(d.point.y)),[this.start,this.end],id));this.selected=new Set([id]);this.h.audition?.(this.notes.find(n=>n.id===id));}
      else if(d.kind==='range'){if(d.moved){const a=this.time(d.point.x),b=this.time(p.x);if(Math.abs(a-b)>.03)this.h.range?.(Math.min(a,b),Math.max(a,b));}else this.h.seek?.(this.time(p.x));}
      else if(!d.moved){const n=this.notes.find(n=>n.id===d.id);this.h.audition?.(n);}
    }catch(error){this.h.error?.(error.message);}this.render();}
  render(){const g=this.geom();if(g.w<1||g.h<1||g.bottom<=g.top)return;const ratio=devicePixelRatio||1,c=this.canvas;c.width=g.w*ratio;c.height=g.h*ratio;const ctx=c.getContext('2d');ctx.scale(ratio,ratio);ctx.fillStyle='#111e22';ctx.fillRect(0,0,g.w,g.h);ctx.font='10px system-ui';
    const ns=this.drag?.preview||this.notes;
    for(let p=Math.ceil(this.low);p<=this.high;p++){const y=this.y(p),black=[1,3,6,8,10].includes((p%12+12)%12);ctx.fillStyle=black?'#16272a':'#1c3031';ctx.fillRect(g.left,y-g.row/2,g.w-g.left,g.row);ctx.fillStyle=black?'#304346':'#b7c9b7';ctx.fillRect(0,y-g.row/2,g.left-2,g.row-1);ctx.fillStyle=black?'#bed0c6':'#15251e';if(g.row>8)ctx.fillText(MelodyEdits.pitchName(p),7,y+3);}
    const step=this.end-this.start>20?5:this.end-this.start>8?2:1;
    ctx.fillStyle='#abc5bc';for(let t=Math.ceil(this.start/step)*step;t<=this.end;t+=step){const x=this.x(t);ctx.fillText(this.h.editable?`${t+1}`:`${t.toFixed(t%1?1:0)}s`,x+2,15);ctx.strokeStyle='#8aa39520';ctx.beginPath();ctx.moveTo(x,20);ctx.lineTo(x,g.bottom);ctx.stroke();}
    if(this.report){const wave=this.report.waveform;ctx.strokeStyle='#77a8a5';ctx.beginPath();for(let i=Math.max(0,Math.floor(this.start/wave.hop_seconds));i<wave.min.length&&i*wave.hop_seconds<=this.end;i++){const x=this.x(i*wave.hop_seconds);ctx.moveTo(x,45+wave.min[i]*23);ctx.lineTo(x,45+wave.max[i]*23);}ctx.stroke();const raw=this.report.raw_pitch;ctx.strokeStyle='#d4e897';ctx.beginPath();let active=false;for(let i=0;i<raw.times.length;i++){const t=raw.times[i],f=raw.f0_hz[i];if(t<this.start||t>this.end||!f){active=false;continue;}const y=this.y(69+12*Math.log2(f/440));if(y<g.top||y>g.bottom){active=false;continue;}if(active)ctx.lineTo(this.x(t),y);else ctx.moveTo(this.x(t),y);active=true;}ctx.stroke();}
    this.layer.replaceChildren();if(!this.contourOnly)for(const n of ns){if(n.end<=this.start||n.start>=this.end)continue;const b=document.createElement('button');b.className='learning-note'+(this.selected.has(n.id)?' selected':'')+(this.highlight.has(n.id)?' highlighted':'');b.dataset.noteId=n.id;b.style.left=this.x(Math.max(n.start,this.start))+'px';b.style.top=(this.y(n.pitch)-Math.max(5,g.row*.65)/2)+'px';b.style.width=Math.max(3,this.x(Math.min(n.end,this.end))-this.x(Math.max(n.start,this.start)))+'px';b.style.height=Math.max(5,g.row*.65)+'px';b.textContent=MelodyEdits.pitchName(n.pitch);b.title=`${MelodyEdits.pitchName(n.pitch)} · ${n.start.toFixed(3)}–${n.end.toFixed(3)} ${this.h.editable?'beats':'source seconds'}`;
      if(this.h.editable)for(const edge of ['start','end']){const handle=document.createElement('span');handle.className='learning-edge '+edge;handle.dataset.edge=edge;b.append(handle);}this.layer.append(b);}
    if(this.contourOnly&&ns.length){ctx.strokeStyle='#d5e995';ctx.lineWidth=2;ctx.beginPath();ns.forEach((n,i)=>i?ctx.lineTo(this.x(n.start),this.y(n.pitch)):ctx.moveTo(this.x(n.start),this.y(n.pitch)));ctx.stroke();}
    if(this.drag?.now&&['range','draw'].includes(this.drag.kind)){ctx.fillStyle='#c1dc8230';ctx.fillRect(this.drag.point.x,g.top,this.drag.now.x-this.drag.point.x,g.bottom-g.top);}
    if(this.cursor!==null&&this.cursor>=this.start&&this.cursor<=this.end){ctx.strokeStyle='#fff0b5';ctx.beginPath();ctx.moveTo(this.x(this.cursor),0);ctx.lineTo(this.x(this.cursor),g.bottom);ctx.stroke();}
  }
}
window.LearningRoll=LearningRoll;
