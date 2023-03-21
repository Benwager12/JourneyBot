import json
import os.path


class File:
    def __init__(self, filename: str):
        self.filename = filename

    def fetch_file(self):
        return open(self.filename) if os.path.isfile(self.filename) else None

    def __iter__(self):
        return FileIterator(self)

    def add_line(self, line: str):
        with open(self.filename) as file:
            file.write('\n'.join(file.readlines()) + f"\n{line}")


class FileIterator:
    def __init__(self, file: File):
        with open(file.filename) as f:
            self.lines = f.readlines()
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
        f = super().fetch_file()
        self.data = json.loads(f.read() if f is not None else "{}")
        if f:
            f.close()

    def fetch_file(self):
        super().fetch_file()
        f = super().fetch_file()
        self.data = json.load(f)
        f.close()


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
        with open(self.filename, 'w') as file:
            json.dump(self.data, file, indent=4)

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
