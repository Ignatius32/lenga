// Queues page: list, create, manage permissions
export async function loadQueues(pageEl, fetchJson){
  pageEl.innerHTML = `<h2>Queues</h2>
    <div id="queuesToolbar"><input id="newQueueName" placeholder="queue name"/><input id="newQueueDesc" placeholder="description"/><button id="createQueue">Create</button></div>
    <div id="queuesList">Loading...</div>
    <div id="queuePerms" style="margin-top:1rem"></div>
    <div id="queueEditModal" style="display:none;position:fixed;left:50%;top:30%;transform:translate(-50%,-30%);background:#fff;padding:1rem;border:1px solid #ccc;box-shadow:0 2px 10px rgba(0,0,0,0.1);">
      <h3 id="modalTitle">Edit Queue</h3>
      <div><label>Name: <input id="modalName" /></label></div>
      <div><label>Description: <input id="modalDesc" /></label></div>
      <div style="margin-top:0.5rem"><button id="modalSave">Save</button> <button id="modalCancel">Cancel</button></div>
    </div>`;

  const listEl = pageEl.querySelector('#queuesList');

  async function refresh(){
    listEl.innerHTML = 'Loading...';
    try{
      const qs = await fetchJson('/admin/queues');
      listEl.innerHTML = `<table class="queuesTable"><thead><tr><th>ID</th><th>Name</th><th>Description</th><th>Actions</th></tr></thead><tbody>${qs.map(q=>`<tr data-id="${q.id}"><td>${q.id}</td><td>${q.name}</td><td>${q.description||''}</td><td><button class="perms" data-id="${q.id}">Permissions</button> <button class="editQ" data-id="${q.id}">Edit</button> <button class="delQ" data-id="${q.id}">Delete</button></td></tr>`).join('')}</tbody></table>`;
      listEl.querySelectorAll('button.perms').forEach(b=>b.addEventListener('click', ()=>showPerms(b.dataset.id)));
      listEl.querySelectorAll('button.editQ').forEach(b=>b.addEventListener('click', ()=>editQueue(b.dataset.id)));
      listEl.querySelectorAll('button.delQ').forEach(b=>b.addEventListener('click', async (ev)=>{
        const id = ev.target.dataset.id;
        if(!confirm('Delete queue '+id+'?')) return;
        try{
          const res = await fetch('/admin/queues/'+id, {method:'DELETE', headers: new Headers({'x-test-user': localStorage.getItem('dev_x_test_user')||''})});
          if(!res.ok) throw new Error('HTTP '+res.status);
          await refresh();
        }catch(err){ alert('Delete failed: '+err.message) }
      }));
    }catch(err){ listEl.innerHTML = '<p class="error">Failed to load queues: '+err.message+'</p>' }
  }

  async function showPerms(queueId){
    // load queue permissions and groups
    try{
      const groups = await fetchJson('/admin/groups');
      const perms = await fetchJson('/admin/queue_permissions');
      const qPerms = perms.filter(p=>String(p.queue_id)===String(queueId));
      const gidToName = Object.fromEntries(groups.map(g=>[g.id, g.name]));
      const html = `<h3>Permissions for queue ${queueId}</h3>
        <div><select id="permGroupSelect">${groups.map(g=>`<option value="${g.id}">${g.name}</option>`).join('')}</select>
        <button id="addPerm">Grant</button>
        <button id="closePerms">Close</button></div>
        <h4>Allowed groups</h4>
        <ul id="allowedGroups">${qPerms.map(p=>`<li data-group="${p.group_id}">${gidToName[p.group_id]||p.group_id} <button class="removePerm" data-group="${p.group_id}">Remove</button></li>`).join('')}</ul>`;
      pageEl.querySelector('#queuePerms').innerHTML = html;
      pageEl.querySelector('#queuePerms').style.display = 'block';

      document.getElementById('addPerm').addEventListener('click', async ()=>{
        const gid = Number(document.getElementById('permGroupSelect').value);
        try{
          await fetch('/admin/queue_permissions', {method:'POST', headers: new Headers({'Content-Type':'application/json','x-test-user': localStorage.getItem('dev_x_test_user')||''}), body: JSON.stringify({group_id: gid, queue_id: Number(queueId)})});
          showPerms(queueId);
        }catch(err){ alert('Grant failed: '+err.message) }
      });

      pageEl.querySelectorAll('.removePerm').forEach(b=>b.addEventListener('click', async (ev)=>{
        const gid = Number(ev.target.dataset.group);
        try{
          await fetch('/admin/queue_permissions', {method:'DELETE', headers: new Headers({'Content-Type':'application/json','x-test-user': localStorage.getItem('dev_x_test_user')||''}), body: JSON.stringify({group_id: gid, queue_id: Number(queueId)})});
          showPerms(queueId);
        }catch(err){ alert('Remove failed: '+err.message) }
      }));

      document.getElementById('closePerms').addEventListener('click', ()=>{ pageEl.querySelector('#queuePerms').style.display='none' });

    }catch(err){ alert('Failed to load permissions: '+err.message) }
  }

  document.getElementById('createQueue').addEventListener('click', async ()=>{
    const name = document.getElementById('newQueueName').value.trim();
    const desc = document.getElementById('newQueueDesc').value.trim();
    if(!name) return alert('enter a queue name');
    try{
      await fetch('/admin/queues', {method:'POST', headers: new Headers({'Content-Type':'application/json','x-test-user': localStorage.getItem('dev_x_test_user')||''}), body: JSON.stringify({name, description: desc})});
      document.getElementById('newQueueName').value=''; document.getElementById('newQueueDesc').value='';
      await refresh();
    }catch(err){ alert('Create failed: '+err.message) }
  });

    async function editQueue(queueId){
      // fetch queue data
      const qs = await fetchJson('/admin/queues');
      const q = qs.find(x=>String(x.id)===String(queueId));
      if(!q) return alert('Queue not found');
      // show inline modal
      const modal = pageEl.querySelector('#queueEditModal');
      modal.style.display = 'block';
      modal.querySelector('#modalName').value = q.name || '';
      modal.querySelector('#modalDesc').value = q.description || '';
      modal.querySelector('#modalTitle').textContent = 'Edit Queue '+q.id;

      function hide(){ modal.style.display = 'none'; modal.querySelector('#modalSave').removeEventListener('click', onSave); modal.querySelector('#modalCancel').removeEventListener('click', onCancel); }
      async function onSave(){
        const name = modal.querySelector('#modalName').value.trim();
        const desc = modal.querySelector('#modalDesc').value.trim();
        try{
          await fetch('/admin/queues/'+queueId, {method:'PUT', headers: new Headers({'Content-Type':'application/json','x-test-user': localStorage.getItem('dev_x_test_user')||''}), body: JSON.stringify({name, description: desc})});
          hide();
          await refresh();
        }catch(err){ alert('Update failed: '+err.message) }
      }
      function onCancel(){ hide(); }
      modal.querySelector('#modalSave').addEventListener('click', onSave);
      modal.querySelector('#modalCancel').addEventListener('click', onCancel);
    }

    await refresh();
  }
