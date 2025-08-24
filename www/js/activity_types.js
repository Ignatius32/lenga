// Activity Types admin page: list, create, edit, delete
export async function loadActivityTypes(pageEl, fetchJson){
  pageEl.innerHTML = '<h2>Activity Types</h2><div id="atToolbar"><button id="btnNew">New type</button></div><div id="atList">Loading…</div><div id="atForm" style="display:none"></div>';
  document.getElementById('btnNew').addEventListener('click', ()=>showForm());
  await refreshList();

  async function refreshList(){
    const listEl = document.getElementById('atList');
    listEl.innerHTML = 'Loading…';
    try{
      const rows = await fetchJson('/activities/types');
      listEl.innerHTML = rows.map(t=>`<div class="templateRow" data-id="${t.id}"><strong>${t.name}</strong> - ${t.metadata||''} <button class="edit">edit</button> <button class="del">delete</button><div class="fields">${t.fields.map(f=>`<div class="f">${f.name} (${f.field_type}${f.options?(': '+JSON.stringify(f.options)):''})</div>`).join('')}</div></div>`).join('') || '<p>No activity types</p>';
      listEl.querySelectorAll('button.edit').forEach(b=>b.addEventListener('click', (ev)=>{ const id = ev.target.closest('.templateRow').dataset.id; showForm(id); }));
      listEl.querySelectorAll('button.del').forEach(b=>b.addEventListener('click', async (ev)=>{ const id = ev.target.closest('.templateRow').dataset.id; if(!confirm('Delete activity type '+id+'?')) return; try{ await fetch('/activities/types/'+id, {method:'DELETE', headers: new Headers({'x-test-user': localStorage.getItem('dev_x_test_user')||''})}); await refreshList(); }catch(err){alert('Delete failed: '+err.message)} }));
    }catch(err){ listEl.innerHTML = '<p class="error">Failed to load activity types: '+err.message+'</p>'; }
  }

  function showForm(id){
    const formEl = pageEl.querySelector('#atForm');
    formEl.style.display = 'block';
    formEl.innerHTML = `<h3>${id?'Edit':'New'} activity type</h3>
      <form id="atFormElm">
        <input name="name" placeholder="Type name" /><br/>
        <input name="metadata" placeholder="metadata" /><br/>
        <div id="fieldsEditor">
          <h4>Fields</h4>
          <div id="fieldsList"></div>
          <button id="addField" type="button">Add field</button>
        </div>
        <button type="submit">Save</button>
        <button type="button" id="cancelForm">Cancel</button>
      </form>`;
    document.getElementById('cancelForm').addEventListener('click', ()=>{ formEl.style.display='none' });
    const fieldsList = formEl.querySelector('#fieldsList');
    function renderFields(fields){
      fieldsList.innerHTML = fields.map((f,idx)=>`<div class="fieldRow" data-idx="${idx}"><input class="fname" value="${f.name||''}" placeholder="field name" /> <select class="ftype"><option value="text">text</option><option value="number">number</option><option value="select">select</option><option value="datetime">datetime</option><option value="date">date</option><option value="time">time</option><option value="boolean">boolean</option><option value="space">space</option></select> <input class="foptions" placeholder='options (comma separated for select)' value='${f.options? (Array.isArray(f.options)?f.options.join(', '):f.options) : ''}' /> <button class="rm">Remove</button></div>`).join('') || '<p>No fields</p>';
      fieldsList.querySelectorAll('button.rm').forEach(b=>b.addEventListener('click', (ev)=>{ const idx = Number(ev.target.closest('.fieldRow').dataset.idx); fields.splice(idx,1); renderFields(fields); }));
      // set selected ftype
      fieldsList.querySelectorAll('.fieldRow').forEach((r,idx)=>{ const f = fields[idx]; const sel = r.querySelector('.ftype'); if(sel && f.field_type) sel.value = f.field_type; });
    }
    const form = document.getElementById('atFormElm');
    let fields = [];
    form.querySelector('#addField').addEventListener('click', ()=>{ fields.push({name:'', field_type:'text', options: null}); renderFields(fields); });

    if(id){
      // load existing
      fetch('/activities/types').then(r=>r.json()).then(rows=>{ const t = rows.find(x=>String(x.id)===String(id)); if(!t) return alert('Type not found'); form.name.value = t.name||''; form.metadata.value = t.metadata||''; fields = (t.fields||[]).map(f=>({name:f.name, field_type:f.field_type, options:f.options||null})); renderFields(fields); }).catch(err=>alert('Load failed: '+err.message));
    }else{ renderFields([]); }

    form.addEventListener('submit', async (ev)=>{
      ev.preventDefault();
      const frows = Array.from(fieldsList.querySelectorAll('.fieldRow'));
      const payloadFields = frows.map(r=>{ const name = r.querySelector('.fname').value; const field_type = r.querySelector('.ftype').value; const optsRaw = r.querySelector('.foptions').value; let opts = null; if(optsRaw){ opts = optsRaw.split(',').map(x=>x.trim()).filter(x=>x.length>0); } return { name, field_type, options: opts }; });
      const payload = { name: form.name.value, metadata: form.metadata.value, fields: payloadFields };
      try{
        if(id){ await fetch('/activities/types/'+id, {method:'PATCH', headers: new Headers({'Content-Type':'application/json','x-test-user': localStorage.getItem('dev_x_test_user')||''}), body: JSON.stringify(payload)}); }
        else{ await fetch('/activities/types', {method:'POST', headers: new Headers({'Content-Type':'application/json','x-test-user': localStorage.getItem('dev_x_test_user')||''}), body: JSON.stringify(payload)}); }
        formEl.style.display='none';
        await refreshList();
      }catch(err){ alert('Save failed: '+err.message) }
    });
  }
}
