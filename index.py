import re
import copy
import json
import os
import xml.sax
import Stemmer
import sys
from math import ceil
from multiprocessing import Process
from collections import defaultdict
from nltk.corpus import stopwords


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
            self.pageTitleMapping[self.pages] = self.title
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
            print("[wiki-engine-indexer]: Epoch {0} completed...{1} pages indexed".format(ceil(self.pages / self.pageBreakLimit), self.pages))
            self.indexerProcess = Indexer(ceil(self.pages / self.pageBreakLimit), copy.deepcopy(self.xmlData), self.indexFolder, copy.deepcopy(self.pageTitleMapping))
            self.xmlData = []
            self.pageTitleMapping = {}
            self.indexerProcess.start()

    def endProcessing(self):
        self.createIndexerProcess()
        self.indexerProcess.join()
        print("[wiki-engine-indexer]: Finished indexing data")
        print("[wiki-engine-indexer]: Total pages indexed - {}".format(self.pages))

class DocHandler:
    def __init__(self):
        self.stemmer = Stemmer.Stemmer("english")
        self.stopWords = set(stopwords.words("english"))

    def tokenize(self, data):
        data = data.encode("ascii", errors="ignore").decode()
        data = re.sub(
            r"http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\(\), ]|(?:%[0-9a-fA-F][0-9a-fA-F]))+",
            r" ",
            data,
        )  # removing urls
        data = re.sub(
            r"&nbsp;|&lt;|&gt;|&amp;|&quot;|&apos;", r" ", data
        )  # removing html entities
        data = re.sub(
            r"\—|\%|\$|\'|\||\.|\*|\[|\]|\:|\;|\,|\{|\}|\(|\)|\=|\+|\-|\_|\#|\!|\`|\"|\?|\/|\>|\<|\&|\\|\u2013|\n",
            r" ",
            data,
        )  # removing special characters
        return re.split("\s+", data)

    def removeStopWords(self, data):
        return [w for w in data if w not in self.stopWords]

    def stem(self, data):
        return self.stemmer.stemWords(data)

    def processPage(self, title, text):
        text = text.lower()
        data = text.split("==references==")
        if len(data) == 1:
            references = []
            links = []
            categories = []
        else:
            references = self.extractReferences(data[1])
            links = self.extractExternalLinks(data[1])
            categories = self.extractCategories(data[1])
        info = self.extractInfobox(data[0])
        body = self.extractBody(data[0])
        title = self.extractTitle(title.lower())
        return (title, body, info, categories, links, references)

    def processRawText(self, text):
        data = self.tokenize(text)
        data = self.removeStopWords(data)
        data = self.stem(data)
        return data

    def extractTitle(self, text):
        return self.processRawText(text)

    def extractBody(self, text):
        data = re.sub(r"\{\{.*\}\}", r" ", text)
        return self.processRawText(data)

    def extractInfobox(self, text):
        data = text.split("\n")
        infoData = ""
        infoBoxStarted = False
        for line in data:
            if re.match(r"\{\{infobox", line):
                infoBoxStarted = True
                infoData += " " + re.sub(r"\{\{infobox(.*)", r"\1", line)
            elif infoBoxStarted:
                infoData += " " + line
                if line == "}}":
                    infoBoxStarted = False
        return self.processRawText(infoData)

    def extractReferences(self, text):
        data = text.split("\n")
        refs = []
        for line in data:
            if re.search(r"<ref", line):
                refs.append(re.sub(r".*title[\ ]*=[\ ]*([^\|]*).*", r"\1", line))
        return self.processRawText(" ".join(refs))

    def extractCategories(self, text):
        data = text.split("\n")
        categories = []
        for line in data:
            if re.match(r"\[\[category", line):
                categories.append(re.sub(r"\[\[category:(.*)\]\]", r"\1", line))
        return self.processRawText(" ".join(categories))

    def extractExternalLinks(self, text):
        data = text.split("\n")
        links = []
        for line in data:
            if re.match(r"\*[\ ]*\[", line):
                links.append(line)
        return self.processRawText(" ".join(links))

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
        with open(os.path.join(self.indexFolder, "index{}.txt".format(self.offset)), "w") as fp:
            fp.write(json.dumps(self.invertedIndex))

        with open(os.path.join(self.indexFolder, "title{}.txt".format(self.offset)), "w") as fp:
            fp.write(json.dumps(self.pageTitleMapping))

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


if __name__ == "__main__":
    preProcessAndIndex(sys.argv[1], sys.argv[2])
