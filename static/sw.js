/* ─── MOF Jobs Service Worker ─────────────────────────────────────────── */
const VER          = 'mof-v20';
const STATIC_CACHE = `${VER}-static`;
const DYNAMIC_CACHE= `${VER}-dynamic`;
const ICON         = '/static/icons/icon-192.png';
const BADGE        = '/static/icons/badge-96.png';
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
  '/static/icons/icon-1024.png',
  '/static/icons/icon-maskable-192.png',
  '/static/icons/icon-maskable-512.png',
  '/static/icons/badge-96.png',
  '/static/icons/apple-touch-icon.png',
  '/static/icons/favicon-32.png',
  '/manifest.json',
];

function isHtmlRequest(req) {
  return req.mode === 'navigate' || (req.headers.get('accept') || '').includes('text/html');
}

/* Avoid caching auth-sensitive endpoints */
function isUncacheable(url) {
  return /^\/(logout|login|api\/v1\/(auth|push))/.test(url.pathname);
}

async function cacheShellRoutes() {
  const cache = await caches.open(DYNAMIC_CACHE);
  await Promise.allSettled(
    SHELL_ROUTES.map(async route => {
      try {
        const res = await fetch(route, {credentials: 'include'});
        if (res && res.ok && res.status < 400) {
          await cache.put(route, res.clone());
        }
      } catch (_) {}
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
  if (isUncacheable(url)) return;

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
self.addEventListener('push', event => {
  let data = {};
  if (event.data) {
    try { data = event.data.json(); }
    catch { data = {title: 'MOF Jobs', body: event.data.text()}; }
  }

  const title = data.title || 'MOF Jobs';
  const body  = data.body  || data.message || 'You have a new notification';
  const url   = data.url   || data.link    || '/notifications';
  const tag   = data.tag   || ('mof-' + (data.id || Date.now()));

  const options = {
    body,
    icon:    data.icon  || ICON,
    badge:   data.badge || BADGE,
    image:   data.image || undefined,
    tag,
    renotify: true,
    requireInteraction: !!data.requireInteraction,
    silent: false,
    timestamp: Date.now(),
    vibrate: [120, 60, 120],
    data: { url, id: data.id || null },
    actions: [
      { action: 'open', title: 'Open' },
      { action: 'dismiss', title: 'Dismiss' },
    ],
  };

  event.waitUntil(
    self.registration.showNotification(title, options)
      .then(() => self.clients.matchAll({type:'window', includeUncontrolled:true}))
      .then(cs => cs.forEach(c => c.postMessage({type:'push', title, body, url})))
  );
});

self.addEventListener('notificationclick', event => {
  event.notification.close();
  if (event.action === 'dismiss') return;
  const dest = (event.notification.data && event.notification.data.url) || '/';
  event.waitUntil(
    clients.matchAll({type:'window', includeUncontrolled:true}).then(cs => {
      for (const c of cs) {
        try {
          const u = new URL(c.url);
          if (u.pathname + u.search === dest || c.url === dest) {
            return c.focus();
          }
        } catch (_) {}
      }
      return clients.openWindow(dest);
    })
  );
});

/* Re-subscribe when the push subscription changes (browser may rotate keys) */
self.addEventListener('pushsubscriptionchange', event => {
  event.waitUntil((async () => {
    try {
      const r = await fetch('/api/v1/push/vapid-public-key', {credentials: 'include'});
      const { publicKey } = await r.json();
      if (!publicKey) return;
      const conv = b64 => {
        const pad = '='.repeat((4 - b64.length % 4) % 4);
        const raw = atob((b64 + pad).replace(/-/g, '+').replace(/_/g, '/'));
        return Uint8Array.from([...raw].map(c => c.charCodeAt(0)));
      };
      const sub = await self.registration.pushManager.subscribe({
        userVisibleOnly: true,
        applicationServerKey: conv(publicKey),
      });
      await fetch('/api/v1/push/subscribe', {
        method: 'POST',
        credentials: 'include',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify(sub.toJSON()),
      });
    } catch (e) {}
  })());
});

/* Allow page → SW messages (skipWaiting trigger) */
self.addEventListener('message', e => {
  if (e.data && e.data.type === 'SKIP_WAITING') self.skipWaiting();
});
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

