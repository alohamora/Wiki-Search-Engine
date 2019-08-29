import re
import json
import sys
from collections import Counter
from index import DocHandler

class SearchEngine:
    def __init__(self, inverted_index, pageTitleMapping):
        self.inverted_index = inverted_index
        self.pageTitleMapping = pageTitleMapping
        self.docs_id = []

    def searchQuery(self, query):
        parsed_query = self.parseQuery(query.lower())
        docHandler = DocHandler()
        for key, val in parsed_query.items():
            self.add_documents(key, docHandler.processRawText(" ".join(val)))
        documentSet = Counter(self.docs_id)
        searchResultIds = sorted(documentSet.items(), key = lambda x:x[1], reverse = True)
        searchResultsTitles = []
        for docId, count in searchResultIds[:10]:
            searchResultsTitles.append(self.pageTitleMapping[docId])
        self.docs_id.clear()
        return searchResultsTitles

    def add_documents(self, __type, queryWords):
        for word in queryWords:
            if word in self.inverted_index:
                for x in self.inverted_index[word]:
                    if __type != "document" and __type[0] in x:
                        self.docs_id.append(re.split('b|t|r|c|l|i', x)[0])
                    elif __type == "document":
                        self.docs_id.append(re.split('b|t|r|c|l|i', x)[0])

    def parseQuery(self, query):
        parsedQuery = {}
        if re.match(r'title|body|infobox|category|ref|link:', query):
            parsedObjects = query.split(":")
            prevType = parsedObjects[0]
            for ind in range(1, len(parsedObjects)):
                parsedText = [word for word in parsedObjects[ind].split(" ") if word != ""]
                parsedQuery[prevType] = parsedText[:-1] if ind != (len(parsedObjects) - 1) else parsedText
                prevType = parsedText[-1]
            __type = 1
        else:
            parsedQuery["document"] = [word for word in query.split(" ") if word != ""]
        return parsedQuery

def read_file(testfile):
    with open(testfile, 'r') as file:
        queries = file.readlines()
    return queries

def write_file(outputs, path_to_output):
    with open(path_to_output, 'w') as file:
        for output in outputs:
            for line in output:
                file.write(line.strip() + '\n')
            file.write('\n')

def search(indexFolder, queryFile, outputFile):
    inverted_index = None
    pageTitleMapping = None
    searchResults = []
    with open(indexFolder + "/" + "inverted_index.txt", "r") as fp:
        inverted_index = json.load(fp)
    with open(indexFolder + "/" + "title.txt", "r") as fp:
        pageTitleMapping = json.load(fp)
    engine = SearchEngine(inverted_index, pageTitleMapping)
    for query in read_file(queryFile):
        searchResults.append(engine.searchQuery(query))
    write_file(searchResults, outputFile)

if __name__ == "__main__":
    search(sys.argv[1], sys.argv[2], sys.argv[3])