/* ─── MOF Jobs Service Worker ─────────────────────────────────────────── */
const VER          = 'mof-v8';
const STATIC_CACHE = `${VER}-static`;
const DYNAMIC_CACHE= `${VER}-dynamic`;
const ICON         = '/static/icons/icon-192.png';
const OFFLINE_URL  = '/offline.html';
const SHELL_ROUTES = ['/', '/login', '/dashboard', '/pwa-launch'];

/* Assets to precache immediately on install */
const PRECACHE = [
  '/',
  '/login',
  '/pwa-launch',
  OFFLINE_URL,
  '/static/icons/icon-192.png',
  '/static/icons/icon-512.png',
  '/static/icons/icon-192.svg',
  '/static/icons/icon-512.svg',
  '/manifest.json',
];

function isHtmlRequest(req) {
  return req.mode === 'navigate' || (req.headers.get('accept') || '').includes('text/html');
}

async function cacheShellRoutes() {
  const cache = await caches.open(DYNAMIC_CACHE);
  await Promise.allSettled(
    SHELL_ROUTES.map(async route => {
      const res = await fetch(route, {credentials: 'include'});
      if (res && res.ok && res.status < 400) {
        await cache.put(route, res.clone());
      }
    })
  );
}

async function offlineFallback(req) {
  const cached = await caches.match(req, {ignoreSearch: true});
  if (cached) return cached;

  if (req.mode === 'navigate') {
    const dashboard = await caches.match('/dashboard');
    if (dashboard) return dashboard;

    const home = await caches.match('/');
    if (home) return home;

    const login = await caches.match('/login');
    if (login) return login;
  }

  return caches.match(OFFLINE_URL);
}

/* ── Install ───────────────────────────────────────────────────────────────── */
self.addEventListener('install', e => {
  self.skipWaiting();
  e.waitUntil(
    caches.open(STATIC_CACHE)
      .then(c => c.addAll(PRECACHE).catch(() => {}))
      .then(() => cacheShellRoutes())
  );
});

/* ── Activate — purge old caches ──────────────────────────────────────────── */
self.addEventListener('activate', e => {
  e.waitUntil(
    caches.keys()
      .then(keys => Promise.all(
        keys.filter(k => k !== STATIC_CACHE && k !== DYNAMIC_CACHE).map(k => caches.delete(k))
      ))
      .then(() => self.clients.claim())
  );
});

/* ── Fetch strategy ───────────────────────────────────────────────────────── */
self.addEventListener('fetch', e => {
  const req = e.request;
  const url = new URL(req.url);

  if (req.method !== 'GET') return;
  if (!url.protocol.startsWith('http')) return;

  /* Static assets (css/js/fonts/images) → cache-first */
  if (/\.(css|js|woff2?|ttf|svg|png|jpg|jpeg|gif|ico|webp)(\?.*)?$/.test(url.pathname)
      || url.hostname !== self.location.hostname) {
    e.respondWith(
      caches.match(req).then(cached => {
        if (cached) return cached;
        return fetch(req).then(res => {
          if (res.ok) {
            const clone = res.clone();
            caches.open(DYNAMIC_CACHE).then(c => c.put(req, clone));
          }
          return res;
        }).catch(() => new Response('', {status: 408}));
      })
    );
    return;
  }

  /* HTML pages → network-first with cached shell fallback */
  if (isHtmlRequest(req)) {
    e.respondWith(
      fetch(req)
        .then(res => {
          if (res.ok && res.status < 400) {
            const clone = res.clone();
            caches.open(DYNAMIC_CACHE).then(c => c.put(req, clone));
          }
          return res;
        })
        .catch(() => offlineFallback(req))
    );
    return;
  }

  /* Everything else → network-first with generic cache fallback */
  e.respondWith(
    fetch(req)
      .then(res => {
        if (res.ok && res.status < 400) {
          const clone = res.clone();
          caches.open(DYNAMIC_CACHE).then(c => c.put(req, clone));
        }
        return res;
      })
      .catch(() => caches.match(req, {ignoreSearch: true}).then(cached => cached || new Response('', {status: 408})))
  );
});

/* ── Push notifications ───────────────────────────────────────────────────── */
self.addEventListener('push', e => {
  if (!e.data) return;
  let data = {};
  try { data = e.data.json(); } catch { data = {title: 'MOF Jobs', body: e.data.text()}; }

  e.waitUntil(
    self.registration.showNotification(data.title || 'MOF Jobs', {
      body:    data.body    || '',
      icon:    data.icon    || ICON,
      badge:   ICON,
      tag:     data.tag     || 'mof-notif',
      data:    {url: data.url || '/'},
      vibrate: [150, 75, 150],
      actions: data.url ? [{action:'open', title:'Open'}] : [],
    })
  );
});

self.addEventListener('notificationclick', e => {
  e.notification.close();
  const dest = e.notification.data?.url || '/';
  e.waitUntil(
    clients.matchAll({type:'window', includeUncontrolled:true}).then(cs => {
      const found = cs.find(c => c.url === dest);
      return found ? found.focus() : clients.openWindow(dest);
    })
  );
});

