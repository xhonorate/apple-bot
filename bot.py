import cv2 as cv
import pyautogui
from time import sleep, time
from threading import Thread, Lock
from math import sqrt


class BotState:
    INITIALIZING = 0
    SEARCHING = 1
    MOVING = 2


class Bot:
    # constants
    INITIALIZING_SECONDS = 3
    MINING_SECONDS = 14
    MOVEMENT_STOPPED_THRESHOLD = 0.975
    IGNORE_RADIUS = 130
    TOOLTIP_MATCH_THRESHOLD = 0.72

    # threading properties
    stopped = True
    lock = None

    # properties
    state = None
    targets = []
    minX = 0
    minY = 0
    avgX = 0
    avgY = 0
    curr_row = 0
    screenshot = None
    timestamp = None
    movement_screenshot = None
    window_offset = (0,0)
    window_w = 0
    window_h = 0
    limestone_tooltip = None
    click_history = []

    def __init__(self, window_offset, window_size):
        # create a thread lock object
        self.lock = Lock()

        # for translating window positions into screen positions, it's easier to just
        # get the offsets and window size from WindowCapture rather than passing in 
        # the whole object
        self.window_offset = window_offset
        self.window_w = window_size[0]
        self.window_h = window_size[1]

        # start bot in the initializing mode to allow us time to get setup.
        # mark the time at which this started so we know when to complete it
        self.state = BotState.INITIALIZING
        self.timestamp = time()

    def draw_rectangle(self, p1, p2):
        if self.stopped:
            return

        self.curr_row += 1

        for x in range(p1[0], p2[0] + 1):
            for y in range(p1[1], p2[1] + 1):
                self.targets[y][x] = 0

        self.state = BotState.MOVING

        offset_x = 20
        offset_y = 40
        padding = 30
        speed = 0.35 * (0.5 + 0.5 * max((abs(p1[0] - p2[0]), abs(p1[1] - p2[1]))))
        screen_x1, screen_y1 = self.get_screen_position(p1)
        screen_x2, screen_y2 = self.get_screen_position(p2)

        x1 = screen_x1 - padding + offset_x
        y1 = screen_y1 - padding + offset_y
        x2 = screen_x2 + padding + offset_x
        y2 = screen_y2 + padding + offset_y

        pyautogui.moveTo(x=x1, y=y1)
        pyautogui.dragTo(x=x2, y=y2, duration=speed)

        #img = cv.rectangle(self.screenshot, (int(x1), int(y1)), (int(x2), int(y2)), (0, 255, 0), 2)
        #cv.imshow('Computer Vision', self.screenshot)
    
        self.state = BotState.SEARCHING

    def check_adj_matches(self):
        targets = self.targets

        if self.curr_row >= len(self.targets):
            self.curr_row = 0
        
        i = self.curr_row
        found_match = False
        while not found_match and i < len(targets):
            # if we stopped our script, exit this loop
            if self.stopped:
                break

            for j in range(len(targets[i])):
                current_target = targets[i][j]
                if current_target == 0:
                    continue

                next_target = 0
                delta = 0
                while not found_match and next_target == 0 and j + delta < len(targets[i]) - 1:
                    delta += 1
                    next_target = targets[i][j + delta]
                    if next_target == 0:
                        continue
                    if (next_target + current_target == 10):
                        found_match = True
                        self.draw_rectangle([j, i], [j + delta, i])
                        return True

                next_target = 0
                delta = 0
                while not found_match and next_target == 0 and i + delta < len(targets) - 1:
                    delta += 1
                    next_target = targets[i + delta][j]
                    if next_target == 0:
                        continue
                    if (next_target + current_target == 10):
                        found_match = True
                        self.draw_rectangle([j, i], [j, i + delta])
                        return True
            i += 1

        return found_match

    # for board - get list of all matches
    # for each match, apply the move, then get list of all matches
    # whichever move has the best increase in possible matches, do that one
    def chooseBestMove(self, targets):
        bestMove = None
        bestMatches = -999
        matches = self.getAllMatches(targets)
        print("Moves Left: " + str(len(matches)))

        if len(matches) == 0:
            return None

        for match in matches:
            tempTargets = self.targets.copy()
            
            # apply the move
            for x in range(match[0][0], match[1][0] + 1):
                for y in range(match[0][1], match[1][1] + 1):
                    tempTargets[y][x] = 0

            # get all matches
            newMatches = self.getAllMatches(tempTargets)

            # if we have more matches, update best move
            if len(newMatches) > bestMatches:
                bestMatches = len(newMatches)
                bestMove = match

            # much faster way. less thorough 
            if len(newMatches) >= len(matches):
                # found a good enough move, take it
                return match

        return bestMove

    def getAllMatches(self, targets):
        i = 0
        matches = []
        while i < len(targets):
            for j in range(len(targets[i])):
                current_target = targets[i][j]

                #span both mult
                deltaX = 0
                deltaY = -1
                while j + deltaX < len(targets[i]) - 1:
                    deltaX += 1
                    deltaY = -1
                    while i + deltaY < len(targets) - 1:
                        deltaY += 1
                        
                        if ([[j, i], [j + deltaX, i + deltaY]]) in matches:
                            continue

                        firstRowSum = 0
                        for x in range(j, j + deltaX + 1):
                            firstRowSum += targets[i][x]
                        
                        firstColSum = 0
                        for y in range(i, i + deltaY + 1):
                            firstColSum += targets[y][j]
                        
                        if firstRowSum == 0 or firstColSum == 0:
                            continue
                        
                        # sum all targets from i, j  to i + deltaY, j + deltaX
                        sumInBox = 0
                        for y in range(i, i + deltaY + 1):
                            for x in range(j, j + deltaX + 1):
                                sumInBox += targets[y][x]
                        
                        if sumInBox == 10:
                            matches.append([[j, i], [j + deltaX, i + deltaY]])

                #span both mult
                deltaX = -1
                deltaY = 0
                while i + deltaY < len(targets) - 1:
                    deltaY += 1
                    deltaX = -1
                    while j + deltaX < len(targets[i]) - 1:
                        deltaX += 1

                        if ([[j, i], [j + deltaX, i + deltaY]]) in matches:
                            continue

                        firstRowSum = 0
                        for x in range(j, j + deltaX + 1):
                            firstRowSum += targets[i][x]
                        
                        firstColSum = 0
                        for y in range(i, i + deltaY + 1):
                            firstColSum += targets[y][j]
                        
                        if firstRowSum == 0 or firstColSum == 0:
                            continue
                        
                        # sum all targets from i, j  to i + deltaY, j + deltaX
                        sumInBox = 0
                        for y in range(i, i + deltaY + 1):
                            for x in range(j, j + deltaX + 1):
                                sumInBox += targets[y][x]

                        if sumInBox == 10:
                            matches.append([[j, i], [j + deltaX, i + deltaY]])

            i += 1

        return matches

    def check_combo_matches(self):
        targets = self.targets

        if self.curr_row >= len(self.targets):
            self.curr_row = 0
        
        i = self.curr_row
        found_match = False
        while not found_match and i < len(targets):
            # if we stopped our script, exit this loop
            if self.stopped:
                break

            for j in range(len(targets[i])):
                current_target = targets[i][j]

                #span both mult
                deltaX = 0
                deltaY = -1
                while not found_match and j + deltaX < len(targets[i]) - 1:
                    deltaX += 1
                    deltaY = -1
                    while not found_match and i + deltaY < len(targets) - 1:
                        deltaY += 1
                        
                        # sum all targets from i, j  to i + deltaY, j + deltaX
                        sumInBox = 0
                        for y in range(i, i + deltaY + 1):
                            for x in range(j, j + deltaX + 1):
                                sumInBox += targets[y][x]

                        if sumInBox == 10:
                            found_match = True
                            self.draw_rectangle([j, i], [j + deltaX, i + deltaY])
                            return True

                #span both mult
                deltaX = -1
                deltaY = 0
                while not found_match and i + deltaY < len(targets) - 1:
                    deltaY += 1
                    deltaX = -1
                    while not found_match and j + deltaX < len(targets[i]) - 1:
                        deltaX += 1
                        
                        # sum all targets from i, j  to i + deltaY, j + deltaX
                        sumInBox = 0
                        for y in range(i, i + deltaY + 1):
                            for x in range(j, j + deltaX + 1):
                                sumInBox += targets[y][x]

                        if sumInBox == 10:
                            found_match = True
                            self.draw_rectangle([j, i], [j + deltaX, i + deltaY])
                            return True

            i += 1

        return found_match

    # translate a pixel position on a screenshot image to a pixel position on the screen.
    # pos = (x, y)
    # WARNING: if you move the window being captured after execution is started, this will
    # return incorrect coordinates, because the window position is only calculated in
    # the WindowCapture __init__ constructor.
    def get_screen_position(self, pos):
        return (self.minX + self.avgX * pos[0],self.minY + self.avgY * pos[1])

    # threading methods

    def update_targets(self, targets, minX, minY, avgX, avgY):
        self.lock.acquire()
        self.targets = targets
        self.minX = minX
        self.minY = minY
        self.avgX = avgX
        self.avgY = avgY
        self.lock.release()

    def update_screenshot(self, screenshot):
        self.lock.acquire()
        self.screenshot = screenshot
        self.lock.release()

    def start(self):
        self.stopped = False
        t = Thread(target=self.run)
        t.start()

    def stop(self):
        self.stopped = True

    # main logic controller
    def run(self):
        while not self.stopped:          
            if self.state == BotState.INITIALIZING:
                # do no bot actions until the startup waiting period is complete
                if time() > self.timestamp + self.INITIALIZING_SECONDS:
                    # start searching when the waiting period is over
                    self.lock.acquire()
                    self.state = BotState.SEARCHING
                    self.lock.release()

            elif self.state == BotState.SEARCHING:
                if (len(self.targets) == 0):
                    sleep(0.500)
                    continue

                # check first for adjacent matches (minimum search effort)
                self.lock.acquire()
                success = self.check_adj_matches()
                if not success:
                    self.curr_row = 0
                    # on failure, reset curr_row (to check from first row again)
                    # then try search one more time
                    success = self.check_adj_matches()

                if not success:
                    # if search still unsuccessful, check for combo matches
                    bestMove = self.chooseBestMove(self.targets)

                    if not bestMove:
                        self.stopped = True
                        print("No moves found")
                        break

                    self.draw_rectangle(bestMove[0], bestMove[1])
                self.lock.release()

            elif self.state == BotState.MOVING:
                self.lock.acquire()
                self.timestamp = time()
                self.lock.release()