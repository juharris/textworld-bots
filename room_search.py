import random

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
        self.optimal_path = None
        self._backtrack_stack = []
        self.visited = {self.current_room.name}

    def get_next_direction(self):
        # TODO Keep track if all rooms have been explored so that we can know if the target is on the map.
        if self.target_name in self._rooms:
            self.optimal_path = self.get_path_to(self.target_name)
        if self.optimal_path is not None and len(self.optimal_path) > 0:
            result = self.optimal_path[0]
            self.prev_direction_traveled = result
            return result
        result = None
        direction_options = []
        for direction, room in self.current_room.directions.items():
            if room is not None and room.name == self.target_name:
                result = direction
                break
            elif room is None or room.name not in self.visited:
                # Don't know what that room is OR haven't visited that room.
                direction_options.append(direction)
        if result is None:
            # Nowhere specific to go.
            if len(direction_options) == 0:
                # Nowhere to go. Need to backtrack.
                if len(self._backtrack_stack) == 0:
                    # No path exists.
                    return None
                else:
                    backtrack_target = self._backtrack_stack.pop()
                    self.optimal_path = self.get_path_to(backtrack_target)
                    result = self.optimal_path.pop()
                    self.prev_direction_traveled = result
                    return result
            result = random.choice(direction_options)
            # If we reach a dead-end then we should come back to here.
            self._backtrack_stack.append(self.current_room.name)
        self.prev_direction_traveled = result
        return result

    def get_path_to(self, target_room_name: str):
        queue = [self.current_room]
        paths = {self.current_room.name: []}
        found = False
        while not found and len(queue) > 0:
            current_room = queue.pop(0)
            path_so_far = paths[current_room.name]
            for direction, room in current_room.directions.items():
                if room is not None:
                    if room.name not in paths:
                        paths[room.name] = path_so_far + [direction]
                        queue.append(room)
                    if room.name == target_room_name:
                        found = True
                        break
        return paths[target_room_name]
