import os
from math import ceil


class MergeIndex:
    def __init__(self, indexFolder, pageCount, pageBreakLimit):
        self.fileCount = ceil(pageCount / pageBreakLimit)
        self.pages = pageCount
        self.pageBreakLimit = pageBreakLimit
        self.filePointers = []
        self.indexFolder = indexFolder

    def mergeIndex(self):
        for count in range(self.fileCount):
            self.filePointers.append(
                open(
                    os.path.join(self.indexFolder, "index{}.txt".format(self.offset)),
                    "r",
                )
            )

        return 0
