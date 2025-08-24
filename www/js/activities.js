// Activities admin page: list and create activities using templates with proper widgets
export async function loadActivities(pageEl, fetchJson){
  pageEl.innerHTML = '<h2>Activities</h2><div id="actToolbar"><button id="btnNew">New activity</button></div><div id="actList">Loading…</div><div id="actForm" style="display:none"></div>';
  document.getElementById('btnNew').addEventListener('click', ()=>showForm());
  await refreshList();

  async function refreshList(){
    const listEl = document.getElementById('actList');
    listEl.innerHTML = 'Loading…';
    try{
      const rows = await fetchJson('/activities');
      listEl.innerHTML = rows.map(a=>`<div class="activityRow"><strong>${a.title}</strong> ${a.start_time} - ${a.end_time} <small>type:${a.activity_type_id||'-'}</small></div>`).join('') || '<p>No activities</p>';
    }catch(err){ listEl.innerHTML = '<p class="error">Failed to load activities: '+err.message+'</p>'; }
  }

  async function showForm(){
    const formEl = pageEl.querySelector('#actForm');
    formEl.style.display = 'block';
    formEl.innerHTML = `<h3>New activity</h3>
      <form id="actFormElm">
        <input name="title" placeholder="title" required /><br/>
        <label>Category ID: <input name="category_id" type="number" required /></label><br/>
        <label>Organizer user id: <input name="organizer_user_id" type="number" required /></label><br/>
        <label>Start: <input name="start_time" type="datetime-local" required /></label><br/>
        <label>End: <input name="end_time" type="datetime-local" required /></label><br/>
        <label>Space: <select name="space_id" required><option value="">(select)</option></select></label><br/>
        <label>Template: <select name="activity_type_id"><option value="">(none)</option></select></label>
        <div id="templatePreview"></div>
        <button type="submit">Create</button>
        <button type="button" id="cancelForm">Cancel</button>
      </form>`;
    document.getElementById('cancelForm').addEventListener('click', ()=>{ formEl.style.display='none' });
    const form = document.getElementById('actFormElm');
    const templateSel = form.activity_type_id;
    const spaceSel = form.space_id;
    const preview = form.querySelector('#templatePreview');

    // load spaces
    try{
      const spaces = await fetchJson('/logistics/spaces');
      spaceSel.innerHTML = '<option value="">(select)</option>' + spaces.map(s=>`<option value="${s.id}">${s.name} (${s.type||''})</option>`).join('');
    }catch(err){ spaceSel.innerHTML = '<option value="">(failed to load spaces)</option>' }

    // load activity templates
    let templates = [];
    try{
      templates = await fetchJson('/activities/types');
      templateSel.innerHTML = '<option value="">(none)</option>' + templates.map(t=>`<option value="${t.id}">${t.name}</option>`).join('');
    }catch(err){ templateSel.innerHTML = '<option value="">(templates load failed)</option>' }

    templateSel.addEventListener('change', ()=>{
      const tid = templateSel.value;
      const t = templates.find(x=>String(x.id)===String(tid));
      if(!t){ preview.innerHTML = '' ; return; }
      preview.innerHTML = `<h4>Template: ${t.name}</h4><div id="templateFields">${t.fields.map((f,idx)=>`<div class="tf" data-idx="${idx}"><label>${f.name}: ${renderFieldInput(f, idx)}</label></div>`).join('')}</div>`;
    });

    function renderFieldInput(f, idx){
      const name = `field_${idx}`;
      switch(f.field_type){
        case 'datetime': return `<input data-idx="${idx}" name="${name}" class="tfinput" type="datetime-local" />`;
        case 'date': return `<input data-idx="${idx}" name="${name}" class="tfinput" type="date" />`;
        case 'time': return `<input data-idx="${idx}" name="${name}" class="tfinput" type="time" />`;
        case 'boolean': return `<input data-idx="${idx}" name="${name}" class="tfinput" type="checkbox" />`;
        case 'number': return `<input data-idx="${idx}" name="${name}" class="tfinput" type="number" />`;
        case 'select': {
          const opts = (f.options||[]);
          return `<select data-idx="${idx}" name="${name}" class="tfinput">${opts.map(o=>`<option value="${o}">${o}</option>`).join('')}</select>`;
        }
        case 'space': return `<select data-idx="${idx}" name="${name}" class="tfinput">${(spaceSel.innerHTML||'')}</select>`;
        default: return `<input data-idx="${idx}" name="${name}" class="tfinput" placeholder="${f.field_type}" />`;
      }
    }

    form.addEventListener('submit', async (ev)=>{
      ev.preventDefault();
      // validate required space
      if(!form.space_id.value) return alert('Space is required');
      const payload = { title: form.title.value, category_id: Number(form.category_id.value), start_time: new Date(form.start_time.value).toISOString(), end_time: new Date(form.end_time.value).toISOString(), organizer_user_id: Number(form.organizer_user_id.value) };
      if(form.activity_type_id.value) payload.activity_type_id = Number(form.activity_type_id.value);
      // attach space booking via API after creation; but include space id as a required custom field when template defines a space field
      const tfwrap = form.querySelector('#templateFields');
      if(tfwrap){
        const t = templates.find(x=>String(x.id)===String(form.activity_type_id.value));
        const tfEls = Array.from(tfwrap.querySelectorAll('.tf'));
        const custom_fields = tfEls.map((el, idx)=>{
          const fdef = t.fields[idx];
          const input = el.querySelector('.tfinput');
          let val = null;
          if(fdef.field_type === 'boolean') val = input.checked;
          else if(fdef.field_type === 'space') val = (input.value || form.space_id.value);
          else val = input.value;
          return { name: fdef.name, value: val };
        }).filter(x=>x.value !== null && x.value !== '');
        if(custom_fields.length) payload.custom_fields = custom_fields;
      }
      if(form.activity_type_id.value === '' && !payload.custom_fields){
        // still require space selection even without template
        payload.custom_fields = [{ name: 'space', value: form.space_id.value }];
      }

      try{
        await fetch('/activities/', {method:'POST', headers: new Headers({'Content-Type':'application/json','x-test-user': localStorage.getItem('dev_x_test_user')||''}), body: JSON.stringify(payload)});
        formEl.style.display='none';
        await refreshList();
      }catch(err){ alert('Create failed: '+err.message) }
    });
  }
}
