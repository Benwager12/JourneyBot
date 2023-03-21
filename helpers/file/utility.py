import json


class File:
    def __init__(self, filename: str):
        self.filename = filename
        self.file = open(filename)

    def fetch_file(self):
        with open(self.filename) as file:
            self.file = file

    def __iter__(self):
        return FileIterator(self)

    def add_line(self, line: str):
        self.file.write('\n'.join(self.file.readlines()) + f"\n{line}")


class FileIterator:
    def __init__(self, file: File):
        self.lines = file.file.readlines()
        self.index = 0

    def __iter__(self):
        return self

    def __next__(self):
        if self.index >= len(self.lines):
            raise StopIteration
        else:
            self.index += 1
            return self.lines[self.index - 1]


class JsonFile(File):
    def __init__(self, filename: str):
        super().__init__(filename)
        self.data = json.load(self.file)

    def fetch_file(self):
        super().fetch_file()
        self.data = json.load(self.file)

    def get(self, key, default=None):
        if isinstance(self.data, list):
            return self.data[int(key)]
        return self.data.get(key, default)

    def __getitem__(self, item):
        return self.data.get(item, None)

    def __len__(self):
        return len(self.data)

    def __setitem__(self, key, value):
        self.data[key] = value

    def set(self, key, value):
        self.data[key] = value

    def save(self):
        json.dump(self.data, self.file, indent=4)

    def __iter__(self):
        return JsonFileIterator(self)


class JsonFileIterator:
    def __init__(self, json_file: JsonFile):
        self.json_file = json_file
        self.index = 0

    def __iter__(self):
        return self

    def __next__(self):
        if self.index >= len(self.json_file.data):
            raise StopIteration
        else:
            self.index += 1
            return self.json_file.data[self.index - 1]
