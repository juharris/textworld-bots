from room import Room


def opposite_dir(direction):
    if direction == "east":
        return "west"
    elif direction == "west":
        return "east"
    elif direction == "north":
        return "south"
    else:
        return "north"


class RoomSearch(object):
    """
    Currently a depth first search
    but it should be made smarter to know things like the Kitchen is near the Living Room.
    """

    def __init__(self, rooms: dict, current_room: Room, target_name: str):
        self._rooms = rooms
        self.current_room = current_room
        self.target_name = target_name
        self._backtrack_target = None
        self._search_stack = []
        self.visited = {self.current_room.name}

    def get_next_direction(self):
        if self.target_name in self._rooms:
            pass
            # TODO Find a path to the room.
        result = None
        for direction, room in self.current_room.directions.items():
            if room is not None and room.name == self.target_name:
                result = direction
                break
            elif room is not None and room.name == self._backtrack_target:
                self._backtrack_target = None
                result = direction
                break
            elif room is not None and room.name not in self.visited:
                result = direction
            elif room is None:
                result = direction
        if result is None:
            # Nowhere to go.
            # TODO Set self._backtrack_target.
            self._backtrack_target = 'TODO'
        self.prev_direction_traveled = result
        return result
