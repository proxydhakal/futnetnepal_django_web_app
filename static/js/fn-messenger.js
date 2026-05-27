/**
 * Futnet Nepal — private 1:1 event messenger
 */
window.FnMessenger = function (config) {
    return {
        threads: [],
        activeThread: null,
        messages: [],
        loadingThreads: true,
        loadingMessages: false,
        messageText: '',
        sending: false,
        _chatWs: null,
        activeConversationId: config.activeConversationId || null,
        currentUserId: Number(config.currentUserId) || 0,
        mobileView: config.activeConversationId ? 'thread' : 'inbox',

        normalizeMessage(m) {
            if (!m) return m;
            if (m.is_system) return m;
            const senderId = m.sender_id != null ? Number(m.sender_id) : null;
            return {
                ...m,
                is_mine: senderId !== null && senderId === this.currentUserId,
            };
        },

        init() {
            this.loadThreads().then(() => {
                if (this.activeConversationId) {
                    this.openThread(this.activeConversationId, { skipHistory: true });
                }
            });
        },

        csrf() {
            return document.querySelector('[name=csrfmiddlewaretoken]')?.value || config.csrf || '';
        },

        convUrl(template, conversationId) {
            return template.replace('CONV_ID', String(conversationId));
        },

        async loadThreads() {
            this.loadingThreads = true;
            try {
                const res = await fetch(config.inboxUrl);
                const d = await res.json();
                if (d.success) this.threads = d.threads;
            } catch (e) {}
            this.loadingThreads = false;
        },

        backToInbox() {
            this.mobileView = 'inbox';
            this.disconnectWs();
            this.activeConversationId = null;
            this.activeThread = null;
            this.messages = [];
            history.replaceState(null, '', '/messages/');
        },

        async openThread(conversationId, opts = {}) {
            this.activeConversationId = conversationId;
            this.mobileView = 'thread';
            this.loadingMessages = true;
            this.messages = [];
            this.disconnectWs();
            const thread = this.threads.find(t => t.conversation_id === conversationId);
            if (thread && !opts.skipHistory) {
                history.replaceState(null, '', thread.url);
            }
            try {
                const res = await fetch(this.convUrl(config.threadUrl, conversationId));
                const d = await res.json();
                if (d.success) {
                    this.activeThread = d.thread;
                    this.messages = d.messages.map((m) => this.normalizeMessage(m));
                    this.connectWs(conversationId);
                    this.$nextTick(() => this.scrollToBottom());
                }
            } catch (e) {}
            this.loadingMessages = false;
        },

        connectWs(conversationId) {
            if (!window.FnRealtime) return;
            this._chatWs = FnRealtime.connectDmChat(conversationId, {
                onmessage: (data) => this.handleWsMessage(data),
            });
        },

        disconnectWs() {
            if (this._chatWs?.close) this._chatWs.close();
            this._chatWs = null;
        },

        handleWsMessage(data) {
            if (data.event === 'chat_message' && data.message) {
                const m = this.normalizeMessage(data.message);
                if (!this.messages.some(x => x.id === m.id)) {
                    this.messages.push(m);
                    this.scrollToBottom();
                }
                if (data.thread) this.activeThread = data.thread;
                this.loadThreads();
            }
        },

        scrollToBottom() {
            this.$nextTick(() => {
                const el = this.$refs.messageList;
                if (el) el.scrollTop = el.scrollHeight;
            });
        },

        async sendMessage() {
            if (this.activeThread?.is_locked) return;
            const body = this.messageText.trim();
            if (!body || !this.activeConversationId) return;
            this.sending = true;
            const fd = new FormData();
            fd.append('csrfmiddlewaretoken', this.csrf());
            fd.append('body', body);
            try {
                const res = await fetch(this.convUrl(config.sendUrl, this.activeConversationId), {
                    method: 'POST',
                    body: fd,
                    headers: { 'X-Requested-With': 'XMLHttpRequest' },
                });
                const d = await res.json();
                if (d.success) {
                    this.messageText = '';
                    if (d.message && !this.messages.some(x => x.id === d.message.id)) {
                        this.messages.push(this.normalizeMessage(d.message));
                    }
                    if (d.thread) this.activeThread = d.thread;
                    this.scrollToBottom();
                    this.loadThreads();
                }
            } catch (e) {}
            this.sending = false;
        },

        async confirmAttendance() {
            await this._postAction(this.convUrl(config.confirmAttendanceUrl, this.activeConversationId));
        },

        async declineAttendance() {
            await this._postAction(this.convUrl(config.declineAttendanceUrl, this.activeConversationId));
        },

        async confirmMatch() {
            if (!confirm('Confirm this match? Chat, comments, and reactions will be locked.')) return;
            await this._postAction(this.convUrl(config.confirmMatchUrl, this.activeConversationId));
        },

        async cancelConfirmation() {
            if (!confirm('Cancel match confirmation? Chat, comments, and reactions will reopen for everyone.')) return;
            await this._postAction(this.convUrl(config.cancelConfirmationUrl, this.activeConversationId));
        },

        async _postAction(url) {
            const fd = new FormData();
            fd.append('csrfmiddlewaretoken', this.csrf());
            try {
                const res = await fetch(url, {
                    method: 'POST',
                    body: fd,
                    headers: { 'X-Requested-With': 'XMLHttpRequest' },
                });
                const d = await res.json();
                if (d.success) {
                    if (d.message && !this.messages.some(x => x.id === d.message.id)) {
                        this.messages.push(this.normalizeMessage(d.message));
                    }
                    if (d.thread) this.activeThread = d.thread;
                    this.scrollToBottom();
                    this.loadThreads();
                }
            } catch (e) {}
        },

        statusLabel(status) {
            const map = {
                open: 'Open',
                discussing: 'Discussing',
                confirmed: 'Match confirmed',
                cancelled: 'Cancelled',
            };
            return map[status] || status;
        },

        statusClass(status) {
            if (status === 'confirmed') return 'bg-emerald-100 text-emerald-800';
            if (status === 'discussing') return 'bg-sky-100 text-sky-800';
            return 'bg-slate-100 text-slate-700';
        },
    };
};
