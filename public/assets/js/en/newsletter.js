import '/assets/js/common.js';
const status=new URLSearchParams(location.search).get('status');
const box=document.querySelector('[data-status-page]');
const messages={confirmed:'Your subscription is confirmed.',invalid:'This confirmation link is invalid or expired.'};
if(box&&status&&messages[status]){box.textContent=messages[status];box.classList.add('show',status==='confirmed'?'success-status':'error-status');box.setAttribute('tabindex','-1');box.focus();}
