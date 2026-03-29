from trakt.interfaces.base import Interface
from trakt.interfaces.users.settings import UsersSettingsInterface

__all__ = (
    'UsersInterface',
    'UsersSettingsInterface',
)


class UsersInterface(Interface):
    path = 'users'
