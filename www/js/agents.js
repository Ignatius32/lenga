// Agents assignment UI: list assignments, assign agent to queue, unassign
export async function loadAgents(pageEl, fetchJson){
  pageEl.innerHTML = `<h2>Agents</h2>
    <div id="agentsToolbar">
      <label>Agent user id: <input id="assignAgentId" style="width:80px"/></label>
      <label>Queue: <select id="assignQueue"></select></label>
      <label>Access: <select id="assignAccess"><option value="">default</option><option value="full">full</option><option value="limited">limited</option></select></label>
      <button id="assignBtn">Assign</button>
    </div>
    <div id="agentList">Loading...</div>`;

  const listEl = pageEl.querySelector('#agentList');
  const assignQueue = pageEl.querySelector('#assignQueue');

  // add filters UI
  const filterBar = document.createElement('div');
  filterBar.style.margin = '0.5rem 0';
  filterBar.innerHTML = `<label>Filter by queue: <select id="filterQueue"><option value="">--all--</option></select></label> <label>Filter by agent: <select id="filterAgent"><option value="">--all--</option></select></label> <button id="clearFilters">Clear</button>`;
  pageEl.insertBefore(filterBar, listEl);

  async function refresh(){
    listEl.innerHTML = 'Loading...';
    try{
      // also fetch users to show names
      const [assignments, queues, users] = await Promise.all([fetchJson('/admin/agent_assignments'), fetchJson('/admin/queues'), fetchJson('/admin/users')]);
  // populate queue select
  assignQueue.innerHTML = '<option value="">--select--</option>' + queues.map(q=>`<option value="${q.id}">${q.name}</option>`).join('');
  // populate filters
  const filterQueue = pageEl.querySelector('#filterQueue');
  const filterAgent = pageEl.querySelector('#filterAgent');
  filterQueue.innerHTML = '<option value="">--all--</option>' + queues.map(q=>`<option value="${q.id}">${q.name}</option>`).join('');
  filterAgent.innerHTML = '<option value="">--all--</option>' + (users||[]).map(u=>`<option value="${u.id}">${(u.first_name||'')+' '+(u.last_name||'')+' ('+u.id+')'}</option>`).join('');
      // build user map and replace agent id input with select
      const uidToName = Object.fromEntries((users||[]).map(u=>[u.id, (u.first_name||'')+' '+(u.last_name||'')+' ('+u.id+')']));
      const assignAgentEl = pageEl.querySelector('#assignAgentId');
      // replace input with select only once
      if(assignAgentEl && assignAgentEl.tagName.toLowerCase() === 'input'){
        const sel = document.createElement('select'); sel.id = 'assignAgentId'; sel.innerHTML = '<option value="">--select user--</option>'+ (users||[]).map(u=>`<option value="${u.id}">${(u.first_name||'')+' '+(u.last_name||'')+' ('+u.id+')'}</option>`).join('');
        assignAgentEl.parentNode.replaceChild(sel, assignAgentEl);
      }
      if(!Array.isArray(assignments)) throw new Error('unexpected assignments payload');
      // apply filters
      const selQueue = pageEl.querySelector('#filterQueue').value;
      const selAgent = pageEl.querySelector('#filterAgent').value;
      const filtered = assignments.filter(a => {
        if(selQueue && String(a.queue_id) !== String(selQueue)) return false;
        if(selAgent && String(a.agent_user_id) !== String(selAgent)) return false;
        return true;
      });
      listEl.innerHTML = `<table class="agentsTable"><thead><tr><th>ID</th><th>Agent User</th><th>Queue</th><th>Access</th><th>Actions</th></tr></thead><tbody>${filtered.map(a=>`<tr data-id="${a.id}"><td>${a.id}</td><td>${uidToName[a.agent_user_id]||a.agent_user_id}</td><td>${(Object.fromEntries(queues.map(q=>[q.id,q.name])))[a.queue_id]||a.queue_id}</td><td>${a.access_level||''}</td><td><button class="unassign" data-id="${a.id}">Unassign</button></td></tr>`).join('')}</tbody></table>`;
      listEl.querySelectorAll('button.unassign').forEach(b=>b.addEventListener('click', async (ev)=>{
        const id = ev.target.dataset.id;
        if(!confirm('Unassign agent assignment '+id+'?')) return;
        try{
          const res = await fetch('/admin/agents/assign/' + id, { method: 'DELETE', headers: new Headers({'x-test-user': localStorage.getItem('dev_x_test_user')||''}) });
          if(!res.ok) throw new Error('HTTP '+res.status);
          await refresh();
        }catch(err){ alert('Unassign failed: '+err.message) }
      }));
    }catch(err){ listEl.innerHTML = '<p class="error">Failed to load agent assignments: '+err.message+'</p>' }
  }

  // wire filter events
  pageEl.addEventListener('change', (ev)=>{
    if(ev.target && (ev.target.id === 'filterQueue' || ev.target.id === 'filterAgent')){
      refresh();
    }
  });
  pageEl.querySelector('#clearFilters').addEventListener('click', ()=>{
    pageEl.querySelector('#filterQueue').value = '';
    pageEl.querySelector('#filterAgent').value = '';
    refresh();
  });

  pageEl.querySelector('#assignBtn').addEventListener('click', async ()=>{
  const agentId = Number(pageEl.querySelector('#assignAgentId').value);
    const queueId = Number(assignQueue.value);
    const access = pageEl.querySelector('#assignAccess').value || null;
    if(!agentId || !queueId) return alert('agent id and queue required');
    try{
      await fetch('/admin/agents/assign', {method: 'POST', headers: new Headers({'Content-Type':'application/json','x-test-user': localStorage.getItem('dev_x_test_user')||''}), body: JSON.stringify({agent_user_id: agentId, queue_id: queueId, access_level: access})});
      pageEl.querySelector('#assignAgentId').value = '';
      assignQueue.value = '';
      await refresh();
    }catch(err){ alert('Assign failed: '+err.message) }
  });

  await refresh();
}
