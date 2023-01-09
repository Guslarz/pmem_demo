#!/usr/bin/env python3

import sys

from guess_lib import reopen_game, GameError

try:
    pool = reopen_game()
except (OSError, GameError) as err:
    print(err)
    sys.exit(1)

with pool:
    guesser = pool.root
    if not guesser.guesses:
        print("No guesses yet, use 'guess <integer>' to make a guess")
        sys.exit(0)
    print("guesses so far:")
    for guess in guesser.guesses:
        print(f"  {guess}")
    print("my response to your last guess:")
    print(f"  {guesser.message(guesser.current_outcome)}")