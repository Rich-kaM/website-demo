import '/assets/js/common.js';
const latestGrid=document.querySelector('[data-latest-actuality-grid]');
const latestEmpty=document.querySelector('[data-latest-actuality-empty]');
(async()=>{try{const r=await fetch('/api/actuality?lang=fr');const xs=(r.items||[]).slice(0,3);if(!xs.length)return;latestEmpty?.remove();if(latestGrid)latestGrid.innerHTML=xs.map(v=>`<article class=\"card\"><span class=\"pill\">${v.category}</span><p class=\"help\">${new Date(v.published_at).toLocaleDateString('fr-FR')}</p><h3>${v.title}</h3><p>${v.summary}</p><a class=\"text-link\" href=\"/fr/actualites/${encodeURIComponent(v.slug)}\">Lire la suite</a></article>`).join('');}catch{}})();
