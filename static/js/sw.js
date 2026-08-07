self.addEventListener('install',e=>self.skipWaiting());
self.addEventListener('activate',e=>e.waitUntil(self.clients.claim()));
self.addEventListener('push',function(e){let d={title:'Romseerr',body:''};
 try{d=e.data.json()}catch(_){if(e.data)d.body=e.data.text()}
 e.waitUntil(self.registration.showNotification(d.title||'Romseerr',{body:d.body||'',icon:'/icon.svg',badge:'/icon.svg'}));});
self.addEventListener('notificationclick',function(e){e.notification.close();
 e.waitUntil(clients.matchAll({type:'window'}).then(cs=>{for(const c of cs){if('focus'in c)return c.focus();}if(clients.openWindow)return clients.openWindow('/');}));});
