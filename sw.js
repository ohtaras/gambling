/* Τράβα ρε — service worker: η σελίδα ανοίγει σαν εφαρμογή. Πάντα φέρνει τη νέα έκδοση από το δίκτυο· αν δεν υπάρχει ίντερνετ δείχνει την τελευταία αποθηκευμένη. */
var C = 'trv-v1';
self.addEventListener('install', function(e){ self.skipWaiting(); });
self.addEventListener('activate', function(e){ e.waitUntil(self.clients.claim()); });
self.addEventListener('fetch', function(e){
  var r = e.request; if(r.method !== 'GET' || r.mode !== 'navigate') return;
  e.respondWith(fetch(r).then(function(res){ var cp = res.clone(); caches.open(C).then(function(c){ c.put(r.url.split('?')[0], cp); }); return res; })
    .catch(function(){ return caches.match(r.url.split('?')[0]); }));
});
