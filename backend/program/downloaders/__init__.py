from .realdebrid import Debrid as RealDebrid
from .torbox import TorBoxDownloader
from program.media.item import MediaItem
from ..cache import HashCache

class Downloader:
    def __init__(self, hash_cache:HashCache):
        self.key = "downloader"
        self.initialized = False
        services = [
            RealDebrid(hash_cache),
            TorBoxDownloader(hash_cache)
        ]
        self.service = next(service for service in services if service.initialized)
        self.initialized = self.validate()

    def validate(self):
        return self.service is not None

    def run(self, item: MediaItem):
        yield next(self.service.run(item))