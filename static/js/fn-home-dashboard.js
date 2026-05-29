/**
 * Futnet home dashboard shell — create modal + Alpine merge with post edit/delete.
 */
function dashboard() {
    return {
        showCreate: false,
        creating: false,
        initDashboard() {
            if (this._formHasErrors) {
                this.$nextTick(() => this.openCreate());
            }
        },
        openCreate() {
            this.showCreate = true;
            this.$nextTick(() => {
                document.dispatchEvent(new CustomEvent('fn-select2-init', {
                    detail: { scope: '#createForm', parent: '#createModalPanel' },
                }));
            });
        },
        closeCreate() {
            if (window.fnDestroySelect2) window.fnDestroySelect2('#createForm');
            this.showCreate = false;
        },
        submitCreate() {
            if (this.creating) return;
            const form = document.getElementById('createForm');
            if (!form) return;
            if (typeof fnApplyFormErrors === 'function') fnApplyFormErrors(form, null);
            this.creating = true;
            fetch(form.action, {
                method: 'POST',
                body: new FormData(form),
                headers: { 'X-Requested-With': 'XMLHttpRequest' },
            })
                .then(r => r.json().then(d => ({ ok: r.ok, d })))
                .then(({ ok, d }) => {
                    if (ok && d.success) {
                        this.prependPost(d.post_html);
                        form.reset();
                        if (window.fnDestroySelect2) window.fnDestroySelect2('#createForm');
                        this.closeCreate();
                        window.dispatchEvent(new CustomEvent('toast', {
                            detail: { text: d.message || 'Match posted successfully.', type: 'success' },
                        }));
                    } else if (d.errors && typeof fnApplyFormErrors === 'function') {
                        fnApplyFormErrors(form, d.errors);
                    } else {
                        window.dispatchEvent(new CustomEvent('toast', {
                            detail: { text: d.error || 'Please check the form and try again.', type: 'error' },
                        }));
                    }
                })
                .catch(() => {
                    window.dispatchEvent(new CustomEvent('toast', {
                        detail: { text: 'Could not post match. Please try again.', type: 'error' },
                    }));
                })
                .finally(() => { this.creating = false; });
        },
        prependPost(html) {
            if (!html) return;
            const feed = document.getElementById('homeFeed');
            if (!feed) return;
            const empty = document.getElementById('homeFeedEmpty');
            if (empty) empty.remove();
            feed.insertAdjacentHTML('afterbegin', html);
            const inserted = feed.firstElementChild;
            if (inserted && window.Alpine) window.Alpine.initTree(inserted);
        },
    };
}

function appShell() {
    return Object.assign(
        {
            _formHasErrors: false,
            init() {
                this.initDashboard();
            },
        },
        dashboard(),
    );
}

function profileShell() {
    return Object.assign(
        {
            init() {
                this.initDashboard();
            },
        },
        dashboard(),
        typeof postEditModal === 'function' ? postEditModal() : {},
        typeof postDeleteModal === 'function' ? postDeleteModal() : {},
    );
}

function homeShell() {
    return Object.assign(
        {
            scrolled: false,
            mobileOpen: false,
            activeNav: 'feed',
            _formHasErrors: false,
            init() {
                this._formHasErrors = document.querySelector('[data-form-errors]') !== null;
                this.initDashboard();
            },
        },
        dashboard(),
        typeof postEditModal === 'function' ? postEditModal() : {},
        typeof postDeleteModal === 'function' ? postDeleteModal() : {},
    );
}
