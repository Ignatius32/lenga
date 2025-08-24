// Buildings page: list, create, edit, delete
export async function loadBuildingsPage(pageEl, fetchJson){
  pageEl.innerHTML = '<h2>Buildings</h2><div id="bToolbar"><button id="btnNew">New building</button></div><div id="bList">Loading…</div><div id="bForm" style="display:none"></div>';
  document.getElementById('btnNew').addEventListener('click', ()=>showForm());
  await refreshList();

  async function refreshList(){
    const listEl = document.getElementById('bList');
    listEl.innerHTML = 'Loading…';
    try{
      const rows = await fetchJson('/logistics/buildings');
      listEl.innerHTML = rows.map(b=>`<div class="bRow" data-id="${b.id}"><strong>${b.name}</strong> - ${b.address||''} <button class="edit">edit</button> <button class="del">delete</button></div>`).join('') || '<p>No buildings</p>';
      listEl.querySelectorAll('button.edit').forEach(b=>b.addEventListener('click', (ev)=>{ const id = ev.target.closest('.bRow').dataset.id; showForm(id); }));
      listEl.querySelectorAll('button.del').forEach(b=>b.addEventListener('click', async (ev)=>{ const id = ev.target.closest('.bRow').dataset.id; if(!confirm('Delete building '+id+'?')) return; try{ await fetch('/logistics/buildings/'+id, {method:'DELETE', headers: new Headers({'x-test-user': localStorage.getItem('dev_x_test_user')||''})}); await refreshList(); }catch(err){alert('Delete failed: '+err.message)} }));
    }catch(err){ listEl.innerHTML = '<p class="error">Failed to load buildings: '+err.message+'</p>'; }
  }

  function showForm(id){
    const formEl = pageEl.querySelector('#bForm');
    formEl.style.display = 'block';
    formEl.innerHTML = `<h3>${id?'Edit':'New'} building</h3>
      <form id="bFormElm">
        <input name="name" placeholder="name" /><br/>
        <input name="address" placeholder="address" /><br/>
        <button type="submit">Save</button>
        <button type="button" id="cancelForm">Cancel</button>
      </form>`;
    document.getElementById('cancelForm').addEventListener('click', ()=>{ formEl.style.display='none' });
    const form = document.getElementById('bFormElm');
    if(id){ fetchJson('/logistics/buildings').then(rows=>{ const b = rows.find(x=>String(x.id)===String(id)); if(!b) return alert('Building not found'); form.name.value = b.name||''; form.address.value = b.address||''; }); }
    form.addEventListener('submit', async (ev)=>{
      ev.preventDefault();
      const payload = { name: form.name.value, address: form.address.value };
      try{
        if(id){ await fetch('/logistics/buildings/'+id, {method:'PATCH', headers: new Headers({'Content-Type':'application/json','x-test-user': localStorage.getItem('dev_x_test_user')||''}), body: JSON.stringify(payload)}); }
        else{ await fetch('/logistics/buildings', {method:'POST', headers: new Headers({'Content-Type':'application/json','x-test-user': localStorage.getItem('dev_x_test_user')||''}), body: JSON.stringify(payload)}); }
        formEl.style.display='none';
        await refreshList();
      }catch(err){ alert('Save failed: '+err.message) }
    });
  }
}
