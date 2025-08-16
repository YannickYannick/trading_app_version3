/**
 * Service Worker pour Trading App PWA
 * Gère le cache, les notifications push et l'offline
 */

const CACHE_NAME = 'trading-app-v1.0.0';
const STATIC_CACHE = 'trading-app-static-v1.0.0';
const DYNAMIC_CACHE = 'trading-app-dynamic-v1.0.0';

// URLs à mettre en cache statique
const STATIC_URLS = [
  '/',
  '/static/css/bootstrap.min.css',
  '/static/css/fontawesome.min.css',
  '/static/js/bootstrap.bundle.min.js',
  '/static/js/jquery.min.js',
  '/static/icons/icon-192x192.png',
  '/static/icons/icon-512x512.png'
];

// URLs à mettre en cache dynamique
const DYNAMIC_URLS = [
  '/strategies/tabulator/',
  '/brokers/',
  '/positions/tabulator/',
  '/assets/tabulator/',
  '/trades/tabulator/'
];

// Installation du Service Worker
self.addEventListener('install', (event) => {
  console.log('🚀 Service Worker: Installation...');
  
  event.waitUntil(
    caches.open(STATIC_CACHE)
      .then((cache) => {
        console.log('📦 Cache statique ouvert');
        return cache.addAll(STATIC_URLS);
      })
      .then(() => {
        console.log('✅ Cache statique rempli');
        return self.skipWaiting();
      })
      .catch((error) => {
        console.error('❌ Erreur lors de l\'installation:', error);
      })
  );
});

// Activation du Service Worker
self.addEventListener('activate', (event) => {
  console.log('🔄 Service Worker: Activation...');
  
  event.waitUntil(
    caches.keys()
      .then((cacheNames) => {
        return Promise.all(
          cacheNames.map((cacheName) => {
            if (cacheName !== STATIC_CACHE && cacheName !== DYNAMIC_CACHE) {
              console.log('🗑️ Suppression de l\'ancien cache:', cacheName);
              return caches.delete(cacheName);
            }
          })
        );
      })
      .then(() => {
        console.log('✅ Service Worker activé');
        return self.clients.claim();
      })
  );
});

// Interception des requêtes réseau
self.addEventListener('fetch', (event) => {
  const { request } = event;
  const url = new URL(request.url);
  
  // Ignorer les requêtes non-GET
  if (request.method !== 'GET') {
    return;
  }
  
  // Ignorer les requêtes d'API
  if (url.pathname.startsWith('/api/') || url.pathname.includes('ajax')) {
    return;
  }
  
  // Stratégie de cache: Cache First pour les ressources statiques
  if (STATIC_URLS.includes(url.pathname) || url.pathname.startsWith('/static/')) {
    event.respondWith(cacheFirst(request, STATIC_CACHE));
    return;
  }
  
  // Stratégie de cache: Network First pour les pages
  if (DYNAMIC_URLS.includes(url.pathname) || url.pathname === '/') {
    event.respondWith(networkFirst(request, DYNAMIC_CACHE));
    return;
  }
  
  // Stratégie par défaut: Network First
  event.respondWith(networkFirst(request, DYNAMIC_CACHE));
});

// Stratégie Cache First
async function cacheFirst(request, cacheName) {
  try {
    const cachedResponse = await caches.match(request);
    if (cachedResponse) {
      return cachedResponse;
    }
    
    const networkResponse = await fetch(request);
    if (networkResponse.ok) {
      const cache = await caches.open(cacheName);
      cache.put(request, networkResponse.clone());
    }
    return networkResponse;
  } catch (error) {
    console.error('❌ Erreur Cache First:', error);
    return new Response('Erreur de cache', { status: 500 });
  }
}

// Stratégie Network First
async function networkFirst(request, cacheName) {
  try {
    const networkResponse = await fetch(request);
    if (networkResponse.ok) {
      const cache = await caches.open(cacheName);
      cache.put(request, networkResponse.clone());
    }
    return networkResponse;
  } catch (error) {
    console.log('🌐 Hors ligne, utilisation du cache...');
    const cachedResponse = await caches.match(request);
    if (cachedResponse) {
      return cachedResponse;
    }
    
    // Page d'erreur hors ligne
    if (request.destination === 'document') {
      return caches.match('/offline.html');
    }
    
    return new Response('Hors ligne', { status: 503 });
  }
}

// Gestion des notifications push
self.addEventListener('push', (event) => {
  console.log('📱 Notification push reçue:', event);
  
  let notificationData = {
    title: 'Trading App',
    body: 'Nouvelle notification',
    icon: '/static/icons/icon-192x192.png',
    badge: '/static/icons/badge-72x72.png',
    vibrate: [100, 50, 100],
    data: {
      dateOfArrival: Date.now(),
      primaryKey: 1
    },
    actions: [
      {
        action: 'open',
        title: 'Ouvrir',
        icon: '/static/icons/open-96x96.png'
      },
      {
        action: 'close',
        title: 'Fermer',
        icon: '/static/icons/close-96x96.png'
      }
    ]
  };
  
  // Traitement des données de notification
  if (event.data) {
    try {
      const data = event.data.json();
      notificationData = { ...notificationData, ...data };
    } catch (error) {
      notificationData.body = event.data.text();
    }
  }
  
  event.waitUntil(
    self.registration.showNotification(notificationData.title, notificationData)
  );
});

// Gestion des clics sur les notifications
self.addEventListener('notificationclick', (event) => {
  console.log('👆 Clic sur notification:', event);
  
  event.notification.close();
  
  if (event.action === 'open' || !event.action) {
    event.waitUntil(
      clients.matchAll({ type: 'window', includeUncontrolled: true })
        .then((clientList) => {
          // Si une fenêtre est déjà ouverte, la focaliser
          for (const client of clientList) {
            if (client.url.includes('/') && 'focus' in client) {
              return client.focus();
            }
          }
          
          // Sinon, ouvrir une nouvelle fenêtre
          if (clients.openWindow) {
            return clients.openWindow('/');
          }
        })
    );
  }
});

// Gestion des messages du client
self.addEventListener('message', (event) => {
  console.log('💬 Message reçu du client:', event.data);
  
  if (event.data && event.data.type === 'SKIP_WAITING') {
    self.skipWaiting();
  }
  
  if (event.data && event.data.type === 'GET_VERSION') {
    event.ports[0].postMessage({ version: CACHE_NAME });
  }
});

// Synchronisation en arrière-plan
self.addEventListener('sync', (event) => {
  console.log('🔄 Synchronisation en arrière-plan:', event.tag);
  
  if (event.tag === 'background-sync') {
    event.waitUntil(doBackgroundSync());
  }
});

// Fonction de synchronisation en arrière-plan
async function doBackgroundSync() {
  try {
    console.log('🔄 Début de la synchronisation en arrière-plan...');
    
    // Ici vous pouvez ajouter la logique de synchronisation
    // Par exemple, récupérer les dernières données des brokers
    
    console.log('✅ Synchronisation terminée');
  } catch (error) {
    console.error('❌ Erreur lors de la synchronisation:', error);
  }
}

// Gestion des erreurs
self.addEventListener('error', (event) => {
  console.error('💥 Erreur Service Worker:', event.error);
});

// Gestion des rejets de promesses non gérés
self.addEventListener('unhandledrejection', (event) => {
  console.error('💥 Promesse rejetée non gérée:', event.reason);
});
