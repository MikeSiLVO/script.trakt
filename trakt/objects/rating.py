from trakt.core.helpers import from_iso8601_datetime


class Rating(object):
    def __init__(self, client, value=None, timestamp=None, votes=None):
        self._client = client

        self.value = value
        self.votes = votes
        self.timestamp = timestamp

    @classmethod
    def _construct(cls, client, info):
        if not info or 'rating' not in info:
            return

        # Only accept personal ratings (have rated_at timestamp).
        # The Trakt API now returns community ratings (float, no rated_at)
        # in collection/watched responses — ignore those.
        if not info.get('rated_at'):
            return

        r = cls(client)
        r.value = info.get('rating')
        r.votes = info.get('votes')
        r.timestamp = from_iso8601_datetime(info.get('rated_at'))
        return r

    def __getstate__(self):
        state = self.__dict__

        if hasattr(self, '_client'):
            del state['_client']

        return state

    def __eq__(self, other):
        if not isinstance(other, Rating):
            return NotImplemented

        return self.value == other.value and self.timestamp == other.timestamp

    def __repr__(self):
        return '<Rating %s/10 voted by %s (%s) >' % (self.value, self.votes, self.timestamp)

    def __str__(self):
        return self.__repr__()
