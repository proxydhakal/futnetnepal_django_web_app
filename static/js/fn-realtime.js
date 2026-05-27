/**
 * Futnet Nepal WebSocket helpers (Django Channels).
 */
window.FnRealtime = {
    wsUrl(path) {
        const proto = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        return `${proto}//${window.location.host}${path}`;
    },

    connect(path, handlers) {
        const ws = new WebSocket(this.wsUrl(path));
        ws.onopen = () => handlers.onopen && handlers.onopen(ws);
        ws.onmessage = (e) => {
            try {
                const data = JSON.parse(e.data);
                if (data.event === 'connected') return;
                handlers.onmessage && handlers.onmessage(data, ws);
            } catch (err) {
                console.warn('FnRealtime parse error', err);
            }
        };
        ws.onclose = (ev) => {
            handlers.onclose && handlers.onclose(ws, ev);
            if (handlers.reconnect !== false && !handlers._stopped && ev.code !== 4403) {
                setTimeout(() => {
                    if (handlers._stopped) return;
                    this.connect(path, handlers);
                }, handlers.reconnectDelay || 3000);
            }
        };
        ws.onerror = () => handlers.onerror && handlers.onerror(ws);
        handlers._stopped = false;
        handlers.close = () => {
            handlers._stopped = true;
            handlers.reconnect = false;
            ws.close();
        };
        return ws;
    },

    connectNotifications(callbacks) {
        return this.connect('/ws/notifications/', {
            reconnect: true,
            reconnectDelay: 4000,
            onmessage: (data) => callbacks.onmessage && callbacks.onmessage(data),
            onopen: () => callbacks.onopen && callbacks.onopen(),
        });
    },

    connectDmChat(conversationId, callbacks) {
        return this.connect(`/ws/dm/${conversationId}/`, {
            reconnect: true,
            reconnectDelay: 3000,
            onmessage: (data) => callbacks.onmessage && callbacks.onmessage(data),
            onclose: () => callbacks.onclose && callbacks.onclose(),
        });
    },

    /** @deprecated Use connectDmChat(conversationId). Kept for cached scripts. */
    connectEventChat(postId, callbacks) {
        return this.connect(`/ws/events/${postId}/chat/`, {
            reconnect: true,
            reconnectDelay: 3000,
            onmessage: (data) => callbacks.onmessage && callbacks.onmessage(data),
            onclose: () => callbacks.onclose && callbacks.onclose(),
        });
    },
};
