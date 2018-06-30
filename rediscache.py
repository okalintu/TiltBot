import json
import redis
import logging
import base64

class RedisCache:
    def __init__(self, prefix, get_value, expire_time=None, host='127.0.0.1', port=6379, db=0):
        self.logger = logging.getLogger('TiltBot')
        self.redis = redis.Redis(host=host, port=port, db=db)
        self.prefix = prefix
        self.get_value = get_value
        self.expire_time = expire_time

    def __getitem__(self, key):
        str_key = str(key)
        value = self.redis.get(self.prefix + str_key)
        # Fetch value if it does not exist
        if value is None:
            self.logger.info('key "%s" not in cache. fetching..', key)
            value = self.get_value(key)
            self._set_key(str_key, value)
            return value
        
        self.logger.debug('Using cached value for key "%s%s"', self.prefix, key)
        value = self._deserialize(value)
        return value

    def _set_key(self, key, value):
        redis_key = self.prefix + key
        if self.expire_time is not None:
            return self.redis.setex(redis_key, self._serialize(value), self.expire_time)
        return self.redis.set(redis_key, self._serialize(value))
        
    @staticmethod
    def _serialize(item):
        return base64.b64encode(json.dumps(item).encode('utf-8'))
    @staticmethod
    def _deserialize(item):
        return json.loads(base64.b64decode(item).decode('utf-8'))