class TextStorage:
    def __init__(self):
        self.storage = dict()
    
    def get(self, key, language="en"):
        return self.storage[key][language]

    def set(self, **texts: dict):
        self.storage.update(texts)
