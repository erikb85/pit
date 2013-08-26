# -*- coding: utf-8 -*-
#
# Copyright 2013, Erik Bernoth <erik.bernoth@gmail.com>

import shutil
import sha
import zlib
import os


class ObjSizeException(Exception):
    pass

class ObjCheckException(Exception):
    pass

class OutsideStoreRangeException(Exception):
    pass

class FileNotInWorkspaceException(Exception):
    pass

class NoVersionException(Exception):
    pass

class Object(object):

    modes = {
            "blob" : "10644",
            "tree" : "040000",
            "staging" : "040000",
            "commit" : "160000"
    }

    def __init__(self, content="", type_="blob"):
        self.type_ = type_
        self.content = content

    def __str__(self):
        return "{} {}\x00{}".format(self.type_, len(self.content), self.content)

    @property
    def mode(self):
        return self.modes[self.type_]

    @property
    def binary(self):
        return zlib.compress(str(self))

    @property
    def key(self):
        return sha.new(self.binary).hexdigest()

    @classmethod
    def from_binary(cls, binary, key):
        if sha.new(binary).hexdigest() != key:
            raise ObjCheckException()
        txt = zlib.decompress(binary)
        meta, content = txt.split("\x00")
        type_, size = meta.split(" ")
        size = int(size)
        if size != len(content):
            raise ObjSizeException("'{}' != len('{}')".format(size, content))
        return cls(content, type_)

    def __eq__(self, other):
        return self.key == other.key

    def __ne__(self, other):
        return not self.__eq__(other)


class ObjectStore(object):

    def __init__(self, pit_dir=".pit", obj_dir="obj", stage="StageArea"):
        self.pit_dir = pit_dir + "/"
        self.obj_dir = self.pit_dir + obj_dir + "/"
        self.stage = self.pit_dir + "/" + stage

    def init(self):
        shutil.rmtree(self.pit_dir, ignore_errors=True)
        os.mkdir(self.pit_dir)
        os.mkdir(self.obj_dir)
        with open(self.index_dir, "a") as f: pass

    def _read(self, name):
        with open(name, "rb") as f:
            return f.read()

    def _write(self, name, txt):
        """
        """
        # mkdir -p to make sure the dirs exist
        dir_ = os.path.dirname(name)
        if dir_:
            try:
                os.makedirs(dir_)
            except OSError:
                pass
        with open(name, "w") as f:
            return f.write(txt)

    def _key_to_path(self, key):
        return key[:2] + "/" + key[2:]

    def store(self, obj):
        self._write(self.obj_dir + self._key_to_path(obj.key), obj.binary)
        return self

    def get(self, key):
        return Object.from_binary(
                self._read(self.obj_dir + self._key_to_path(key)), key)

    @property
    def location(self):
        try:
            return self._location
        except AttributeError:
            self._location = self.get_location()
            return self._location

    def get_location(self, path="."):
        path = os.path.abspath(path)
        if self.pit_dir[:-1] in os.listdir(path):
            return path
        elif path == "/":
            raise OutsideStoreRangeException()
        else:
            return self.get_location(os.path.dirname(path))


class Workspace(object):

    def __init__(self, objectstore=None):
        self.objectstore = objectstore if objectstore else ObjectStore()

    @property
    def yield_files(self):
        for d, _, fs in os.walk(self.objectstore.location, topdown=False):
            for f in fs:
                yield os.path.relpath(os.path.join(d, f),
                        self.objectstore.location)

    def has(self, file_path):
        relpath = os.path.relpath(file_path, self.objectstore.location)
        for f in self.yield_files:
            if relpath == f:
                return True
        return False

    def get_content(self, file_path):
        with open(file_path, "r") as f:
            return f.read()


class StagingArea(object):

    line_format = "{mode} {key} {version}    {path}"
    line_regex = re.compile("(?P<mode>\w+)\s(?P<key>\w+)\s(?<version>\w+)\s{4}(?P<path>\w+)")

    @classmethod
    def from_object(cls, obj, workspace=None):
        txt = obj.content
        return cls.from_txt(cls, txt, workspace)

    @classmethod
    def from_txt(cls, txt, workspace=None):
        self = StagingArea(workspace)
        for line in txt.split("\n"):
            content = cls.line_regex.match(line).groupdict()
            obj = self.objectstore.get(content["key"])
            self.add_object(content["path"], obj, stored=True)
        return self

    def __init__(self, workspace=None):
        self.workspace = workspace if workspace else Workspace()
        self.objectstore = self.workspace.objectstore
        self.content = {}

    def relpath(self, file_path):
        return self.objectstore.relpath(file_path)

    def in_workspace(self, path):
        return self.workspace.has(path)

    def get_version(self, file_path):
        obj = Object(self.workspace.get_content(file_path))
        try:
            for i, version in enumerate(self.content[file_path]):
                if obj.key == version.key:
                    return i, version
        except KeyError:
            # better raise our own exception instead of KeyError
            pass
        raise NoVersionException(file_path)

    def add_object(self, relpath, obj, stored=False):
        if not stored:
            self.objectstore.store(obj)
        try:
            self.content[relpath].append(obj)
            return len(self.content[relpath])-1, obj
        except KeyError:
            self.content[relpath] = [obj]
            return 0, obj

    def add_file(self, file_path):
        relpath = self.relpath(file_path)
        if not self.in_workspace(relpath):
            raise FileNotInWorkspaceException(relpath)
        try:
            return self.get_version(relpath)
        except NoVersionException:
            return self.add_object(
                    relpath, Object(self.workspace.get_content(relpath)))

    def remove_file(self, file_path):
        rel_path = os.path.relpath(file_path, self.objectstore.location)
        del self.content[rel_path]
        return self

    def __str__(self):
        return "\n".join([self.line_format.format(
                    mode=obj.mode,
                    key=obj.key,
                    version= str(ver),
                    path=path
            ) for path, versions in self.content.items()
              for ver, obj in enumerate(versions)])

    def store(self, ref_file=None):
        ref_file = ref_file or self.objectstore.stage
        obj = Object(str(self), type_="staging")
        self.objectstore.store(obj)
        return obj.key


class Register(Object):
    """ what was once called a "Tree" although it was actually a DAG
    """

    line_format = "{mode} {type_} {key}    {name}"

    def __init__(self):
        self._objects = {}
        self.type_ = "tree"

    def add(self, name, obj):
        self._objects[name] = obj
        return self

    def remove(self, name):
        if name in self._objects:
            del self._objects[name]

    def __str__(self):
        return "\n".join([self.line_format.format(
                    mode=obj.mode,
                    type_=obj.type_
                    key=obj.key,
                    name=name
            ) for name, obj in self._objects.items()])


class Snapshot(object):
    """ instead of commit
    """
    pass
