// Minimal admin SPA: routing and tiny fetch wrapper
const pageEl = document.getElementById('page');
const links = document.querySelectorAll('nav a[data-route]');

links.forEach(a => a.addEventListener('click', (e) => {
  e.preventDefault();
  const route = a.dataset.route;
  navigate(route);
}));

function navigate(route){
  if(route === 'users') return loadUsersPage();
  if(route === 'queues') return loadQueues();
  if(route === 'agents') return loadAgents();
  if(route === 'ticket-types') return loadTicketTypes();
  if(route === 'activity-types') return loadActivityTypes();
  if(route === 'activities') return loadActivities();
  if(route === 'roles-groups') return loadRolesGroups();
  if(route === 'spaces') return loadSpaces();
  if(route === 'space-templates') return loadSpaceTemplates();
  if(route === 'buildings') return loadBuildings();
  pageEl.innerHTML = '<p>Unknown route</p>';
}

async function fetchJson(path, opts={}){
  // Inject dev test-user header if configured in localStorage
  const devUser = localStorage.getItem('dev_x_test_user');
  const headers = new Headers(opts.headers || {});
  if (devUser) headers.set('x-test-user', devUser);
  const finalOpts = Object.assign({}, opts, { headers });
  const res = await fetch(path, finalOpts);
  if(!res.ok) throw new Error('HTTP '+res.status);
  return res.json();
}

async function loadUsersPage(){
  const mod = await import('/admin/static/js/users.js');
  return mod.loadUsersPage(pageEl, fetchJson);
}

async function loadQueues(){
  // dynamic import
  const mod = await import('/admin/static/js/queues.js');
  return mod.loadQueues(pageEl, fetchJson);
}

async function loadTicketTypes(){
  const mod = await import('/admin/static/js/ticket_types.js');
  return mod.loadTicketTypes(pageEl, fetchJson);
}

async function loadActivityTypes(){
  const mod = await import('/admin/static/js/activity_types.js');
  return mod.loadActivityTypes(pageEl, fetchJson);
}

async function loadActivities(){
  const mod = await import('/admin/static/js/activities.js');
  return mod.loadActivities(pageEl, fetchJson);
}

async function loadRolesGroups(){
  const mod = await import('/admin/static/js/roles_groups.js');
  return mod.loadRolesGroups(pageEl, fetchJson);
}

async function loadSpaces(){
  const mod = await import('/admin/static/js/spaces.js');
  return mod.loadSpacesPage(pageEl, fetchJson);
}

async function loadSpaceTemplates(){
  const mod = await import('/admin/static/js/space_templates.js');
  return mod.loadSpaceTemplatesPage(pageEl, fetchJson);
}

async function loadAgents(){
  const mod = await import('/admin/static/js/agents.js');
  return mod.loadAgents(pageEl, fetchJson);
}

async function loadBuildings(){
  const mod = await import('/admin/static/js/buildings.js');
  return mod.loadBuildingsPage(pageEl, fetchJson);
}

// Auto open users on first load
navigate('users');

// Dev auth UI wiring
const devInput = document.getElementById('devTestUser');
const setBtn = document.getElementById('setDevUser');
const clearBtn = document.getElementById('clearDevUser');
if(devInput && setBtn && clearBtn){
  const cur = localStorage.getItem('dev_x_test_user') || '';
  devInput.value = cur;
  setBtn.addEventListener('click', ()=>{
    const v = devInput.value.trim();
    if(v) localStorage.setItem('dev_x_test_user', v); else localStorage.removeItem('dev_x_test_user');
    alert('dev x-test-user set to: '+(v||'<cleared>'));
  });
  clearBtn.addEventListener('click', ()=>{
    localStorage.removeItem('dev_x_test_user');
    devInput.value = '';
    alert('cleared');
  });
}
