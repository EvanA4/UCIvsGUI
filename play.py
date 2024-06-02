import os
os.environ['PYGAME_HIDE_SUPPORT_PROMPT'] = "hide"
import pygame
import chess
import chess.engine
import sys
import time
import shutil
import asyncio
from cairosvg import svg2png


class GameBoard:

    def __init__(self, engineDir, defaultFullscreen, startingPlayerTeam, startingTime, incTime, screen):
        self.board = chess.Board() # set to startpos by default
        # self.board.set_fen("r1bqkbnr/p1pp1ppp/1pn5/4p2Q/2B1P3/8/PPPP1PPP/RNB1K1NR w KQkq - 0 4") # test white win
        # self.board.set_fen("rnb1k1nr/pppp1ppp/8/2b1p3/4P2q/PPN5/2PP1PPP/R1BQKBNR b KQkq - 0 4") # test black win
        # self.board.set_fen("rnb2bnr/pp1pkppp/8/8/8/8/5q2/7K b - - 7 25") # test black stalemate
        # self.board.set_fen("rnbqkbnr/pPppppp1/8/8/8/8/1PPPPPpP/RNBQKBNR w KQkq - 0 5") # test pawn promotion
        self.screen = screen
        self.availableMoves = self.board.legal_moves
        self.startingPlayerTeam = startingPlayerTeam
        self.hasWon = -1

        self.botMove = None
        self.engineDir = engineDir

        # self.times = [5, 500] # test time loss
        self.times = [startingTime * 60, startingTime * 60] # [black seconds, white seconds]
        self.incTime = incTime
        self.startTime = time.time()

        self.buttonPos = [] # buttonDrawY, buttonDrawX1, ... buttonDrawX4, buttonSize
        self.promoMoveStr = ""
        self.promoMoveNum = []
        self.handlingPromo = False

        # set dimensions of board
        self.padding = 20
        self.height = 0
        if (defaultFullscreen):
            self.padding = 40
            self.height = 1080 - self.padding * 2
        else:
            self.height = 800 - self.padding * 2
        self.width = self.height

        # remember previous move squares
        self.prevMove = [[], []]
        self.selected = [-1, -1]
        self.shaded = []


    # handles move coming asynchronously from engine
    def handle_bot_move(self):
        self.board.push(self.botMove)
        self.times[self.startingPlayerTeam != "white"] += self.incTime
        moveStr = self.botMove.uci()
        self.prevMove = [[8 - int(moveStr[1]), ord(moveStr[0]) - 97], [8 - int(moveStr[3]), ord(moveStr[2]) - 97]]
        self.draw()

        self.handle_time()
        if (self.hasWon != -1):
            self.handle_end()
            return

        # check for mate
        if (self.board.is_checkmate()):
            self.hasWon = 1
            self.handle_end()
            return

        # check for stalemate
        if (self.board.is_stalemate()):
            self.hasWon = 2
            self.handle_end()


    # generates string for time of "t" seconds
    def time_string(self, seconds):
        if (seconds // 3600 > 0):
            displayMinutes = str(int((seconds % 3600) // 60)).zfill(2)
            displaySeconds = str(f"{seconds % 60 : .1f}"[1:]).zfill(4)
            return f"{int(seconds // 3600)}:{displayMinutes}:{displaySeconds}"
        elif (seconds // 60 > 0):
            displaySeconds = str(f"{seconds % 60 : .1f}"[1:]).zfill(4)
            return f"{int((seconds % 3600) // 60)}:{displaySeconds}"
        else:
            return f"{seconds % 60 :.1f}"

    # updates time for team and starts next timer for other team, checks for out of time, and draws times
    def handle_time(self):
        stopTime = time.time()
        self.times[self.board.turn] -= stopTime - self.startTime

        if (self.times[self.board.turn] < 0):
            self.hasWon = int(self.board.turn != (self.startingPlayerTeam == "white"))
            self.times[self.board.turn] = 0

        # draws times
        timePadding = 40
        pygame.font.init()
        my_font = pygame.font.SysFont('arial', 100)
        bTimeText = my_font.render(self.time_string(self.times[0]), True, (255, 255, 255))
        wTimeText = my_font.render(self.time_string(self.times[1]), True, (255, 255, 255))
        pygame.draw.rect(self.screen, "black", pygame.Rect(self.width + self.padding * 2, 0, self.screen.get_width() - self.width - self.padding * 2, bTimeText.get_height() + timePadding + 2))
        pygame.draw.rect(self.screen, "black", pygame.Rect(self.width + self.padding * 2, self.screen.get_height() - timePadding - wTimeText.get_height(), self.screen.get_width() - self.width - self.padding * 2, timePadding + wTimeText.get_height()))
        self.screen.blit(bTimeText, (self.screen.get_width() - bTimeText.get_width() - timePadding, timePadding))
        self.screen.blit(wTimeText, (self.screen.get_width() - wTimeText.get_width() - timePadding, self.screen.get_height() - wTimeText.get_height() - timePadding))

        if (self.hasWon != -1):
            self.handle_end()

        pygame.display.flip()


    # handle pawn promotion with small gui
    def handle_promotion(self):
        self.handlingPromo = True
        if (self.board.turn):
            team = "white"
            color = "black"
        else:
            team = "black"
            color = (100, 100, 100, 255)

        # if windowed
        if self.padding == 20:
            promoW = 600
            promoH = 300
            drawx = (1536 - promoW) / 2
            drawy = (800 - promoH) / 2
        else:
            promoW = 700
            promoH = 350
            drawx = (1920 - promoW) / 2
            drawy = (1080 - promoH) / 2

        pygame.draw.rect(self.screen, "white", pygame.Rect(drawx - 1, drawy - 1, promoW + 2, promoH + 2))
        pygame.draw.rect(self.screen, (34, 34, 34, 255), pygame.Rect(drawx, drawy, promoW, promoH))

        # draw buttons
        if (len(self.buttonPos) == 0):
            buttonGap = 20
            self.buttonPos = [drawy + (promoH - self.height // 8) // 2 - 5, drawx + (promoW - (buttonGap * 3 + self.width // 2)) // 2 - 5]
            for i in range(3):
                self.buttonPos.append(self.buttonPos[-1] + self.width // 8 + buttonGap)
            self.buttonPos.append(self.width // 8 + 10)

        pygame.draw.rect(self.screen, color, pygame.Rect(self.buttonPos[1], self.buttonPos[0], self.buttonPos[-1], self.buttonPos[-1]))
        image = pygame.image.load(f"./pngs/queen_{team}.png").convert_alpha()
        self.screen.blit(image, (self.buttonPos[1] + 5, self.buttonPos[0] + 5))

        pygame.draw.rect(self.screen, color, pygame.Rect(self.buttonPos[2], self.buttonPos[0], self.buttonPos[-1], self.buttonPos[-1]))
        image = pygame.image.load(f"./pngs/rook_{team}.png").convert_alpha()
        self.screen.blit(image, (self.buttonPos[2] + 5, self.buttonPos[0] + 5))

        pygame.draw.rect(self.screen, color, pygame.Rect(self.buttonPos[3], self.buttonPos[0], self.buttonPos[-1], self.buttonPos[-1]))
        image = pygame.image.load(f"./pngs/bishop_{team}.png").convert_alpha()
        self.screen.blit(image, (self.buttonPos[3] + 5, self.buttonPos[0] + 5))

        pygame.draw.rect(self.screen, color, pygame.Rect(self.buttonPos[4], self.buttonPos[0], self.buttonPos[-1], self.buttonPos[-1]))
        image = pygame.image.load(f"./pngs/knight_{team}.png").convert_alpha()
        self.screen.blit(image, (self.buttonPos[4] + 5, self.buttonPos[0] + 5))

        pygame.display.flip()


    # drawing the result of the game
    def handle_end(self):

        # if windowed
        if self.padding == 20:
            gameOverW = 600
            gameOverH = 300
            drawx = (1536 - gameOverW) / 2
            drawy = (800 - gameOverH) / 2
        else:
            gameOverW = 700
            gameOverH = 350
            drawx = (1920 - gameOverW) / 2
            drawy = (1080 - gameOverH) / 2

        endSets = [
            ["You Lose!", "red", (43, 0, 0, 255)],
            ["You Win!", "green", (0, 43, 0, 255)],
            ["You Tied!", "yellow", (43, 43, 0, 255)]
        ]

        pygame.draw.rect(self.screen, endSets[self.hasWon][1], pygame.Rect(drawx - 1, drawy - 1, gameOverW + 2, gameOverH + 2))
        pygame.draw.rect(self.screen, endSets[self.hasWon][2], pygame.Rect(drawx, drawy, gameOverW, gameOverH))
        pygame.font.init()
        my_font = pygame.font.SysFont('arial', 100)
        text_surface = my_font.render(endSets[self.hasWon][0], True, (255, 255, 255))
        self.screen.blit(text_surface, ((gameOverW - text_surface.get_width()) / 2 + drawx, (gameOverH - text_surface.get_height()) / 2 + drawy))
        pygame.display.flip()


    # a lot of move logic happens here, as this is when moves start/end
    def handle_click(self, x, y):
        # if clicking on promo button
        if (self.handlingPromo):
            charMap = ["q", "r", "b", "n"]
            for i in range(1, 5):
                if (x > self.buttonPos[i] and x < self.buttonPos[i] + self.buttonPos[-1]) and (y > self.buttonPos[0] and y < self.buttonPos[0] + self.buttonPos[-1]):
                    self.board.push_uci(self.promoMoveStr + charMap[i - 1])
                    self.times[self.startingPlayerTeam == "white"] += self.incTime

                    # draw board after move
                    self.prevMove = [self.selected, self.promoMoveNum]
                    self.shaded = []
                    self.selected = [-1, -1]
                    self.availableMoves = self.board.legal_moves
                    self.draw()
                    self.handlingPromo = False

                    # check for mate
                    if (self.board.is_checkmate()):
                        self.hasWon = 1
                        self.handle_end()
                        return

                    # check for stalemate
                    if (self.board.is_stalemate()):
                        self.hasWon = 2
                        self.handle_end()
            return

        # determine the row
        row = -1
        col = -1
        if x >= self.padding and x <= self.padding + self.width:
            col = (x - self.padding) // (self.width // 8)
        if y >= self.padding and y <= self.padding + self.height:
            row = (y - self.padding) // (self.height // 8)
        
        # determine if selected was a move
        if ([row, col] in self.shaded):
            terse = chr(97 + self.selected[1]) + str(8 - self.selected[0]) + chr(97 + col) + str(8 - row)

            # check if pawn promotion
            if (self.board.piece_at(chess.square(self.selected[1], 7 - self.selected[0])).piece_type == chess.PAWN):
                if (row == 0 and self.board.turn or row == 7 and not self.board.turn):
                    self.handle_promotion()
                    self.promoMoveStr = terse
                    self.promoMoveNum = [row, col]
                    return

            self.board.push_uci(terse)
            self.times[self.startingPlayerTeam == "white"] += self.incTime

            # draw board after move
            self.prevMove = [self.selected, [row, col]]
            self.shaded = []
            self.selected = [-1, -1]
            self.availableMoves = self.board.legal_moves
            self.draw()

            # check for mate
            if (self.board.is_checkmate()):
                self.hasWon = 1
                self.handle_end()
                return

            # check for stalemate
            if (self.board.is_stalemate()):
                self.hasWon = 2
                self.handle_end()


        # if not, handle these cases
        else:
            piece = self.board.piece_at(chess.square(col, 7 - row))

            # 1. clicked on another friendly piece
            if (piece != None and piece.color == self.board.turn):
                self.selected = [row, col]

                toSquare = chr(97 + col) + str(8 - row)
                self.shaded = []
                for move in self.availableMoves:
                    terse = move.uci()
                    if (toSquare == terse[:2]):
                        self.shaded.append([8 - int(terse[3]), ord(terse[2]) - 97])

            # 2. clicked on nothing or enemy, deselect everything
            else:
                self.selected = [-1, -1]
                self.shaded = []
        
            self.draw()
    

    def draw(self):
        # cover potential promotion menu
        if self.padding == 20:
            promoW = 600
            promoH = 300
            drawx = (1536 - promoW) / 2
            drawy = (800 - promoH) / 2
        else:
            promoW = 700
            promoH = 350
            drawx = (1920 - promoW) / 2
            drawy = (1080 - promoH) / 2
        pygame.draw.rect(self.screen, "black", pygame.Rect(drawx - 1, drawy - 1, promoW + 2, promoH + 2))

        pieceStrs = ["pawn", "knight", "bishop", "rook", "queen", "king"]
        colorsStrs = ["black", "white"]

        # go through each square
        for i in range(64):

            # draw the square color
            drawx = self.padding + (i % 8) * (self.width // 8)
            drawy = self.padding + (i // 8) * (self.height // 8)
            color = (0, 0, 0, 0)
            if ((i + (i // 8)) & 1): # light
                if ([i // 8, i % 8] == self.selected or [i // 8, i % 8] in self.prevMove):
                    color = (245,246,130,255)
                else:
                    color = (235,236,208,255)
            else: # dark
                if ([i // 8, i % 8] == self.selected or [i // 8, i % 8] in self.prevMove):
                    color = (185,202,67,255)
                else:
                    color = (115,149,82,255)
                
            pygame.draw.rect(self.screen, color, pygame.Rect(drawx, drawy, (self.width // 8), (self.height // 8)))

            # draw the dot or ring if necessary
            piece = self.board.piece_at(chess.square(i % 8, 7 - i // 8))
            if ([i // 8, i % 8] in self.shaded):
                if (piece == None):
                    image = pygame.image.load(f"./pngs/dot.png")
                else:
                    image = pygame.image.load(f"./pngs/circle.png")
                image.set_alpha(50)
                self.screen.blit(image, (drawx, drawy))

            # draw the pieces
            if (piece != None):
                image = pygame.image.load(f"./pngs/{pieceStrs[piece.piece_type - 1]}_{colorsStrs[int(piece.color)]}.png").convert_alpha()
                self.screen.blit(image, (drawx, drawy))
                
        pygame.display.flip()


# prints usage of this program
def print_usage():
    print("usage: python3 play.py", file=sys.stderr)
    print("flags:\n" +
          "-e [dir]        :           directory of engine binary\n" +
          "-fs             :           game will start in fullscreen\n" +
          "-b              :           player will start as black\n" +
          "-time [time]    :           integer of minutes for game\n" +
          "-inc  [inc]     :           integer of seconds clock goes up at end of turn\n", file=sys.stderr)
    exit()


# asynch function to run engine
async def run_engine(board):
    transport, engine = await chess.engine.popen_uci(board.engineDir) # r"../engine/build/engine"
    result = await engine.play(board.board, chess.engine.Limit(white_clock=board.times[1], black_clock=board.times[0], white_inc=board.incTime, black_inc=board.incTime))
    await engine.quit()
    board.botMove = result.move


async def main_loop(board):
    # actual game loop
    running = True
    botRunning = False
    while running:
        board.startTime = time.time()

        # event detection
        for event in pygame.event.get():

            # check for quit game
            if event.type == pygame.QUIT:
                running = False
            if event.type == pygame.KEYDOWN:
                if event.key == 27:
                    quit()
                # elif event.key == 32: # space bar should pause game
                
            
            # check for mouse click
            if event.type == pygame.MOUSEBUTTONDOWN:
                if (board.board.turn == (board.startingPlayerTeam == "white") and board.hasWon == -1):
                    board.handle_click(event.pos[0], event.pos[1])

        # check for if waiting for bot move
        if (board.board.turn != (board.startingPlayerTeam == "white")):
            if (not botRunning and board.hasWon == -1):
                board.startTime = time.time()
                asyncio.ensure_future(run_engine(board))
                botRunning = True
            else:
                if (board.botMove != None):
                    botRunning = False
                    if (board.hasWon == -1):
                        board.handle_bot_move()
                    board.botMove = None

        await asyncio.sleep(.1)
        if (board.hasWon == -1):
            board.handle_time()

    pygame.quit()


# handles args
def handle_args(args):
    prevArgs = [False, False, False, False, False]

    defaultFullscreen = False
    startingPlayerTeam = "white"
    startingTime = 5
    incTime = 2

    for i in range(1, len(args)):
        if args[i] == "-fs":
            if prevArgs[0]:
                print_usage()
            else:
                prevArgs[0] = True
                defaultFullscreen = True
        elif args[i] == "-b":
            if prevArgs[1]:
                print_usage()
            else:
                prevArgs[1] = True
                startingPlayerTeam = "black"
        elif args[i] == "-time":
            if prevArgs[2]:
                print_usage()
            else:
                prevArgs[2] = True
                try:
                    startingTime = int(args[i + 1])
                except:
                    print_usage()
        elif args[i] == "-inc":
            if prevArgs[3]:
                print_usage()
            else:
                prevArgs[3] = True
                try:
                    incTime = int(args[i + 1])
                except:
                    print_usage()
        elif args[i] == "-e":
            if prevArgs[4]:
                print_usage()
            else:
                prevArgs[4] = True
                try:
                    engineDir = args[i + 1]
                except:
                    print_usage()
                if (not os.path.isfile(engineDir)):
                    print("Error: invalid engine directory.")

        else:
            # may be a number for a flag
            if (args[i - 1] != "-time" and args[i - 1] != "-inc" and args[i - 1] != "-e"):
                print_usage()

    if (not prevArgs[4]):
        print("Error: the engine binary must be passed as a flag.")
        print_usage()

    return engineDir, defaultFullscreen, startingPlayerTeam, startingTime, incTime


# initializes board and both asynch functions
def main():
    engineDir, defaultFullscreen, startingPlayerTeam, startingTime, incTime = handle_args(sys.argv)

    # set up pygame screen and clock
    pygame.init()
    screen = None
    if defaultFullscreen:
        screen = pygame.display.set_mode((0, 0))
        pygame.display.toggle_fullscreen()
    else:
        screen = pygame.display.set_mode((1536, 800))
    pygame.display.set_caption("EvanBOT")

    # create board to process what is happening on screen
    board = GameBoard(engineDir, defaultFullscreen, startingPlayerTeam, startingTime, incTime, screen)

    # convert all svg files into png files of proper size, then draw first frame
    if os.path.isdir("pngs"):
        shutil.rmtree("pngs")
    os.mkdir("pngs")
    dir = os.fsencode("svgs")
    for file in os.listdir(dir):
        svg2png(url="svgs/" + os.fsdecode(file), write_to="pngs/" + os.fsdecode(file)[:-3] + "png", output_height=board.width // 8, output_width=board.width // 8) # output_height=board.width // 8, output_width=board.width // 8
    board.draw()

    asyncio.run(main_loop(board))


if __name__ == "__main__":
    main()

'''
for the whole project: only use absolute directories relative to the files being ran
-- this will allow people to run the files regardless of what directory their console is in
'''