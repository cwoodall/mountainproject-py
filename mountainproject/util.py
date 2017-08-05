# -*- coding: utf-8 -*-
"""
"""
from itertools import izip_longest
from multiprocessing import Process, Pipe
from itertools import izip


def grouper(n, iterable, fillvalue=None):
    "grouper(3, 'ABCDEFG', 'x') --> ABC DEF Gxx"
    args = [iter(iterable)] * n
    return izip_longest(fillvalue=fillvalue, *args)


def spawn(f):
    """
    Spawn a function in its own Process
    """
    def fun(pipe, x):
        pipe.send(f(x))
        pipe.close()
    return fun

def parmap(f, X):
    """
    Map function f over inputs X in parallel
    """
    pipe = [Pipe() for x in X]
    proc = [Process(target=spawn(f), args=(c, x))
            for x, (p, c) in izip(X, pipe)]
    [p.start() for p in proc]
    [p.join() for p in proc]
    return [p.recv() for (p, c) in pipe]

