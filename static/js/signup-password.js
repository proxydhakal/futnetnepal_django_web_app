function signupPasswordHints(checkUrl) {
    return {
        passwordHints: [],
        showHints: false,
        checking: false,
        _debounce: null,

        init() {
            const input = document.getElementById('id_password1');
            if (!input) return;
            input.addEventListener('input', () => this.onPasswordInput());
            input.addEventListener('focus', () => { this.showHints = true; this.onPasswordInput(); });
            input.addEventListener('blur', () => {
                if (!input.value) this.showHints = false;
            });
            ['id_full_name', 'id_username', 'id_email'].forEach((id) => {
                const el = document.getElementById(id);
                if (el) el.addEventListener('input', () => this.onPasswordInput());
            });
        },

        onPasswordInput() {
            clearTimeout(this._debounce);
            this._debounce = setTimeout(() => this.fetchHints(), 280);
        },

        csrf() {
            return document.querySelector('[name=csrfmiddlewaretoken]')?.value || '';
        },

        async fetchHints() {
            const password = document.getElementById('id_password1')?.value || '';
            if (!password) {
                this.passwordHints = [];
                return;
            }
            this.checking = true;
            const fd = new FormData();
            fd.append('password', password);
            fd.append('username', document.getElementById('id_username')?.value || '');
            fd.append('email', document.getElementById('id_email')?.value || '');
            fd.append('full_name', document.getElementById('id_full_name')?.value || '');
            fd.append('csrfmiddlewaretoken', this.csrf());
            try {
                const res = await fetch(checkUrl, {
                    method: 'POST',
                    body: fd,
                    headers: { 'X-Requested-With': 'XMLHttpRequest' },
                });
                const data = await res.json();
                if (data.suggestions) this.passwordHints = data.suggestions;
            } catch (_) {
                /* ignore network blips while typing */
            }
            this.checking = false;
        },

        hintClass(ok) {
            if (ok === true) return 'fn-password-hint fn-password-hint--ok';
            if (ok === false) return 'fn-password-hint fn-password-hint--fail';
            return 'fn-password-hint fn-password-hint--pending';
        },

        hintIcon(ok) {
            if (ok === true) return 'fa-circle-check';
            if (ok === false) return 'fa-circle-xmark';
            return 'fa-circle';
        },
    };
}
