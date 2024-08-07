"""Updater module"""
from typing import Dict

from program.media.item import MediaItem
from program.updaters.local import LocalUpdater
from program.updaters.plex import PlexUpdater
from utils.logger import logger


class Updater:
    def __init__(self):
        self.key = "updater"
        self.services = {
            PlexUpdater: PlexUpdater(),
            LocalUpdater: LocalUpdater(),
        }
        self.initialized = self.validate()

    def validate(self) -> bool:
        """Validate that at least one updater service is initialized."""
        initialized_services = [service for service in self.services.values() if service.initialized]

        if self.services[LocalUpdater].initialized and len(initialized_services) > 1:
            logger.error("Local updater can not be used together with other updaters.")
            return False

        return len(initialized_services) > 0

    def run(self, item: MediaItem):
        if not self.initialized:
            logger.error("Updater is not initialized properly.")
            return

        for service_cls, service in self.services.items():
            if service.initialized:
                try:
                    item = next(service.run(item))
                except StopIteration:
                    logger.debug(f"{service_cls.__name__} finished updating {item.log_string}")
                except Exception as e:
                    logger.error(f"{service_cls.__name__} failed to update {item.log_string}: {e}")
        yield item