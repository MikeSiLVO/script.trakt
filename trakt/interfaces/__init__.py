from trakt.interfaces import movies
from trakt.interfaces import oauth
from trakt.interfaces import scrobble
from trakt.interfaces import search
from trakt.interfaces import shows
from trakt.interfaces import sync
from trakt.interfaces import users

# Flat registry: path string → interface class
INTERFACES = {
    'oauth':            oauth.OAuthInterface,
    'oauth/device':     oauth.DeviceOAuthInterface,

    'scrobble':         scrobble.ScrobbleInterface,
    'search':           search.SearchInterface,

    'sync':             sync.SyncInterface,
    'sync/collection':  sync.SyncCollectionInterface,
    'sync/history':     sync.SyncHistoryInterface,
    'sync/playback':    sync.SyncPlaybackInterface,
    'sync/ratings':     sync.SyncRatingsInterface,
    'sync/watched':     sync.SyncWatchedInterface,
    'sync/watchlist':   sync.SyncWatchlistInterface,

    'shows':            shows.ShowsInterface,
    'movies':           movies.MoviesInterface,

    'users':            users.UsersInterface,
    'users/settings':   users.UsersSettingsInterface,
}


def construct_map(client):
    return {path: cls(client) for path, cls in INTERFACES.items()}
