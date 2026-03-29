
from trakt.objects.list.base import List


class CustomList(List):
    @classmethod
    def _construct(cls, client, keys, info, user):
        if not info:
            return None

        obj = cls(client, keys, user)
        obj._update(info)
        return obj
