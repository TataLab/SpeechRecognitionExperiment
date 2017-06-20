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

def mergeChunk(bufferA, bufferB):
    res = [''] * len(bufferA) * 2
    res[::4]  = bufferA[::2]
    res[1::4] = bufferA[1::2]
    res[2::4] = bufferB[::2]
    res[3::4] = bufferB[1::2]
    return ''.join(res)

def mergeChunks(list):
    if len(list) == 1:
        return list[0];

    res = [];

    for i in range(len(list)-1):
        if i%2 == 1:
            continue;
        res.append(mergeChunk(list[i], list[i+1]));


    return mergeChunks(res)

def check(list):
    for i in range(len(list)-1):
        if not list[i] or not list[i+1]:
            return False;

        if len(list[i]) != len(list[i+1]):
            return False;

    return True;


def playAudio(fileLocs, numTalkers):

    #open a wav format music
    files = [];

    for fileLoc in fileLocs:
        files.append(wave.open(fileLoc, "rb"));

    #instantiate PyAudio
    p = pyaudio.PyAudio();
    #open stream
    stream = p.open(format = p.get_format_from_width(files[0].getsampwidth()),
                    channels = numTalkers,
                    rate = files[0].getframerate(),
                    output = True);

    #read data
    data = [];

    for i in range(len(fileLocs)):
        data.append(files[i].readframes(chunk));

    ind=0;
    #play stream
    while check(data):
        ind+=1;
        stream.write(mergeChunks(data));

        for i in range(len(fileLocs)):
            data[i] = files[i].readframes(chunk);

        if ind>10000:
            break;


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

numChannels = 2;

audioList = [];

for i in range(numChannels-1):
 audioList.append(audioFiles[randint(0, len(audioFiles))]);

audioList.append(audioFiles[index]);

playAudio(audioList, numChannels);

while True:
     speech = p.read(False);

     if speech:
         file = open("../pnnc-v2/transcripts/" + audioFiles[index][-9:-3] + "txt", 'r');
         correct = file.read();
         correct = correct.replace(",","").replace(".","").lower()

         file.close()

         print "INDEX: " + str(index) + ", RESULT: " + speech.toString()+ ", CORRECT: " + correct + ", WER: " + str(wer(correct, speech.toString()));

         index += 1;

         audioList = [];

         for i in range(numChannels-1):
             audioList.append(audioFiles[randint(0, len(audioFiles))]);

         audioList.append(audioFiles[index]);

         playAudio(audioList, numChannels);
