import random
import re
from collections import defaultdict
from enum import Enum
from operator import itemgetter
from typing import Any, Dict, List, Optional, Union

from textworld import EnvInfos

from room import Room
from room_search import opposite_dir, RoomSearch

_directions = ["north", "east", "south", "west"]

_all_ingredients = """
black pepper
bell pepper
egg
lettuce
salt
sugar
pepper
potato
red hot pepper
""".split('\n')
_all_ingredients = list(filter(None, map(str.strip, _all_ingredients)))

_max_capacity = 3
"""
The maximum number of objects that can be held.
"""

_rooms_with_ingredients = [
    "Backyard",
    "Garden",
    "Kitchen",
    "Pantry",
    "Supermarket",
]
_ingredient_to_rooms = defaultdict(lambda: _rooms_with_ingredients, {
    "egg": ["Kitchen", "Supermarket"],
})
"""
The rooms that each ingredient can be found in.
"""


class Feature(Enum):
    OBSERVING_KITCHEN = 0
    COOKBOOK_PRESENT = 1
    SEEN_COOKBOOK = 2
    COOKBOOK_SHOWING = 3

    CURRENT_ROOM = 4
    """
    String for current room name.
    """

    DONE_INIT_INVENTORY_CHECK = 5
    INVENTORY_SHOWING = 6

    NUM_ITEMS_HELD = 7
    HOLDING_KNIFE = 8

    FOUND_ALL_INGREDIENTS = 9

    OPENED_FRIDGE = 10

    CURRENT_RECIPE_STEP = 11

    def __repr__(self):
        return self.name


#######################################
# Functions For Features
#######################################
def _feat(qualifier, term):
    return (qualifier, term)


def _carrying_feat(item):
    return _feat('carrying', item)


def _direction_feat(direction):
    return _feat('available', direction)


def _ingredient_feat(ingredient):
    return _feat('ingredient', ingredient)


def _ingredient_present_feat(ingredient):
    return _feat('present', ingredient)


def _recipe_step_feat(recipe_step_index, recipe_step):
    return ('recipe_step', recipe_step_index, recipe_step)


def _get_feats_with_qualifier(feats: Dict, qualifier: Union[str, tuple]):
    result = []
    if not isinstance(qualifier, tuple):
        qualifier = (qualifier,)
    for feat, val in feats.items():
        if val != False and isinstance(feat, tuple) and feat[:len(qualifier)] == qualifier:
            if len(feat) == len(qualifier) + 1:
                result.append(feat[len(qualifier)])
            else:
                result.append(feat[len(qualifier):])
    return result


def _get_all_present_ingredients(feats: Dict) -> List[str]:
    return _get_feats_with_qualifier(feats, 'present')


def _get_all_required_ingredients(feats: Dict) -> List[str]:
    return _get_feats_with_qualifier(feats, 'ingredient')


def _get_carrying(feats: Dict):
    return _get_feats_with_qualifier(feats, 'carrying')


def _get_recipe_steps(feats: Dict):
    """
    :param feats: The features.
    :return: The recipe steps in order.
    """
    recipe_feats = _get_feats_with_qualifier(feats, 'recipe_step')
    recipe_feats.sort(key=itemgetter(0))
    return [step[1] for step in recipe_feats]


#######################################
# END Functions For Features
#######################################
_roast_pattern = re.compile('roast (?P<ingredient>.*)')
_fry_pattern = re.compile('fry (?P<ingredient>.*)')


def _commandify_recipe_step(recipe_step):
    result = recipe_step
    m = _roast_pattern.match(recipe_step)
    if m:
        result = f"cook {m['ingredient']} with oven"
    elif _fry_pattern.match(recipe_step):
        m = _fry_pattern.match(recipe_step)
        result = f"cook {m['ingredient']} with stove"

    return result


def _get_ingredients_present(observation, ingredient_candidates):
    result = []
    covered = set()
    for ingredient in sorted(ingredient_candidates, key=len, reverse=True):
        m = re.search(r'\b{}\b'.format(ingredient), observation, re.IGNORECASE)
        if m and m.start() not in covered:
            covered.update(range(m.start(), m.end()))
            result.append(ingredient)
    return result


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
        self._game_features: List[Dict] = [defaultdict(lambda: False) for _ in obs]
        self._rooms: List[Dict] = [dict() for _ in obs]
        self._searches: List[Optional[RoomSearch]] = [None for _ in obs]

    def _add_features(self, obs: List[str], infos: Dict[str, List[Any]]) -> None:
        """
        Add features for each game.

        Arguments:
            obs: Initial feedback for each game.
            infos: Additional information for each game.
        """
        for ob, feats in zip(obs, self._game_features):
            # Defaults
            if feats[Feature.NUM_ITEMS_HELD] == False:
                feats[Feature.NUM_ITEMS_HELD] = 0

            if feats[Feature.CURRENT_RECIPE_STEP] == False:
                feats[Feature.CURRENT_RECIPE_STEP] = 0

            feats[Feature.CURRENT_ROOM] = self._get_room_name(ob) or feats[Feature.CURRENT_ROOM]

            feats[Feature.INVENTORY_SHOWING] = ob.startswith("You are carrying:")

            feats[Feature.OBSERVING_KITCHEN] = "-= Kitchen =-" in ob
            feats[Feature.COOKBOOK_PRESENT] = feats[Feature.OBSERVING_KITCHEN] and " cookbook" in ob
            feats[Feature.COOKBOOK_SHOWING] = "\nIngredients:\n" in ob and "\nDirections:\n" in ob
            if feats[Feature.COOKBOOK_SHOWING] and not feats[Feature.SEEN_COOKBOOK]:
                feats[Feature.SEEN_COOKBOOK] = True
                ingredients, recipe_steps = self._gather_recipe(ob)
                for ingredient in ingredients:
                    feats[_ingredient_feat(ingredient)] = True
                for recipe_step_index, recipe_step in enumerate(recipe_steps):
                    feats[_recipe_step_feat(recipe_step_index, recipe_step)] = True

            ingredients_needed = tuple(
                set(_get_all_required_ingredients(feats)) - set(_get_all_present_ingredients(feats)))
            if len(ingredients_needed) == 0:
                feats[Feature.FOUND_ALL_INGREDIENTS] = True

            if feats[Feature.INVENTORY_SHOWING]:
                items = self._gather_inventory(ob)
                feats[Feature.NUM_ITEMS_HELD] = len(items)
                for item in items:
                    feats[_carrying_feat(item)] = True
            elif not feats[Feature.COOKBOOK_SHOWING]:
                ingredients_present = _get_ingredients_present(ob, ingredients_needed)
                for ingredient in ingredients_present:
                    feats[_ingredient_present_feat(ingredient)] = True

            for direction in _directions:
                present = re.search(r'\b{}\b'.format(direction), ob, re.IGNORECASE) is not None
                feats[_direction_feat(direction)] = present

    def _gather_inventory(self, ob):
        lines = ob.split('\n')
        result = list(filter(None, map(str.strip, lines[1:])))
        return result

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
            for direction in _directions:
                if self._game_features[game_index][_direction_feat(direction)]:
                    directions.append(direction)
            room = Room(current_room_name, directions)
            rooms[current_room_name] = room
        if self._searches[game_index] is not None and prev_room is not None:
            prev_dir = self._searches[game_index].prev_direction_traveled
            rooms[prev_room.name].directions[prev_dir] = room
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

            current_room_name: str = feats[Feature.CURRENT_ROOM]
            rooms = self._rooms[game_index]

            if self._searches[game_index] is not None:
                self._searches[game_index].visited.add(current_room_name)
                prev_room: Room = self._searches[game_index].current_room
            else:
                prev_room = None
            self._update_map(game_index,
                             prev_room, current_room_name, ob)
            current_room = rooms[current_room_name]

            if not feats[Feature.DONE_INIT_INVENTORY_CHECK]:
                result.append("inventory")
                feats[Feature.DONE_INIT_INVENTORY_CHECK] = True
                continue

            if self._searches[game_index] is not None:
                # There is a search in progress.
                self._searches[game_index].current_room = current_room
                if self._searches[game_index].target_name == current_room_name:
                    # Found target, stop the search.
                    self._searches[game_index] = None
                else:
                    # Keep searching.
                    direction = self._searches[game_index].get_next_direction()
                    if direction is not None:
                        result.append(direction)
                        continue
                    else:
                        # No path exists.
                        # TODO Need to backtrack to whatever we were doing before.
                        self._searches[game_index] = None

            if not feats[Feature.SEEN_COOKBOOK] and feats[Feature.COOKBOOK_PRESENT]:
                result.append("look cookbook")
                continue

            if not feats[Feature.SEEN_COOKBOOK]:
                # Find the Kitchen.
                self._searches[game_index] = RoomSearch(rooms, current_room, "Kitchen")
                result.append(self._searches[game_index].get_next_direction())
                continue

            if current_room_name == "Kitchen" \
                    and not feats[Feature.FOUND_ALL_INGREDIENTS] \
                    and not feats[Feature.OPENED_FRIDGE]:
                feats[Feature.OPENED_FRIDGE] = True
                result.append("open fridge")
                continue

            # Check if current room has the ingredient.
            if not feats[Feature.FOUND_ALL_INGREDIENTS]:
                if current_room_name == "Kitchen" and feats[Feature.NUM_ITEMS_HELD] < _max_capacity:
                    # Go find ingredients.
                    # TODO Keep track of the target room and ingredient.
                    ingredients_needed = tuple(
                        set(_get_all_required_ingredients(feats)) - set(_get_all_present_ingredients(feats)))
                    assert len(ingredients_needed) > 0
                    direction = None
                    while direction is None:
                        ingredient = random.choice(ingredients_needed)
                        room_options = _ingredient_to_rooms[ingredient]
                        for target_room_name in random.sample(room_options, len(room_options)):
                            self._searches[game_index] = RoomSearch(rooms, current_room, target_room_name)
                            direction = self._searches[game_index].get_next_direction()
                            if direction is not None:
                                break
                            else:
                                # No path exists.
                                self._searches[game_index] = None

                    # Found a direction to go.
                    result.append(direction)
                    continue

                elif current_room_name != "Kitchen" and feats[Feature.NUM_ITEMS_HELD] < _max_capacity:
                    take_item = False
                    for ingredient in set(_get_all_required_ingredients(feats)) & set(
                            _get_all_present_ingredients(feats)):
                        # Pick up the ingredient so that we can bring it to the Kitchen.
                        result.append("take {}".format(ingredient))
                        feats[_carrying_feat(ingredient)] = True
                        feats[Feature.NUM_ITEMS_HELD] += 1
                        take_item = True
                        break
                    if take_item:
                        continue
                    else:
                        # TODO Optimization: Keep track of the target room and ingredient.
                        pass

            if not feats[Feature.FOUND_ALL_INGREDIENTS] and feats[Feature.NUM_ITEMS_HELD] == _max_capacity:
                if current_room_name != "Kitchen":
                    # Bring items to Kitchen.
                    self._searches[game_index] = RoomSearch(rooms, current_room, "Kitchen")
                    result.append(self._searches[game_index].get_next_direction())
                    continue
                elif feats[Feature.CURRENT_RECIPE_STEP] == 0:
                    # In Kitchen.
                    # Not started cooking.
                    item = random.choice(_get_carrying(feats))
                    result.append("drop {}".format(item))
                    feats[_carrying_feat(item)] = False
                    feats[Feature.NUM_ITEMS_HELD] -= 1
                    continue

            # TODO Check if knife is needed.
            # TODO Drop prepared item if needed.

            # Go through recipe steps.
            recipe_steps = _get_recipe_steps(feats)
            if feats[Feature.CURRENT_RECIPE_STEP] == len(recipe_steps):
                # Done
                result.append("eat meal")
                continue
            else:
                next_recipe_step = recipe_steps[feats[Feature.CURRENT_RECIPE_STEP]]
                result.append(_commandify_recipe_step(next_recipe_step))
                feats[Feature.CURRENT_RECIPE_STEP] += 1
                # TODO Maybe remove from required ingredients (remove ingredient feature).
                continue


            result.append("")
        return result
