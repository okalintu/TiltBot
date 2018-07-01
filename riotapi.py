import json
import logging
import requests
from rediscache import RedisCache
from riotdata import ChampionData
import time

# hoba summoner id: 21768137
# hoba account id: 25407967

class RitoPlsError(RuntimeError):
    pass

class RiotApi:
    api_url = None

    def __init__(self):
        self.logger = logging.getLogger('TiltBot')
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
            headers={'X-Riot-Token': self.api_token})

        # ratelimit hit try again after some time!
        if resp.status_code == 429: 
            self.logger.warning('Rate limit hit with %s!', self.__class__)
            for head, val in resp.headers.items():
                if 'Rate' in head:
                    logger.debug('Header %s: %s', head, val)
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
        with open('ritoapi.key') as f:
            return f.read().strip()
    
    def _get_backoff_time(self, resp) -> int:
        try:
            return int(resp.headers['Retry-After'])
        except (KeyError, ValueError):
            self.logger.info('Could not get backoff time from headers. using exponential')
            backoff = self.backoff
            self.backoff = min(self.max_backoff, self.backoff*2)
            return backoff


class MatchListApi(RiotApi):
    api_url = 'https://euw1.api.riotgames.com/lol/match/v3/matchlists/by-account/'

class MatchApi(RiotApi):
    api_url = 'https://euw1.api.riotgames.com/lol/match/v3/matches/'

class ChampionApi(RiotApi):
    api_url = 'https://euw1.api.riotgames.com/lol/static-data/v3/champions/'

def pretty_print(item) -> None:
    print(json.dumps(item, indent=4))

def map_key(container : dict, target_key: str, func) -> None:

    print(type(container), container)
    for key in container:
        if key == target_key:
            container[key] = func(container[key])
        elif isinstance(container[key], dict):
            map_key(container[key], key, func)
        elif isinstance(container[key], list):
            for item in container[key]:
                map_key(item, target_key, func)

def champ_mapper(i):
    try:
        return champions[i]
    except ValueError:
        return i

if __name__ == '__main__':

    # configure logger
    logger = logging.getLogger('TiltBot')
    logger.setLevel(logging.DEBUG)
    sh = logging.StreamHandler()
    sh.setFormatter(logging.Formatter('[%(asctime)s][%(name)s - %(levelname)-8s] %(message)s'))
    logger.addHandler(sh)
    
    # Initialize apis

    champions = ChampionData()

    match_api = MatchApi()
    matches = RedisCache('matches_', match_api.get)

    # get last games 
    match_list = MatchListApi().get(25407967)['matches'][:3]
    game_ids = [match['gameId'] for match in match_list][:3]

    for game_id in game_ids:
        try:
            match = matches[game_id]
            map_key(match, 'championId', champ_mapper)
            pretty_print(match)
        except RitoPlsError:
            logger.warning('Advertized game %s could not be fetched', game_id)