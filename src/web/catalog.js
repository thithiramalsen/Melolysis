/* Identity sidecar editor: opening/saving never loads a different audio/editor. */
class CatalogUI {
 constructor(h){this.h=h;this.dialog=document.createElement('dialog');this.dialog.id='catalog-dialog';
 this.dialog.innerHTML=`<form method="dialog"><h2>Song / artist associations</h2><p id="catalog-source"></p><p id="catalog-suggestions" class="muted"></p>
 <label>Recording<select id="catalog-recording"></select></label>
 <label>Artist / performer<select id="catalog-artists"></select></label><details><summary>Additional performers (optional)</summary><label>Other credited performers<select id="catalog-additional-artists" multiple size="3"></select></label></details>
 <p>No artist selected means unresolved. Performer credit does not establish authorship.</p><button type="button" id="catalog-clear-artists">Leave artist unknown</button>
 <label>Add artist<input id="catalog-new-artist" maxlength="200" placeholder="Optional new artist name"></label>
 <label>Musical work<select id="catalog-work"></select></label>
 <label>Add a different work<input id="catalog-new-work" maxlength="200" placeholder="Optional new song/work title"></label>
 <label>Take / version<input id="catalog-take" maxlength="200" placeholder="e.g. live take, chorus excerpt"></label>
 <label>Primary analysis edition<select id="catalog-edition"></select></label>
 <p>Choose the same work for different takes or excerpts of one song. Sections and beat maps stay on each recording's own timeline.</p>
 <output id="catalog-result" aria-live="polite"></output><div class="catalog-actions">
 <button type="button" id="catalog-preview">Preview count changes</button><button type="button" id="catalog-save" class="primary">Save associations</button><button value="cancel">Close</button></div>
 <details><summary>Pin reproducible input snapshot</summary><p>Uses the library's selected recordings and primary analysis editions. Research requires the explicit research-corpus opt-in.</p><button type="button" id="catalog-snapshot">Save selected input snapshot</button><output id="catalog-snapshot-result"></output></details></form>`;
 document.body.append(this.dialog);this.$=id=>this.dialog.querySelector('#'+id);
 this.$('catalog-recording').onchange=()=>this.select(this.$('catalog-recording').value);
 this.$('catalog-clear-artists').onclick=()=>{this.$('catalog-artists').value='';for(const o of this.$('catalog-additional-artists').options)o.selected=false;this.$('catalog-new-artist').value='';};
 this.$('catalog-preview').onclick=()=>this.action(true);this.$('catalog-save').onclick=()=>this.action(false);
 this.$('catalog-snapshot').onclick=()=>this.guard(async()=>{const ids=this.h.state.recordings.filter(g=>this.h.state.selected.has(g.source_hash)).map(g=>g.preferred_analysis);const result=await this.h.api('corpus-save',{ids,catalog_revision:this.value.revision,purpose:document.getElementById('allow-research-corpus').checked?'research':'artist'});this.$('catalog-snapshot-result').textContent=`Pinned snapshot ${result.id} (${result.counts.works} confirmed works).`;});
 }
 async guard(fn){try{await fn();}catch(e){this.$('catalog-result').textContent=e.message;}}
 async open(source){await this.guard(async()=>{this.value=await this.h.api('catalog-get',{});this.$('catalog-recording').replaceChildren(...this.value.recordings.map(g=>new Option(`${g.name} (${g.source_hash.slice(0,8)})`,g.source_hash)));this.select(source);this.dialog.showModal();});}
 select(source){this.source=source;this.$('catalog-recording').value=source;const g=this.value.recordings.find(g=>g.source_hash===source);if(!g)return;
 this.$('catalog-source').textContent=`${g.name} · ${g.identity_status} · ${g.recording_id}`;
 this.$('catalog-suggestions').textContent=`Legacy metadata, unconfirmed: artist “${g.metadata_suggestions.artist||'unknown'}”, title “${g.metadata_suggestions.song}”. Nothing is inferred from these names.`;
 this.$('catalog-artists').replaceChildren(new Option('Unresolved artist — choose one',''),...Object.values(this.value.artists).map(a=>new Option(a.name,a.id)));this.$('catalog-artists').value=g.artist_ids[0]||'';
 this.$('catalog-additional-artists').replaceChildren(...Object.values(this.value.artists).map(a=>{const o=new Option(a.name,a.id);o.selected=g.artist_ids.slice(1).includes(a.id);return o;}));
 this.$('catalog-work').replaceChildren(new Option('Unresolved work',''),...Object.values(this.value.works).map(w=>new Option(w.title,w.id)));this.$('catalog-work').value=g.work_id||'';
 this.$('catalog-edition').replaceChildren(...g.editions.map(e=>new Option(`${e.model.name} · ${e.id.slice(0,8)}${e.correction_revision?' · working correction':''}`,e.analysis_id)));this.$('catalog-edition').value=g.preferred_analysis;
 this.$('catalog-take').value=g.take;for(const id of ['catalog-new-artist','catalog-new-work'])this.$(id).value='';this.$('catalog-result').textContent='';
 }
 async action(dry_run){this.$('catalog-save').disabled=true;this.$('catalog-preview').disabled=true;this.$('catalog-result').textContent=dry_run?'Checking…':'Saving associations…';try{await this.guard(async()=>{const data={base_revision:this.value.revision,source_hash:this.source,artist_ids:[...new Set([this.$('catalog-artists').value,...[...this.$('catalog-additional-artists').selectedOptions].map(o=>o.value)].filter(Boolean))],work_id:this.$('catalog-work').value,new_artist:this.$('catalog-new-artist').value,new_work:this.$('catalog-new-work').value,take:this.$('catalog-take').value,preferred_analysis:this.$('catalog-edition').value,dry_run};const result=await this.h.api('catalog-reconcile',data);
 if(dry_run){this.$('catalog-result').textContent=`Preview only: ${result.before.works} → ${result.after.works} confirmed works; ${result.after.unresolved_recordings} unresolved recordings. No files written.`;return;}
 this.value=result;this.select(data.source_hash);const g=result.recordings.find(g=>g.source_hash===data.source_hash);this.$('catalog-result').textContent=`Associations saved. ${g.artist||'Unresolved artist'} · ${g.work_title||'Unresolved work'}. ${result.counts.works} confirmed works; ${result.counts.unresolved_recordings} unresolved recordings.`;await this.h.refresh();this.h.status('Associations saved for '+g.name+'.');
 });}finally{this.$('catalog-save').disabled=false;this.$('catalog-preview').disabled=false;this.$('catalog-result').scrollIntoView({block:'nearest'});}}
}
window.CatalogUI=CatalogUI;
