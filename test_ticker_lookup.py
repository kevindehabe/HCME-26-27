import unittest
from datetime import datetime
from unittest.mock import patch

import update


TOKEN = "0123456789abcdef0123456789abcdef"


def example_game(game_id="9448651"):
    return {
        "gID": game_id,
        "gDate": "17.10.26",
        "gTime": "20:00",
        "gHomeTeam": "HC Metter-Enz",
        "gGuestTeam": "BBM Bietigheim 4",
        "gToken": "",
    }


class Handball4AllTickerTests(unittest.TestCase):
    def test_nested_views_only_match_exact_game_id(self):
        result = update.ticker_tokens_in_response(
            [{"content": {
                "classes": [{"games": [
                    {"gID": "different", "gToken": TOKEN},
                    {"gID": "9448651", "gToken": TOKEN},
                ]}]
            }}],
            {"9448651"},
        )
        self.assertEqual(result, {"9448651": TOKEN})

    def test_missing_and_invalid_tokens_are_not_used(self):
        self.assertEqual(
            update.ticker_tokens_in_response(
                [{"games": [{"gID": "9448651", "gToken": "short"}]}],
                {"9448651"},
            ),
            {},
        )

    def test_official_secondary_urls(self):
        urls = update.secondary_ticker_urls(
            update.CALENDARS[0]["api"], ["2026-10-17"]
        )
        self.assertEqual(len(urls), 2)
        self.assertIn("cmd=ps", urls[0])
        self.assertIn("ca=1", urls[0])
        self.assertIn("cl=161551", urls[0])
        self.assertIn("cmd=po", urls[1])
        self.assertIn("do=2026-10-17", urls[1])

    @patch("update.fetch_json")
    def test_can_recover_token_from_other_official_schedule(self, fetch):
        fetch.side_effect = [
            [{"content": {"actualGames": {"games": [
                {"gID": "other-match", "gToken": TOKEN}
            ]}}}],
            [{"content": {"classes": [{"games": [
                {"gID": "9448651", "gToken": TOKEN}
            ]}]}}],
        ]
        game = example_game()
        result = update.recover_ticker_tokens(
            update.CALENDARS[0]["api"],
            [game],
            {},
            datetime(2026, 10, 17, 20, 20, tzinfo=update.TZ),
        )
        self.assertEqual(result[0]["gToken"], TOKEN)
        self.assertEqual(fetch.call_count, 2)

    @patch("update.fetch_json")
    def test_only_searches_near_match_time(self, fetch):
        game = example_game()
        update.recover_ticker_tokens(
            update.CALENDARS[0]["api"],
            [game],
            {},
            datetime(2026, 10, 18, 5, 0, tzinfo=update.TZ),
        )
        fetch.assert_not_called()

    @patch("update.fetch_json")
    def test_retains_token_once_already_saved(self, fetch):
        game = example_game()
        update.recover_ticker_tokens(
            update.CALENDARS[0]["api"],
            [game],
            {"9448651": TOKEN},
            datetime(2026, 10, 17, 20, 20, tzinfo=update.TZ),
        )
        fetch.assert_not_called()


if __name__ == "__main__":
    unittest.main()
