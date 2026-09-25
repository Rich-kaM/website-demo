import '/assets/js/common.js';
const loginForm=document.getElementById('admin-login');
const statusBox=loginForm?.querySelector('[data-status]');
const dashboard=document.getElementById('dashboard');
const editorControls=document.getElementById('editor-controls');
const loginBox=document.getElementById('login');
function showStatus(el,msg,error=false){if(!el)return;el.textContent=msg;el.classList.add('show');el.classList.toggle('error-status',error);}
async function refresh(){
  const d=await APAH.api('/api/admin/data');
  document.getElementById('counts').innerHTML=`<div class="card"><b>Leads</b><div>${d.counts.leads}</div></div><div class="card"><b>Applications</b><div>${d.counts.applications}</div></div><div class="card"><b>Subscribers</b><div>${d.counts.subscribers}</div></div>`;
  document.getElementById('leads').innerHTML=d.leads.map(x=>`<p><strong>${x.name}</strong>, ${x.email}, ${x.status}</p>`).join('')||'<p>Aucun contact.</p>';
  document.getElementById('apps').innerHTML=d.applications.map(x=>`<p><strong>${x.name}</strong>, ${x.email}, ${x.status}</p>`).join('')||'<p>Aucune candidature.</p>';
}
loginForm?.addEventListener('submit',async e=>{e.preventDefault();try{const r=await APAH.api('/api/admin/login',{method:'POST',body:JSON.stringify(Object.fromEntries(new FormData(loginForm)))});loginBox.classList.add('hide');dashboard.classList.remove('hide');if(editorControls) editorControls.classList.remove('hide');await refresh();showStatus(statusBox,`Connecté avec le rôle ${r.role}.`);}catch(err){showStatus(statusBox,err.message||'Échec de la connexion.',true);}});
async function submitJson(form,endpoint,statusEl){try{await APAH.api(endpoint,{method:'POST',body:JSON.stringify(Object.fromEntries(new FormData(form)))});showStatus(statusEl,'Enregistré.');form.reset();await refresh();}catch(err){showStatus(statusEl,err.message||'Échec de l’enregistrement.',true);}}
document.getElementById('actuality-form')?.addEventListener('submit',e=>{e.preventDefault();submitJson(e.currentTarget,'/api/admin/actuality',document.querySelector('[data-actuality-status]'));});
document.getElementById('job-form')?.addEventListener('submit',e=>{e.preventDefault();submitJson(e.currentTarget,'/api/admin/jobs',document.querySelector('[data-job-status]'));});
document.getElementById('admin-logout')?.addEventListener('click',async()=>{try{await APAH.api('/api/admin/logout',{method:'POST'});location.reload();}catch(err){alert(err.message||'Échec de la déconnexion.');}});
