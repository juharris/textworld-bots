import glob
import logging
import os
import random
import re

import cherrypy
import textworld
from expiringdict import ExpiringDict

"""
Start:
BOT_LOG_LEVEL=DEBUG python3 bot.py
or:
docker run --rm -it --detach -p 5050:5050 -v ${PWD}:/root/workspace/textworld-bots --name tw tw bash -c 'BOT_LOG_LEVEL=DEBUG cd /root/workspace/textworld-bots && python3 bot.py' 

Query: 
curl localhost:5050/process  -H 'Content-Type: application/json' --data '{"user": 1, "command": "go south"}'
"""

TEXTWORLD_HEADER = "\n\n\n                    ________  ________  __    __  ________        \n                   |        \\|        \\|  \\  |  \\|        \\       \n                    \\$$$$$$$$| $$$$$$$$| $$  | $$ \\$$$$$$$$       \n                      | $$   | $$__     \\$$\\/  $$   | $$          \n                      | $$   | $$  \\     >$$  $$    | $$          \n                      | $$   | $$$$$    /  $$$$\\    | $$          \n                      | $$   | $$_____ |  $$ \\$$\\   | $$          \n                      | $$   | $$     \\| $$  | $$   | $$          \n                       \\$$    \\$$$$$$$$ \\$$   \\$$    \\$$          \n              __       __   ______   _______   __        _______  \n             |  \\  _  |  \\ /      \\ |       \\ |  \\      |       \\ \n             | $$ / \\ | $$|  $$$$$$\\| $$$$$$$\\| $$      | $$$$$$$\\\n             | $$/  $\\| $$| $$  | $$| $$__| $$| $$      | $$  | $$\n             | $$  $$$\\ $$| $$  | $$| $$    $$| $$      | $$  | $$\n             | $$ $$\\$$\\$$| $$  | $$| $$$$$$$\\| $$      | $$  | $$\n             | $$$$  \\$$$$| $$__/ $$| $$  | $$| $$_____ | $$__/ $$\n             | $$$    \\$$$ \\$$    $$| $$  | $$| $$     \\| $$    $$\n              \\$$      \\$$  \\$$$$$$  \\$$   \\$$ \\$$$$$$$$ \\$$$$$$$ \n\n"


class Game(object):
    def __init__(self, logger: logging.Logger):
        self._logger = logger
        self._start_new_game()

    def _clean_output(self, output):
        result = re.sub(r'-=\s*([^=]+) =-\n', "\n# \\1\n", output)
        if result.startswith(TEXTWORLD_HEADER):
            result = result[len(TEXTWORLD_HEADER):]
        return result

    def _normalize_command(self, command):
        result = command.lower()
        return result

    def _start_new_game(self):
        # Pick random game.
        while True:
            path = random.choice(glob.glob('all_games/train/*.ulx'))
            self._logger.info("Will try to start game at \"%s\".", path)
            try:
                self._env = textworld.start(path)
                self._game_state = self._env.reset()
                break
            except:
                self._logger.exception("Error using game at \"%s\".\nWill try with another game.", path)

    def get_feedback(self):
        return self._clean_output(self._game_state.feedback)

    def process(self, command: str):
        normalized_command = self._normalize_command(command)
        if normalized_command in ("new game", "start a new game"):
            self._start_new_game()
        elif normalized_command in ("reset", "restart"):
            self._game_state = self._env.reset()
        elif normalized_command in ("score",):
            return f"Your score is {self._game_state.score}."
        else:
            self._game_state, reward, done = self._env.step(command)
        result = self._game_state.feedback
        return self._clean_output(result)


class BotService(object):
    def __init__(self, logger: logging.Logger):
        self._game_cache = ExpiringDict(max_len=100, max_age_seconds=60 * 60)
        self._logger = logger

    @cherrypy.expose
    @cherrypy.tools.json_in()
    @cherrypy.tools.json_out()
    def process(self):
        data = cherrypy.request.json
        user = data['user']
        command = data['command']

        game = self._game_cache.get(user)
        if game is None:
            game = Game(self._logger)
            self._game_cache[user] = game
            result = game.get_feedback()
        else:
            result = game.process(command)
        return dict(response=result)


def get_logger():
    result = logging.getLogger('bot')
    level = os.environ.get('BOT_LOG_LEVEL', logging.CRITICAL)
    result.setLevel(level)
    ch = logging.StreamHandler()
    ch.setLevel(level)
    formatter = logging.Formatter('[%(levelname)s] %(asctime)s - %(filename)s::%(funcName)s\n%(message)s')
    ch.setFormatter(formatter)
    result.addHandler(ch)
    result.propagate = False
    result.debug("Set up logger.")
    return result


if __name__ == '__main__':
    logger = get_logger()
    service_port = 5050
    if not logger.isEnabledFor(logging.INFO):
        # Disable CherryPy logging.
        cherrypy.log.access_log.setLevel(logging.CRITICAL)
        cherrypy.log.access_log.disabled = True
        cherrypy.log.access_log.propagate = False
        cherrypy.log.error_log.setLevel(logging.CRITICAL)
        cherrypy.log.error_log.disabled = True
        cherrypy.log.error_log.propagate = False

    logger.info("Starting service on port: %s", service_port)
    config = {
        'global': {
            'server.socket_host': '0.0.0.0',
            'server.socket_port': service_port,
        }
    }
    cherrypy.quickstart(BotService(logger), '/', config)
