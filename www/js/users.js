// Users page: list, detail, create, edit, delete
export async function loadUsersPage(pageEl, fetchJson){
  pageEl.innerHTML = '<h2>Users</h2><div id="usersToolbar"><button id="btnNew">New user</button></div><div id="usersList">Loading…</div><div id="usersForm" style="display:none"></div>';
  document.getElementById('btnNew').addEventListener('click', ()=>showForm());
  await refreshList();

  async function refreshList(){
    const listEl = document.getElementById('usersList');
    listEl.innerHTML = 'Loading…';
    try{
      const rows = await fetchJson('/admin/users');
      if(!Array.isArray(rows)) throw new Error('unexpected users payload');
      listEl.innerHTML = `<table class="usersTable"><thead><tr><th>ID</th><th>Name</th><th>Email</th><th>actions</th></tr></thead><tbody>${rows.map(u=>`<tr data-id="${u.id}"><td>${u.id}</td><td>${(u.first_name||'')+' '+(u.last_name||'')}</td><td>${u.email||''}</td><td><button class="view">view</button> <button class="edit">edit</button> <button class="del">delete</button></td></tr>`).join('')}</tbody></table>`;
      // wire actions
      listEl.querySelectorAll('button.view').forEach(b=>b.addEventListener('click', (ev)=>{
        const id = ev.target.closest('tr').dataset.id; showDetail(id);
      }));
      listEl.querySelectorAll('button.edit').forEach(b=>b.addEventListener('click', (ev)=>{
        const id = ev.target.closest('tr').dataset.id; showForm(id);
      }));
      listEl.querySelectorAll('button.del').forEach(b=>b.addEventListener('click', async (ev)=>{
        const id = ev.target.closest('tr').dataset.id;
        if(!confirm('Delete user '+id+'?')) return;
        try{
          await fetch(`/admin/users/${id}`, {method:'DELETE', headers: new Headers({'x-test-user': localStorage.getItem('dev_x_test_user')||''})});
          await refreshList();
        }catch(err){alert('Delete failed: '+err.message)}
      }));
    }catch(err){
      listEl.innerHTML = '<p class="error">Failed to load users: '+err.message+'</p>';
    }
  }

  async function showDetail(id){
    const rows = await fetchJson('/admin/users');
    const u = rows.find(x=>String(x.id)===String(id));
    if(!u) return alert('User not found');
    const html = `<h3>User ${u.id}</h3><p>Name: ${u.first_name||''} ${u.last_name||''}</p><p>Email: ${u.email||''}</p><p>Keycloak id: ${u.keycloak_id}</p><p><button id="backFromDetail">Back</button></p>`;
    pageEl.querySelector('#usersForm').innerHTML = html;
    pageEl.querySelector('#usersForm').style.display = 'block';
    document.getElementById('backFromDetail').addEventListener('click', ()=>{pageEl.querySelector('#usersForm').style.display='none'});
  }

  function showForm(id){
    const formEl = pageEl.querySelector('#usersForm');
    formEl.style.display = 'block';
    formEl.innerHTML = `<h3>${id?'Edit':'New'} user</h3>
      <form id="userFormElm">
        <input name="keycloak_id" placeholder="keycloak_id" /><br/>
        <input name="first_name" placeholder="first_name" /><br/>
        <input name="last_name" placeholder="last_name" /><br/>
        <input name="email" placeholder="email" /><br/>
        <button type="submit">Save</button>
        <button type="button" id="cancelForm">Cancel</button>
      </form>`;
    document.getElementById('cancelForm').addEventListener('click', ()=>{formEl.style.display='none'});
    const form = document.getElementById('userFormElm');
    if(id){
      // load existing
      fetchJson('/admin/users').then(rows=>{
        const u = rows.find(x=>String(x.id)===String(id));
        if(u){
          form.keycloak_id.value = u.keycloak_id||'';
          form.first_name.value = u.first_name||'';
          form.last_name.value = u.last_name||'';
          form.email.value = u.email||'';
        }
      });
    }
    form.addEventListener('submit', async (ev)=>{
      ev.preventDefault();
      const payload = { keycloak_id: form.keycloak_id.value, first_name: form.first_name.value, last_name: form.last_name.value, email: form.email.value };
      try{
        if(id){
          await fetch(`/admin/users/${id}`, {method:'PUT', headers: new Headers({'Content-Type':'application/json','x-test-user': localStorage.getItem('dev_x_test_user')||''}), body: JSON.stringify(payload)});
        }else{
          await fetch('/admin/users', {method:'POST', headers: new Headers({'Content-Type':'application/json','x-test-user': localStorage.getItem('dev_x_test_user')||''}), body: JSON.stringify(payload)});
        }
        formEl.style.display='none';
        await refreshList();
      }catch(err){alert('Save failed: '+err.message)}
    });
  }
}
