// Roles & Groups UI
export async function loadRolesGroups(pageEl, fetchJson){
  pageEl.innerHTML = `<h2>Roles & Groups</h2>
    <div id="rolesArea"><h3>Roles</h3><div id="rolesList">Loading…</div><div><input id="newRoleName" placeholder="role name"/><button id="createRole">Create</button></div></div>
    <div id="groupsArea"><h3>Groups</h3><div id="groupsList">Loading…</div><div><input id="newGroupName" placeholder="group name"/><button id="createGroup">Create</button></div></div>
    <div id="groupMembers" style="margin-top:1rem"></div>`;

  const rolesList = pageEl.querySelector('#rolesList');
  const groupsList = pageEl.querySelector('#groupsList');

  async function refreshRoles(){
    try{
      const roles = await fetchJson('/admin/roles');
  rolesList.innerHTML = `<ul>${roles.map(r=>`<li>${r.name} <button class="assignRole" data-role="${r.name}">Assign to user</button> <button class="removeRole" data-role="${r.name}">Remove from user</button></li>`).join('')}</ul>`;
  rolesList.querySelectorAll('button.assignRole').forEach(b=>b.addEventListener('click', ()=>assignRolePrompt(b.dataset.role)));
  rolesList.querySelectorAll('button.removeRole').forEach(b=>b.addEventListener('click', ()=>removeRolePrompt(b.dataset.role)));
    }catch(err){rolesList.innerHTML = '<p class="error">Failed to load roles: '+err.message+'</p>'}
  }

  async function refreshGroups(){
    try{
  const gs = await fetchJson('/admin/groups');
  groupsList.innerHTML = `<ul>${gs.map(g=>`<li data-id="${g.id}">${g.name} <button class="viewMembers" data-id="${g.id}">Members</button> <button class="manageQueues" data-id="${g.id}">Queues</button></li>`).join('')}</ul>`;
  groupsList.querySelectorAll('button.viewMembers').forEach(b=>b.addEventListener('click', ()=>showMembers(b.dataset.id)));
  groupsList.querySelectorAll('button.manageQueues').forEach(b=>b.addEventListener('click', ()=>showQueuesForGroup(b.dataset.id)));
    }catch(err){groupsList.innerHTML = '<p class="error">Failed to load groups: '+err.message+'</p>'}
  }

  async function showQueuesForGroup(groupId){
    try{
      const [queues, permissions] = await Promise.all([fetchJson('/admin/queues'), fetchJson('/admin/queue_permissions')]);
      const allowed = new Set((permissions||[]).filter(p=>p.group_id===Number(groupId)).map(p=>p.queue_id));
      const el = pageEl.querySelector('#groupMembers');
      el.style.display = 'block';
      el.innerHTML = `<h4>Allowed queues for group ${groupId}</h4><div id="allowedQueuesList"></div><div id="grantQueueArea"></div><div><button id="closeQueues">Close</button></div>`;
      const listEl = el.querySelector('#allowedQueuesList');
      const granted = queues.filter(q=>allowed.has(q.id));
      listEl.innerHTML = granted.length? '<ul>'+granted.map(q=>`<li>${q.name} <button class="revokeQueue" data-qid="${q.id}">Revoke</button></li>`).join('')+'</ul>' : '<p>No queues granted</p>';

      const grantArea = el.querySelector('#grantQueueArea');
      const select = document.createElement('select'); select.id = 'grantQueueSelect';
      queues.filter(q=>!allowed.has(q.id)).forEach(q=>{ const opt = document.createElement('option'); opt.value = q.id; opt.textContent = q.name; select.appendChild(opt); });
      const grantBtn = document.createElement('button'); grantBtn.id = 'grantQueueBtn'; grantBtn.textContent = 'Grant selected queue';
      grantArea.appendChild(select); grantArea.appendChild(grantBtn);

      // wire revoke
      el.querySelectorAll('.revokeQueue').forEach(b=>b.addEventListener('click', async ev=>{
        const qid = Number(ev.target.dataset.qid);
        try{
          await fetch('/admin/queue_permissions', { method: 'DELETE', headers: new Headers({'Content-Type':'application/json','x-test-user': localStorage.getItem('dev_x_test_user')||''}), body: JSON.stringify({ group_id: Number(groupId), queue_id: qid }) });
          showQueuesForGroup(groupId);
        }catch(err){ alert('Revoke failed: '+err.message) }
      }));

      grantBtn.addEventListener('click', async ()=>{
        const qid = Number(select.value);
        if(!qid) return alert('Select a queue');
        try{
          await fetch('/admin/queue_permissions', { method: 'POST', headers: new Headers({'Content-Type':'application/json','x-test-user': localStorage.getItem('dev_x_test_user')||''}), body: JSON.stringify({ group_id: Number(groupId), queue_id: qid }) });
          showQueuesForGroup(groupId);
        }catch(err){ alert('Grant failed: '+err.message) }
      });

      el.querySelector('#closeQueues').addEventListener('click', ()=>{ el.style.display='none' });
    }catch(err){ alert('Failed to load queues: '+err.message) }
  }

  async function assignRolePrompt(roleName){
    const uid = prompt('Enter user id to assign role '+roleName+':');
    if(!uid) return;
    try{
      const payload = { user_id: Number(uid), role_name: roleName };
      await fetch('/admin/roles/assign', {method:'POST', headers: new Headers({'Content-Type':'application/json','x-test-user': localStorage.getItem('dev_x_test_user')||''}), body: JSON.stringify(payload)});
      alert('Assigned');
    }catch(err){alert('Failed: '+err.message)}
  }

  async function removeRolePrompt(roleName){
    const uid = prompt('Enter user id to remove role '+roleName+':');
    if(!uid) return;
    try{
      const payload = { user_id: Number(uid), role_name: roleName };
      await fetch('/admin/roles/remove', {method:'POST', headers: new Headers({'Content-Type':'application/json','x-test-user': localStorage.getItem('dev_x_test_user')||''}), body: JSON.stringify(payload)});
      alert('Removed (or not assigned)');
    }catch(err){alert('Failed: '+err.message)}
  }

  async function showMembers(groupId){
    try{
      const members = await fetchJson(`/admin/groups/${groupId}/members`);
      // load all users for a selector (lightweight list)
      const users = await fetchJson('/admin/users');
      // build a small map
      const userMap = Object.fromEntries(users.map(u=>[u.id, u]));
      const html = `<h4>Members of group ${groupId}</h4>
        <div><input id="memberFilter" placeholder="filter members by name or id" style="margin-bottom:.5rem"/></div>
        <ul id="membersList">${members.map(m=>`<li data-id="${m.id}">${m.first_name||''} ${m.last_name||''} (${m.id}) <button class="removeMember" data-id="${m.id}" data-group="${groupId}">Remove</button></li>`).join('')}</ul>
        <div style="margin-top:.5rem"><label>Add user: <select id="addMemberSelect"><option value="">-- select user --</option>${users.map(u=>`<option value="${u.id}">${u.first_name||''} ${u.last_name||''} (${u.id})</option>`).join('')}</select></label> <button id="addMemberBtn">Add</button> <button id="closeMembers">Close</button></div>`;
      pageEl.querySelector('#groupMembers').innerHTML = html;
      pageEl.querySelector('#groupMembers').style.display = 'block';

      // wire remove buttons (DELETE only)
      pageEl.querySelectorAll('.removeMember').forEach(b=>b.addEventListener('click', async (ev)=>{
        const uid = ev.target.dataset.id; const gid = ev.target.dataset.group;
        try{
          await fetch(`/admin/groups/${gid}/users/${uid}`, {method:'DELETE', headers: new Headers({'x-test-user': localStorage.getItem('dev_x_test_user')||''})});
          showMembers(gid);
        }catch(err){alert('Failed to remove: '+err.message)}
      }));

      // filter members locally
      const memberFilter = document.getElementById('memberFilter');
      memberFilter.addEventListener('input', ()=>{
        const q = memberFilter.value.toLowerCase().trim();
        const list = pageEl.querySelector('#membersList');
        list.innerHTML = members.filter(m=>{
          const name = `${m.first_name||''} ${m.last_name||''}`.toLowerCase();
          return String(m.id).includes(q) || name.includes(q);
        }).map(m=>`<li data-id="${m.id}">${m.first_name||''} ${m.last_name||''} (${m.id}) <button class="removeMember" data-id="${m.id}" data-group="${groupId}">Remove</button></li>`).join('');
        // re-wire remove buttons
        pageEl.querySelectorAll('.removeMember').forEach(b=>b.addEventListener('click', async (ev)=>{
          const uid = ev.target.dataset.id; const gid = ev.target.dataset.group;
          try{
            await fetch(`/admin/groups/${gid}/users/${uid}`, {method:'DELETE', headers: new Headers({'x-test-user': localStorage.getItem('dev_x_test_user')||''})});
            showMembers(gid);
          }catch(err){alert('Failed to remove: '+err.message)}
        }));
      });

      document.getElementById('addMemberBtn').addEventListener('click', async ()=>{
        const sel = document.getElementById('addMemberSelect');
        const uid = Number(sel.value);
        if(!uid) return alert('select a user');
        try{
          await fetch(`/admin/groups/${groupId}/users`, {method:'POST', headers: new Headers({'Content-Type':'application/json','x-test-user': localStorage.getItem('dev_x_test_user')||''}), body: JSON.stringify({user_id: uid})});
          showMembers(groupId);
        }catch(err){alert('add failed: '+err.message)}
      });

      document.getElementById('closeMembers').addEventListener('click', ()=>{pageEl.querySelector('#groupMembers').style.display='none'});
      // wire remove buttons already added
    }catch(err){alert('Failed to load members: '+err.message)}
  }

  document.getElementById('createRole').addEventListener('click', async ()=>{
    const rn = document.getElementById('newRoleName').value.trim();
    if(!rn) return alert('enter role name');
    try{
      await fetch('/admin/roles/assign', {method:'POST', headers: new Headers({'Content-Type':'application/json','x-test-user': localStorage.getItem('dev_x_test_user')||''}), body: JSON.stringify({user_id: Number(localStorage.getItem('dev_x_test_user')||0), role_name: rn})});
      document.getElementById('newRoleName').value='';
      await refreshRoles();
    }catch(err){alert('create role failed: '+err.message)}
  });

  document.getElementById('createGroup').addEventListener('click', async ()=>{
    const gn = document.getElementById('newGroupName').value.trim();
    if(!gn) return alert('enter group name');
    try{
      await fetch('/admin/groups', {method:'POST', headers: new Headers({'Content-Type':'application/json','x-test-user': localStorage.getItem('dev_x_test_user')||''}), body: JSON.stringify({name: gn, description: ''})});
      document.getElementById('newGroupName').value='';
      await refreshGroups();
    }catch(err){alert('create group failed: '+err.message)}
  });

  await refreshRoles();
  await refreshGroups();
}
