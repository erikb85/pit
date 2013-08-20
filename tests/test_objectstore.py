# -*- coding: utf-8 -*-
#
# Copyright 2013, Erik Bernoth <erik.bernoth@gmail.com

import shutil
import os

import nose.tools as nt

import pit.plumbing as plumbing

def clean_objectstore():
    shutil.rmtree(".just_for_testing", ignore_errors=True)
    shutil.rmtree(".hi", ignore_errors=True)

@nt.with_setup(None, clean_objectstore)
def test_add_file():
    """ add a file and check if it gets stored
    """
    # set up
    sut = plumbing.ObjectStore(".just_for_testing")
    content = plumbing.Object("thecontent")
    # exec
    sut.store(content)
    out = sut.get(content.key)
    # assert
    nt.eq_(content, out, "{} != {}".format(str(content), str(out)))

@nt.with_setup(None, clean_objectstore)
@nt.raises(IOError)
def test_reinit():
    """ test_objstore: add a file and check if init really creates new Store
    """
    # set up
    sut = plumbing.ObjectStore(".just_for_testing")
    content = plumbing.Object("thecontent")
    # exec
    sut.store(content)
    sut.init()
    out = sut.get(content.key)

@nt.with_setup(None, clean_objectstore)
def test_root():
    """ test_objstore: look up the root folder from deeper inside the workspace
    """
    # set up
    expected = os.path.abspath(".")
    sut = plumbing.ObjectStore(".just_for_testing")
    dirname = ".hi"
    # exec
    os.mkdir(dirname)
    sut.init()
    out = sut.get_location(dirname)
    # assert
    nt.ok_(expected, out)
