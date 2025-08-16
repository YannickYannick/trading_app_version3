/**
 * Configuration PWA pour Trading App
 * Gestion des notifications push, installation, etc.
 */

class PWAManager {
    constructor() {
        this.isSupported = 'serviceWorker' in navigator && 'PushManager' in window;
        this.registration = null;
        this.subscription = null;
        this.isInstalled = false;
        
        this.init();
    }
    
    async init() {
        if (!this.isSupported) {
            console.warn('⚠️ PWA non supportée par ce navigateur');
            return;
        }
        
        console.log('🚀 Initialisation PWA...');
        
        try {
            // Enregistrer le Service Worker
            await this.registerServiceWorker();
            
            // Vérifier l'installation
            this.checkInstallation();
            
            // Initialiser les notifications
            await this.initPushNotifications();
            
            console.log('✅ PWA initialisée avec succès');
            
        } catch (error) {
            console.error('❌ Erreur initialisation PWA:', error);
        }
    }
    
    async registerServiceWorker() {
        try {
            this.registration = await navigator.serviceWorker.register('/static/sw.js');
            console.log('✅ Service Worker enregistré:', this.registration);
            
            // Écouter les mises à jour
            this.registration.addEventListener('updatefound', () => {
                const newWorker = this.registration.installing;
                newWorker.addEventListener('statechange', () => {
                    if (newWorker.state === 'installed' && navigator.serviceWorker.controller) {
                        this.showUpdateNotification();
                    }
                });
            });
            
            return this.registration;
            
        } catch (error) {
            console.error('❌ Erreur enregistrement Service Worker:', error);
            throw error;
        }
    }
    
    checkInstallation() {
        // Vérifier si l'app est installée
        if (window.matchMedia('(display-mode: standalone)').matches) {
            this.isInstalled = true;
            console.log('📱 Application installée en mode standalone');
        }
        
        // Écouter les changements de mode d'affichage
        window.matchMedia('(display-mode: standalone)').addEventListener('change', (e) => {
            this.isInstalled = e.matches;
            console.log('🔄 Mode d\'affichage changé:', this.isInstalled ? 'standalone' : 'browser');
        });
    }
    
    async initPushNotifications() {
        try {
            // Vérifier les permissions
            const permission = await Notification.requestPermission();
            
            if (permission === 'granted') {
                console.log('✅ Permissions notifications accordées');
                await this.subscribeToPush();
            } else if (permission === 'denied') {
                console.warn('⚠️ Permissions notifications refusées');
            } else {
                console.log('ℹ️ Permissions notifications non définies');
            }
            
        } catch (error) {
            console.error('❌ Erreur initialisation notifications:', error);
        }
    }
    
    async subscribeToPush() {
        try {
            if (!this.registration) {
                throw new Error('Service Worker non enregistré');
            }
            
            // S'abonner aux notifications push
            this.subscription = await this.registration.pushManager.subscribe({
                userVisibleOnly: true,
                applicationServerKey: this.urlBase64ToUint8Array(this.getVapidPublicKey())
            });
            
            console.log('✅ Abonnement push créé:', this.subscription);
            
            // Envoyer l'abonnement au serveur
            await this.sendSubscriptionToServer();
            
        } catch (error) {
            console.error('❌ Erreur abonnement push:', error);
        }
    }
    
    async sendSubscriptionToServer() {
        try {
            const response = await fetch('/pwa/subscribe/', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': this.getCSRFToken()
                },
                body: JSON.stringify({
                    subscription: this.subscription,
                    user_id: this.getCurrentUserId()
                })
            });
            
            const data = await response.json();
            
            if (data.success) {
                console.log('✅ Abonnement envoyé au serveur');
            } else {
                console.error('❌ Erreur envoi abonnement:', data.error);
            }
            
        } catch (error) {
            console.error('❌ Erreur envoi abonnement:', error);
        }
    }
    
    async unsubscribeFromPush() {
        try {
            if (this.subscription) {
                await this.subscription.unsubscribe();
                console.log('✅ Désabonnement push réussi');
                
                // Notifier le serveur
                await this.sendUnsubscriptionToServer();
                
                this.subscription = null;
            }
            
        } catch (error) {
            console.error('❌ Erreur désabonnement push:', error);
        }
    }
    
    async sendUnsubscriptionToServer() {
        try {
            const response = await fetch('/pwa/unsubscribe/', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': this.getCSRFToken()
                },
                body: JSON.stringify({
                    subscription: this.subscription,
                    user_id: this.getCurrentUserId()
                })
            });
            
            const data = await response.json();
            
            if (data.success) {
                console.log('✅ Désabonnement notifié au serveur');
            } else {
                console.error('❌ Erreur notification désabonnement:', data.error);
            }
            
        } catch (error) {
            console.error('❌ Erreur notification désabonnement:', error);
        }
    }
    
    showUpdateNotification() {
        const toast = document.createElement('div');
        toast.className = 'alert alert-info position-fixed';
        toast.style.cssText = 'top: 20px; right: 20px; z-index: 9999; min-width: 300px;';
        toast.innerHTML = `
            <div class="d-flex align-items-center">
                <i class="fas fa-sync-alt me-2"></i>
                <div>
                    <strong>Mise à jour disponible</strong><br>
                    <small>Une nouvelle version de l'app est disponible</small>
                </div>
                <button class="btn btn-sm btn-primary ms-3" onclick="pwaManager.updateApp()">
                    Mettre à jour
                </button>
            </div>
        `;
        
        document.body.appendChild(toast);
        
        setTimeout(() => {
            toast.remove();
        }, 10000);
    }
    
    async updateApp() {
        if (this.registration && navigator.serviceWorker.controller) {
            navigator.serviceWorker.controller.postMessage({ type: 'SKIP_WAITING' });
            window.location.reload();
        }
    }
    
    async sendTestNotification(message = 'Test PWA') {
        try {
            const response = await fetch('/pwa/test-notification/', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': this.getCSRFToken()
                },
                body: JSON.stringify({
                    user_id: this.getCurrentUserId(),
                    message: message
                })
            });
            
            const data = await response.json();
            
            if (data.success) {
                console.log('✅ Notification de test envoyée');
                this.showToast('Notification de test envoyée !', 'success');
            } else {
                console.error('❌ Erreur notification de test:', data.error);
                this.showToast('Erreur notification de test', 'danger');
            }
            
        } catch (error) {
            console.error('❌ Erreur notification de test:', error);
            this.showToast('Erreur notification de test', 'danger');
        }
    }
    
    async getPWAStatus() {
        try {
            const response = await fetch('/pwa/status/');
            const data = await response.json();
            
            if (data.success) {
                console.log('📊 Statut PWA:', data.data);
                return data.data;
            } else {
                console.error('❌ Erreur récupération statut:', data.error);
                return null;
            }
            
        } catch (error) {
            console.error('❌ Erreur récupération statut:', error);
            return null;
        }
    }
    
    showToast(message, type = 'info') {
        const toast = document.createElement('div');
        toast.className = `alert alert-${type} position-fixed`;
        toast.style.cssText = 'top: 20px; right: 20px; z-index: 9999; min-width: 300px;';
        toast.innerHTML = message;
        
        document.body.appendChild(toast);
        
        setTimeout(() => {
            toast.remove();
        }, 3000);
    }
    
    // Utilitaires
    getCSRFToken() {
        const name = 'csrftoken';
        let cookieValue = null;
        if (document.cookie && document.cookie !== '') {
            const cookies = document.cookie.split(';');
            for (let i = 0; i < cookies.length; i++) {
                const cookie = cookies[i].trim();
                if (cookie.substring(0, name.length + 1) === (name + '=')) {
                    cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                    break;
                }
            }
        }
        return cookieValue;
    }
    
    getCurrentUserId() {
        // Récupérer l'ID utilisateur depuis le DOM ou une variable globale
        const userIdElement = document.querySelector('[data-user-id]');
        if (userIdElement) {
            return userIdElement.dataset.userId;
        }
        
        // Fallback: essayer de récupérer depuis une variable globale
        if (window.currentUserId) {
            return window.currentUserId;
        }
        
        return null;
    }
    
    getVapidPublicKey() {
        // Clé publique VAPID pour les notifications push
        // À remplacer par votre vraie clé VAPID
        return 'BEl62iUYgUivxIkv69yViEuiBIa1ORoFmVmrJMKdNWY';
    }
    
    urlBase64ToUint8Array(base64String) {
        const padding = '='.repeat((4 - base64String.length % 4) % 4);
        const base64 = (base64String + padding)
            .replace(/-/g, '+')
            .replace(/_/g, '/');
        
        const rawData = window.atob(base64);
        const outputArray = new Uint8Array(rawData.length);
        
        for (let i = 0; i < rawData.length; ++i) {
            outputArray[i] = rawData.charCodeAt(i);
        }
        return outputArray;
    }
}

// Initialiser le gestionnaire PWA
let pwaManager;

document.addEventListener('DOMContentLoaded', () => {
    pwaManager = new PWAManager();
});

// Exposer globalement pour les tests
window.pwaManager = pwaManager;
