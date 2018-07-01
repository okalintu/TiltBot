import json
import redis
from rediscache import SerializerMixin

class RiotData(SerializerMixin):

    redis_prefix = 'riot_data'

    def __init__(self, host='127.0.0.1', port=6379, db=0):
        self.redis = redis.Redis(host=host, port=port, db=db)


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
            raise ValueError(f'Key {redis_key} not in redis')
        return self._deserialize(value)

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