import json


class Convert:
    def __init__(self, file):
        self.file = file
        with open(file, 'r', encoding='utf-8') as f:
            self.js = json.load(f)

    def movie2company(self):
        pass

    def movie2actor(self):
        pass
