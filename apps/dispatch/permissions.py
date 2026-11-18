from apps.accounts.models import UserProfile


def can_dispatch(user):
    if not user.is_authenticated:
        return False
    if user.is_staff:
        return True
    profile = getattr(user, "taxi_profile", None)
    return bool(profile and profile.role in (UserProfile.Role.DISPATCHER, UserProfile.Role.ADMIN))
