// Mini ERP Service Worker
// Versão: controla invalidação do cache
const CACHE_VERSION = 'v1.4.0';
const STATIC_CACHE  = `erp-static-${CACHE_VERSION}`;
const PAGES_CACHE   = `erp-pages-${CACHE_VERSION}`;

// Arquivos estáticos para pré-cache (Cache First)
const STATIC_ASSETS = [
  '/static/css/style.css',
  '/static/css/vendas.css',
  '/static/js/themeManager.js',
  '/static/js/webauthn.js',
  '/static/js/sidebar.js',
  '/static/js/dateValidation.js',
  '/static/img/pwa-icon-light-192.png',
  '/static/img/pwa-icon-light-512.png',
  '/static/img/pwa-icon-dark-192.png',
  '/static/img/pwa-icon-dark-512.png',
  '/static/img/apple-touch-icon-light.png',
  '/static/img/apple-touch-icon-dark.png',
  '/static/manifest.json',
  '/static/manifest-light.json',
  '/static/manifest-dark.json',
];

// Página offline fallback
const OFFLINE_PAGE = '/offline';

// ─── INSTALL ─────────────────────────────────────────────
self.addEventListener('install', event => {
  event.waitUntil(
    caches.open(STATIC_CACHE).then(cache => {
      return cache.addAll(STATIC_ASSETS).catch(() => {
        // Falha silenciosa se algum asset não estiver disponível
      });
    }).then(() => self.skipWaiting())
  );
});

// ─── ACTIVATE ────────────────────────────────────────────
self.addEventListener('activate', event => {
  event.waitUntil(
    caches.keys().then(keys =>
      Promise.all(
        keys
          .filter(k => k !== STATIC_CACHE && k !== PAGES_CACHE)
          .map(k => caches.delete(k))
      )
    ).then(() => self.clients.claim())
  );
});

// ─── FETCH ───────────────────────────────────────────────
self.addEventListener('fetch', event => {
  const { request } = event;
  const url = new URL(request.url);

  // Ignorar requests não-GET, extensões e outros origins
  if (request.method !== 'GET') return;
  if (url.origin !== self.location.origin) return;

  // API / dados dinâmicos → Network First
  if (isApiRequest(url)) {
    event.respondWith(networkFirst(request));
    return;
  }

  // Assets estáticos → Cache First
  if (isStaticAsset(url)) {
    event.respondWith(cacheFirst(request));
    return;
  }

  // Páginas HTML → Network First com fallback offline
  event.respondWith(networkFirstWithOffline(request));
});

// ─── Helpers ─────────────────────────────────────────────
function isApiRequest(url) {
  return (
    url.pathname.startsWith('/api/') ||
    url.pathname.startsWith('/vendas') && url.search.includes('json')
  );
}

function isStaticAsset(url) {
  return url.pathname.startsWith('/static/');
}

async function cacheFirst(request) {
  const cached = await caches.match(request);
  if (cached) return cached;
  try {
    const response = await fetch(request);
    if (response.ok) {
      const cache = await caches.open(STATIC_CACHE);
      cache.put(request, response.clone());
    }
    return response;
  } catch {
    return new Response('Recurso indisponível offline', { status: 503 });
  }
}

async function networkFirst(request) {
  try {
    const response = await fetch(request);
    if (response.ok) {
      const cache = await caches.open(PAGES_CACHE);
      cache.put(request, response.clone());
    }
    return response;
  } catch {
    const cached = await caches.match(request);
    return cached || new Response('{"error":"offline"}', {
      status: 503,
      headers: { 'Content-Type': 'application/json' }
    });
  }
}

async function networkFirstWithOffline(request) {
  try {
    const response = await fetch(request);
    if (response.ok) {
      const cache = await caches.open(PAGES_CACHE);
      cache.put(request, response.clone());
    }
    return response;
  } catch {
    const cached = await caches.match(request);
    if (cached) return cached;
    // Fallback: página offline simples
    return new Response(offlineHTML(), {
      status: 200,
      headers: { 'Content-Type': 'text/html; charset=utf-8' }
    });
  }
}

function offlineHTML() {
  return `<!DOCTYPE html>
<html lang="pt-BR">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Sem conexão – Mini ERP</title>
  <style>
    *{margin:0;padding:0;box-sizing:border-box}
    body{background:#0f172a;color:#f1f5f9;font-family:system-ui,sans-serif;
         display:flex;flex-direction:column;align-items:center;justify-content:center;
         min-height:100vh;gap:24px;padding:24px;text-align:center}
    .icon{font-size:4rem}
    h1{font-size:1.5rem;font-weight:700;color:#f8fafc}
    p{color:#94a3b8;max-width:320px;line-height:1.6}
    button{background:#2563eb;color:#fff;border:none;border-radius:12px;
           padding:14px 28px;font-size:1rem;font-weight:600;cursor:pointer;margin-top:8px}
    button:hover{background:#1d4ed8}
  </style>
</head>
<body>
  <div class="icon">📡</div>
  <h1>Você está offline</h1>
  <p>Verifique sua conexão com a internet e tente novamente.</p>
  <button onclick="location.reload()">Tentar novamente</button>
</body>
</html>`;
}
