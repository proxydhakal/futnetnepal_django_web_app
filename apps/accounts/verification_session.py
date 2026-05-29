"""Session keys used during signup email + phone verification."""


def stash_pending_verification(request, user, profile):
    """Keep signup verification context in session for the combined verify page."""
    request.session['pending_verify_email'] = user.email
    request.session['pending_verify_phone'] = profile.phone or ''
