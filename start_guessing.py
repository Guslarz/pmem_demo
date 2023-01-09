#!/usr/bin/env python3

import os
import sys
from nvm.pmemobj import create
from guess_lib import Guesser, pool_fn

name = input("Hello, what is your name?  ")
if os.path.isfile(pool_fn):
    print("There is already a game file.  Use the guess_status command"
          " to see details of the current game.")
    sys.exit(1)
try:
    pool = create(pool_fn)
except OSError as err:
    print(err)
    sys.exit(err.errno)

with pool:
    pool.root = game = pool.new(Guesser, name)
    print(game.message('START'))
    print("Type 'guess' followed by your guess at the prompt.")