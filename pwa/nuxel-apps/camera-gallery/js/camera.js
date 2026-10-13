// Helper: wrap the shared bridge call with a graceful offline fallback.
async function nuxelBridgeCall(namespace, verb, params, fallback) {
    try {
        const b = window.NuxelBridge;
        if (!b) { window.__nuxelBridgeOffline = true; return fallback; }
        const res = await b.call(namespace, verb, params);
        if (!res || res.success === false) { window.__nuxelBridgeOffline = true; return fallback; }
        window.__nuxelBridgeOffline = false;
        return res;
    } catch (e) { window.__nuxelBridgeOffline = true; return fallback; }
}

function nuxelBridgeOfflineBanner() {
    if (!window.__nuxelBridgeOffline) return;
    if (document.getElementById('bridge-offline-banner')) return;
    const el = document.createElement('div');
    el.id = 'bridge-offline-banner';
    el.textContent = '🔌 Bridge offline — showing local data';
    el.style.cssText = 'position:fixed;bottom:0;left:0;right:0;background:#ef6c00;color:#fff;font-size:13px;padding:6px 12px;z-index:9999;text-align:center;';
    document.body.appendChild(el);
}

// Nuxel Camera - Camera & Gallery PWA

class CameraApp {
    constructor() {
        this.stream = null;
        this.photos = [];
        this.isRecording = false;
        this.currentMode = 'photo'; // 'photo' or 'video'
        this._init();
    }

    async _init() {
        await this._loadGallery();
        this._bindEvents();
    }

    async _startCamera(facingMode = 'environment') {
        try {
            const constraints = {
                video: {
                    facingMode: facingMode,
                    width: { ideal: 1440 },
                    height: { ideal: 3120 },
                },
                audio: this.currentMode === 'video',
            };

            this.stream = await navigator.mediaDevices.getUserMedia(constraints);
            
            const video = document.getElementById('video-preview');
            video.srcObject = this.stream;
            video.classList.remove('hidden');
            await video.play();

            document.querySelector('.viewfinder-placeholder').classList.add('hidden');
            
        } catch (e) {
            console.warn('[Camera] Could not access camera:', e.message);
            // Show placeholder with error
            document.querySelector('.viewfinder-placeholder p').textContent = 
                'Camera not available: ' + e.message;
        }
    }

    _stopCamera() {
        if (this.stream) {
            this.stream.getTracks().forEach(track => track.stop());
            this.stream = null;
        }
        const video = document.getElementById('video-preview');
        video.classList.add('hidden');
        video.srcObject = null;
        document.querySelector('.viewfinder-placeholder').classList.remove('hidden');
        document.querySelector('.viewfinder-placeholder p').textContent = 'Camera preview';
    }

    async _capturePhoto() {
        if (!this.stream) {
            await this._startCamera();
            // Give camera time to warm up
            await new Promise(r => setTimeout(r, 500));
        }

        const video = document.getElementById('video-preview');
        const canvas = document.createElement('canvas');
        const width = video.videoWidth || 1440;
        const height = video.videoHeight || 3120;
        
        canvas.width = width;
        canvas.height = height;
        
        const ctx = canvas.getContext('2d');
        ctx.drawImage(video, 0, 0, width, height);
        
        // Get JPEG data
        const dataUrl = canvas.toDataURL('image/jpeg', 0.92);
        
        // Save to gallery
        const photo = {
            id: `photo-${Date.now()}`,
            dataUrl: dataUrl,
            timestamp: new Date().toISOString(),
            width: width,
            height: height,
        };
        
        this.photos.unshift(photo);
        this._saveGallery();
        // Report the capture to the shared bridge (best effort).
        nuxelBridgeCall('camera', 'capture', { app_id: 'org.nuxel.Camera', captures: this.photos, capture: photo }, null);
        
        // Haptic feedback
        if (navigator.vibrate) navigator.vibrate(50);
        
        // Show brief flash effect
        const flash = document.createElement('div');
        flash.style.cssText = 'position:fixed;top:0;left:0;right:0;bottom:0;background:white;z-index:5;animation:fadeOut 0.3s ease;';
        document.body.appendChild(flash);
        setTimeout(() => flash.remove(), 300);
        
        return photo;
    }

    _toggleMode() {
        this.currentMode = this.currentMode === 'photo' ? 'video' : 'photo';
        document.getElementById('switch-mode').textContent = 
            this.currentMode === 'photo' ? '📹' : '📷';
    }

    _openGallery() {
        this._stopCamera();
        document.getElementById('camera-view').classList.add('hidden');
        document.getElementById('gallery-view').classList.remove('hidden');
        this._renderGallery();
    }

    _closeGallery() {
        document.getElementById('gallery-view').classList.add('hidden');
        document.getElementById('camera-view').classList.remove('hidden');
    }

    _renderGallery() {
        const grid = document.getElementById('photo-grid');
        
        if (this.photos.length === 0) {
            grid.innerHTML = `
                <div style="grid-column:1/-1;display:flex;flex-direction:column;align-items:center;justify-content:center;padding:80px 20px;color:#555;">
                    <span style="font-size:48px;margin-bottom:12px">🖼️</span>
                    <p>No photos yet</p>
                </div>`;
            return;
        }

        grid.innerHTML = this.photos.map(photo => `
            <div class="photo-item" data-id="${photo.id}">
                <img src="${photo.dataUrl}" alt="Photo ${photo.id}" loading="lazy">
            </div>
        `).join('');

        // Click to view full size
        grid.querySelectorAll('.photo-item').forEach(item => {
            item.addEventListener('click', () => {
                const id = item.dataset.id;
                const photo = this.photos.find(p => p.id === id);
                if (photo) {
                    // Show fullscreen viewer
                    const viewer = document.createElement('div');
                    viewer.style.cssText = 'position:fixed;top:0;left:0;right:0;bottom:0;background:#000;z-index:20;display:flex;align-items:center;justify-content:center;';
                    const img = document.createElement('img');
                    img.src = photo.dataUrl;
                    img.style.cssText = 'max-width:100%;max-height:100%;object-fit:contain;';
                    viewer.appendChild(img);
                    viewer.addEventListener('click', () => viewer.remove());
                    document.body.appendChild(viewer);
                }
            });
        });
    }

    async _loadGallery() {
        const fallback = () => {
            try {
                const raw = localStorage.getItem('nuxel-camera-photos');
                return raw ? JSON.parse(raw) : [];
            } catch (e) {
                return [];
            }
        };
        try {
            const res = await nuxelBridgeCall('camera', 'list-captures', { app_id: 'org.nuxel.Camera' }, null);
            if (res && Array.isArray(res.captures)) {
                this.photos = res.captures;
            } else {
                this.photos = fallback();
            }
            nuxelBridgeOfflineBanner();
        } catch (e) {
            this.photos = fallback();
        }
    }

    _saveGallery() {
        try {
            // Only keep last 50 photos to manage storage
            if (this.photos.length > 50) {
                this.photos = this.photos.slice(0, 50);
            }
            localStorage.setItem('nuxel-camera-photos', JSON.stringify(this.photos));
        } catch (e) {
            console.warn('[Camera] Storage full, clearing old photos');
            this.photos = this.photos.slice(0, 10);
            try {
                localStorage.setItem('nuxel-camera-photos', JSON.stringify(this.photos));
            } catch (e2) {}
        }
    }

    _bindEvents() {
        // Capture button
        document.getElementById('capture-btn').addEventListener('click', async () => {
            if (this.currentMode === 'photo') {
                await this._capturePhoto();
            }
        });

        // Switch camera
        document.getElementById('switch-camera').addEventListener('click', () => {
            this._stopCamera();
            const currentFacing = this.stream?.getVideoTracks()[0]?.getSettings().facingMode;
            const newFacing = currentFacing === 'environment' ? 'user' : 'environment';
            this._startCamera(newFacing);
        });

        // Switch mode
        document.getElementById('switch-mode').addEventListener('click', () => this._toggleMode());

        // Gallery
        document.getElementById('gallery-btn').addEventListener('click', () => this._openGallery());
        document.getElementById('gallery-back').addEventListener('click', () => this._closeGallery());

        // Animation keyframes
        const style = document.createElement('style');
        style.textContent = `
            @keyframes fadeOut { from { opacity: 1; } to { opacity: 0; } }
        `;
        document.head.appendChild(style);

        // Start camera on mount
        this._startCamera();

        // Handle visibility changes to save power
        document.addEventListener('visibilitychange', () => {
            if (document.hidden) {
                this._stopCamera();
            } else {
                this._startCamera();
            }
        });
    }
}

document.addEventListener('DOMContentLoaded', () => {
    window.cameraApp = new CameraApp();
});
