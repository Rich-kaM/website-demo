import '/assets/js/common.js';
const grid=document.querySelector('[data-actuality-grid]');
const empty=document.querySelector('[data-actuality-empty]');
const search=document.querySelector('[data-actuality-search]');
let items=[];
function render(){const q=(search?.value||'').toLowerCase().trim();const filtered=items.filter(x=>[x.title,x.summary,x.category,x.author||''].join(' ').toLowerCase().includes(q));if(!filtered.length){if(grid)grid.innerHTML='';if(empty){empty.hidden=false;empty.textContent=items.length?'Aucune actualité correspondante.':'Aucune actualité n’a encore été publiée. Abonnez-vous à notre newsletter pour suivre les actualités de l’entreprise.';}return;}if(empty)empty.hidden=true;grid.innerHTML=filtered.map(x=>`<article class="card reveal"><span class="pill">${x.category}</span><p class="help">${new Date(x.published_at).toLocaleDateString('fr-FR')}</p><h2>${x.title}</h2><p>${x.summary}</p><a class="text-link" href="/fr/actualites/${encodeURIComponent(x.slug)}">Lire la suite</a></article>`).join('');}
async function load(){try{const r=await fetch('/api/actuality?lang=fr');items=r.items||[];render();}catch{if(empty){empty.hidden=false;empty.textContent='Le service Actualités est temporairement indisponible.';}}}
search?.addEventListener('input',render);load();
