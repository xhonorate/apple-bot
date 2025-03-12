## Apple Bot
This is a bot to beat the fruit box apple game:
https://en.gamesaien.com/game/fruit_box/

PIP install dependancies, then run main.py to start
Will look at screen until it sees a board for the apple game.
Terminal will output a rating of how strong a board it is (more low numbers means a higher score is possible)
If the board looks good, press enter to start the bot, or reset the game until you find a better board.

Bot works by first matching adjacent pairs of apples as quickly as possible, then begins to analyze all matches on board to find the option that will best improve board state.

Todo:
- Increase searching speed with better algorithms
- Enqueue moves rather than only seaching after previous move has completed
- Improve move selection logic
