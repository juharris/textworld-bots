import glob
import logging
import os
import random

import cherrypy
import textworld
from expiringdict import ExpiringDict


"""
Start:
BOT_LOG_LEVEL=DEBUG python3 bot.py

Query: 
curl localhost:5050/process  -H 'Content-Type: application/json' --data '{"user":1, "command":"go south"}'
"""


class Game(object):
    def __init__(self, path):
        self._env = textworld.start(path)
        self._game_state = self._env.reset()

    def _clean_output(self, output):
        # TODO
        return output

    def get_feedback(self):
        return self._game_state.feedback

    def process(self, command: str):
        if command.lower() in ("reset", "restart"):
            self._game_state = self._env.reset()
            return self._game_state.feedback
        if command.lower() in ("score",):
            return f"Your score is {self._game_state.score}"
        self._game_state, reward, done = self._env.step(command)
        return self._game_state.feedback


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
            # Pick random game.
            while True:
                path = random.choice(glob.glob('all_games/train/*.ulx'))
                self._logger.info("Will try to start game at \"%s\".", path)
                try:
                    game = Game(path)
                    break
                except:
                    self._logger.exception("Error using game at \"%s\".\nWill try with another game.", path)
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
