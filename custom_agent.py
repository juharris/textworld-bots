import logging
import random
import re
import sys
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
carrot
cilantro
egg
lettuce
salt
sliced carrot
sugar
pepper
potato
red hot pepper
red onion
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

    CARRYING_TOO_MUCH = 11

    CANT_SEE_SUCH_THING = 12

    STARTED_COOKING = 13

    YOU_TAKE = 14

    BBQ_PRESENT = 15

    NEED_TO_OPEN_FIRST = 16
    YOU_OPENED_DOOR = 17

    def __repr__(self):
        return self.name


#######################################
# Functions For Features
#######################################
_closed_door_pattern = re.compile(r'\bclosed (?P<item>[^\s]+ door) leading (?P<direction>[^\s.,!?]+)\b', re.IGNORECASE)
_need_to_open_door_pattern = re.compile(r'You have to (?P<task>open .* door) first.')
_you_open_door_pattern = re.compile(r'You open (.* door).')


def _feat(qualifier, term):
    return (qualifier, term)


def _carrying_feat(item):
    return _feat('carrying', item)


def _direction_closed_feat(direction):
    return _feat('closed', direction)


def _direction_feat(direction):
    return _feat('available', direction)


def _ingredient_feat(ingredient):
    return _feat('ingredient', ingredient)


def _ingredient_present_feat(ingredient):
    return _feat('present', ingredient)


def _recipe_step_feat(recipe_step_index, recipe_step):
    return ('recipe_step', recipe_step_index, recipe_step)


def _get_feats_with_qualifier(feats: Dict, qualifier: Union[str, tuple]) -> List:
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


def _remove_recipe_step(feats: Dict, recipe_step: str):
    recipe_feats = _get_feats_with_qualifier(feats, 'recipe_step')
    for recipe_feat in recipe_feats:
        if recipe_feat[1] == recipe_step:
            feats[_recipe_step_feat(recipe_feat[0], recipe_step)] = False


#######################################
# END Functions For Features
#######################################

def _gather_inventory(ob):
    result = []
    for line in ob.split('\n'):
        line = line.strip()
        if line.startswith("You are carrying:") or line.startswith("You are carrying nothing."):
            continue
        if line:
            prefixes = ("a ", "an ", "some ", "raw ")
            modified = True
            while modified:
                modified = False
                for prefix in prefixes:
                    if line.startswith(prefix):
                        modified = True
                        line = line[len(prefix):]
            result.append(line)

    return result


# Cooking Patterns
_fry_pattern = re.compile('^fry the (?P<ingredient>.*)', re.IGNORECASE)
_grill_pattern = re.compile('^grill the (?P<ingredient>.*)', re.IGNORECASE)
_roast_pattern = re.compile('^roast the (?P<ingredient>.*)', re.IGNORECASE)

_fried_pattern = re.compile('^fried (?P<ingredient>.*)', re.IGNORECASE)
_grilled_pattern = re.compile('^grilled (?P<ingredient>.*)', re.IGNORECASE)
_roasted_pattern = re.compile('^roasted (?P<ingredient>.*)', re.IGNORECASE)

# Cutting Patterns
_chop_pattern = re.compile('^chop the (?P<ingredient>.*)', re.IGNORECASE)
_dice_pattern = re.compile('^dice the (?P<ingredient>.*)', re.IGNORECASE)
_slice_pattern = re.compile('^slice the (?P<ingredient>.*)', re.IGNORECASE)

_chopped_pattern = re.compile('^chopped (?P<ingredient>.*)', re.IGNORECASE)
_diced_pattern = re.compile('^diced (?P<ingredient>.*)', re.IGNORECASE)
_sliced_pattern = re.compile('^sliced (?P<ingredient>.*)', re.IGNORECASE)

_require_knife_pattern = re.compile('^(chop|dice|slice) ', re.IGNORECASE)


def _commandify_recipe_step(recipe_step):
    result = recipe_step
    m = _fry_pattern.match(recipe_step)
    if m:
        result = f"cook {m['ingredient']} with stove"
    elif _grill_pattern.match(recipe_step):
        m = _grill_pattern.match(recipe_step)
        result = f"cook {m['ingredient']} with BBQ"
    elif _roast_pattern.match(recipe_step):
        m = _roast_pattern.match(recipe_step)
        result = f"cook {m['ingredient']} with oven"

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


def _get_recipe_steps_to_make(ingredient) -> set:
    result = set()
    if _fried_pattern.match(ingredient):
        m = _fried_pattern.match(ingredient)
        result.add(f"fry the {_base_ingredient(m['ingredient'])}")
        result.update(_get_recipe_steps_to_make(m['ingredient']))
    if _grilled_pattern.match(ingredient):
        m = _grilled_pattern.match(ingredient)
        result.add(f"grill the {_base_ingredient(m['ingredient'])}")
        result.update(_get_recipe_steps_to_make(m['ingredient']))
    if _roasted_pattern.match(ingredient):
        m = _roasted_pattern.match(ingredient)
        result.add(f"roast the {_base_ingredient(m['ingredient'])}")
        result.update(_get_recipe_steps_to_make(m['ingredient']))
    if _chopped_pattern.match(ingredient):
        m = _chopped_pattern.match(ingredient)
        result.add(f"chop the {_base_ingredient(m['ingredient'])}")
        result.update(_get_recipe_steps_to_make(m['ingredient']))
    if _diced_pattern.match(ingredient):
        m = _diced_pattern.match(ingredient)
        result.add(f"dice the {_base_ingredient(m['ingredient'])}")
        result.update(_get_recipe_steps_to_make(m['ingredient']))
    if _sliced_pattern.match(ingredient):
        m = _sliced_pattern.match(ingredient)
        result.add(f"slice the {_base_ingredient(m['ingredient'])}")
        result.update(_get_recipe_steps_to_make(m['ingredient']))
    return result


def _recipe_step_to_ingredient(recipe_step):
    result = None
    if _chop_pattern.match(recipe_step):
        m = _chop_pattern.match(recipe_step)
        result = f"chopped {m['ingredient']}"
    elif _dice_pattern.match(recipe_step):
        m = _dice_pattern.match(recipe_step)
        result = f"diced {m['ingredient']}"
    elif _slice_pattern.match(recipe_step):
        m = _slice_pattern.match(recipe_step)
        result = f"sliced {m['ingredient']}"
    elif _fry_pattern.match(recipe_step):
        m = _fry_pattern.match(recipe_step)
        result = f"fried {m['ingredient']}"
    elif _grill_pattern.match(recipe_step):
        m = _grill_pattern.match(recipe_step)
        result = f"grilled {m['ingredient']}"
    elif _roast_pattern.match(recipe_step):
        m = _roast_pattern.match(recipe_step)
        result = f"roasted {m['ingredient']}"
    return result


def _requires_knife(recipe_step):
    return _require_knife_pattern.match(recipe_step) is not None


def _base_ingredient(ingredient: str) -> str:
    result = ingredient
    prefixes = ("chopped ", "diced ", "sliced ",
                "fried ", "grilled ", "roasted ")
    updated = True
    while updated:
        updated = False
        for prefix in prefixes:
            if result.startswith(prefix):
                result = result[len(prefix):]
                updated = True

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
        # Get all admissible commands so that this bot has a handicap on the scoreboard.
        # Even though we don't use the commands, we do use prior knowledge so in effect we should have a handicap.
        # return EnvInfos()
        return EnvInfos(admissible_commands=True)

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

            # TODO Optimization: Check if fridge is already open in more ways.
            if "The fridge is empty" in ob:
                feats[Feature.OPENED_FRIDGE] = True

            new_room = self._get_room_name(ob)
            changed_room = new_room is not None and new_room != feats[Feature.CURRENT_ROOM]
            feats[Feature.CURRENT_ROOM] = new_room or feats[Feature.CURRENT_ROOM]

            feats[Feature.INVENTORY_SHOWING] = ob.startswith("You are carrying:") \
                                               or ob.startswith("You are carrying nothing.")

            feats[Feature.CARRYING_TOO_MUCH] = ob.startswith("You're carrying too many things already.")

            feats[Feature.CANT_SEE_SUCH_THING] = ob.startswith("You can't see any such thing.")

            feats[Feature.YOU_TAKE] = ob.startswith("You take ")

            feats[Feature.NEED_TO_OPEN_FIRST] = _need_to_open_door_pattern.search(ob) is not None

            feats[Feature.YOU_OPENED_DOOR] = _you_open_door_pattern.search(ob) is not None

            if feats[Feature.CARRYING_TOO_MUCH] or feats[Feature.CANT_SEE_SUCH_THING]:
                # Pick up failed.
                feats[Feature.NUM_ITEMS_HELD] -= 1

            if ob.startswith("You take the knife "):
                feats[Feature.HOLDING_KNIFE] = True
            elif ob.startswith("You drop the knife "):
                feats[Feature.HOLDING_KNIFE] = False

            feats[Feature.BBQ_PRESENT] = "BBQ" in ob

            feats[Feature.OBSERVING_KITCHEN] = "-= Kitchen =-" in ob
            feats[Feature.COOKBOOK_PRESENT] = feats[Feature.OBSERVING_KITCHEN] and " cookbook" in ob
            feats[Feature.COOKBOOK_SHOWING] = "\nIngredients:\n" in ob and "\nDirections:\n" in ob
            if feats[Feature.COOKBOOK_SHOWING] and not feats[Feature.SEEN_COOKBOOK]:
                feats[Feature.SEEN_COOKBOOK] = True
                ingredients, recipe_steps = self._gather_recipe(ob)
                carrying = set(_get_carrying(feats))
                for ingredient in ingredients:
                    if ingredient not in carrying:
                        feats[_ingredient_feat(ingredient)] = True
                    else:
                        feats[_ingredient_feat(ingredient)] = False

                # Remove recipe steps for what we're carrying.
                done_recipe_steps = set()
                for item in carrying:
                    done_recipe_steps.update(_get_recipe_steps_to_make(item))

                for recipe_step_index, recipe_step in enumerate(recipe_steps):
                    if recipe_step not in done_recipe_steps:
                        feats[_recipe_step_feat(recipe_step_index, recipe_step)] = True

            if feats[Feature.INVENTORY_SHOWING]:
                items = _gather_inventory(ob)
                feats[Feature.NUM_ITEMS_HELD] = len(items)
                for item in items:
                    feats[_carrying_feat(item)] = True
                    feats[_ingredient_feat(item)] = False
                    base_ingredient = _base_ingredient(item)
                    if base_ingredient != item:
                        feats[_ingredient_feat(base_ingredient)] = False
                        for step in _get_recipe_steps_to_make(item):
                            _remove_recipe_step(feats, step)
            elif not feats[Feature.COOKBOOK_SHOWING] \
                    and feats[Feature.SEEN_COOKBOOK] \
                    and not feats[Feature.YOU_TAKE]:
                ingredients_needed = _get_all_required_ingredients(feats)
                ingredients_present = _get_ingredients_present(ob, ingredients_needed)
                for ingredient in ingredients_present:
                    feats[_ingredient_present_feat(ingredient)] = True

            if feats[Feature.SEEN_COOKBOOK]:
                # Had before:
                # and not feats[Feature.COOKBOOK_SHOWING] \
                # and not feats[Feature.INVENTORY_SHOWING]\

                # Discount ingredients we have that can be satisfied by later recipe steps.
                # E.g. "fried carrot" when we have a "carrot" and need to fry later.
                ingredients_to_make = tuple(map(_recipe_step_to_ingredient, _get_recipe_steps(feats)))
                ingredients_to_make = set(filter(None, ingredients_to_make))
                ingredients_needed = tuple(
                    set(_get_all_required_ingredients(feats))
                    # Had before: - set(_get_all_present_ingredients(feats))
                    - ingredients_to_make)
                if len(ingredients_needed) == 0:
                    feats[Feature.FOUND_ALL_INGREDIENTS] = True

            if changed_room:
                # Check directions you can go.
                for direction in _directions:
                    present = re.search(r'\b{}\b'.format(direction), ob, re.IGNORECASE) is not None
                    feats[_direction_feat(direction)] = present

            # Check closed directions.
            # Clear closed feats.
            for direction in _directions:
                if feats[_direction_closed_feat(direction)]:
                    del feats[_direction_closed_feat(direction)]
            m = _closed_door_pattern.search(ob)
            while m:
                item = m.group('item')
                direction = m.group('direction')
                feats[_direction_closed_feat(direction)] = item
                m = _closed_door_pattern.search(ob, pos=m.endpos)

    def _gather_recipe(self, ob):
        ingredients = []
        recipe_steps = []
        in_ingredients = False
        in_recipe_steps = False
        for line in ob.split('\n'):
            if len(line.strip()) == 0:
                in_ingredients = False
                in_recipe_steps = False
                continue
            if line == "Ingredients:":
                in_ingredients = True
                continue
            elif line == "Directions:":
                in_recipe_steps = True
                continue

            if in_ingredients:
                ingredients.append(line.strip())
            elif in_recipe_steps:
                recipe_steps.append(line.strip())

        # Extend.
        for recipe_step in recipe_steps:
            modified_ingredient = _recipe_step_to_ingredient(recipe_step)
            if modified_ingredient is not None:
                ingredients.append(modified_ingredient)

        return ingredients, recipe_steps

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
            assert prev_room.name != room.name, f"{prev_room.name}--{prev_dir}-->{room.name}"
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
        debug = '--debug' in sys.argv

        if all(dones):
            self._end_episode(obs, scores, infos)
            return  # Nothing to return.

        if not self._epsiode_has_started:
            self._start_episode(obs, infos)

        self._add_features(obs, infos)

        result = []
        for game_index, ob, done, feats in zip(range(len(obs)), obs, dones, self._game_features):
            if debug:
                print(ob)
            if done:
                result.append("wait")
                continue

            try:
                current_room_name: str = feats[Feature.CURRENT_ROOM]
                rooms = self._rooms[game_index]

                if self._searches[game_index] is not None:
                    self._searches[game_index].visited.add(current_room_name)
                    prev_room: Room = self._searches[game_index].current_room
                else:
                    prev_room = None
                if not feats[Feature.NEED_TO_OPEN_FIRST] and not feats[Feature.YOU_OPENED_DOOR]:
                    self._update_map(game_index,
                                     prev_room, current_room_name, ob)
                current_room: Room = rooms[current_room_name]

                if feats[Feature.NEED_TO_OPEN_FIRST]:
                    m = _need_to_open_door_pattern.search(ob)
                    assert m
                    result.append(m.group('task'))
                    continue

                if self._searches[game_index] is not None:
                    if feats[Feature.YOU_OPENED_DOOR]:
                        # Optimization: Open the door before getting the error.
                        direction = self._searches[game_index].prev_direction_traveled
                        result.append(direction)
                        continue
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

                if feats[Feature.CARRYING_TOO_MUCH]:
                    # Need to drop something.
                    candidates = tuple(set(_get_carrying(feats)) - set(_get_all_required_ingredients(feats)))
                    assert len(candidates) > 0
                    recipe_steps = _get_recipe_steps(feats)
                    assert len(recipe_steps) > 0
                    next_recipe_step = recipe_steps[0]
                    item = random.choice(candidates)
                    while item in next_recipe_step:
                        item = random.choice(candidates)
                    result.append("drop {}".format(item))
                    feats[_carrying_feat(item)] = False
                    # TODO Note that we might need this later.
                    # if feats.get(_ingredient_feat(item)) == False:
                    #     feats[_ingredient_feat(item)] = True
                    #     feats[Feature.FOUND_ALL_INGREDIENTS] = False
                    feats[Feature.NUM_ITEMS_HELD] -= 1
                    continue

                if not feats[Feature.SEEN_COOKBOOK] and feats[Feature.COOKBOOK_PRESENT]:
                    result.append("look cookbook")
                    continue

                if not feats[Feature.DONE_INIT_INVENTORY_CHECK]:
                    result.append("inventory")
                    feats[Feature.DONE_INIT_INVENTORY_CHECK] = True
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
                    if feats[Feature.NUM_ITEMS_HELD] < _max_capacity:
                        # See if ingredient is here.
                        ingredients_here = tuple(
                            set(_get_all_required_ingredients(feats)) & set(_get_all_present_ingredients(feats)))
                        if len(ingredients_here) > 0:
                            ingredient = random.choice(ingredients_here)
                            result.append("take {}".format(ingredient))
                            feats[_ingredient_present_feat(ingredient)] = False
                            feats[_carrying_feat(ingredient)] = True
                            feats[Feature.NUM_ITEMS_HELD] += 1

                            # Remove required ingredients.
                            feats[_ingredient_feat(ingredient)] = False
                            base_ingredient = _base_ingredient(ingredient)
                            if base_ingredient != ingredient:
                                feats[_ingredient_feat(base_ingredient)] = False
                                for step in _get_recipe_steps_to_make(ingredient):
                                    _remove_recipe_step(feats, step)

                            continue

                    if current_room_name == "Kitchen":
                        # Go find ingredients.
                        ingredients_needed = tuple(
                            set(_get_all_required_ingredients(feats)) - set(_get_all_present_ingredients(feats)))
                        assert len(ingredients_needed) > 0
                        direction = None
                        while len(current_room.directions) > 0 and direction is None:
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

                        if direction is not None:
                            # Found a direction to go.
                            result.append(direction)
                            continue

                if not feats[Feature.FOUND_ALL_INGREDIENTS] and feats[Feature.NUM_ITEMS_HELD] >= _max_capacity:
                    if current_room_name != "Kitchen":
                        # Bring items to Kitchen.
                        self._searches[game_index] = RoomSearch(rooms, current_room, "Kitchen")
                        direction = self._searches[game_index].get_next_direction()
                        result.append(direction)
                        continue
                    elif not feats[Feature.STARTED_COOKING]:
                        # In Kitchen.
                        # Not started cooking.
                        item = random.choice(_get_carrying(feats))
                        result.append("drop {}".format(item))
                        feats[_carrying_feat(item)] = False
                        # TODO Note that we might need this later.
                        # if feats.get(_ingredient_feat(item)) == False:
                        #     feats[_ingredient_feat(item)] = True
                        #     feats[Feature.FOUND_ALL_INGREDIENTS] = False

                        feats[Feature.NUM_ITEMS_HELD] -= 1
                        continue

                # Go through recipe steps.
                recipe_steps = _get_recipe_steps(feats)
                if len(recipe_steps) > 0:
                    next_recipe_step = recipe_steps[0]
                    if _requires_knife(next_recipe_step) and not feats[Feature.HOLDING_KNIFE]:
                        if feats[Feature.NUM_ITEMS_HELD] < _max_capacity:
                            result.append("take knife")
                            feats[Feature.NUM_ITEMS_HELD] += 1
                            continue
                        else:
                            # Need to drop something.
                            candidates = tuple(set(_get_carrying(feats)) - set(_get_all_required_ingredients(feats)))
                            assert len(candidates) > 0
                            item = random.choice(candidates)
                            while item in next_recipe_step:
                                item = random.choice(candidates)
                            result.append("drop {}".format(item))
                            feats[_carrying_feat(item)] = False
                            # TODO Note that we might need this later.
                            # if feats.get(_ingredient_feat(item)) == False:
                            #     feats[_ingredient_feat(item)] = True
                            #     feats[Feature.FOUND_ALL_INGREDIENTS] = False
                            feats[Feature.NUM_ITEMS_HELD] -= 1
                            continue

                    if _grill_pattern.match(next_recipe_step) and not feats[Feature.BBQ_PRESENT]:
                        # Go to the BBQ in the Backyard.
                        self._searches[game_index] = RoomSearch(rooms, current_room, "Backyard")
                        direction = self._searches[game_index].get_next_direction()
                        result.append(direction)
                        continue
                    elif (_fry_pattern.match(next_recipe_step)
                          or _roast_pattern.match(next_recipe_step)
                          or next_recipe_step == "prepare meal") \
                            and current_room_name != "Kitchen":
                        self._searches[game_index] = RoomSearch(rooms, current_room, "Kitchen")
                        direction = self._searches[game_index].get_next_direction()
                        result.append(direction)
                        continue

                    # TODO Maybe check if the ingredient is already modified.
                    result.append(_commandify_recipe_step(next_recipe_step))
                    _remove_recipe_step(feats, next_recipe_step)
                    feats[Feature.STARTED_COOKING] = True
                    # TODO Maybe remove from required ingredients (remove ingredient feature).
                    continue
                else:
                    # Done
                    result.append("eat meal")
                    continue
            except:
                if debug:
                    logging.exception("Will wait.")
            result.append(None)

        result = ["wait" if r is None else r for r in result]
        if debug:
            print(f"ACT: \"{result[-1]}\"")

        return result
