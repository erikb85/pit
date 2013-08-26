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

    TYPES = ("data", "listing")

    def __init__(self, content="", type_="data"):
        self.type_ = type_
        self.content = content

    def __repr__(self):
        return "{} {}\x00{}".format(self.type_, self.size, self.content)

    def __str__(self):
        return repr(self).sub("\x00","\n")

    @property
    def size(self):
        return len(self.content)

    @property
    def binary(self):
        return zlib.compress(repr(self))

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


class Listing(Object):

    def __init__(self):
        self.type_ = "listing"
        self.entries = {}

    @propperty
    def content(self):
        return str(self)

    def add_entry(self, name, obj):
        self.entries[name] = obj

    def remove_entry(self, name):
        del self.entries[name]

    def walk(self):
        # like os.walk, consider that every object could be a Listing itself
        # TODO
        pass


class ObjectStore(object):

    def __init__(self, pit_dir=".pit", obj_dir="obj", index="INDEX"):
        self.pit_dir = pit_dir + "/"
        self.obj_dir = self.pit_dir + obj_dir + "/"
        self.index_dir = self.pit_dir + "/" + index

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

    def __init__(self, objstore=None):
        self.objstore = objstore if objstore else ObjectStore()

    @property
    def yield_files(self):
        for d, _, fs in os.walk(self.objstore.location, topdown=False):
            for f in fs:
                yield os.path.relpath(os.path.join(d, f),
                        self.objstore.location)

    def has(self, file_path):
        relpath = os.path.relpath(file_path, self.objstore.location)
        for f in self.yield_files:
            if relpath == f:
                return True
        return False

    def get_content(self, file_path):
        with open(file_path, "r") as f:
            return f.read()


class StagingArea(object):

    line_format = "{mode} {key} {version}    {path}"

    def __init__(self, workspace=None):
        self.workspace = workspace if workspace else Workspace()
        self.objstore = self.workspace.objstore
        self.content = {}

    def relpath(self, file_path):
        return self.objstore.relpath(file_path)

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

    def add_object(self, relpath, obj):
        self.objstore.store(obj)
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
        rel_path = os.path.relpath(file_path, self.objstore.location)
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
