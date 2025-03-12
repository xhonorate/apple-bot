import cv2 as cv
import pyautogui
from time import sleep, time
from threading import Thread, Lock
from math import sqrt
import numpy as np

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
        speed = 0.2 * (0.7 + 0.3 * max((abs(p1[0] - p2[0]), abs(p1[1] - p2[1]))))
        screen_x1, screen_y1 = self.get_screen_position(p1)
        screen_x2, screen_y2 = self.get_screen_position(p2)

        x1 = screen_x1 - padding + offset_x
        y1 = screen_y1 - padding + offset_y
        x2 = screen_x2 + padding + offset_x
        y2 = screen_y2 + padding + offset_y

        pyautogui.moveTo(x=x1, y=y1)
        pyautogui.mouseDown()
        pyautogui.dragTo(x2, y2, speed, pyautogui.easeOutQuad)
        pyautogui.mouseUp()

        #img = cv.rectangle(self.screenshot, (int(x1), int(y1)), (int(x2), int(y2)), (0, 255, 0), 2)
        #cv.imshow('Computer Vision', self.screenshot)
    
        self.state = BotState.SEARCHING

    # for board - get list of all matches
    # for each match, apply the move, then get list of all matches
    # whichever move has the best increase in possible matches, do that one
    def chooseBestMove(self, targets):        
        totalRows = len(targets)
        totalCols = len(targets[0])

        matches = self.getAllMatches(targets, totalRows, totalCols)
        print("Moves Left: " + str(len(matches)))

        numMatches = len(matches)
        if numMatches == 0:
            return None

        bestMove = None
        bestMatches = -1
        highestNum = 0
        tempTargets = np.array(targets)  # Initialize with original targets

        for match in matches:
            changes = []
        
            # Apply the move
            for x in range(match[0][0], match[1][0] + 1):
                for y in range(match[0][1], match[1][1] + 1):
                    changes.append((y, x, tempTargets[y][x]))
                    tempTargets[y][x] = 0
            
            newMatches = self.getAllMatches(tempTargets, totalRows, totalCols)

            # get max z in changes
            newHighestNum = 0
            # Undo the changes after processing this move
            for y, x, z in changes:
                newHighestNum = max(newHighestNum, z)
                tempTargets[y][x] = z  # Replace with actual value to restore
            
            # good enough move, just take it (for speed)
            # if len(newMatches) > numMatches + 1 or (numMatches > 50 and len(newMatches) > numMatches):
            #     return match


            # if we have more matches, update best move
            newMatchCount = len(newMatches)
            if newMatchCount > bestMatches or (newMatchCount == bestMatches and newHighestNum > highestNum):
                highestNum = newHighestNum # prioritize getting rid of 9s, 8s, etc.
                bestMatches = newMatchCount
                bestMove = match

        return bestMove

    def getAllMatches(self, targets, totalRows, totalCols):
        # precompute prefix sum for faster sliced sum calculations
        prefix_sum = np.zeros((totalRows + 1, totalCols + 1), dtype=int)
        for i in range(1, totalRows + 1):
            for j in range(1, totalCols + 1):
                prefix_sum[i][j] = prefix_sum[i - 1][j] + prefix_sum[i][j - 1] - prefix_sum[i - 1][j - 1] + targets[i - 1][j - 1]
        
        def slicedSum(x1, x2, y1, y2):
            return prefix_sum[y2 + 1][x2 + 1] - prefix_sum[y1][x2 + 1] - prefix_sum[y2 + 1][x1] + prefix_sum[y1][x1]

        matches = []

        i = 0
        while i < totalRows:
            j = 0
            while j < totalCols:
                current_target = targets[i][j]
                # we have selected a target, now we search for a match

                found_match = False

                # check for horizontal matches
                deltaX = -1
                while j + deltaX < totalCols - 1:
                    if found_match:
                        break
                    deltaX += 1
                    deltaY = 0
                    while i + deltaY < totalRows - 1:
                        if found_match:
                            break
                        deltaY += 1

                        # sum all targets from i, j  to i + deltaY, j + deltaX
                        sumInBox = slicedSum(j, j + deltaX, i, i + deltaY)

                        if sumInBox > 10:
                            break

                        if sumInBox == 10:
                            # check if there is unnecessary empty space in this box (if first or last row or column is all zeroes)
                            firstRowSum = 0
                            for x in range(j, j + deltaX + 1):
                                firstRowSum += targets[i][x]
                            
                            firstColSum = 0
                            for y in range(i, i + deltaY + 1):
                                firstColSum += targets[y][j]
                                
                            lastRowSum = 0
                            for x in range(j, j + deltaX + 1):
                                lastRowSum += targets[i + deltaY][x]
                            
                            lastColSum = 0
                            for y in range(i, i + deltaY + 1):
                                lastColSum += targets[y][j + deltaX]
                            
                            if firstRowSum == 0 or lastRowSum == 0 or firstColSum == 0 or lastColSum == 0:
                                break

                            found_match = True
                            matches.append([[j, i], [j + deltaX, i + deltaY]])

                # check for vertical matches
                deltaY = -1
                while i + deltaY < totalRows - 1:
                    if found_match:
                        break
                    deltaY += 1
                    deltaX = 0
                    while j + deltaX < totalCols - 1:
                        if found_match:
                            break
                        deltaX += 1

                        # sum all targets from i, j  to i + deltaY, j + deltaX
                        sumInBox = slicedSum(j, j + deltaX, i, i + deltaY)

                        if sumInBox > 10:
                            break

                        if sumInBox == 10:
                            # check if there is unnecessary empty space in this box (if first or last row or column is all zeroes)
                            firstRowSum = 0
                            for x in range(j, j + deltaX + 1):
                                firstRowSum += targets[i][x]
                            
                            firstColSum = 0
                            for y in range(i, i + deltaY + 1):
                                firstColSum += targets[y][j]
                                
                            lastRowSum = 0
                            for x in range(j, j + deltaX + 1):
                                lastRowSum += targets[i + deltaY][x]
                            
                            lastColSum = 0
                            for y in range(i, i + deltaY + 1):
                                lastColSum += targets[y][j + deltaX]
                            
                            if firstRowSum == 0 or lastRowSum == 0 or firstColSum == 0 or lastColSum == 0:
                                break

                            found_match = True
                            matches.append([[j, i], [j + deltaX, i + deltaY]])

                j += 1
            i += 1

        return matches


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

                self.lock.acquire()
                bestMove = self.chooseBestMove(self.targets)
                
                if not bestMove:
                    self.stopped = True
                    print("No moves found")
                    break

                self.draw_rectangle(bestMove[0], bestMove[1])
                self.lock.release()
                continue

            elif self.state == BotState.MOVING:
                self.lock.acquire()
                self.timestamp = time()
                self.lock.release()