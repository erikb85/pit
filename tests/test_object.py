# -*- coding: utf-8 -*-
#
# Copyright 2013, Erik Bernoth <erik.bernoth@gmail.com

import nose.tools as nt

import pit.plumbing as plumbing

def test_add_file():
    """ create correct string for new Object
    """
    # set up
    txt = "test text"
    expected_out = "blob 9\x00" + txt
    sut = plumbing.Object(txt)
    # exec
    out = str(sut)
    # assert
    nt.eq_(expected_out, out)

def test_compare_objs():
    """ create 2 equal objects and check the comparator
    """
    # set up + exec
    sut1 = plumbing.Object()
    sut2 = plumbing.Object()
    # assert
    nt.ok_(sut1 == sut2)
