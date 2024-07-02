import contextlib
import time
from datetime import datetime
from typing import Generator

from ..cache import HashCache
from program.media.item import MediaItem, Movie
from program.settings.manager import settings_manager
from RTN import parse
from RTN.exceptions import GarbageTorrent
from utils.logger import logger
from utils.request import get, post


class TorBoxDownloader:
    """TorBox Downloader"""

    def __init__(self, hash_cache: HashCache):
        self.key = "torbox_downloader"
        self.settings = settings_manager.settings.downloaders.torbox
        self.api_key = self.settings.api_key
        self.base_url = "https://api.torbox.app/v1/api"
        self.headers = {"Authorization": f"Bearer {self.api_key}"}
        self.initialized = self.validate()
        if not self.initialized:
            return
        self.hash_cache = hash_cache
        logger.success("TorBox Downloader initialized!")

    def validate(self) -> bool:
        """Validate the TorBox Downloader as a service"""
        if not self.settings.enabled:
            logger.warning("Torbox downloader is set to disabled.")
            return False
        if not self.settings.api_key:
            logger.error("Torbox API key is not set")
        try:
            return self.get_expiry_date() > datetime.now()
        except:
            return False

    def run(self, item: MediaItem) -> Generator[MediaItem, None, None]:
        """Download media item from TorBox"""   
        logger.info(f"Downloading {item.log_string} from TorBox")
        if self.settings.usenet_enabled:
            # Usenet is fast so ignore caching?
            if self.download_via_usenet(item=item):
                yield item
            else:
                logger.info(f"Failed to download {item.log_string} from TorBox via Usenet")

        if self.is_cached(item):
            self.download(item)
        yield item


    def is_cached(self, item: MediaItem):
        streams = [hash for hash in item.streams]
        #usenet_data = self.get_usenet_download_cached(streams)
        #for hash in usenet_data:
        #    item.active_stream=usenet_data[hash]
        #    return True
        torrent_data = self.get_web_download_cached(streams)
        for hash in torrent_data:
            item.active_stream=torrent_data[hash]
            return True

    def download_via_usenet(self, item: MediaItem):
        nzb_file_url = self.hash_cache.get_nzb_file_url(infohash=item.active_stream["hash"])
        if not nzb_file_url:
            return False
        
        exists = False
        usenet_list = self.get_usenet_list()
        for data in usenet_list:
            if item.active_stream["hash"] == data["hash"]:
                    id = data["id"]
                    exists = True
                    break
        if not exists:
            id = self.create_usenet_download(nzb_link=nzb_file_url)
        for data in usenet_list:
            if data["id"] == id:
                with contextlib.suppress(GarbageTorrent, TypeError):
                    for file in data["files"]:
                        if file["size"] > 10000:
                            parsed_file = parse(file["short_name"])
                            if parsed_file.type == "movie":
                                item.set("folder", ".")
                                item.set("alternative_folder", ".")
                                item.set("file", file["short_name"])
                                return True
            

    def download(self, item: MediaItem):
        if item.type == "movie":
            exists = False
            torrent_list = self.get_torrent_list()
            for torrent in torrent_list:
                if item.active_stream["hash"] == torrent["hash"]:
                    id = torrent["id"]
                    exists = True
                    break
            if not exists:
                id = self.create_torrent(item.active_stream["hash"])
            for torrent in torrent_list:
                if torrent["id"] == id:
                    with contextlib.suppress(GarbageTorrent, TypeError):
                        for file in torrent["files"]:
                            if file["size"] > 10000:
                                parsed_file = parse(file["short_name"])
                                if parsed_file.type == "movie":
                                    item.set("folder", ".")
                                    item.set("alternative_folder", ".")
                                    item.set("file", file["short_name"])
                                    return True

    def get_expiry_date(self):
        expiry = datetime.fromisoformat(self.get_user_data().premium_expires_at)
        expiry = expiry.replace(tzinfo=None)
        return expiry

    def get_web_download_cached(self, hash_list):
        hash_string = ",".join(hash_list)
        response = get(f"{self.base_url}/webdl/checkcached?hash={hash_string}", additional_headers=self.headers, response_type=dict)
        return response.data["data"]
    
    def get_usenet_download_cached(self, hash_list):
        hash_string = ",".join(hash_list)
        response = get(f"{self.base_url}/usenet/checkcached?hash={hash_string}", additional_headers=self.headers, response_type=dict)
        return response.data["data"]

    def get_user_data(self):
        response = get(f"{self.base_url}/user/me", additional_headers=self.headers, retry_if_failed=False)
        return response.data.data

    def create_torrent(self, hash) -> int:
        magnet_url = f"magnet:?xt=urn:btih:{hash}&dn=&tr="
        response = post(f"{self.base_url}/torrents/createtorrent", data={"magnet": magnet_url}, additional_headers=self.headers)
        return response.data.data.torrent_id
    
    def create_usenet_download(self, nzb_link) -> int:
        response = post(f"{self.base_url}/torrents/createtorrent", data={"link": nzb_link}, additional_headers=self.headers)
        return response.data.data.usenetdownload_id

    def get_torrent_list(self) -> list:
        response = get(f"{self.base_url}/torrents/mylist", additional_headers=self.headers, response_type=dict)
        return response.data["data"]
    
    def get_usenet_list(self) -> list:
        response = get(f"{self.base_url}/usenet/mylist", additional_headers=self.headers, response_type=dict)
        return response.data["data"]
