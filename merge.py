import os
import json
from math import ceil
from collections import defaultdict


class MergeIndex:
    def __init__(self, indexFolder, fileCount):
        self.fileCount = fileCount
        self.filePointers = []
        self.words = set()
        self.fileOpen = [True for i in range(fileCount)]
        self.postingsList = defaultdict(list)
        self.filesList = defaultdict(list)
        self.wordIndex = {}
        self.nextFiles = range(fileCount)
        self.indexFolder = indexFolder
        self.fileLines = []
        self.count = 0
        self.pageBreakLimit = 100000

    def mergeIndex(self):
        for count in range(self.fileCount):
            self.filePointers.append(
                open(os.path.join(self.indexFolder, "index{}.txt".format(count)), "r")
            )
        while any(self.fileOpen):
            self.pushWords()
            self.popWord()
            if self.count % self.pageBreakLimit == 0:
                self.writeToFile()
                print(
                    "[wiki-engine-indexer]: Epoch {0} completed...{1} words merged".format(
                        ceil(self.count / self.pageBreakLimit) - 1, self.count
                    )
                )

        if self.fileLines:
            self.writeToFile()
            print(
                "[wiki-engine-indexer]: Merge process finished...{} words merged".format(
                    self.count
                )
            )

    def pushWords(self):
        for fileInd in self.nextFiles:
            line = self.filePointers[fileInd].readline()
            if line == "":
                self.fileOpen[fileInd] = False
                self.filePointers[fileInd].close()
            else:
                word, postingListString = line.split(":")
                self.postingsList[word].append(postingListString[:-1].strip("[]"))
                self.filesList[word].append(fileInd)
                self.words.add(word)

    def popWord(self):
        try:
            word = min(self.words)
            self.words.remove(word)
            self.nextFiles = self.filesList[word]
            self.fileLines.append(
                "{0}:{1}".format(word, ",".join(self.postingsList[word]))
            )
            self.filesList.pop(word)
            self.postingsList.pop(word)
            self.wordIndex[word] = len(self.fileLines) - 1
            self.count += 1
        except:
            pass

    def writeToFile(self):
        fileNo = ceil(self.count / self.pageBreakLimit) - 1
        with open(
            os.path.join(self.indexFolder, "mergedIndex{}.txt".format(fileNo)), "w"
        ) as fp:
            fp.write("\n".join(self.fileLines))
        with open(
            os.path.join(self.indexFolder, "wordOffset{}.txt".format(fileNo)), "w"
        ) as fp:
            fp.write(json.dumps(self.wordIndex))
        self.wordIndex = {}
        self.fileLines = []
