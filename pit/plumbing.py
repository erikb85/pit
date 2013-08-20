# -*- coding: utf-8 -*-
#
# Copyright 2013, Erik Bernoth <erik.bernoth@gmail.com

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

class Object(object):

    modes = {
            "blob" : "10644",
            "tree" : "040000",
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

    def __init__(self, pit_dir=".pit", obj_dir="obj", index="INDEX"):
        self.pit_dir = pit_dir + "/"
        self.obj_dir = self.pit_dir + obj_dir + "/"
        self.index_dir = self.pit_dir + "/" + index
        self.re_init()

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
            print d
            for f in fs:
                yield os.path.relpath(os.path.join(d, f),
                        self.objstore.location)

    def has(self, file_path):
        relpath = os.path.relpath(file_path, self.objstore.location)
        for f in self.yieldfiles:
            if relpath == f:
                return True
        return False
