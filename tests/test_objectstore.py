# -*- coding: utf-8 -*-
#
# Copyright 2013, Erik Bernoth <erik.bernoth@gmail.com

import nose.tools as nt

import pit.plumbing as plumbing

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

@nt.raises(IOError)
def test_reinit():
    """ add a file and check if re_init really creates new Store
    """
    # set up
    sut = plumbing.ObjectStore(".just_for_testing")
    content = plumbing.Object("thecontent")
    # exec
    sut.store(content)
    sut.re_init()
    out = sut.get(content.key)
