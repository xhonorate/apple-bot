import cv2 as cv
import numpy as np
import os
from time import sleep, time
from windowcapture import WindowCapture
from vision import Vision
from bot import Bot, BotState
import keyboard
import sys
import pyautogui

# Change the working directory to the folder this script is in.
# Doing this because I'll be putting the files from each video in their own folder on GitHub
os.chdir(os.path.dirname(os.path.abspath(__file__)))


# initialize the WindowCapture class
wincap = WindowCapture()
# initialize the Vision class
vision1 = Vision('Screenshot_1.jpg')
vision2 = Vision('Screenshot_2.jpg')
vision3 = Vision('Screenshot_3.jpg')
vision4 = Vision('Screenshot_4.jpg')
vision5 = Vision('Screenshot_5.jpg')
vision6 = Vision('Screenshot_6.jpg')
vision7 = Vision('Screenshot_7.jpg')
vision8 = Vision('Screenshot_8.jpg')
vision9 = Vision('Screenshot_9.jpg')
resetVision = Vision('Screenshot_Reset.jpg')
playVision = Vision('Screenshot_Play.jpg')
bot = Bot((wincap.offset_x, wincap.offset_y), (wincap.w, wincap.h))

global minX
global minY
global maxX
global maxY

minX = 9999
minY = 9999
maxX = 0
maxY = 0
loop_time = time()

# pass a number as additional argument to auto start the bot when the spawn value is greater than the number
minspawn = None
if len(sys.argv) > 1:
    minspawn = int(sys.argv[1])

def startBot():
    print("Starting bot...")
    global minX
    global minY
    global maxX
    global maxY

    bot.start()
    
    for arr in [points1, points2, points3, points4, points5, points6, points7, points8, points9]:
        for point in arr:
            if point[0] < minX:
                minX = point[0]
            if point[1] < minY:
                minY = point[1]
            if point[0] > maxX:
                maxX = point[0]
            if point[1] > maxY:
                maxY = point[1]

        rows = 10
        cols = 17

        dx = maxX - minX
        dy = maxY - minY

        avgX = dx / (cols - 1)
        avgY = dy / (rows - 1)

        if avgX > 0 and avgY > 0:
            sortedPoints = np.array(np.zeros((rows, cols), dtype=int))
            for i in range(9):
                arr = [points1, points2, points3, points4, points5, points6, points7, points8, points9][i]
                for point in arr:
                    x = round((point[0] - minX) / avgX)
                    x = max(0, min(x, cols - 1))
                    y = round((point[1] - minY) / avgY)
                    y = max(0, min(y, rows - 1))
                    sortedPoints[y][x] = i + 1

            bot.update_targets(sortedPoints, minX, minY, avgX, avgY)

def stopBot():
    print("Stopping bot...")
    os._exit(0)

keyboard.add_hotkey('enter', startBot)
keyboard.add_hotkey('q', stopBot)

while(True):
    accuracy = 0.95
    # get an updated image of the game
    screenshot = wincap.get_screenshot()
    #cv.imshow('Computer Vision', screenshot)
    #bot.update_screenshot(screenshot)
    
    if bot.state == BotState.INITIALIZING:
        # auto press play button
        playbtn = playVision.find(screenshot, accuracy)
        if len(playbtn) > 0:
            pyautogui.moveTo(x=playbtn[0][0], y=playbtn[0][1])
            pyautogui.click()
            continue

        points1 = vision1.find(screenshot, accuracy)
        points2 = vision2.find(screenshot, accuracy)
        points3 = vision3.find(screenshot, accuracy)
        points4 = vision4.find(screenshot, accuracy)
        points5 = vision5.find(screenshot, accuracy)
        points6 = vision6.find(screenshot, accuracy)
        points7 = vision7.find(screenshot, accuracy)
        points8 = vision8.find(screenshot, accuracy)
        points9 = vision9.find(screenshot, accuracy)

        if len(points1) == 0 and len(points2) == 0 and len(points3) == 0 and len(points4) == 0 and len(points5) == 0 and len(points6) == 0 and len(points7) == 0 and len(points8) == 0 and len(points9) == 0:
            #do nothing
            print("No points found")
        else:
            spawnVal = len(points1) * 5 + len(points2) * 3 + len(points3) * 2 + len(points4) - len(points6) - len(points7) * 2 - len(points8) * 3 - len(points9) * 5
            spawnValString = "TRASH"
            if spawnVal > -10:
                spawnValString = "TRASH"
            if spawnVal > 0:
                spawnValString = "OK"
            if spawnVal > 25:
                spawnValString = "GOOD"
            if spawnVal > 50:
                spawnValString = "GREAT"
            if spawnVal > 75:
                spawnValString = "AMAZING"
            if spawnVal > 100:
                spawnValString = "PERFECT"
            print("Spawn value: " + str(spawnVal) + " (" + spawnValString + ")")

            if minspawn:
                if spawnVal > minspawn:
                    startBot()
                else:
                    resetbtn = resetVision.find(screenshot, accuracy)
                    if len(resetbtn) > 0:
                        #reset board
                        pyautogui.moveTo(x=resetbtn[0][0], y=resetbtn[0][1] + 20)
                        pyautogui.click()
                        
            else:
                print("Press Enter to start the bot...")


    # debug the loop rate
    #print('FPS {}'.format(1 / (time() - loop_time)))
    loop_time = time()

print('Done.')
