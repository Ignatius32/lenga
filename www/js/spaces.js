// Spaces page: list and create spaces; allow selecting a Space Template
export async function loadSpacesPage(pageEl, fetchJson){
  pageEl.innerHTML = '<h2>Spaces</h2><div id="spacesToolbar"><button id="btnNew">New space</button></div><div id="spacesList">Loading…</div><div id="spacesForm" style="display:none"></div>';
  document.getElementById('btnNew').addEventListener('click', ()=>showForm());
  await refreshList();

  // renderFieldInput used by both create and edit forms
  function renderFieldInput(f, idx){
    if(f.field_type === 'select'){
      const opts = (f.options||[]);
      return `<select data-idx="${idx}" class="tfinput">${opts.map(o=>`<option value="${o}">${o}</option>`).join('')}</select>`;
    }
    return `<input data-idx="${idx}" class="tfinput" placeholder="${f.field_type}" />`;
  }

  async function refreshList(){
    const listEl = document.getElementById('spacesList');
    listEl.innerHTML = 'Loading…';
    try{
      const rows = await fetchJson('/logistics/spaces');
      listEl.innerHTML = rows.map(s=>`<div class="spaceRow" data-id="${s.id}"><strong>${s.name}</strong> (${s.type||''}) - capacity: ${s.capacity||''} <small>template: ${s.space_template_id||'-'}</small> <button class="editBtn">Edit</button> <button class="deleteBtn">Delete</button></div>`).join('') || '<p>No spaces</p>';
      // attach handlers
      Array.from(listEl.querySelectorAll('.editBtn')).forEach(btn=>{
        btn.addEventListener('click', (ev)=>{
          const id = ev.target.closest('.spaceRow').dataset.id;
          const space = rows.find(r=>String(r.id)===String(id));
          if(space) showEditForm(space);
        });
      });
      Array.from(listEl.querySelectorAll('.deleteBtn')).forEach(btn=>{
        btn.addEventListener('click', async (ev)=>{
          const id = ev.target.closest('.spaceRow').dataset.id;
          if(!confirm('Delete this space?')) return;
          try{
            await fetch(`/logistics/spaces/${id}`, {method:'DELETE', headers: new Headers({'x-test-user': localStorage.getItem('dev_x_test_user')||''})});
            await refreshList();
          }catch(err){ alert('Delete failed: '+err.message) }
        });
      });
    }catch(err){ listEl.innerHTML = '<p class="error">Failed to load spaces: '+err.message+'</p>'; }
  }

  async function showForm(){
    const formEl = pageEl.querySelector('#spacesForm');
    formEl.style.display = 'block';
    formEl.innerHTML = `<h3>New space</h3>
      <form id="spaceFormElm">
        <label>Building: <select name="building_id"></select> <button id="btnAddBuilding" type="button">New building</button></label><br/>
        <input name="name" placeholder="name" /><br/>
        <input name="type" placeholder="type" /><br/>
        <input name="capacity" placeholder="capacity" type="number" /><br/>
        <label>Template: <select name="space_template_id"><option value="">(none)</option></select></label>
        <div id="templatePreview"></div>
        <button type="submit">Create</button>
        <button type="button" id="cancelForm">Cancel</button>
      </form>`;
    document.getElementById('cancelForm').addEventListener('click', ()=>{ formEl.style.display='none' });
    const form = document.getElementById('spaceFormElm');
    const buildingSel = form.building_id;
    const templateSel = form.space_template_id;
    const preview = form.querySelector('#templatePreview');

    // load buildings and templates
    try{
      const buildings = await fetchJson('/logistics/buildings');
      buildingSel.innerHTML = buildings.map(b=>`<option value="${b.id}">${b.name}</option>`).join('');
    }catch(err){ buildingSel.innerHTML = '<option value="">(failed to load buildings)</option>' }

    // inline add building
    const addBBtn = form.querySelector('#btnAddBuilding');
    addBBtn.addEventListener('click', ()=>{
      const html = `<div id="newBuildingInline"><input id="newBName" placeholder="name" /> <input id="newBAddress" placeholder="address" /> <button id="createB">Create</button> <button id="cancelB">Cancel</button></div>`;
      preview.insertAdjacentHTML('beforebegin', html);
      addBBtn.disabled = true;
      document.getElementById('cancelB').addEventListener('click', ()=>{ document.getElementById('newBuildingInline').remove(); addBBtn.disabled = false; });
      document.getElementById('createB').addEventListener('click', async ()=>{
        const name = document.getElementById('newBName').value.trim();
        const address = document.getElementById('newBAddress').value.trim();
        if(!name) return alert('Name required');
        try{
          await fetch('/logistics/buildings', {method:'POST', headers: new Headers({'Content-Type':'application/json','x-test-user': localStorage.getItem('dev_x_test_user')||''}), body: JSON.stringify({name, address})});
          // refresh building select
          const buildings = await fetchJson('/logistics/buildings');
          buildingSel.innerHTML = buildings.map(b=>`<option value="${b.id}">${b.name}</option>`).join('');
          document.getElementById('newBuildingInline').remove();
          addBBtn.disabled = false;
        }catch(err){ alert('Create building failed: '+err.message); addBBtn.disabled = false; }
      });
    });

    let templates = [];
    try{
      templates = await fetchJson('/logistics/space_templates');
      templateSel.innerHTML = '<option value="">(none)</option>' + templates.map(t=>`<option value="${t.id}">${t.name}</option>`).join('');
    }catch(err){ templateSel.innerHTML = '<option value="">(templates load failed)</option>' }

    templateSel.addEventListener('change', ()=>{
      const tid = templateSel.value;
      const t = templates.find(x=>String(x.id)===String(tid));
      if(!t){ preview.innerHTML = '' ; return; }
    // render preview and inputs for custom fields
    preview.innerHTML = `<h4>Template: ${t.name}</h4><div id="templateFields">${t.fields.map((f,idx)=>`<div class="tf" data-idx="${idx}"><label>${f.name}: ${renderFieldInput(f, idx)}</label></div>`).join('')}</div>`;
    });

  // renderFieldInput moved to outer scope for reuse

    form.addEventListener('submit', async (ev)=>{
      ev.preventDefault();
      const payload = { building_id: buildingSel.value, name: form.name.value, type: form.type.value, capacity: form.capacity.value ? Number(form.capacity.value) : null };
      if(templateSel.value) payload.space_template_id = Number(templateSel.value);
      // collect custom field values if any
      const tfwrap = form.querySelector('#templateFields');
      if(tfwrap){
        const tfEls = Array.from(tfwrap.querySelectorAll('.tf'));
        const custom_fields = tfEls.map(el=>{
          const idx = el.dataset.idx;
          const input = el.querySelector('.tfinput');
          return { name: templates[Number(templateSel.selectedIndex)-1]?.fields[idx]?.name || ('field'+idx), value: input ? (input.tagName === 'SELECT' ? input.value : input.value) : null };
        }).filter(x=>x.value !== null && x.value !== '');
        if(custom_fields.length) payload.custom_fields = custom_fields;
      }
      try{
        await fetch('/logistics/spaces', {method:'POST', headers: new Headers({'Content-Type':'application/json','x-test-user': localStorage.getItem('dev_x_test_user')||''}), body: JSON.stringify(payload)});
        formEl.style.display='none';
        await refreshList();
      }catch(err){ alert('Create failed: '+err.message) }
    });
  }

  // show edit form for a given space
  async function showEditForm(space){
    const formEl = pageEl.querySelector('#spacesForm');
    formEl.style.display = 'block';
    formEl.innerHTML = `<h3>Edit space</h3>
      <form id="spaceEditFormElm">
        <label>Building: <select name="building_id"></select></label><br/>
        <input name="name" placeholder="name" /><br/>
        <input name="type" placeholder="type" /><br/>
        <input name="capacity" placeholder="capacity" type="number" /><br/>
        <label>Template: <select name="space_template_id"><option value="">(none)</option></select></label>
        <div id="templatePreview"></div>
        <button type="submit">Save</button>
        <button type="button" id="cancelEdit">Cancel</button>
      </form>`;
    document.getElementById('cancelEdit').addEventListener('click', ()=>{ formEl.style.display='none' });
    const form = document.getElementById('spaceEditFormElm');
    const buildingSel = form.building_id;
    const templateSel = form.space_template_id;
    const preview = form.querySelector('#templatePreview');

    // load buildings and templates
    let templates = [];
    try{
      const buildings = await fetchJson('/logistics/buildings');
      buildingSel.innerHTML = buildings.map(b=>`<option value="${b.id}">${b.name}</option>`).join('');
      // set building
      buildingSel.value = space.building_id;
    }catch(err){ buildingSel.innerHTML = '<option value="">(failed to load buildings)</option>' }
    try{
      templates = await fetchJson('/logistics/space_templates');
      templateSel.innerHTML = '<option value="">(none)</option>' + templates.map(t=>`<option value="${t.id}">${t.name}</option>`).join('');
      if(space.space_template_id) templateSel.value = space.space_template_id;
    }catch(err){ templateSel.innerHTML = '<option value="">(templates load failed)</option>' }

    form.name.value = space.name;
    form.type.value = space.type || '';
    form.capacity.value = space.capacity || '';

    function renderPreviewForSelected(){
      const tid = templateSel.value;
      const t = templates.find(x=>String(x.id)===String(tid));
      if(!t){ preview.innerHTML = '' ; return; }
      preview.innerHTML = `<h4>Template: ${t.name}</h4><div id="templateFields">${t.fields.map((f,idx)=>`<div class="tf" data-idx="${idx}"><label>${f.name}: ${renderFieldInput(f, idx)}</label></div>`).join('')}</div>`;
      // populate existing custom field values
      const cfByName = {};
      (space.custom_fields||[]).forEach(x=>{ cfByName[x.name]=x.value; });
      const tfEls = preview.querySelectorAll('.tf');
      tfEls.forEach(el=>{
        const idx = el.dataset.idx;
        const input = el.querySelector('.tfinput');
        const fieldName = t.fields[idx].name;
        if(input){
          if(input.tagName === 'SELECT'){
            input.value = cfByName[fieldName] || input.value;
          }else{
            input.value = cfByName[fieldName] || '';
          }
        }
      });
    }

    templateSel.addEventListener('change', renderPreviewForSelected);
    // initial preview
    renderPreviewForSelected();

    form.addEventListener('submit', async (ev)=>{
      ev.preventDefault();
      const payload = { building_id: buildingSel.value, name: form.name.value, type: form.type.value, capacity: form.capacity.value ? Number(form.capacity.value) : null };
      if(templateSel.value) payload.space_template_id = Number(templateSel.value);
      const tfwrap = form.querySelector('#templateFields');
      if(tfwrap){
        const tfEls = Array.from(tfwrap.querySelectorAll('.tf'));
        const custom_fields = tfEls.map(el=>{
          const idx = el.dataset.idx;
          const input = el.querySelector('.tfinput');
          const fname = templates.find(x=>String(x.id)===String(templateSel.value))?.fields[idx]?.name || ('field'+idx);
          return { name: fname, value: input ? (input.tagName === 'SELECT' ? input.value : input.value) : null };
        }).filter(x=>x.value !== null && x.value !== '');
        if(custom_fields.length) payload.custom_fields = custom_fields;
        else payload.custom_fields = [];
      }
      try{
        await fetch(`/logistics/spaces/${space.id}`, {method:'PATCH', headers: new Headers({'Content-Type':'application/json','x-test-user': localStorage.getItem('dev_x_test_user')||''}), body: JSON.stringify(payload)});
        formEl.style.display='none';
        await refreshList();
      }catch(err){ alert('Save failed: '+err.message) }
    });
  }
}
