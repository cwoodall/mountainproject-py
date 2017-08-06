#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""Tests for `mountainproject` package."""


import unittest

from mountainproject import Api


class TestMountainproject(unittest.TestCase):
    """Tests for `mountainproject` package."""

    def setUp(self):
        """Set up test fixtures, if any."""
        with open("key.ignore") as keyfile:
            self.key = keyfile.read()

    def tearDown(self):
        """Tear down test fixtures, if any."""

    def test_000_run_search(self):
        """Test something."""
        a = Api(self.key)
        res = a.search_routes("Dick Williams The Yellow Wall")
        assert(res["success"] == 1)
        assert(len(res["routes"]) > 0)
