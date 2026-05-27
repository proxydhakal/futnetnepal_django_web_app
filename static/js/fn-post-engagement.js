function postEngagement(postId, postSlug, hostUsername, interested, liked, interestCount, likeCount, commentCount, canChat, isHost, eventLocked) {
    return {
        postId,
        postSlug,
        hostUsername,
        interested,
        liked,
        interestCount,
        likeCount,
        commentCount,
        canChat,
        isHost,
        eventLocked,
        showComments: false,
        loadingComments: false,
        comments: [],
        newComment: '',
        replyTo: null,
        commenting: false,
        get messageUrl() {
            if (this.isHost) return '/messages/';
            if (this.hostUsername) return `/messages/${this.postSlug}/with/${this.hostUsername}/`;
            return `/messages/${this.postSlug}/`;
        },
        csrf() {
            return document.querySelector('#createForm [name=csrfmiddlewaretoken]')?.value
                || document.querySelector('#editForm [name=csrfmiddlewaretoken]')?.value
                || document.querySelector('[name=csrfmiddlewaretoken]')?.value || '';
        },
        confirmMatch() {
            if (!confirm('Confirm this match? Interest and chat will close for everyone.')) return;
            const fd = new FormData();
            fd.append('csrfmiddlewaretoken', this.csrf());
            fetch(`/posts/${this.postId}/confirm-match/`, { method: 'POST', body: fd, headers: { 'X-Requested-With': 'XMLHttpRequest' } })
                .then(r => r.json())
                .then(d => {
                    if (d.success) {
                        this.eventLocked = true;
                        location.reload();
                    } else if (d.error) {
                        alert(d.error);
                    }
                });
        },
        cancelConfirmation() {
            if (!confirm('Cancel match confirmation? Planning and chat will reopen.')) return;
            const fd = new FormData();
            fd.append('csrfmiddlewaretoken', this.csrf());
            fetch(`/posts/${this.postId}/cancel-confirmation/`, { method: 'POST', body: fd, headers: { 'X-Requested-With': 'XMLHttpRequest' } })
                .then(r => r.json())
                .then(d => {
                    if (d.success) {
                        this.eventLocked = false;
                        location.reload();
                    } else if (d.error) {
                        alert(d.error);
                    }
                });
        },
        toggleInterest() {
            if (this.eventLocked) return;
            const fd = new FormData();
            fd.append('csrfmiddlewaretoken', this.csrf());
            fetch(`/posts/${this.postId}/interest/`, { method: 'POST', body: fd, headers: { 'X-Requested-With': 'XMLHttpRequest' } })
                .then(r => r.json())
                .then(d => {
                    if (d.success) {
                        this.interested = d.interested;
                        this.interestCount = d.interest_count;
                        if (d.interested) this.canChat = true;
                        else this.canChat = false;
                    }
                });
        },
        toggleLike() {
            if (this.eventLocked) return;
            const fd = new FormData();
            fd.append('csrfmiddlewaretoken', this.csrf());
            fetch(`/posts/${this.postId}/react/`, { method: 'POST', body: fd, headers: { 'X-Requested-With': 'XMLHttpRequest' } })
                .then(r => r.json().then(d => ({ ok: r.ok, d })))
                .then(({ ok, d }) => {
                    if (ok && d.success) {
                        this.liked = d.liked;
                        this.likeCount = d.like_count;
                    } else if (d.error) {
                        alert(d.error);
                    }
                });
        },
        toggleComments() {
            this.showComments = !this.showComments;
            if (this.showComments && !this.comments.length) this.loadComments();
        },
        startReply(id, name) {
            this.replyTo = id;
            this.newComment = `@${name} `;
        },
        loadComments() {
            this.loadingComments = true;
            fetch(`/posts/${this.postId}/comments/`, { headers: { 'X-Requested-With': 'XMLHttpRequest' } })
                .then(r => r.json())
                .then(d => { if (d.success) this.comments = d.comments; })
                .finally(() => { this.loadingComments = false; });
        },
        addComment() {
            if (this.eventLocked) return;
            const body = this.newComment.trim();
            if (!body) return;
            this.commenting = true;
            const fd = new FormData();
            fd.append('csrfmiddlewaretoken', this.csrf());
            fd.append('body', body);
            if (this.replyTo) fd.append('parent_id', this.replyTo);
            fetch(`/posts/${this.postId}/comments/add/`, { method: 'POST', body: fd, headers: { 'X-Requested-With': 'XMLHttpRequest' } })
                .then(r => r.json().then(d => ({ ok: r.ok, d })))
                .then(({ ok, d }) => {
                    if (ok && d.success) {
                        this.newComment = '';
                        this.replyTo = null;
                        this.commentCount = d.comment_count;
                        this.comments = d.comments;
                    } else if (d.error) {
                        alert(d.error);
                    }
                })
                .finally(() => { this.commenting = false; });
        },
    };
}

function postEditModal() {
    return {
        showEdit: false,
        editingPostId: null,
        saving: false,
        openEdit(id) {
            this.editingPostId = id;
            fetch('/get_edit_data/' + id + '/')
                .then(r => r.json().then(d => ({ ok: r.ok, d })))
                .then(({ ok, d }) => {
                    if (!ok || d.error) {
                        alert(d.error || 'Could not load event.');
                        return;
                    }
                    document.getElementById('edit_date').value = d.date;
                    document.getElementById('edit_message').value = d.message;
                    this.showEdit = true;
                    this.$nextTick(() => {
                        setTimeout(() => {
                            if (window.fnSetSelect2Values) {
                                window.fnSetSelect2Values({
                                    edit_location: d.location,
                                    edit_venue: d.venue,
                                    edit_time: d.time,
                                });
                            }
                        }, 120);
                    });
                })
                .catch(() => alert('Could not load event.'));
        },
        closeEdit() {
            if (window.fnDestroySelect2) window.fnDestroySelect2('#editForm');
            this.showEdit = false;
            this.editingPostId = null;
        },
        submitEdit() {
            this.saving = true;
            document.getElementById('editFormError').classList.add('hidden');
            fetch('/update_post/' + this.editingPostId + '/', {
                method: 'POST',
                body: new FormData(document.getElementById('editForm')),
                headers: { 'X-Requested-With': 'XMLHttpRequest' },
            })
                .then(r => r.json().then(d => ({ ok: r.ok, d })))
                .then(({ ok, d }) => {
                    if (ok && d.success) {
                        window.dispatchEvent(new CustomEvent('toast', { detail: { text: d.message || 'Event updated.', type: 'success' } }));
                        setTimeout(() => location.reload(), 600);
                    } else {
                        const err = document.getElementById('editFormError');
                        err.textContent = d.error || 'Please check the form and try again.';
                        err.classList.remove('hidden');
                    }
                })
                .catch(() => alert('Update failed. Please try again.'))
                .finally(() => { this.saving = false; });
        },
    };
}

function postDeleteModal() {
    return {
        showDelete: false,
        deletingPostId: null,
        deletingPostSlug: null,
        deletingPreview: '',
        deleting: false,
        deleteError: '',
        csrf() {
            return document.querySelector('#createForm [name=csrfmiddlewaretoken]')?.value
                || document.querySelector('#editForm [name=csrfmiddlewaretoken]')?.value
                || document.querySelector('[name=csrfmiddlewaretoken]')?.value || '';
        },
        openDelete(detail) {
            this.deletingPostId = detail.id;
            this.deletingPostSlug = detail.slug;
            this.deletingPreview = detail.preview || '';
            this.deleteError = '';
            this.deleting = false;
            this.showDelete = true;
        },
        closeDelete() {
            if (this.deleting) return;
            this.showDelete = false;
            this.deletingPostId = null;
            this.deletingPostSlug = null;
            this.deletingPreview = '';
            this.deleteError = '';
        },
        confirmDelete() {
            if (!this.deletingPostId || this.deleting) return;
            this.deleting = true;
            this.deleteError = '';
            const fd = new FormData();
            fd.append('csrfmiddlewaretoken', this.csrf());
            fetch(`/posts/${this.deletingPostId}/delete/`, {
                method: 'POST',
                body: fd,
                headers: { 'X-Requested-With': 'XMLHttpRequest' },
            })
                .then(r => r.json().then(d => ({ ok: r.ok, d })))
                .then(({ ok, d }) => {
                    if (ok && d.success) {
                        const el = this.deletingPostSlug
                            ? document.getElementById('post-' + this.deletingPostSlug)
                            : null;
                        if (el) el.remove();
                        this.showDelete = false;
                        window.dispatchEvent(new CustomEvent('toast', {
                            detail: { text: d.message || 'Match deleted.', type: 'success' },
                        }));
                        this.deletingPostId = null;
                        this.deletingPostSlug = null;
                        this.deletingPreview = '';
                    } else {
                        this.deleteError = d.error || 'Could not delete this match.';
                    }
                })
                .catch(() => { this.deleteError = 'Delete failed. Please try again.'; })
                .finally(() => { this.deleting = false; });
        },
    };
}
