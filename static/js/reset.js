let tok=new URLSearchParams(location.search).get('token')||'';
async function go(e){e.preventDefault();
 let r=await fetch('/api/reset',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({token:tok,new:document.getElementById('p').value})});
 let d=await r.json();if(d.ok)location.href='/login';else document.getElementById('err').textContent=d.msg||'Fehler';}
