# -*- coding: utf-8 -*-
#
# Copyright 2013, Erik Bernoth <erik.bernoth@gmail.com>

import nose.tools as nt

import pit.plumbing as plumbing

def test_add_file():
    """ test_staging_area: add a file
    """
    # set up
    file_name = ".test/file"
    expected_version = 0
    sut = plumbing.StagingArea(WSStub())
    # exec
    version, _ = sut.add_file(file_name)
    # assert
    nt.eq_(expected_version, version)

def test_add_more_files():
    """ test_staging_area: add more files
    """
    # set up
    files = [".test/file1", ".test/file2", ".test/file3"]
    expected_version = 0
    sut = plumbing.StagingArea(WSStub())
    # exec
    map(sut.add_file, files)
    # assert
    for f in files:
        nt.eq_(expected_version, sut.get_version(f)[0])

def test_two_versions():
    """ test_staging_area: add a file in different versions
    """
    # set up
    file_name = ".test/file"
    file_contents = ["a", "b"]
    stub = WSStub()
    sut = plumbing.StagingArea(stub)
    # exec
    for c in file_contents:
        stub.content = c
        sut.add_file(file_name)
    # assert
    for i, c in enumerate(file_contents):
        stub.content = c
        nt.eq_(i, sut.get_version(file_name)[0])

def test_remove():
    """ test_staging_area: add and remove a file
    """
    # set up
    file_name = ".test/file"
    sut = plumbing.StagingArea(WSStub())
    # exec
    sut.add_file(file_name)
    sut.remove_file(file_name)
    # assert
    nt.eq_("", str(sut))


class WSStub(object):

    def __init__(self, has=True, location=".", content=None):
        self.objstore = self
        self._has = has
        self.location = location
        self.content = content

    def has(self, stuff):
        return self._has

    def get_content(self, path):
        return self.content if self.content else path

    def store(self, obj):
        return self

    def relpath(self, path):
        return path
