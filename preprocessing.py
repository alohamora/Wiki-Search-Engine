import re
import Stemmer
from nltk.corpus import stopwords


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
            r"\@|\~|\—|\%|\$|\'|\||\.|\*|\[|\]|\:|\;|\,|\{|\}|\(|\)|\=|\+|\-|\_|\#|\!|\`|\"|\?|\/|\>|\<|\&|\\|\u2013|\n",
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
        data = [word for word in self.tokenize(text) if word != ""]
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
