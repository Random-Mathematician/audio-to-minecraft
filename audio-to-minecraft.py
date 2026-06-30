#!/usr/bin/python3
# AudioToMinecraft v1.0 by RandomMathematician
import pyautogui as Input
import pyaudio as Audio
import numpy as np
import threading
from time import sleep
from os import system as bash

# Specify Audio constants:
RATE = 44100
CHANNELS = 1
SAMPLE_SECS = 0.1
SAMPLE_LEN = int((RATE*SAMPLE_SECS)//1)
FORMAT = Audio.paInt16
DEBUG = False

def raiseOnDebug(err):
	if DEBUG: raise err
	else: print(err)

def debugPrint(*args, **kwargs):
	if DEBUG: print(*args, **kwargs)

# The action function, to emulate Input events.
# It serves as a wrapper for keyDown, keyUp, press, mouseDown,
# mouseUp, click and scroll from pyautogui
def action(key, act):
	if key == None: return # Allow an option to not do anything
	if key in Input.KEYBOARD_KEYS:
		# Tap/hold/release a keyboard key
		if act == "tap": Input.press(key)
		elif act == "up": Input.keyUp(key)
		elif act == "down": Input.keyDown(key)
		else: raiseOnDebug(ValueError("Invalid keyboard action: "+repr(act)))
	elif key[:5] == "mouse":
		# Move the mouse around
		# "key" can be: mouseleft, mouseright, mouseup, mousedown
		dirc = key[5]
		global MOUSEMOVE
		if act == "tap":
			d = {"l":(-1,0),"r":(1,0),"u":(0,-1),"d":(0,1)}[dirc]
			Input.move(*d)
		elif act == "down": MOUSEMOVE[dirc] = 20
		elif act == "up": MOUSEMOVE[dirc] = 0
		else: raiseOnDebug(ValueError("Invalid move action: "+repr(act)))
	elif key[:5] == "click":
		# Click/hold/release a mouse button
		# "key" can be: clickleft, clickmiddle, clickright
		btn = key[5:]
		if act == "tap": Input.click(button=btn)
		elif act == "down": Input.mouseDown(button=btn)
		elif act == "up": Input.mouseUp(button=btn)
		else: raiseOnDebug(ValueError("Invalid click action: "+repr(act)))
	elif key[:6] == "scroll":
		# Scroll up or down, once or continuously
		dirc = key[6]
		global MOUSESCROLL
		if act == "tap": Input.scroll({"d":-1, "u":1}[dirc])
		elif act == "down": MOUSESCROLL[dirc] = 1
		elif act == "up": MOUSESCROLL[dirc] = 0
		else: raiseOnDebug(ValueError("Invalid scroll action: "+repr(act)))

# Global dictionaries to execute movement continuously
# Mouse position and scroll are updated on another thread
# so as to not be slowed down by the audio processing
MOUSEMOVE = {"l": 0, "r": 0, "u": 0, "d": 0}
MOUSESCROLL = {"u": 0, "d": 0}

def continuous_input():
	global MOUSEMOVE
	global MOUSESCROLL
	while True: 
		hz = MOUSEMOVE["r"] - MOUSEMOVE["l"] # Vertical
		vt = MOUSEMOVE["d"] - MOUSEMOVE["u"] # Horizontal
		sc = MOUSESCROLL["u"] - MOUSESCROLL["d"] # Scroll
		if hz or vt: Input.move(hz, vt)
		if sc: Input.scroll(sc)
		sleep(0.01) # To not overprocess

# The function handling held movement is a separate daemon thread
threading.Thread(target=continuous_input, daemon=True).start()

# Shortcut for reading microphone bytes
def WAVtoInt(b):
	return int.from_bytes(b, "little", signed=True)

# Converts a pitch into the number of semitones it's above C5
def pitchToNum(hz):
	return int((12*np.log(hz/440)/np.log(2)-2.5)//1)

# Purely for testing purposes
def numToName(n):
	names = {0:"C", 1:"C#", 2:"D", 3:"Eb", 4:"E", 5:"F",
		6:"F#", 7:"G", 8:"Ab", 9:"A", 10:"Bb", 11:"B"}
	if n < 0: return None
	elif n > 23: return None
	elif n < 12: return names[n]
	else: return numToName(n-12) + "'"

# PITCH TO INPUTS MAPPING:
STARTMAP = {0: ("s", "down"), # C5 is hold S key
			2: ("d", "down"), # D5 is hold D key
			4: ("a", "down"), # E5 is hold A key
			5: ("w", "down"), # F5 is hold W key
			6: ("clickleft", "down"), # F5 is hold left click
			7: ("e", "tap"), # G5 is tap E key
			8: ("scrolldown", "tap"), # G#5 is scroll once
			9: ("space", "down"), #A5 is tap Space key
			10: ("clickright", "tap"), # Bb5 is hold right click
			11: ("shift", "tap"), # B5 is tap Shift key
			12: ("mousedown", "down"), # C6 is move mouse down
			14: ("mouseright", "down"), # D6 is move mouse right
			16: ("mouseleft", "down"), # E6 is move mouse left
			17: ("mouseup", "down"), # F6 is move mouse up
			19: ("esc", "tap")} # G6 is tap Escape key
ENDMAP = {0: ("s", "up"),
			2: ("d", "up"),
			4: ("a", "up"),
			5: ("w", "up"),
			6: ("clickleft", "up"),
			7: (None, None),
			8: (None, None),
			9: ("space", "up"),
			10: (None, None),
			11: (None, None),
			12: ("mousedown", "up"),
			14: ("mouseright", "up"),
			16: ("mouseleft", "up"),
			17: ("mouseup", "up"),
			19: (None, None)}

# Initialize Audio module and microphone
p = Audio.PyAudio()
bash("clear")
mic = p.open(format=FORMAT, channels=CHANNELS, rate=RATE, input=True)
print("Recording started")

try:
	num = -1
	while True:
		data = []
		for i in range(SAMPLE_LEN):
			# Record 100ms of audio and store them
			chunk = mic.read(1)
			data.append(WAVtoInt(chunk[0:2]))
		# Calculate the FFT
		dft = np.abs(np.fft.fft(data))
		mult = int(RATE//len(dft))
		dft = dft[200*mult:2500*mult]
		# Obtain the main frequency
		freq = 26100-(np.argmax(dft)+200)*mult
		# Store the last and current pitches
		lastnum = num
		num = pitchToNum(freq)
		# Show the current recieved pitch as a name (DEGUB only)
		debugPrint(numToName(num))
		# If the pitch changed, update actions accordingly
		if lastnum != num:
			if num in STARTMAP.keys():
				action(*STARTMAP[num])
			if lastnum in ENDMAP.keys():
				action(*ENDMAP[lastnum])
except KeyboardInterrupt:
	# Properly terminate audio reading
	mic.close()
	p.terminate()
