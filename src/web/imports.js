"use strict";
// Transfer progress and durable server jobs are separate: inference has no invented percentage.
window.ImportQueue=class ImportQueue {
  constructor({$,api,run,refresh,load,state,status,isDirty,onAttempt}) {
    Object.assign(this,{$,api,run,refresh,load,state,status,isDirty,onAttempt});
    this.jobs=[];this.transfers=new Map();this.openWhenReady=new Map();this.handled=new Set();
    this.dismissed=new Set(JSON.parse(sessionStorage.getItem('dismissed-imports')||'[]'));
    this.poll();this.timer=setInterval(()=>this.poll(),1500);
  }
  async submit(file,request) {
    const name=file.name,key=crypto.randomUUID();
    if(!file.size)throw new Error(`${name}: the file is empty.`);
    if(file.size>256*1024*1024)throw new Error(`${name}: upload limit is 256 MiB.`);
    if(!/\.(wav|mp3|flac|m4a|ogg|aac)$/i.test(name))throw new Error('Choose WAV, FLAC, MP3, M4A, OGG or AAC audio.');
    const row={id:key,name,status:'uploading',progress:0};this.transfers.set(key,row);this.render();
    try {
      const upload=await new Promise((resolve,reject)=>{
        const xhr=new XMLHttpRequest();xhr.open('POST','/api/import?name='+encodeURIComponent(name));
        xhr.setRequestHeader('Content-Type','application/octet-stream');
        xhr.upload.onprogress=e=>{row.progress=e.lengthComputable?Math.round(e.loaded/e.total*100):null;this.render();};
        xhr.upload.onload=()=>{row.status='uploaded';this.render();};
        xhr.onload=()=>{let data;try{data=JSON.parse(xhr.responseText);}catch{reject(new Error('Upload returned an invalid response. Check that the server is running.'));return;}
          xhr.status>=200&&xhr.status<300?resolve(data):reject(new Error(data.error||'Upload failed'));};
        xhr.onerror=()=>reject(new Error('Connection lost while uploading. Check the local server, then choose the file again.'));
        xhr.send(file);
      });
      row.status='queued';this.render();
      const job=await this.api('import-start',{...request,upload_id:upload.upload_id});
      this.openWhenReady.set(job.id,{id:this.state.id,attempt:request.metadata.tags.includes('practice-attempt')});
      this.dismissed.delete(job.id);this.handled.delete(job.id);
      this.jobs=[job,...this.jobs.filter(j=>j.id!==job.id)];this.transfers.delete(key);this.render();
      await this.poll();return job;
    }catch(error){row.status='failed';row.error=error.message;this.render();throw error;}
  }
  async poll() {
    if(this.polling)return;this.polling=true;
    try {
      const jobs=await this.api('import-jobs');this.connectionError=false;
      const changed=jobs.filter(j=>j.status==='complete'&&!this.handled.has(j.id));
      this.jobs=jobs;this.render();
      if(changed.length){
        await this.refresh();
        for(const job of changed){
          this.handled.add(job.id);
          const pending=this.openWhenReady.get(job.id);this.openWhenReady.delete(job.id);
          // Background completions must never discard edits or steal a different open song.
          if(pending&&pending.id===this.state.id&&!this.isDirty()) {
            if(await this.load(job.analysis_id)!==false&&pending.attempt)await this.onAttempt(job.analysis_id);
          }
        }
      }
    }catch(error){this.connectionError=true;this.render();}
    finally{this.polling=false;}
  }
  render() {
    const host=this.$('import-progress');if(!host)return;
    const jobs=[...this.transfers.values(),...this.jobs.filter(j=>!this.dismissed.has(j.id))];
    host.hidden=!jobs.length&&!this.connectionError;host.replaceChildren();
    if(this.connectionError){const p=document.createElement('p');p.textContent='Cannot check import status. Reconnecting automatically…';host.append(p);}
    for(const job of jobs){
      const row=document.createElement('div');row.className='import-job';row.dataset.job=job.id;row.dataset.status=job.status;
      const title=document.createElement('strong');title.textContent=job.name;row.append(title);
      const message=document.createElement('span');
      const elapsed=Math.max(0,Math.floor((Date.now()-Date.parse(job.created))/1000));
      message.textContent=job.status==='uploading'?`Uploading · ${job.progress??'…'}${job.progress===null?'':'%'}`:
        job.status==='uploaded'?'File uploaded · confirming receipt…':job.status==='queued'?'File uploaded · waiting to process':
        job.status==='processing'?`File uploaded · transcribing · ${elapsed}s elapsed. CPU processing can take several minutes; no refresh needed.`:
        job.status==='complete'?'Ready · added to your song library':`${job.status==='interrupted'?'Interrupted':'Failed'} · ${job.error}`;
      row.append(message);
      if(['uploading','uploaded','queued','processing'].includes(job.status)){
        const progress=document.createElement('progress');progress.max=100;progress.setAttribute('aria-label',job.name+' import progress');
        if(job.status==='uploading'&&job.progress!==null)progress.value=job.progress;
        row.append(progress);
      }
      const button=(label,action)=>{const b=document.createElement('button');b.textContent=label;b.onclick=()=>this.run(action);row.append(b);};
      if(job.status==='complete')button('Open song',()=>this.load(job.analysis_id));
      if(['failed','interrupted'].includes(job.status)&&job.request)button('Retry processing',async()=>{
        const next=await this.api('import-start',job.request);this.dismissed.add(job.id);this.jobs=[next,...this.jobs.filter(j=>j.id!==next.id)];this.render();await this.poll();
      });
      if(['complete','failed','interrupted'].includes(job.status))button('Dismiss',async()=>{
        this.transfers.delete(job.id);this.dismissed.add(job.id);sessionStorage.setItem('dismissed-imports',JSON.stringify([...this.dismissed]));this.render();
      });
      host.append(row);
    }
  }
};
