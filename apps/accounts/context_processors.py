from apps.accounts.models import Profile


def user_profile(request):
    if not request.user.is_authenticated:
        return {}
    try:
        return {'userprofiledata': Profile.objects.get(user=request.user)}
    except Profile.DoesNotExist:
        return {}
