import unittest
from typing import List

from room import Room
from room_search import opposite_dir, RoomSearch


def complete_map(rooms: List[Room]):
    for room in rooms:
        for direction, to_room in room.directions.items():
            to_room.directions[opposite_dir(direction)] = room


class TestRoomSearch(unittest.TestCase):
    def test_search_one_way(self):
        current_room = Room("Kitchen", ['west'])
        target = "Supermarket"
        rooms = dict(Kitchen=current_room)
        s = RoomSearch(rooms, current_room, target)
        self.assertEqual('west', s.get_next_direction())

    def test_search_discover_along_the_way(self):
        # Kitchen -> Living Room -> Driveway -> Street -> Supermarket
        #    v            v
        #  Pantry     Corridor

        sup = Room("Supermarket", {})
        street = Room("Street", {'east': sup})
        driveway = Room("Driveway", {'east': street})
        corridor = Room("Corridor", {})
        living_room = Room("Living Room", {'east': driveway, 'south': corridor})
        pantry = Room("Pantry", {})
        kitchen = Room("Kitchen", {'east': living_room, 'south': pantry})
        all_rooms = [
            kitchen, living_room, driveway, street, sup,
            pantry, corridor,
        ]
        complete_map(all_rooms)
        all_rooms = {room.name: room for room in all_rooms}

        current_room = Room("Kitchen", ['east', 'south'])
        target = "Supermarket"
        rooms = dict(Kitchen=current_room)
        s = RoomSearch(rooms, current_room, target)
        for _ in range(8):
            s.visited.add(current_room.name)
            s.current_room = current_room
            direction = s.get_next_direction()
            prev_room = current_room
            # Update map.
            complete_current_room = all_rooms[prev_room.name].directions[direction]
            current_room = rooms.get(complete_current_room.name)
            if current_room is None:
                directions = dict.fromkeys(complete_current_room.directions.keys())
                current_room = Room(complete_current_room.name, directions)
                directions = current_room.directions
                rooms[current_room.name] = current_room
            else:
                directions = current_room.directions

            directions[opposite_dir(direction)] = prev_room
            prev_room.directions[direction] = current_room

            if current_room.name == target:
                break
        self.assertEqual(target, current_room.name)

    def test_search_discover_along_the_way_does_not_exist(self):
        # Kitchen -> Living Room -> Driveway -> Street -> Supermarket
        #    v            v
        #  Pantry     Corridor

        sup = Room("Supermarket", {})
        street = Room("Street", {'east': sup})
        driveway = Room("Driveway", {'east': street})
        corridor = Room("Corridor", {})
        living_room = Room("Living Room", {'east': driveway, 'south': corridor})
        pantry = Room("Pantry", {})
        kitchen = Room("Kitchen", {'east': living_room, 'south': pantry})
        all_rooms = [
            kitchen, living_room, driveway, street, sup,
            pantry, corridor,
        ]
        complete_map(all_rooms)
        all_rooms = {room.name: room for room in all_rooms}

        current_room = Room("Kitchen", ['east', 'south'])
        target = "Shed"
        rooms = dict(Kitchen=current_room)
        s = RoomSearch(rooms, current_room, target)
        direction = 'not none'
        for _ in range(20):
            s.visited.add(current_room.name)
            s.current_room = current_room
            direction = s.get_next_direction()
            if direction is None:
                break
            prev_room = current_room
            # Update map.
            complete_current_room = all_rooms[prev_room.name].directions[direction]
            current_room = rooms.get(complete_current_room.name)
            if current_room is None:
                directions = dict.fromkeys(complete_current_room.directions.keys())
                current_room = Room(complete_current_room.name, directions)
                directions = current_room.directions
                rooms[current_room.name] = current_room
            else:
                directions = current_room.directions

            directions[opposite_dir(direction)] = prev_room
            prev_room.directions[direction] = current_room

            if current_room.name == target:
                break
        self.assertIsNone(direction)

    def test_search_known_path(self):
        # Kitchen -> Living Room -> Driveway -> Street -> Supermarket
        #    v            v
        #  Pantry     Corridor

        sup = Room("Supermarket", {})
        street = Room("Street", {'east': sup})
        driveway = Room("Driveway", {'east': street})
        corridor = Room("Corridor", {})
        living_room = Room("Living Room", {'east': driveway, 'south': corridor})
        pantry = Room("Pantry", {})
        kitchen = Room("Kitchen", {'east': living_room, 'south': pantry})
        rooms = [
            kitchen, living_room, driveway, street, sup,
            pantry, corridor,
        ]
        complete_map(rooms)
        rooms = {room.name: room for room in rooms}

        current_room = kitchen
        target = "Supermarket"
        s = RoomSearch(rooms, current_room, target)
        for _ in range(4):
            s.visited.add(current_room.name)
            s.current_room = current_room
            direction = s.get_next_direction()
            prev_room = current_room
            # Update map.
            complete_current_room = rooms[prev_room.name].directions[direction]
            current_room = rooms.get(complete_current_room.name)
            if current_room is None:
                directions = dict.fromkeys(complete_current_room.directions.keys())
                current_room = Room(complete_current_room.name, directions)
                directions = current_room.directions
                rooms[current_room.name] = current_room
            else:
                directions = current_room.directions

            directions[opposite_dir(direction)] = prev_room
            prev_room.directions[direction] = current_room

            if current_room.name == target:
                break
        self.assertEqual(target, current_room.name)

    def test_search_known_path2(self):
        # Kitchen -> Living Room -> Driveway -> Street
        #    v            v                       v
        #  Pantry     Corridor                Supermarket

        sup = Room("Supermarket", {})
        street = Room("Street", {'south': sup})
        driveway = Room("Driveway", {'east': street})
        corridor = Room("Corridor", {})
        living_room = Room("Living Room", {'east': driveway, 'south': corridor})
        pantry = Room("Pantry", {})
        kitchen = Room("Kitchen", {'east': living_room, 'south': pantry})
        rooms = [
            kitchen, living_room, driveway, street, sup,
            pantry, corridor,
        ]
        complete_map(rooms)
        rooms = {room.name: room for room in rooms}

        current_room = kitchen
        target = "Supermarket"
        s = RoomSearch(rooms, current_room, target)
        for _ in range(4):
            s.visited.add(current_room.name)
            s.current_room = current_room
            direction = s.get_next_direction()
            prev_room = current_room
            # Update map.
            complete_current_room = rooms[prev_room.name].directions[direction]
            current_room = rooms.get(complete_current_room.name)
            if current_room is None:
                directions = dict.fromkeys(complete_current_room.directions.keys())
                current_room = Room(complete_current_room.name, directions)
                directions = current_room.directions
                rooms[current_room.name] = current_room
            else:
                directions = current_room.directions

            directions[opposite_dir(direction)] = prev_room
            prev_room.directions[direction] = current_room

            if current_room.name == target:
                break
        self.assertEqual(target, current_room.name)

    def test_search_known_path_does_not_exist(self):
        # Kitchen -> Living Room -> Driveway -> Street -> Supermarket
        #    v            v
        #  Pantry     Corridor

        sup = Room("Supermarket", {})
        street = Room("Street", {'east': sup})
        driveway = Room("Driveway", {'east': street})
        corridor = Room("Corridor", {})
        living_room = Room("Living Room", {'east': driveway, 'south': corridor})
        pantry = Room("Pantry", {})
        kitchen = Room("Kitchen", {'east': living_room, 'south': pantry})
        rooms = [
            kitchen, living_room, driveway, street, sup,
            pantry, corridor,
        ]
        complete_map(rooms)
        rooms = {room.name: room for room in rooms}

        current_room = kitchen
        target = "Shed"
        s = RoomSearch(rooms, current_room, target)
        direction = 'not none'
        for _ in range(20):
            s.visited.add(current_room.name)
            s.current_room = current_room
            direction = s.get_next_direction()
            if direction is None:
                break
            prev_room = current_room
            # Update map.
            complete_current_room = rooms[prev_room.name].directions[direction]
            current_room = rooms.get(complete_current_room.name)
            if current_room is None:
                directions = dict.fromkeys(complete_current_room.directions.keys())
                current_room = Room(complete_current_room.name, directions)
                directions = current_room.directions
                rooms[current_room.name] = current_room
            else:
                directions = current_room.directions

            directions[opposite_dir(direction)] = prev_room
            prev_room.directions[direction] = current_room

            if current_room.name == target:
                break

        self.assertIsNone(direction)
