import re
from collections import defaultdict
from enum import Enum
from typing import List, Dict, Any, Optional

from textworld import EnvInfos


class Feature(Enum):
    IN_KITCHEN = 0
    COOKBOOK_PRESENT = 1
    SEEN_COOKBOOK = 2
    COOKBOOK_SHOWING = 3

    CURRENT_ROOM = 4
    """
    String for current room name.
    """


class Room(object):
    def __init__(self, name: str, directions: list):
        self.name = name
        self.directions = dict.fromkeys(directions)


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
            # TODO Try to find a path to the room.
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
        if result is None:
            # Nowhere to go.
            # TODO Set self._backtrack_target.
            self._backtrack_target = 'TODO'
        self.prev_direction_traveled = result
        return result


def opposite_dir(direction):
    if direction == "east":
        return "west"
    elif direction == "west":
        return "east"
    elif direction == "north":
        return "south"
    else:
        return "north"


class CustomAgent:
    """ Template agent for the TextWorld competition. """

    def __init__(self) -> None:
        self._initialized = False
        self._epsiode_has_started = False

    def train(self) -> None:
        """ Tell the agent it is in training mode. """
        pass  # [You can insert code here.]

    def eval(self) -> None:
        """ Tell the agent it is in evaluation mode. """
        pass  # [You can insert code here.]

    def select_additional_infos(self) -> EnvInfos:
        """
        Returns what additional information should be made available at each game step.

        Requested information will be included within the `infos` dictionary
        passed to `CustomAgent.act()`. To request specific information, create a
        :py:class:`textworld.EnvInfos <textworld.envs.wrappers.filter.EnvInfos>`
        and set the appropriate attributes to `True`. The possible choices are:

        * `description`: text description of the current room, i.e. output of the `look` command;
        * `inventory`: text listing of the player's inventory, i.e. output of the `inventory` command;
        * `max_score`: maximum reachable score of the game;
        * `objective`: objective of the game described in text;
        * `entities`: names of all entities in the game;
        * `verbs`: verbs understood by the the game;
        * `command_templates`: templates for commands understood by the the game;
        * `admissible_commands`: all commands relevant to the current state;

        In addition to the standard information, game specific information
        can be requested by appending corresponding strings to the `extras`
        attribute. For this competition, the possible extras are:

        * `'recipe'`: description of the cookbook;
        * `'walkthrough'`: one possible solution to the game (not guaranteed to be optimal);

        Example:
            Here is an example of how to request information and retrieve it.

            >>> from textworld import EnvInfos
            >>> request_infos = EnvInfos(description=True, inventory=True, extras=["recipe"])
            ...
            >>> env = gym.make(env_id)
            >>> ob, infos = env.reset()
            >>> print(infos["description"])
            >>> print(infos["inventory"])
            >>> print(infos["extra.recipe"])

        Notes:
            The following information *won't* be available at test time:

            * 'walkthrough'

            Requesting additional infos comes with some penalty (called handicap).
            The exact penalty values will be defined in function of the average
            scores achieved by agents using the same handicap.

            Handicap is defined as follows
                max_score, has_won, has_lost,               # Handicap 0
                description, inventory, verbs, objective,   # Handicap 1
                command_templates,                          # Handicap 2
                entities,                                   # Handicap 3
                extras=["recipe"],                          # Handicap 4
                admissible_commands,                        # Handicap 5
        """
        return EnvInfos()

    def _init(self) -> None:
        """ Initialize the agent. """
        self._initialized = True

        # [You can insert code here.]

    def _start_episode(self, obs: List[str], infos: Dict[str, List[Any]]) -> None:
        """
        Prepare the agent for the upcoming episode.

        Arguments:
            obs: Initial feedback for each game.
            infos: Additional information for each game.
        """
        if not self._initialized:
            self._init()

        self._epsiode_has_started = True
        self._game_features = [defaultdict(lambda: False) for _ in obs]
        self._ingredient_lists = [[] for _ in obs]
        self._direction_lists = [[] for _ in obs]
        self._rooms = [dict() for _ in obs]
        self._searches = [None for _ in obs]

    def _add_features(self, obs: List[str], infos: Dict[str, List[Any]]) -> None:
        """
        Add features for each game.

        Arguments:
            obs: Initial feedback for each game.
            infos: Additional information for each game.
        """
        # TODO
        for ob, feats in zip(obs, self._game_features):
            feats[Feature.IN_KITCHEN] = "-= Kitchen =-" in ob
            feats[Feature.COOKBOOK_PRESENT] = feats[Feature.IN_KITCHEN] and " cookbook" in ob
            feats[Feature.COOKBOOK_SHOWING] = "\nIngredients:\n" in ob and "\nDirections:\n" in ob

            feats[Feature.CURRENT_ROOM] = self._get_room_name(ob) or feats[Feature.CURRENT_ROOM]

    def _gather_recipe(self, ob):
        ingredients = []
        directions = []
        in_ingredients = False
        in_directions = False
        for line in ob.split('\n'):
            if len(line.strip()) == 0:
                in_ingredients = False
                in_directions = False
                continue
            if line == "Ingredients:":
                in_ingredients = True
                continue
            elif line == "Directions:":
                in_directions = True
                continue

            if in_ingredients:
                ingredients.append(line.strip())
            elif in_directions:
                directions.append(line.strip())

        return ingredients, directions

    @staticmethod
    def _get_room_name(ob: str) -> Optional[str]:
        result = None
        m = re.search(r'-=\s*([^=]+) =-', ob)
        if m:
            result = m.group(1)
        return result

    def _update_map(self, game_index,
                    prev_room: Room, current_room_name: str, ob: str):
        rooms = self._rooms[game_index]
        room = rooms.get(current_room_name)
        if room is None:
            directions = []
            for direction in ["north", "east", "south", "west"]:
                if re.search(r'\b{}\b'.format(direction), ob):
                    directions.append(direction)
            room = Room(current_room_name, directions)
            rooms[current_room_name] = room
        if self._searches[game_index] is not None and prev_room is not None:
            prev_dir = self._searches[game_index].prev_direction_traveled
            rooms[prev_room].directions[prev_dir] = room
            room.directions[opposite_dir(prev_dir)] = prev_room

    def _end_episode(self, obs: List[str], scores: List[int], infos: Dict[str, List[Any]]) -> None:
        """
        Tell the agent the episode has terminated.

        Arguments:
            obs: Previous command's feedback for each game.
            score: The score obtained so far for each game.
            infos: Additional information for each game.
        """
        self._epsiode_has_started = False

        # [You can insert code here.]

    def act(self, obs: List[str], scores: List[int], dones: List[bool], infos: Dict[str, List[Any]]) -> Optional[
        List[str]]:
        """
        Acts upon the current list of observations.

        One text command must be returned for each observation.

        Arguments:
            obs: Previous command's feedback for each game.
            scores: The score obtained so far for each game.
            dones: Whether a game is finished.
            infos: Additional information for each game.

        Returns:
            Text commands to be performed (one per observation).
            If episode had ended (e.g. `all(dones)`), the returned
            value is ignored.

        Notes:
            Commands returned for games marked as `done` have no effect.
            The states for finished games are simply copy over until all
            games are done.
        """
        if all(dones):
            self._end_episode(obs, scores, infos)
            return  # Nothing to return.

        if not self._epsiode_has_started:
            self._start_episode(obs, infos)

        self._add_features(obs, infos)

        result = []
        for game_index, ob, done, feats in zip(range(len(obs)), obs, dones, self._game_features):
            if done:
                result.append("wait")
                continue

            current_room_name = feats[Feature.CURRENT_ROOM]
            if self._searches[game_index] is not None:
                self._searches[game_index].visited.add(current_room_name)
                prev_room: Room = self._searches[game_index].current_room
            else:
                prev_room = None
            self._update_map(game_index,
                             prev_room, current_room_name, ob)
            current_room = self._rooms[game_index][current_room_name]
            self._searches[game_index].current_room = current_room

            if feats[Feature.COOKBOOK_SHOWING]:
                feats[Feature.SEEN_COOKBOOK] = True
                self._ingredient_lists[game_index], self._direction_lists[game_index] = self._gather_recipe(ob)

            if self._searches[game_index] is not None:
                # There is a search in progress.
                if self._searches[game_index].target == current_room_name:
                    # Found target, stop the search.
                    self._searches[game_index] = None
                else:
                    # Keep searching.
                    result.append(self._searches[game_index].get_next_direction())
                    continue

            if not feats[Feature.SEEN_COOKBOOK] and feats[Feature.COOKBOOK_PRESENT]:
                result.append("look cookbook")
                continue

            if not Feature.SEEN_COOKBOOK in feats:
                # Find the Kitchen.
                self._searches[game_index] = RoomSearch(self._rooms[game_index], current_room, "Kitchen")
                result.append(self._searches[game_index].get_next_direction())
                continue

            # TODO Find ingredients.

            result.append("")

        return result
