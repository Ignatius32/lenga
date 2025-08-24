export async function loadTicketTypes(pageEl, fetchJson){
  pageEl.innerHTML = `<h2>Ticket Types</h2>
    <div id="ttToolbar"><button id="btnNewTT">New Ticket Type</button></div>
    <div id="ttList">Loading…</div>
    <div id="ttForm" style="display:none;margin-top:1rem"></div>`;

  const listEl = pageEl.querySelector('#ttList');
  const formEl = pageEl.querySelector('#ttForm');

  async function refresh(){
    listEl.innerHTML = 'Loading…';
    try{
      const [tts, queues, groups] = await Promise.all([fetchJson('/admin/ticket_types'), fetchJson('/admin/queues'), fetchJson('/admin/groups')]);
  const qMap = Object.fromEntries(queues.map(q=>[q.id, q.name]));
  const gMap = Object.fromEntries(groups.map(g=>[g.id, g.name]));
  listEl.innerHTML = `<table class="ttTable"><thead><tr><th>ID</th><th>Name</th><th>Queue</th><th>Fields</th><th>Allowed Groups</th><th>Actions</th></tr></thead><tbody>${tts.map(tt=>`<tr data-id="${tt.id}"><td>${tt.id}</td><td>${tt.name}</td><td>${qMap[tt.queue_id]||tt.queue_id}</td><td>${(tt.fields||[]).length}</td><td>${(tt.allowed_group_ids||[]).map(gid=>gMap[gid]||gid).join(', ')}</td><td><button class="editTT" data-id="${tt.id}">Edit</button> <button class="delTT" data-id="${tt.id}">Delete</button></td></tr>`).join('')}</tbody></table>`;

      // wire actions
      listEl.querySelectorAll('button.editTT').forEach(b=>b.addEventListener('click',(ev)=>{ showForm(Number(ev.target.dataset.id)); }));
      listEl.querySelectorAll('button.delTT').forEach(b=>b.addEventListener('click', async (ev)=>{
        const id = Number(ev.target.dataset.id);
        if(!confirm('Delete ticket type '+id+'? This will fail if tickets reference it.')) return;
        try{
          await fetch('/admin/ticket_types/'+id, { method: 'DELETE', headers: new Headers({'x-test-user': localStorage.getItem('dev_x_test_user')||''}) });
          await refresh();
        }catch(err){ alert('Delete failed: '+err.message) }
      }));
    }catch(err){ listEl.innerHTML = '<p class="error">Failed to load ticket types: '+err.message+'</p>' }
  }

  function emptyFieldRow(){
    return { id: null, name: '', field_type: 'text', options: [] };
  }

  function renderFieldEditor(fieldsContainer, idx, f){
    const row = document.createElement('div');
    row.style.border = '1px solid #eee';
    row.style.padding = '6px';
    row.style.marginBottom = '4px';
    row.innerHTML = `
      <input class="fieldName" placeholder="Field name" value="${f.name||''}" />
      <select class="fieldType"><option value="text">text</option><option value="select">select</option><option value="space">space</option></select>
      <span class="fieldOptions" style="display:none">Options (comma separated): <input class="fieldOptionsInput" value="${(f.options||[]).join(',')||''}" /></span>
      <button class="removeField">Remove</button>
    `;
    const select = row.querySelector('.fieldType'); select.value = f.field_type || 'text';
    const optsSpan = row.querySelector('.fieldOptions');
    function updateOptsVisibility(){ if(select.value==='select'){ optsSpan.style.display='inline'; } else { optsSpan.style.display='none'; } }
    updateOptsVisibility();
    select.addEventListener('change', updateOptsVisibility);
    row.querySelector('.removeField').addEventListener('click', ()=>{ fieldsContainer.removeChild(row); });
    return row;
  }

  async function showForm(id){
    formEl.style.display = 'block';
    formEl.innerHTML = '<p>Loading form…</p>';
    try{
      const [queues, groups] = await Promise.all([fetchJson('/admin/queues'), fetchJson('/admin/groups')]);
      let tt = { id: null, name: '', queue_id: '', allowed_group_ids: [], fields: [] };
      if(id){ tt = await fetchJson('/admin/ticket_types/'+id); }
      // build form
      formEl.innerHTML = '';
      const form = document.createElement('div');
      form.innerHTML = `<div><label>Name: <input id="ttName" value="${tt.name||''}" /></label></div>
        <div><label>Queue: <select id="ttQueue">${queues.map(q=>`<option value="${q.id}" ${q.id===tt.queue_id? 'selected':''}>${q.name}</option>`).join('')}</select></label></div>
        <div><label>Allowed Groups: <select id="ttGroups" multiple style="min-width:200px">${groups.map(g=>`<option value="${g.id}" ${ (tt.allowed_group_ids||[]).includes(g.id) ? 'selected' : '' }>${g.name}</option>`).join('')}</select></label></div>
        <h4>Fields</h4><div id="fieldsContainer"></div><div><button id="addField">Add Field</button></div>
        <div style="margin-top:0.6rem"><button id="saveTT">Save</button> <button id="cancelTT">Cancel</button></div>`;
      formEl.appendChild(form);
      const fieldsContainer = form.querySelector('#fieldsContainer');
      (tt.fields||[]).forEach(f => { fieldsContainer.appendChild(renderFieldEditor(fieldsContainer, null, f)); });
      form.querySelector('#addField').addEventListener('click', ()=>{ fieldsContainer.appendChild(renderFieldEditor(fieldsContainer, null, emptyFieldRow())); });
      form.querySelector('#cancelTT').addEventListener('click', ()=>{ formEl.style.display='none'; });
      form.querySelector('#saveTT').addEventListener('click', async ()=>{
        // gather payload
        const payload = { name: form.querySelector('#ttName').value.trim(), queue_id: Number(form.querySelector('#ttQueue').value), allowed_group_ids: Array.from(form.querySelector('#ttGroups').selectedOptions).map(o=>Number(o.value)), fields: [] };
        const rows = fieldsContainer.querySelectorAll('div');
        rows.forEach(r=>{
          const name = r.querySelector('.fieldName').value.trim();
          const field_type = r.querySelector('.fieldType').value;
          const optsVal = r.querySelector('.fieldOptionsInput') ? r.querySelector('.fieldOptionsInput').value.trim() : '';
          const options = optsVal ? optsVal.split(',').map(s=>s.trim()).filter(Boolean) : undefined;
          if(name){ payload.fields.push({ name, field_type, options }); }
        });

        try{
          if(id){
            // update
            await fetch('/admin/ticket_types/'+id, { method: 'PUT', headers: new Headers({'Content-Type':'application/json','x-test-user': localStorage.getItem('dev_x_test_user')||''}), body: JSON.stringify(payload) });
          }else{
            await fetch('/admin/ticket_types', { method: 'POST', headers: new Headers({'Content-Type':'application/json','x-test-user': localStorage.getItem('dev_x_test_user')||''}), body: JSON.stringify(payload) });
          }
          formEl.style.display='none';
          await refresh();
        }catch(err){ alert('Save failed: '+err.message) }
      });

    }catch(err){ formEl.innerHTML = '<p class="error">Failed to load form: '+err.message+'</p>' }
  }

  document.getElementById('btnNewTT').addEventListener('click', ()=>showForm(null));

  await refresh();
}
