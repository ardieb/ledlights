import librosa
from enum import Enum
import config
import controller
import serial
import serial.tools
import serial.tools.list_ports
import numpy as np
import time
import pyaudio
import os
import argparse
from datetime import datetime
from colour import Color
import sys

stream=None
arduino=None
prevColor=Color(rgb=(0,0,0))
parser=argparse.ArgumentParser(description='Sync led lights to music.')
parser.add_argument('--reactive',
                    action='store_true',
                    default=False,
                    dest='reactive',
                    help='Lights will respond to soundcard output. This is the default mode')
parser.add_argument('--programable',
                    action='store_true',
                    default=False,
                    dest='programmable',
                    help='Lights will process an audio file and then play the processed file')
parser.add_argument('--fromcsv',
                    action='store_true',
                    default=False,
                    dest='fromcsv',
                    help='Lights will animate to a stored csv animation sequence')
parser.add_argument('-f',
                    action='store',
                    dest='file',
                    help='file to read')


class AnimCodes(Enum):
    ON=101
    OFF=102

    #flashing
    BLINK=103
    BLINKALT=104
    SPARKLE=105
    SPARKLEALT=106
    STROBO=107
    CYCLECOLORS=151

    #shifts
    PIXELSHIFTRIGHT=201
    PIXELBOUNCE=203
    PIXELSMOOTHSHIFTRIGHT=211
    PIXELSMOOTHSHIFTLEFT=212
    PIXELSMOOTHBOUNCE=213
    COMET=221
    COMETCOL=222
    BARSHIFTRIGHT=231
    BARSHIFTLEFT=232
    MOVINGBARS=241
    MOVINGGRADIENT=242
    LARSONSCANNER=251
    LARSONSCANNERALT=252

    #fades
    FADEIN=301
    FADEOUT=302
    FADEINOUT=303
    GLOW=304
    PLASMA=305
    FADECOLORS=351
    FADECOLORSLOOP=352
    PIXELFADECOLORS=353

    #ex
    FLAME=354
    FIRE=501
    BOUNCINGBALLS=502
    BUBBLES=503
    ENDSEQ=0
    STOPSEQ=1
COLORS=[Color(rgb=(40/255,255/255,0/255)),
        Color(rgb=(0/255,255/255,232/255)),
        Color(rgb=(0/255,124/255,255/255)),
        Color(rgb=(5/255,0/255,255/255)),
        Color(rgb=(69/255,0/255,234/255)),
        Color(rgb=(87/255,0/255,158/255)),
        Color(rgb=(116/255,0/255,0/255)),
        Color(rgb=(179/255,0/255,0/255)),
        Color(rgb=(238/255,0/255,0/255)),
        Color(rgb=(255/255,99/255,0/255)),
        Color(rgb=(255/255,236/255,0/255)),
        Color(rgb=(153/255,255/255,0/255))]

import signal
import sys


def signal_handler(signal,frame):
    sys.exit(0)
"""
Returns: An RGB representation of a chroma vector
Parameter chromaVector: 12,1 numpy array
"""
def mapChromaVectorToColor(chromaVector):
    if np.count_nonzero(chromaVector) == 0:
        return Color(rgb=(0,0,0))
    pitch=np.asarray(COLORS[:])
    c = pitch[np.argmax(chromaVector)]
    #range = list(prevColor.range_to(c,3))
    return c
    #return pitch[idx]


"""
Returns: An ala animation sequence based upon a sound file
Parameter fileName: a sound file to read
"""
def animateSound(data):
    global prevColor
    y=np.fromstring(data,dtype=np.int32).astype(np.float32)
    sr=config.MIC_RATE
    if np.isnan(y).any():
        return
    yHarmonic,yPercussive=librosa.effects.hpss(y)
    chromagram=librosa.feature.chroma_cqt(y=yHarmonic,sr=sr)
    try:
        tempo, beatFrames = librosa.beat.beat_track(y=y,sr=sr)
        beatTimes = librosa.frames_to_time(beatFrames,sr=sr)
        beatChroma = librosa.util.sync(chromagram,beatFrames,aggregate=np.median)
        durations = [beatTimes[i]-beatTimes[i-1] for i in range(1,len(beatTimes))]
        durations.append(len(y) / sr - beatTimes[-1])
        for cv,d in beatChroma.T,durations:
            nextColor=mapChromaVectorToColor(cv)
            arduino.sendCmd("I="+nextColor.hex[1:])
            prevColor = nextColor
            time.sleep(d)
    except Exception:
        chromaVector=np.average(chromagram,axis=1).T
        nextColor=mapChromaVectorToColor(chromaVector)
        if prevColor!=nextColor:
            arduino.sendCmd("I="+nextColor.hex[1:])
            prevColor=nextColor
        time.sleep(1/config.FPS)


"""
TODO: Loads an audiofile and generates a csv with animation codes to execute
allows for greater control of animations. i.e. stobo, fades, scanners
"""
def loadAudio(audioFile):
    y,sr=librosa.load(audioFile)
    yHarmonic,yPercussive=librosa.effects.hpss(y)
    if (np.isnan(yPercussive).any()):
        return
    tempo,beatFrames=librosa.beat.beat_track(yPercussive,sr=sr)
    beatTimes=librosa.frames_to_time(beatFrames,sr=sr)
    chromogram=librosa.feature.chroma_cqt(y=yHarmonic,sr=sr)
    beatChromogram=librosa.util.sync(chromogram,beatFrames,aggregate=np.median)
    colors=[]
    durations=[beatTimes[i+1]-beatTimes[i] for i in range(len(beatTimes)-1)]
    durations.append(60*tempo)
    durations.append(60*tempo)
    for chromaVector in beatChromogram.T:
        rgb=mapChromaVectorToColor(chromaVector)
        color='0x%02x%02x%02x'%(rgb[0],rgb[1],rgb[2])
        colors.append(color)

    print('ready to play')
    time.sleep(1)

    pa=pyaudio.PyAudio()
    outputStream=pa.open(format=pyaudio.paInt16,
                         rate=44100,
                         channels=2,
                         output=True)
    outputStream.start_stream()
    prevFrame=0

    data=list(zip(colors,durations,beatFrames))
    for color,duration,frame in data:
        outputStream.write(y[prevFrame:frame].tobytes())
        prevFrame=frame
        print(color,duration*1000)
        sendCmd(arduino,'A='+str(101))
        sendCmd(arduino,'B='+str(100))
        sendCmd(arduino,'C='+str(color))
        sendCmd(arduino,'D='+str(duration*1000))
    stream.stop_stream()
    pa.terminate()


if __name__=='__main__':
    #finds the arduino on the port
    args=parser.parse_args()
    arduino = controller.arduino(controller.MEGA_SN)
    arduino.connect()
    if args.programmable:
        if args.file==None:
            print('Additional argument required: file')
        else:
            file=os.path.abspath(args.file)
            loadAudio(file)
            startTime = datetime.now()
    elif args.fromcsv:
        if args.file==None:
            print('Addition argument required: file')
        else:
            file=os.path.abspath(args.file)
        pass #not implemented yet
    elif args.reactive:
        p=pyaudio.PyAudio()
        frames_per_buffer=int(config.MIC_RATE / config.FPS)
        stream=p.open(format=pyaudio.paInt32,
                      channels=2,
                      rate=config.MIC_RATE,
                      input_device_index=3,
                      input=True,
                      frames_per_buffer=frames_per_buffer)
        stream.start_stream()
        print('Starting...')
        time.sleep(5)
        print('Serial is active')
        startTime=datetime.now()
        while stream.is_active():
            animateSound(stream.read(frames_per_buffer,exception_on_overflow=False))
        print('Stopping stream...')
        stream.stop_stream()
        p.terminate()
        print('Terminated')
    else:
        print('Mode required')
