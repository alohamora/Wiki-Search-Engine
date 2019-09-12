import os
import re
import json
import sys
import signal
import bisect
import timeit
import random
from math import floor, log
from collections import Counter, defaultdict
from index import DocHandler


class SearchEngine:
    def __init__(self, indexFolder, breakWords, npages, titlePageLength):
        self.indexFolder = indexFolder
        self.breakWords = breakWords
        self.docHandler = DocHandler()
        self.titlePageLength = titlePageLength
        self.npages = float(npages)
        self.fields = {
            "t" : 1.0,
            "b" : 0.25,
            "i" : 0.2,
            "c" : 0.1,
            "r" : 0.05,
            "l" : 0.05
        }

    def getSearchResults(self, parsedQuery):
        documentDict = defaultdict(list)
        wordFields = defaultdict(list)
        if parsedQuery["type"] == 2:
            for word in parsedQuery["document"]:
                documentDict[bisect.bisect_left(self.breakWords, word)].append(word)
                wordFields[word].extend(list(self.fields.keys()))
        else:
            for key in parsedQuery:
                if key != "type":
                    for word in parsedQuery[key]:
                        documentDict[bisect.bisect_left(self.breakWords, word)].append(word)
                        wordFields[word].append(key[0])
 
        invertedIndex = self.getPostingsList(documentDict)
        searchResults = self.pageRank(wordFields, invertedIndex)
        return searchResults

    def getPostingsList(self, documentDict):
        invertedIndex = defaultdict(list)
        for doc in documentDict.keys():
            wordOffset = {}
            with open(os.path.join(self.indexFolder, "wordOffset{}.txt".format(doc))) as fp:
                wordOffset = json.load(fp)
            with open(os.path.join(self.indexFolder, "mergedIndex{}.txt".format(doc))) as fp:
                for word in documentDict[doc]:
                    if word in wordOffset:
                        fp.seek(wordOffset[word], 0)
                        postingList = fp.readline()
                        invertedIndex[word] = postingList[:-1].split(",")
        return invertedIndex

    def pageRank(self, wordFields, invertedIndex):
        docRanking = defaultdict(float)
        for word in invertedIndex:
            postingList = invertedIndex[word]
            idf = log(self.npages / float(len(postingList)))
            for x in postingList:
                x = x.strip(" '")
                docId = re.split("b|t|r|c|l|i", x)[0]
                docScore = 0.0
                field = x[len(docId)]
                score = ""
                for char in x[len(docId)+1:]:
                    if char in self.fields:
                        if field in wordFields[word]:
                            docScore += self.fields[field] * (1.0 + log(float(score)))
                        score = ""
                        field = char
                    else:
                        score += char
                if field in wordFields[word]:
                    docScore += self.fields[field] * (1.0 + log(float(score)))
                docRanking[docId] += docScore * idf
        sortedDocs = sorted(docRanking.items(), key = lambda kv: kv[1], reverse = True)
        return self.getTitles([int(x[0]) for x in sortedDocs[:10]])

    def getTitles(self, docIds):
        titleDocs = defaultdict(list)
        titles = {}
        for doc in docIds:
            fileNo = floor(doc / self.titlePageLength)
            titleDocs[fileNo].append(doc)
        for fileNo in titleDocs:
            with open(os.path.join(self.indexFolder, "title{}.txt".format(fileNo)), "r") as fp:
                for i in range(1, self.titlePageLength + 1):
                    line = fp.readline()
                    ind = (i + (fileNo*self.titlePageLength))
                    if ind in titleDocs[fileNo]:
                        titles[ind] = line[len(str(ind))+1:-1]
        results = []
        for doc in docIds:
            results.append(titles[doc])
        return results

    def parseQuery(self, query):
        parsedQuery = {}
        if re.match(r"title:|body:|infobox:|category:|ref|link:", query):
            parsedObjects = query.split(":")
            prevType = parsedObjects[0]
            for ind in range(1, len(parsedObjects)):
                parsedText = parsedObjects[ind].split()
                queryText = parsedText[:-1] if ind != (len(parsedObjects) - 1) else parsedText
                processedText = self.docHandler.processRawText(" ".join(queryText))
                parsedQuery[prevType] = processedText
                prevType = parsedText[-1]
            parsedQuery["type"] = 1
        else:
            parsedQuery["document"] = self.docHandler.processRawText(query)
            parsedQuery["type"] = 2
        return parsedQuery

def signalHandler(signalNumber, frame):
    print("")
    sys.exit("----- Exiting Search engine -----")

def search(indexFolder):
    signal.signal(signal.SIGINT, signalHandler)
    breakWords = None
    with open(os.path.join(indexFolder, "breakWords.txt")) as fp:
        breakWords = [word[:-1] for word in fp.readlines()]
    searchEngine = SearchEngine(indexFolder, breakWords, 19567269, 20000)
    while(True):
        query = input("Type in your query: ")
        start_time = timeit.default_timer()
        parsedQuery = searchEngine.parseQuery(query.lower())
        searchResults = searchEngine.getSearchResults(parsedQuery)
        for result in searchResults:
            print(result)
        print("-----Response time: {}-----".format(timeit.default_timer() - start_time))

if __name__ == "__main__":
    search(sys.argv[1])
