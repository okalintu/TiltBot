import json

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