/* One original-vocal media element and one local reference-tone bus. No vocal synthesis. */
class VocalAudition {
  constructor(audio,notify){
    this.audio=audio;this.notify=notify;this.mode='auto';this.pianoVolume=.25;this.vocalVolume=.8;
    this.context=null;this.segment=null;this.nodes=[];this.token=0;this.lastTone=null;this.startedTones=0;
    this.sessions=new Map();this.main=null;this.workspace=null;
    this.pitchPreservation=('preservesPitch' in audio)||('webkitPreservesPitch' in audio);
    if('preservesPitch' in audio)audio.preservesPitch=true;
    if('webkitPreservesPitch' in audio)audio.webkitPreservesPitch=true;
    audio.addEventListener('pause',()=>this.stopTone());
    audio.addEventListener('seeked',()=>{if(this.segment&&!audio.paused)this.scheduleSegmentTone();});
  }
  async ensure(){
    if(!this.context){
      this.context=new AudioContext({latencyHint:'interactive'});
      this.pianoGain=this.context.createGain();this.vocalGain=this.context.createGain();
      this.pianoMeter=this.context.createAnalyser();this.vocalMeter=this.context.createAnalyser();
      this.pianoMeter.fftSize=8192;this.vocalMeter.fftSize=8192;
      this.pianoMeter.smoothingTimeConstant=0;this.vocalMeter.smoothingTimeConstant=0;
      this.pianoGain.connect(this.pianoMeter);this.pianoMeter.connect(this.context.destination);
      this.source=this.context.createMediaElementSource(this.audio);this.source.connect(this.vocalGain);
      this.vocalGain.connect(this.vocalMeter);this.vocalMeter.connect(this.context.destination);
      this.setVolumes(this.pianoVolume,this.vocalVolume);
    }
    await this.context.resume();return this.context;
  }
  setVolumes(piano,vocal){
    this.pianoVolume=piano;this.vocalVolume=vocal;
    if(this.context){this.pianoGain.gain.setTargetAtTime(piano*.22,this.context.currentTime,.01);this.vocalGain.gain.setTargetAtTime(vocal,this.context.currentTime,.01);}
  }
  stopTone(){for(const node of this.nodes){try{node.stop();}catch{}try{node.disconnect();}catch{}}this.nodes=[];}
  tone(pitch,duration=.65,delay=0,append=false){
    if(!this.context)return;if(!append)this.stopTone();const frequency=MelodyEdits.hz(pitch),at=this.context.currentTime+Math.max(0,delay);
    const envelope=this.context.createGain();envelope.gain.setValueAtTime(0,at);
    envelope.gain.linearRampToValueAtTime(.8,at+Math.min(.012,duration*.2));envelope.gain.exponentialRampToValueAtTime(.36,at+Math.min(.15,duration*.6));
    envelope.gain.setTargetAtTime(.00001,at+Math.max(.02,duration-.04),.015);envelope.connect(this.pianoGain);
    // A gentle local additive piano-like reference. Fundamental is exactly A440 * 2^((p-69)/12).
    for(const [ratio,level] of [[1,1],[2,.14],[3,.04]]){
      if(frequency*ratio>=this.context.sampleRate/2)continue;
      const osc=this.context.createOscillator(),gain=this.context.createGain();osc.frequency.value=frequency*ratio;gain.gain.value=level;
      osc.connect(gain);gain.connect(envelope);osc.start(at);osc.stop(at+duration+.08);this.nodes.push(osc);
      osc.onended=()=>{osc.disconnect();gain.disconnect();};
    }
    setTimeout(()=>envelope.disconnect(),(delay+duration+.15)*1000);
    this.lastTone={pitch,frequency,scheduled_context_time:at,duration};this.startedTones++;
  }
  async pauseVocal(){
    if(this.audio.paused)return;
    await new Promise(resolve=>{this.audio.addEventListener('pause',resolve,{once:true});this.audio.pause();});
  }
  async piano(pitch){this.pauseMain();await this.ensure();this.cancelSegment();const token=this.token;await this.pauseVocal();if(token!==this.token)return;this.tone(pitch);this.notify(`Piano reference · ${MelodyEdits.pitchName(pitch)} · ${MelodyEdits.hz(pitch).toFixed(2)} Hz — listening aid, not annotation truth`);}
  cancelSegment(){this.token++;this.segment=null;this.sequenceInfo=null;this.stopTone();}
  async waitForSeek(time){
    if(Math.abs(this.audio.currentTime-time)<.00001)return;
    await new Promise((resolve,reject)=>{
      const timer=setTimeout(()=>{cleanup();reject(Error('Audio seek timed out; verify the source codec.'));},4000);
      const cleanup=()=>{clearTimeout(timer);this.audio.removeEventListener('seeked',done);this.audio.removeEventListener('error',failed);};
      const done=()=>{cleanup();resolve();},failed=()=>{cleanup();reject(Error('Source audio could not be decoded.'));};
      this.audio.addEventListener('seeked',done,{once:true});this.audio.addEventListener('error',failed,{once:true});this.audio.currentTime=time;
    });
  }
  async note(note,{pre=.06,post=.08,loop=false,mode=this.mode}={}){
    if(mode==='auto')mode='vocal';
    if(mode==='piano'){await this.piano(note.pitch);return;}
    this.pauseMain();await this.ensure();this.cancelSegment();this.audio.pause();const token=this.token;
    const [start,end]=MelodyEdits.segment(note,pre,post,this.audio.duration);
    await this.waitForSeek(start);if(token!==this.token)return;
    this.segment={start,end,note:{...note},loop,mode};
    await this.audio.play();if(token!==this.token)return;
    this.scheduleSegmentTone();
    this.notify(`${mode==='both'?'Both: original vocal + piano reference':'Original vocal'} · source ${start.toFixed(4)}–${end.toFixed(4)} s${loop?' · loop':''}. Vocal audio is unmodified.`);
  }
  scheduleSegmentTone(){
    const s=this.segment;if(!s||s.mode!=='both'||!this.context)return;
    const now=this.audio.currentTime,rate=this.audio.playbackRate;
    if(now>=s.note.end){this.stopTone();return;}
    this.tone(s.note.pitch,Math.max(.02,(s.note.end-Math.max(now,s.note.start))/rate),Math.max(0,(s.note.start-now)/rate));
  }
  async keyboard(pitch){await this.piano(pitch);}
  async sequence(notes,tempo=100){
    MelodyEdits.validate(notes,[0,256]);if(notes.length>200||!Number.isFinite(tempo)||tempo<20||tempo>300)throw Error('Invalid reference sequence');
    this.pauseMain();await this.ensure();this.cancelSegment();await this.pauseVocal();const origin=this.context.currentTime+.06;
    for(const n of notes)this.tone(n.pitch,(n.end-n.start)*60/tempo,.06+n.start*60/tempo,true);
    this.sequenceInfo={started_context_time:origin,end_context_time:origin+Math.max(0,...notes.map(n=>n.end))*60/tempo,
      tempo,frequencies:notes.map(n=>MelodyEdits.hz(n.pitch))};
    this.notify('Your melody · local piano reference · original vocal unchanged');return this.sequenceInfo;
  }
  full(){return this.toggleVocal('review:song:'+this.audio.src,0,this.audio.duration,false,true);}
  async range(start,end,loop=false){
    this.pauseMain();await this.ensure();this.cancelSegment();this.audio.pause();const token=this.token;
    await this.waitForSeek(start);if(token!==this.token)return;
    this.segment={start,end,loop,mode:'vocal',note:{start,end}};await this.audio.play();this.notify(`Original vocal range · ${start.toFixed(3)}–${end.toFixed(3)} source seconds${loop?' · loop':''}`);
  }
  position(){const s=this.main;if(!s)return this.audio.currentTime;
    if(!s.playing||s.pending)return s.position;
    if(s.kind==='vocal')return this.audio.currentTime;
    return Math.min(s.end,s.position+Math.max(0,this.context.currentTime-(s.clock??this.context.currentTime)));}
  pauseMain(){const s=this.main;if(s?.playing){s.position=this.position();s.playing=false;s.pending=false;s.clock=null;this.token++;if(s.kind==='vocal')this.audio.pause();this.stopTone();}}
  pauseAll(){this.pauseMain();this.cancelSegment();this.audio.pause();}
  activateWorkspace(name){if(this.workspace!==name){this.pauseAll();this.main=null;this.workspace=name;}}
  selectMain(spec){
    const signature=JSON.stringify([spec.start,spec.end,spec.notes,spec.tempo,spec.url]);
    if(this.main?.key!==spec.key)this.pauseAll();
    let s=this.sessions.get(spec.key);
    if(!s){s={...spec,signature,position:spec.position??spec.start,playing:false};this.sessions.set(spec.key,s);}
    else if(s.signature!==signature){this.pauseAll();const position=spec.resetOnChange?spec.start:MelodyEdits.clamp(s.position,spec.start,spec.end);Object.assign(s,spec,{signature,position,playing:false,clock:null});}
    s.loop=spec.loop;this.main=s;return s;
  }
  toggleVocal(key,start,end,loop=false,fromCursor=false){
    if(!Number.isFinite(start+end)||end<=start)throw Error('Wait for audio to load and choose valid playback bounds.');
    const s=this.selectMain({key,kind:'vocal',start,end,loop,url:this.audio.src,resetOnChange:true,
      position:fromCursor?MelodyEdits.clamp(this.audio.currentTime,start,end):start});
    return s.playing?this.pauseAll():this.playMain();
  }
  toggleSequence(key,notes,tempo=100,loop=false){
    MelodyEdits.validate(notes,[0,256]);if(!notes.length)throw Error('Draw some original notes first.');
    if(notes.length>200||!Number.isFinite(tempo)||tempo<20||tempo>300)throw Error('Invalid reference sequence');
    const s=this.selectMain({key,kind:'sequence',start:0,end:Math.max(...notes.map(n=>n.end))*60/tempo,notes:MelodyEdits.clone(notes),tempo,loop});
    return s.playing?this.pauseAll():this.playMain();
  }
  async playMain(){
    const s=this.main;if(!s)return;this.cancelSegment();const token=this.token;s.playing=true;s.pending=true;
    if(s.position>=s.end-.001)s.position=s.start;
    await this.ensure();if(token!==this.token||this.main!==s||!s.playing)return;
    await this.pauseVocal();if(token!==this.token||!s.playing)return;
    if(s.kind==='vocal'){
      await this.waitForSeek(s.position);if(token!==this.token||!s.playing)return;
      s.pending=false;await this.audio.play();this.notify(`${s.key.startsWith('review:')?'Complete original recording':'Original vocal transport'} · ${s.position.toFixed(3)} source seconds`);
    }else{
      const delay=.035;s.clock=this.context.currentTime+delay;s.pending=false;
      for(const n of s.notes){const a=n.start*60/s.tempo,b=n.end*60/s.tempo;if(b<=s.position)continue;
        this.tone(n.pitch,b-Math.max(a,s.position),delay+Math.max(0,a-s.position),true);}
      this.sequenceInfo={started_context_time:s.clock-s.position,end_context_time:s.clock+s.end-s.position,tempo:s.tempo,
        frequencies:s.notes.map(n=>MelodyEdits.hz(n.pitch))};
      this.notify('Your melody · piano transport · pause/resume keeps your position');
    }
  }
  async seek(time){
    const s=this.main;if(!s){this.cancelSegment();this.audio.currentTime=time;return;}
    const playing=s.playing;this.pauseAll();s.position=MelodyEdits.clamp(time,s.start,s.end);
    if(s.kind==='vocal')await this.waitForSeek(s.position);
    if(playing)await this.playMain();
  }
  stop(reset=null){this.pauseAll();if(this.main){this.main.position=reset===null?this.main.start:MelodyEdits.clamp(reset,this.main.start,this.main.end);if(this.main.kind==='vocal')this.audio.currentTime=this.main.position;}else if(reset!==null)this.audio.currentTime=reset;}
  stopContext(key,reset=null){this.pauseAll();this.main=this.sessions.get(key)||null;this.stop(reset);}
  speed(rate){
    if(!this.pitchPreservation&&rate!==1)throw Error('This browser does not expose pitch-preserving playback. Use 1×.');
    this.audio.playbackRate=rate;if(this.segment&&!this.audio.paused)this.scheduleSegmentTone();
  }
  tick(){
    const main=this.main;if(main?.playing&&this.position()>=main.end-.001){
      this.pauseMain();main.position=main.loop?main.start:main.end;
      if(main.loop)this.playMain().catch(e=>this.notify(e.message));
    }
    if(this.segment&&!this.audio.paused&&this.audio.currentTime>=this.segment.end){
      const s=this.segment;if(s.loop){this.stopTone();this.audio.currentTime=s.start;}else {this.segment=null;if(Number.isFinite(s.thenPiano))this.piano(s.thenPiano).catch(e=>this.notify(e.message));else this.audio.pause();}
    }
  }
  timing(){return this.context?{sampleRate:this.context.sampleRate,baseLatency:this.context.baseLatency,outputLatency:this.context.outputLatency??null,
    note:'Reported device latency is informational, not calibrated. Both mode shares one media source and AudioContext; exact acoustic alignment is browser/device dependent.'}:{note:'Audio starts only after a user gesture.'};}
}
window.VocalAudition=VocalAudition;
