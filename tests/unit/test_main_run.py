import unittest

from unittest.mock import patch

import main


class TestMainRun(unittest.TestCase):
    @patch('main.web')
    @patch('trader.stocks.get_data')
    @patch('trader.stocks.init')
    def test_main_calls_run(self, mock_init, mock_get, mock_web):
        # patch web.app.run so it doesn't block
        mock_web.app.run = lambda *a, **k: None
        mock_get.return_value = None
        # call main.main should invoke web.app.run without exceptions
        main.main()
        mock_init.assert_called_once()


if __name__ == '__main__':
    unittest.main()
