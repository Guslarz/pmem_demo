#!/usr/bin/env python3

import os
import sys
from guess_lib import reopen_game, GameError, pool_fn

if len(sys.argv) != 2:
    print("Please specify a single integer as your guess.")
    sys.exit(1)
guess = sys.argv[1]

try:
    pool = reopen_game()
except (OSError, GameError) as err:
    print(err)
    sys.exit(1)

with pool:
    guesser = pool.root
    try:
        disposition = guesser.check_guess(guess)
    except ValueError as err:
        print(err)
        sys.exit(1)
    print(guesser.message(disposition))
    if guesser.lost:
        print(guesser.message('LOST'))
    if guesser.done:
        os.remove(pool_fn)