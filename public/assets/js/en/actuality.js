import '/assets/js/common.js';
const grid=document.querySelector('[data-actuality-grid]');
const empty=document.querySelector('[data-actuality-empty]');
const search=document.querySelector('[data-actuality-search]');
let items=[];
function render(){const q=(search?.value||'').toLowerCase().trim();const filtered=items.filter(x=>[x.title,x.summary,x.category,x.author||''].join(' ').toLowerCase().includes(q));if(!filtered.length){if(grid)grid.innerHTML='';if(empty){empty.hidden=false;empty.textContent=items.length?'No matching actuality items.':'No news has been published yet. Subscribe to our newsletter to be informed of company updates.';}return;}if(empty)empty.hidden=true;grid.innerHTML=filtered.map(x=>`<article class="card reveal"><span class="pill">${x.category}</span><p class="help">${new Date(x.published_at).toLocaleDateString('en-GB')}</p><h2>${x.title}</h2><p>${x.summary}</p><a class="text-link" href="/en/actuality/${encodeURIComponent(x.slug)}">Read more</a></article>`).join('');}
async function load(){try{const r=await fetch('/api/actuality?lang=en');items=r.items||[];render();}catch{if(empty){empty.hidden=false;empty.textContent='Actuality is temporarily unavailable.';}}}
search?.addEventListener('input',render);load();
