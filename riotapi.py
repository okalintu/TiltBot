import json
import logging
import time
import requests
from rediscache import RedisCache
from riotdata import ChampionData
from utils import map_key, pretty_print, LogMixin


class RitoPlsError(RuntimeError):
    pass

class RiotApi(LogMixin):
    api_url = None

    def __init__(self):
        self.api_token = self._load_api_key()
        self.backoff = 1
        self.max_backoff = 60
        self.max_rate_limit_retries = 10


    @staticmethod
    def _decode_response(resp : bytes) -> dict:
        return json.loads(resp.decode('utf8'))
    
    def get(self, main_param : str, attempt=0) -> dict:
        self.logger.debug('Requesting %s from %s', main_param, self.api_url)
        resp = requests.get(
            f'{self.api_url}{main_param}',
            self.get_query_params(),
            headers={'X-Riot-Token': self.api_token})

        # ratelimit hit try again after some time!
        if resp.status_code == 429: 
            self.logger.warning('Rate limit hit with %s!', self.__class__)
            for head, val in resp.headers.items():
                if 'Rate' in head:
                    self.logger.debug('Header %s: %s', head, val)
            backoff_time = self._get_backoff_time(resp)
            self.logger.warning('Sleeping for %s seconds', backoff_time)
            time.sleep(backoff_time)
            if attempt + 1 < self.max_rate_limit_retries: 
                return self.get(main_param, attempt + 1)
            raise RitoPlsError('Max ratelimit retries exeeded')

        # we got some error. lets quit

        if resp.status_code not in range(200, 300):
            self.logger.error("error with request code %s: %s", resp.status_code, resp.content)
            raise RitoPlsError(f'Getting data with {self.__class__} failed with status code {resp.status_code}')
        # all ok. proceed to decode response
        return self._decode_response(resp.content)

    def _load_api_key(self):
        with open('/keys/ritoapi.key') as f:
            return f.read().strip()
    
    def _get_backoff_time(self, resp) -> int:
        try:
            return int(resp.headers['Retry-After'])
        except (KeyError, ValueError):
            self.logger.info('Could not get backoff time from headers. using exponential')
            backoff = self.backoff
            self.backoff = min(self.max_backoff, self.backoff*2)
            return backoff
    
    def get_query_params(self):
        return {}

class SummonerApi(RiotApi):
    api_url = 'https://euw1.api.riotgames.com/lol/summoner/v3/summoners/by-name/'

class MatchListApi(RiotApi):
    api_url = 'https://euw1.api.riotgames.com/lol/match/v3/matchlists/by-account/'

    def get_query_params(self):
        return [('queue', 400), ('queue', 420), ('queue', 440)]

class MatchApi(RiotApi):
    api_url = 'https://euw1.api.riotgames.com/lol/match/v3/matches/'

class ChampionApi(RiotApi):
    api_url = 'https://euw1.api.riotgames.com/lol/static-data/v3/champions/'