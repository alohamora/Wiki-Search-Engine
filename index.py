import copy
import os
import xml.sax
import sys
from math import ceil
from multiprocessing import Process
from collections import defaultdict
from preprocessing import DocHandler
from merge import MergeIndex


class ContentHandler(xml.sax.ContentHandler):
    def __init__(self, index_folder):
        super().__init__()
        self.tag = ""
        self.title = ""
        self.text = ""
        self.pages = 0
        self.indexerProcess = None
        self.indexFolder = index_folder
        self.xmlData = []
        self.pageTitleMapping = {}
        self.pageBreakLimit = int(20000)

    def startElement(self, name, attrs):
        self.tag = name
        if self.tag == "page":
            self.pages += 1

    def endElement(self, name):
        if name == "page":
            self.pageTitleMapping[self.pages] = self.title.strip(" ").strip("\n")
            self.xmlData.append((self.title, self.text, self.pages))
            self.resetFields()
            if self.pages % self.pageBreakLimit == 0:
                self.createIndexerProcess()

    def characters(self, content):
        if self.tag == "title" or self.tag == "text":
            previous = getattr(self, self.tag)
            setattr(self, self.tag, previous + content)

    def resetFields(self):
        self.title = ""
        self.text = ""

    def createIndexerProcess(self):
        if self.indexerProcess is not None:
            self.indexerProcess.join()

        if len(self.xmlData) > 0:
            print(
                "[wiki-engine-indexer]: Epoch {0} completed...{1} pages indexed".format(
                    ceil(self.pages / self.pageBreakLimit) - 1, self.pages
                )
            )
            self.indexerProcess = Indexer(
                ceil(self.pages / self.pageBreakLimit) - 1,
                copy.deepcopy(self.xmlData),
                self.indexFolder,
                copy.deepcopy(self.pageTitleMapping),
            )
            self.xmlData = []
            self.pageTitleMapping = {}
            self.indexerProcess.start()

    def endProcessing(self):
        self.createIndexerProcess()
        self.indexerProcess.join()
        print("[wiki-engine-indexer]: Finished indexing data")
        print("[wiki-engine-indexer]: Total pages indexed - {}".format(self.pages))


class Indexer(Process):
    WORD_ORDER = ["t", "b", "i", "c", "l", "r"]

    def __init__(self, offset, xmlData, indexFolder, pageTitleMapping):
        super().__init__()
        self.offset = offset
        self.xmlData = xmlData
        self.docHandler = DocHandler()
        self.indexFolder = indexFolder
        self.pageTitleMapping = pageTitleMapping
        self.invertedIndex = defaultdict(list)

    def run(self):
        for title, text, docInd in self.xmlData:
            parsedObjects = self.docHandler.processPage(title, text)
            self.createIndex(parsedObjects, docInd)
        with open(
            os.path.join(self.indexFolder, "index{}.txt".format(self.offset)), "w"
        ) as fp:
            fp.write(self.sortAndConvertDict(self.invertedIndex))

        with open(
            os.path.join(self.indexFolder, "title{}.txt".format(self.offset)), "w"
        ) as fp:
            fp.write(self.sortAndConvertDict(self.pageTitleMapping))

    def createIndex(self, parsedWords, docInd):
        words = defaultdict(int)
        parsedDicts = []
        for __type in parsedWords:
            parsedDicts.append(self.createDict(words, __type))

        for word in words.keys():
            indexString = str(docInd)
            for i in range(len(parsedDicts)):
                if parsedDicts[i][word]:
                    indexString += self.WORD_ORDER[i] + str(parsedDicts[i][word])
            self.invertedIndex[word].append(indexString)

    @staticmethod
    def sortAndConvertDict(dictionary):
        ret = ""
        for key in sorted(dictionary.keys()):
            ret += "{0}: {1}\n".format(key, dictionary[key])
        return ret

    @staticmethod
    def createDict(wordDict, bagOfWords):
        __typeDict = defaultdict(int)
        for word in bagOfWords:
            __typeDict[word] += 1
            wordDict[word] += 1
        return __typeDict


def preProcessAndIndex(data_filename, index_folder):
    parser = xml.sax.make_parser()
    parser.setFeature(xml.sax.handler.feature_namespaces, 0)
    handler = ContentHandler(index_folder)
    parser.setContentHandler(handler)
    parser.parse(data_filename)
    handler.endProcessing()
    print("------Initial Index files created, starting merge process------")
    merger = MergeIndex(index_folder, handler.pages, handler.pageBreakLimit)
    merger.mergeIndex()


if __name__ == "__main__":
    preProcessAndIndex(sys.argv[1], sys.argv[2])
