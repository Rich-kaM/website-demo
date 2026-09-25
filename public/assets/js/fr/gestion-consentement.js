import '/assets/js/common.js';
document.getElementById('reset-consent')?.addEventListener('click',()=>{try{localStorage.removeItem('apah-theme');localStorage.removeItem('apah-cookie-notice');location.reload();}catch(_){}});
