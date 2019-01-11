import unittest

from custom_agent import (
    _base_ingredient,
    _get_ingredients_present,
)


class TestCustomAgent(unittest.TestCase):
    def test_base_ingredient(self):
        self.assertEqual("carrot", _base_ingredient("carrot"))
        self.assertEqual("carrot", _base_ingredient("sliced carrot"))
        self.assertEqual("carrot", _base_ingredient("fried sliced carrot"))

    def test_get_ingredients_present(self):
        ob = "There's a banana."
        ingredient_candidates = ["banana", "pear"]
        ingredients_present = _get_ingredients_present(ob, ingredient_candidates)
        self.assertEqual(["banana"], ingredients_present)

        ob = "There's a hot pepper."
        ingredient_candidates = ["hot pepper", "pepper"]
        ingredients_present = _get_ingredients_present(ob, ingredient_candidates)
        self.assertEqual(["hot pepper"], ingredients_present)

        ob = "There's a hot pepper."
        ingredient_candidates = ["pepper", "hot pepper"]
        ingredients_present = _get_ingredients_present(ob, ingredient_candidates)
        self.assertEqual(["hot pepper"], ingredients_present)
