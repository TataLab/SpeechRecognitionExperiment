#!/usr/bin/env python
import ctypes

import os
import commands

import yarp
import string
import pyaudio
import wave
from random import randint

#define stream chunk
chunk = 1024

import numpy as np
def wer(ref, hyp ,debug=False):
    r = ref.split()
    h = hyp.split()
    #costs will holds the costs, like in the Levenshtein distance algorithm
    costs = [[0 for inner in range(len(h)+1)] for outer in range(len(r)+1)]
    # backtrace will hold the operations we've done.
    # so we could later backtrace, like the WER algorithm requires us to.
    backtrace = [[0 for inner in range(len(h)+1)] for outer in range(len(r)+1)]

    OP_OK = 0
    OP_SUB = 1
    OP_INS = 2
    OP_DEL = 3

    # First column represents the case where we achieve zero
    # hypothesis words by deleting all reference words.
    for i in range(1, len(r)+1):
        costs[i][0] = 1*i
        backtrace[i][0] = OP_DEL

    # First row represents the case where we achieve the hypothesis
    # by inserting all hypothesis words into a zero-length reference.
    for j in range(1, len(h) + 1):
        costs[0][j] = 1 * j
        backtrace[0][j] = OP_INS

    # computation
    for i in range(1, len(r)+1):
        for j in range(1, len(h)+1):
            if r[i-1] == h[j-1]:
                costs[i][j] = costs[i-1][j-1]
                backtrace[i][j] = OP_OK
            else:
                substitutionCost = costs[i-1][j-1] + 1 # penalty is always 1
                insertionCost    = costs[i][j-1] + 1   # penalty is always 1
                deletionCost     = costs[i-1][j] + 1   # penalty is always 1

                costs[i][j] = min(substitutionCost, insertionCost, deletionCost)
                if costs[i][j] == substitutionCost:
                    backtrace[i][j] = OP_SUB
                elif costs[i][j] == insertionCost:
                    backtrace[i][j] = OP_INS
                else:
                    backtrace[i][j] = OP_DEL

    # back trace though the best route:
    i = len(r)
    j = len(h)
    numSub = 0
    numDel = 0
    numIns = 0
    numCor = 0
    if debug:
        print("OP\tREF\tHYP")
        lines = []
    while i > 0 or j > 0:
        if backtrace[i][j] == OP_OK:
            numCor += 1
            i-=1
            j-=1
            if debug:
                lines.append("OK\t" + r[i]+"\t"+h[j])
        elif backtrace[i][j] == OP_SUB:
            numSub +=1
            i-=1
            j-=1
            if debug:
                lines.append("SUB\t" + r[i]+"\t"+h[j])
        elif backtrace[i][j] == OP_INS:
            numIns += 1
            j-=1
            if debug:
                lines.append("INS\t" + "****" + "\t" + h[j])
        elif backtrace[i][j] == OP_DEL:
            numDel += 1
            i-=1
            if debug:
                lines.append("DEL\t" + r[i]+"\t"+"****")
    if debug:
        lines = reversed(lines)
        for line in lines:
            print(line)
        print("#cor " + str(numCor))
        print("#sub " + str(numSub))
        print("#del " + str(numDel))
        print("#ins " + str(numIns))
    return (numSub + numDel + numIns) / (float) (len(r))
    wer_result = round( (numSub + numDel + numIns) / (float) (len(r)), 3)
    return wer_result

def playAudio(fileLocation1, fileLocation2):

    #open a wav format music
    f1 = wave.open(fileLocation1,"rb");
    f2 = wave.open(fileLocation2,"rb");
    #instantiate PyAudio
    p = pyaudio.PyAudio();
    #open stream
    stream = p.open(format = p.get_format_from_width(f1.getsampwidth()),
                    channels = 2,
                    rate = f1.getframerate(),
                    output = True);

    #read data
    data1 = f1.readframes(chunk);
    data2 = f2.readframes(chunk);

    #play stream
    while data1 and data2 and (len(data1) == len(data2)):

        res = [''] * len(data1) * 2
        res[::4]  = data1[::2]
        res[1::4] = data1[1::2]
        res[2::4] = data2[::2]
        res[3::4] = data2[1::2]

        stream.write(''.join(res));

        data1 = f1.readframes(chunk);
        data2 = f2.readframes(chunk);

    #stop stream
    stream.stop_stream();
    stream.close();

    #close PyAudio
    p.terminate()


audioFiles = [];


for subdir, dirs, files in os.walk("../pnnc-v2/speakers/"):
    for file in files:
        if file.endswith('.wav'):
            audioFiles.append(os.path.join(subdir, file));

print len(audioFiles)

yarp.Network.init()

rf = yarp.ResourceFinder()
rf.setVerbose(True);
rf.setDefaultContext("myContext");
rf.setDefaultConfigFile("default.ini");

p = yarp.BufferedPortBottle()
p.open("/recognizeresult");

yarp.Network.connect("/speech", "/recognizeresult");

index = 1;

playAudio(audioFiles[index], audioFiles[index]);

#playAudio("../pnnc-v2/speakers/PNM080/audio/PNM080_01-01.wav", "../pnnc-v2/speakers/NCF011/audio/NCF011_01-02.wav");
#playAudio("../pnnc-v2/speakers/NCF011/audio/NCF011_01-02.wav", "../pnnc-v2/speakers/NCF011/audio/NCF011_01-02.wav");

while True:
     speech = p.read(False);

     if speech:
         file = open("../pnnc-v2/transcripts/" + audioFiles[index][-9:-3] + "txt", 'r');
         correct = file.read();
         correct = correct.replace(",","").replace(".","").lower()

         file.close()



         print "RESULT: " + speech.toString()+ ", CORRECT: " + correct + ", WER: " + str(wer(correct, speech.toString()));

         index += 1;
         #playAudio(audioFiles[index], audioFiles[index]);
         playAudio(audioFiles[randint(0, len(audioFiles))], audioFiles[index]);