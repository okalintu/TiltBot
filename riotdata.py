import json
import redis
from rediscache import SerializerMixin
from utils import LogMixin

class RiotData(LogMixin, SerializerMixin):

    redis_prefix = 'riot_data'

    def __init__(self, db=0):
        self.redis = redis.Redis(unix_socket_path='/tmp/redis.sock', db=db)


    @classmethod
    def from_file(cls, filepath):
        instance = cls()
        with open(filepath) as f:
            data = json.loads(f.read())
        uploadable_data = instance._process_file_data(data)
        instance._upload_data(uploadable_data)
        return instance

    def _process_file_data(self, data):
        return data

    
    def __getitem__(self, key):
        redis_key = self.get_redis_key(key)
        value = self.redis.get(redis_key)
        if value is None:
            errormsg = f'Key {redis_key} not in redis'
            self.logger.debug(errormsg)
            raise KeyError(errormsg)
        return self._deserialize(value)

    def get(self, key, default=None):
        try:
            return self[key]
        except KeyError:
            return default

    def _upload_data(self, data):
        for key, item in data.items():
            redis_key = self.get_redis_key(key)
            self.redis.set(redis_key, self._serialize(item))

    def get_redis_key(self, key):
        return f"{self.redis_prefix}_{key}"

class ChampionData(RiotData):
    redis_prefix = 'league_champs'

    def _process_file_data(self, data):
        champs = {}
        for _, champ_data in data['data'].items():
            champs[champ_data['key']] = {
                'name': champ_data['name'],
                'tags': champ_data['tags'],
            }
        return champs