// Space Templates admin page: list, create, edit, delete
export async function loadSpaceTemplatesPage(pageEl, fetchJson){
  pageEl.innerHTML = '<h2>Space Templates</h2><div id="stToolbar"><button id="btnNew">New template</button></div><div id="stList">Loading…</div><div id="stForm" style="display:none"></div>';
  document.getElementById('btnNew').addEventListener('click', ()=>showForm());
  await refreshList();

  async function refreshList(){
    const listEl = document.getElementById('stList');
    listEl.innerHTML = 'Loading…';
    try{
      const rows = await fetchJson('/logistics/space_templates');
      listEl.innerHTML = rows.map(t=>`<div class="templateRow" data-id="${t.id}"><strong>${t.name}</strong> - ${t.description||''} <button class="edit">edit</button> <button class="del">delete</button><div class="fields">${t.fields.map(f=>`<div class="f">${f.name} (${f.field_type}${f.options?(': '+JSON.stringify(f.options)):''})</div>`).join('')}</div></div>`).join('') || '<p>No templates</p>';
      listEl.querySelectorAll('button.edit').forEach(b=>b.addEventListener('click', (ev)=>{ const id = ev.target.closest('.templateRow').dataset.id; showForm(id); }));
      listEl.querySelectorAll('button.del').forEach(b=>b.addEventListener('click', async (ev)=>{ const id = ev.target.closest('.templateRow').dataset.id; if(!confirm('Delete template '+id+'?')) return; try{ await fetch('/logistics/space_templates/'+id, {method:'DELETE', headers: new Headers({'x-test-user': localStorage.getItem('dev_x_test_user')||''})}); await refreshList(); }catch(err){alert('Delete failed: '+err.message)} }));
    }catch(err){ listEl.innerHTML = '<p class="error">Failed to load templates: '+err.message+'</p>'; }
  }

  function showForm(id){
    const formEl = pageEl.querySelector('#stForm');
    formEl.style.display = 'block';
    formEl.innerHTML = `<h3>${id?'Edit':'New'} template</h3>
      <form id="stFormElm">
        <input name="name" placeholder="Template name" /><br/>
        <input name="description" placeholder="description" /><br/>
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
  fieldsList.innerHTML = fields.map((f,idx)=>`<div class="fieldRow" data-idx="${idx}"><input class="fname" value="${f.name||''}" placeholder="field name" /> <select class="ftype"><option value="text">text</option><option value="number">number</option><option value="select">select</option><option value="user">user</option></select> <input class="foptions" placeholder='options (comma separated for select)' value='${f.options? (Array.isArray(f.options)?f.options.join(', '):f.options) : ''}' /> <button class="rm">Remove</button></div>`).join('') || '<p>No fields</p>';
      fieldsList.querySelectorAll('button.rm').forEach(b=>b.addEventListener('click', (ev)=>{ const idx = Number(ev.target.closest('.fieldRow').dataset.idx); fields.splice(idx,1); renderFields(fields); }));
      // set selected ftype
      fieldsList.querySelectorAll('.fieldRow').forEach((r,idx)=>{ const f = fields[idx]; const sel = r.querySelector('.ftype'); if(sel && f.field_type) sel.value = f.field_type; });
    }
    const form = document.getElementById('stFormElm');
    let fields = [];
    form.querySelector('#addField').addEventListener('click', ()=>{ fields.push({name:'', field_type:'text', options: null}); renderFields(fields); });

    if(id){
      // load existing template
      fetchJson('/logistics/space_templates').then(rows=>{ const t = rows.find(x=>String(x.id)===String(id)); if(!t) return alert('Template not found'); form.name.value = t.name||''; form.description.value = t.description||''; fields = (t.fields||[]).map(f=>({name:f.name, field_type:f.field_type, options:f.options||null})); renderFields(fields); });
    }else{ renderFields([]); }

    form.addEventListener('submit', async (ev)=>{
      ev.preventDefault();
      // collect fields from DOM
      const frows = Array.from(fieldsList.querySelectorAll('.fieldRow'));
      const payloadFields = frows.map(r=>{ const name = r.querySelector('.fname').value; const field_type = r.querySelector('.ftype').value; const optsRaw = r.querySelector('.foptions').value; let opts = null; if(optsRaw){ // parse comma-separated values for select
        opts = optsRaw.split(',').map(x=>x.trim()).filter(x=>x.length>0);
      }
      return { name, field_type, options: opts }; });
      const payload = { name: form.name.value, description: form.description.value, fields: payloadFields };
      try{
        if(id){ await fetch('/logistics/space_templates/'+id, {method:'PATCH', headers: new Headers({'Content-Type':'application/json','x-test-user': localStorage.getItem('dev_x_test_user')||''}), body: JSON.stringify(payload)}); }
        else{ await fetch('/logistics/space_templates', {method:'POST', headers: new Headers({'Content-Type':'application/json','x-test-user': localStorage.getItem('dev_x_test_user')||''}), body: JSON.stringify(payload)}); }
        formEl.style.display='none';
        await refreshList();
      }catch(err){ alert('Save failed: '+err.message) }
    });
  }
}
