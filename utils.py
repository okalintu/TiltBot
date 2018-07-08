import json
import logging

def pretty_print(item) -> None:
    print(json.dumps(item, indent=4))

def map_key(container : dict, target_key: str, func) -> None:

    for key in container:
        if key == target_key:
            container[key] = func(container[key])
        elif isinstance(container[key], dict):
            map_key(container[key], key, func)
        elif isinstance(container[key], list):
            for item in container[key]:
                map_key(item, target_key, func)


class LogMixin:
    @property
    def logger(self) -> logging.Logger:
       return self.getLogger()

    @staticmethod
    def getLogger() -> logging.Logger:
        return logging.getLogger('TiltBot')
