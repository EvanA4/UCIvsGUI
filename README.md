# UCIvsGUI
Play against any UCI chess engine with a PyGame application!

## How does it work?

This GUI uses the Python library PyGame to allow the user to play against a UCI engine. By keeping track of the mouse inputs and using the Python [chess library](https://python-chess.readthedocs.io/en/latest/), the GUI determines what squares the user is clicking on and performs and chess calculations necessary through the chess library. The chess library has a convenient module to communicate with a UCI chess engine through code. Although the visuals and controls may be superficial, this repository allows for chess developers to quickly test out their chess engines. This GUI also uses asyncio to run the chess engine on the side for a smoother chess experience.

## Setup

I recommend using Anaconda or venv to create a Python environment. You will need to install `chess`, `cairosvg`, and `pygame` through pip.

To actually run the application copy your engine exectutable's directory and run `python3 play.py -e [dir]`, where the last argument is your pasted directory.

> [!WARNING]
> You *must* use the engine directory argument to run this program. Otherwise, the GUI will not know what engine to communicate with!

## Fancier Usages

There are multiple arguments aside from the engine directory that can be used when calling `play.py`. The order does not matter:
1. `-b` will start the player off on the black team.
2. `-d [name]` will set the name of the application (instead of "UCIvsGUI")
3. `-fs` sets the display to fullscreen, although there are performance issues here.
4. `-inc [inc]` sets the clock increment variable (in seconds). When a bot or player finishes their turn, their clock increases by this amount.
5. `-time [time]` sets the time for both players (in minutes).

Finally, you can change the starting position like I did for the reference images below. To do this, go to the top of the `play.py` file and manually set an initial board.

## Some references

![normal reference](references/normal.png)

![winning reference](references/win.png)

![pawn promotion reference](references/promoW.png)

![pawn promotion reference 2](references/promoB.png)
