import logging

import xbmc
import xbmcgui
from resources.lib import syncEpisodes, syncMovies
from resources.lib.kodiUtilities import getSetting, getSettingAsBool, setSetting

logger = logging.getLogger(__name__)


class Sync():
    def __init__(self, show_progress=False, run_silent=False, library="all", api=None, manual=False):
        self.traktapi = api
        self.progress = xbmcgui.DialogProgress()
        self.show_progress = show_progress
        self.run_silent = run_silent
        self.library = library
        self.manual = manual
        if self.show_progress and self.run_silent:
            logger.debug("Sync is being run silently.")
        self.sync_on_update = getSettingAsBool('sync_on_update')
        self.notify = getSettingAsBool('show_sync_notifications')
        self.notify_during_playback = not getSettingAsBool("hide_notifications_playback")

    def __syncCheck(self, media_type):
        return self.__syncCollectionCheck(media_type) or self.__syncWatchedCheck(media_type) or self.__syncPlaybackCheck(media_type) or self.__syncRatingsCheck()

    def __syncPlaybackCheck(self, media_type):
        if media_type == 'movies':
            return getSettingAsBool('trakt_movie_playback')
        else:
            return getSettingAsBool('trakt_episode_playback')

    def __syncCollectionCheck(self, media_type):
        if media_type == 'movies':
            return getSettingAsBool('add_movies_to_trakt') or getSettingAsBool('clean_trakt_movies')
        else:
            return getSettingAsBool('add_episodes_to_trakt') or getSettingAsBool('clean_trakt_episodes')

    def __syncRatingsCheck(self):
        return getSettingAsBool('trakt_sync_ratings')

    def __syncWatchedCheck(self, media_type):
        if media_type == 'movies':
            return getSettingAsBool('trakt_movie_playcount') or getSettingAsBool('kodi_movie_playcount')
        else:
            return getSettingAsBool('trakt_episode_playcount') or getSettingAsBool('kodi_episode_playcount')

    @property
    def show_notification(self):
        return not self.show_progress and self.sync_on_update and self.notify and (self.notify_during_playback or not xbmc.Player().isPlayingVideo())

    def sync(self):
        logger.info("Starting synchronization with Trakt.tv")

        if not self.manual and self.__canSkipSync():
            logger.info("[Sync] No changes on Trakt or Kodi since last sync, skipping.")
            return

        if self.__syncCheck('movies'):
            if self.library in ["all", "movies"]:
                syncMovies.SyncMovies(self, self.progress)
            else:
                logger.debug(
                    "Movie sync is being skipped for this manual sync.")
        else:
            logger.debug("Movie sync is disabled, skipping.")

        if self.__syncCheck('episodes'):
            if self.library in ["all", "episodes"]:
                if not (self.__syncCheck('movies') and self.IsCanceled()):
                    syncEpisodes.SyncEpisodes(self, self.progress)
                else:
                    logger.debug(
                        "Episode sync is being skipped because movie sync was canceled.")
            else:
                logger.debug(
                    "Episode sync is being skipped for this manual sync.")
        else:
            logger.debug("Episode sync is disabled, skipping.")

        self.__saveLastActivities()
        logger.info("[Sync] Finished synchronization with Trakt.tv")

    def __canSkipSync(self):
        """Check if sync can be skipped because nothing changed on either side."""
        if getSettingAsBool("kodi_library_dirty"):
            logger.debug("[Sync] Kodi library is dirty, cannot skip sync.")
            return False

        try:
            activities = self.traktapi.getLastActivities()
        except Exception as ex:
            logger.debug("[Sync] Failed to fetch last_activities: %s" % ex)
            return False

        if not activities or "all" not in activities:
            logger.debug("[Sync] Invalid last_activities response, cannot skip sync.")
            return False

        cached = getSetting("last_activities_all")
        current = activities["all"]

        if not cached:
            logger.debug("[Sync] No cached last_activities, running full sync.")
            return False

        if current == cached:
            logger.debug("[Sync] last_activities unchanged (%s), skipping sync." % current)
            return True

        logger.debug("[Sync] last_activities changed (cached=%s, current=%s)." % (cached, current))
        return False

    def __saveLastActivities(self):
        """Cache post-sync timestamps and clear the dirty flag."""
        try:
            activities = self.traktapi.getLastActivities()
        except Exception as ex:
            logger.debug("[Sync] Failed to fetch last_activities for caching: %s" % ex)
            return

        if activities and "all" in activities:
            setSetting("last_activities_all", activities["all"])
            logger.debug("[Sync] Cached last_activities: %s" % activities["all"])

        setSetting("kodi_library_dirty", "false")

    def IsCanceled(self):
        if self.show_progress and not self.run_silent and self.progress.iscanceled():
            logger.debug("Sync was canceled by user.")
            return True
        else:
            return False

    def UpdateProgress(self, *args, **kwargs):
        if self.show_progress and not self.run_silent:

            line1 = ""
            line2 = ""
            line3 = ""

            if 'line1' in kwargs:
                line1 = kwargs["line1"]

            if 'line2' in kwargs:
                line2 = kwargs["line2"]

            if 'line3' in kwargs:
                line3 = kwargs["line3"]

            percent = args[0]
            message = f'{line1}\n{line2}\n{line3}'
            self.progress.update(percent, message)
