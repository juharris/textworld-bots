from typing import Union


class Room(object):
    def __init__(self, name: str, directions: Union[dict, list]):
        self.name = name
        if isinstance(directions, (tuple, list)):
            self.directions = dict.fromkeys(directions)
        else:
            self.directions = directions

    def __str__(self):
        directions = {direction: room.name if room is not None else None for (direction, room) in
                      self.directions.items()}
        return f'name={self.name}, directions={directions}'
