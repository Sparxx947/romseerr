let setup=false;
fetch('/api/version').then(r=>r.json()).then(v=>{document.getElementById('ver').textContent='v'+v.version;}).catch(()=>{});
fetch('/api/auth/status').then(r=>r.json()).then(d=>{if(d.user){location.href='/';return;}
 setup=d.setup;if(setup){document.getElementById('sub').textContent='Ersteinrichtung — Administrator anlegen';
 document.getElementById('btn').textContent='Administrator anlegen';document.getElementById('fgt').style.display='none';}});
async function forgot(){let q=prompt('Benutzername oder E-Mail / username or email:');if(!q)return;
 await fetch('/api/forgot',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({user:q})});
 let e=document.getElementById('err');e.style.color='#8b929e';
 e.textContent='Falls die Adresse existiert, wurde eine Mail gesendet. / If the address exists, an email was sent.';}
async function go(e){e.preventDefault();
 let u=document.getElementById('u').value.trim(),p=document.getElementById('p').value;
 let r=await fetch(setup?'/api/setup':'/api/login',{method:'POST',headers:{'Content-Type':'application/json'},
   body:JSON.stringify({username:u,password:p})});
 let d=await r.json();if(d.ok)location.href='/';else document.getElementById('err').textContent=d.msg||'Fehler';}
