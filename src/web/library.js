/* A source-level index. No files, predictions or editions are consolidated. */
class RecordingLibrary {
  constructor(h){this.h=h;this.s=h.state;this.$=h.$;this.choices=new Map();this.expanded=new Set();
    this.$('library-search').oninput=()=>this.render();
    for(const id of ['library-artist','library-model','library-category'])this.$(id).onchange=()=>this.render();
    for(const [id,action] of [['corpus-all','all'],['corpus-none','none'],['corpus-invert','invert'],['corpus-select-filtered','filtered'],['corpus-deselect-filtered','unfiltered']])this.$(id).onclick=()=>this.bulk(action);
    this.$('allow-research-corpus').onchange=()=>{if(!this.allowedResearch()){let removed=0;for(const g of this.s.recordings)if(g.category==='research'&&this.s.selected.delete(g.source_hash))removed++;if(removed)this.h.status(`${removed} research recordings removed from corpus selection.`);}this.render();};
  }
  allowedResearch(){return this.$('allow-research-corpus').checked;}
  eligible(g){return g.category==='personal'||this.allowedResearch();}
  groups(){return this.s.recordings||[];}
  versions(g){return g.analysis_ids.map(id=>this.s.library.find(v=>v.id===id)).filter(Boolean);}
  modelKey(v){return `${v.estimator||'F0'} → ${v.model.name==='heuristic'?'stable events':v.model.name}`;}
  modelLabel(v){return `${this.modelKey(v)} · ${v.prediction_id.slice(0,8)}`;}
  filtered(){const search=this.$('library-search').value.trim().toLowerCase(),artist=this.$('library-artist').value,model=this.$('library-model').value,category=this.$('library-category').value;
    return this.groups().filter(g=>(category==='all'||g.category===category)&&(!artist||g.artist===artist)&&(!model||this.versions(g).some(v=>this.modelKey(v)===model))&&(!search||`${g.name} ${g.aliases.join(' ')} ${g.artist} ${g.dataset||''} ${this.versions(g).map(v=>this.modelLabel(v)).join(' ')}`.toLowerCase().includes(search)));
  }
  refreshFilters(){for(const [id,values,empty] of [['library-artist',[...new Set(this.groups().map(g=>g.artist).filter(Boolean))].sort(),'All artists'],['library-model',[...new Set(this.s.library.map(v=>this.modelKey(v)))].sort(),'All models']]){
    const node=this.$(id),previous=node.value;node.replaceChildren(new Option(empty,''));for(const value of values)node.add(new Option(value,value));node.value=values.includes(previous)?previous:'';
  }}
  bulk(action){const filtered=this.filtered(),eligible=this.groups().filter(g=>this.eligible(g));
    if(action==='none')this.s.selected.clear();
    else if(action==='all')eligible.forEach(g=>this.s.selected.add(g.source_hash));
    else if(action==='invert')eligible.forEach(g=>this.s.selected.has(g.source_hash)?this.s.selected.delete(g.source_hash):this.s.selected.add(g.source_hash));
    else for(const g of filtered){if(action==='filtered'&&this.eligible(g))this.s.selected.add(g.source_hash);if(action==='unfiltered')this.s.selected.delete(g.source_hash);}
    this.render();
  }
  corpusIds(){return this.groups().filter(g=>this.s.selected.has(g.source_hash)).map(g=>this.choices.get(g.source_hash)||g.preferred_analysis);}
  count(){const chosen=this.groups().filter(g=>this.s.selected.has(g.source_hash));const songs=new Set(chosen.map(g=>JSON.stringify(g.song_key))).size;
    this.$('corpus-count').textContent=`${chosen.length} recordings · ${songs} songs selected`;
    this.$('corpus-scope').textContent=`All / None / Invert: ${this.allowedResearch()?'all recordings (research explicitly enabled)':'all personal recordings; research excluded'}. Filtered actions: current search and filters.`;
  }
  open(g,id=g.preferred_analysis,reference=null){return this.h.run(async()=>{if(this.s.id!==id){const loaded=await this.h.load(id);if(loaded===false)return;}if(reference){await this.h.openReference(reference);this.h.tab?.('review');}else if(this.s.reference)this.$('reference-working').click();else this.h.tab?.('study');});}
  render(){const parent=this.$('library');parent.replaceChildren();const visible=this.filtered();
    for(const category of ['personal','research']){
      const rows=visible.filter(g=>g.category===category);if(!rows.length)continue;
      const group=document.createElement('section');group.className='library-category';group.dataset.category=category;
      const heading=document.createElement('div');heading.className='library-group-heading';const master=document.createElement('input');master.type='checkbox';master.setAttribute('aria-label',`Include visible ${category} recordings`);
      const count=rows.filter(g=>this.s.selected.has(g.source_hash)).length;master.checked=count===rows.length;master.indeterminate=count>0&&count<rows.length;master.disabled=category==='research'&&!this.allowedResearch();
      master.onchange=()=>{for(const g of rows)master.checked?this.s.selected.add(g.source_hash):this.s.selected.delete(g.source_hash);this.render();};
      heading.append(master,document.createTextNode(`${category==='personal'?'My recordings':'Research datasets'} · ${rows.length}`));group.append(heading);
      for(const g of rows){const card=document.createElement('article');card.className='recording-group'+(this.s.report?.audio.content_sha256===g.source_hash?' current':'');card.dataset.sourceHash=g.source_hash;
        const top=document.createElement('div');top.className='recording-heading';const check=document.createElement('input');check.type='checkbox';check.checked=this.s.selected.has(g.source_hash);check.disabled=!this.eligible(g);check.setAttribute('aria-label',`Include ${g.name} in corpus`);check.title=check.disabled?'Enable research-corpus inclusion explicitly to select this dataset':'Corpus inclusion only; does not open or change the editor';check.onchange=()=>{check.checked?this.s.selected.add(g.source_hash):this.s.selected.delete(g.source_hash);this.render();};
        const title=document.createElement('button');title.className='recording-title';title.textContent=g.name;title.title=`Open recording · source ${g.source_hash}`;title.onclick=()=>this.open(g,this.choices.get(g.source_hash)||g.preferred_analysis);
        const expand=document.createElement('button');expand.className='versions-toggle';expand.textContent=this.expanded.has(g.source_hash)?'▾':'▸';expand.title='Show every model run, working correction and human reference';expand.setAttribute('aria-label',`Versions of ${g.name}`);expand.setAttribute('aria-expanded',this.expanded.has(g.source_hash));expand.onclick=()=>{this.expanded.has(g.source_hash)?this.expanded.delete(g.source_hash):this.expanded.add(g.source_hash);this.render();};top.append(check,title,expand);card.append(top);
        const info=document.createElement('p');info.className='recording-info';info.textContent=`${g.artist||'Artist not set'} · ${g.duration.toFixed(1)} s`;const technical=document.createElement('span');technical.className='library-technical';technical.textContent=` · ${g.analysis_ids.length} model runs${g.references.length?' · '+g.references.length+' refs':''}`;info.append(technical);card.append(info);
        if(this.expanded.has(g.source_hash)){
          const versions=document.createElement('div');versions.className='recording-versions';
          for(const v of this.versions(g)){const b=document.createElement('button');b.className='analysis-version';b.dataset.analysisId=v.id;b.textContent=this.modelLabel(v);b.title='Choose model backdrop; saved working corrections stay separate from raw predictions';b.onclick=()=>this.open(g,v.id);versions.append(b);}
          if(g.working_revision){const b=document.createElement('button');b.className='working-version';b.textContent='Working correction · '+g.working_revision.slice(0,16);b.onclick=()=>this.open(g);versions.append(b);}
          for(const r of g.references){const b=document.createElement('button');b.className='human-version';b.dataset.referenceId=r.id;b.textContent=`${r.annotator} · ${r.review.status} · ${r.excerpt.start.toFixed(2)}–${r.excerpt.end.toFixed(2)} s`;b.title=`Independent reference ${r.id}`;b.onclick=()=>this.open(g,g.preferred_analysis,r.id);versions.append(b);}
          const label=document.createElement('label');label.textContent='Corpus analysis (saved working edition)';const choice=document.createElement('select');choice.setAttribute('aria-label',`Corpus analysis for ${g.name}`);for(const v of this.versions(g))choice.add(new Option(this.modelLabel(v),v.id));choice.value=this.choices.get(g.source_hash)||g.preferred_analysis;choice.onchange=()=>this.choices.set(g.source_hash,choice.value);label.append(choice);versions.append(label);card.append(versions);
        }
        group.append(card);
      }
      parent.append(group);
    }
    if(!visible.length)parent.textContent='No recordings match these filters.';this.count();
  }
}
window.RecordingLibrary=RecordingLibrary;
