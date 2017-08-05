# -*- coding: utf-8 -*-
from .grouper import grouper
import requests
import json
import urllib
from bs4 import BeautifulSoup
import multiprocessing
from multiprocessing import Process, Pipe
from itertools import izip


def spawn(f):
    def fun(pipe, x):
        pipe.send(f(x))
        pipe.close()
    return fun


def parmap(f, X):
    pipe = [Pipe() for x in X]
    proc = [Process(target=spawn(f), args=(c, x))
            for x, (p, c) in izip(X, pipe)]
    [p.start() for p in proc]
    [p.join() for p in proc]
    return [p.recv() for (p, c) in pipe]


SEARCH_URL = "https://www.mountainproject.com/ajax/public/search/results/category"


class MountainProjectData(object):

    def __init__(self, key, url="https://www.mountainproject.com/data", root_url="https://www.mountainproject.com"):
        self.key = key
        self.url = url
        self.root_url = root_url

    def getRoutes(self, routeIds):
        routes = None
        for route_set in grouper(100, routeIds):
            route_set = filter(None, route_set)
            response = requests.get(
                self.url, params={"action": "getRoutes", "key": self.key, "routeIds": ",".join(route_set)})
            if response.ok:
                content = json.loads(response.content)
                if routes:
                    routes["routes"] += content["routes"]
                else:
                    routes = content
            else:
                return None
        return routes

    def _getFAFromRouteHTML(self, soup):
        try:
            return soup.find("td", text=u"FA:\xA0").nextSibling.text
        except:
            return ""

    def _getParentAreaLink(self, soup):
        return self.root_url + soup.find(
            "img", {"src": "https://cdn.apstatic.com/mp-img/up.gif"}).parent.get('href')

    def _getGPSCoordinatesFromArea(self, soup):
        gps_coordinates = []
        location_tag = soup.find('td', text=u"Location: ")
        if location_tag:
            # Parse the location tag in the fomat of Lat, Long View
            # Map (Incorrect?). We just want the Lat and
            # Long
            gps_coordinates = location_tag.nextSibling.text.split("View Map")[
                0].strip().split(", ")

        return gps_coordinates

    def _getNearestGPSCoordinateFromRoute(self, soup):
        coordinates = []

        while not coordinates:
            response = requests.get(self._getParentAreaLink(soup))
            if response.ok:
                soup = BeautifulSoup(response.content, 'html.parser')
                coordinates = self._getGPSCoordinatesFromArea(soup)
            else:
                raise Exception("Network Connection Failed")

        return coordinates

    def enrichRoute(self, route):
        # First lets find the FA informatio
        response = requests.get(route["url"])
        if response.ok:
            soup = BeautifulSoup(response.content, 'html.parser')
            route["fa"] = self._getFAFromRouteHTML(soup)
            route["gps"] = self._getNearestGPSCoordinateFromRoute(soup)
        return route

    def enrichRoutes(self, routes):
        # Enrich all of the routes in parallel
        routes["routes"] = parmap(self.enrichRoute, routes["routes"])
        return routes

    def getToDos(self, startPos, userId):
        response = requests.get(
            self.url, params={"action": "getToDos", "key": self.key, "startPos": startPos, "userId": userId})
        if response.ok:
            return json.loads(response.content)
        else:
            return None

    def getToDosByEmail(self, startPos, email):
        response = requests.get(
            self.url, params={"action": "getToDos", "key": self.key, "startPos": startPos, "email": email})
        if response.ok:
            return json.loads(response.content)
        else:
            return None

    def getTicks(self, startPos, userId):
        response = requests.get(
            self.url, params={"action": "getTicks", "key": self.key, "startPos": startPos, "userId": userId})
        if response.ok:
            return json.loads(response.content)
        else:
            return None

    def getTicksByEmail(self, startPos, email):
        response = requests.get(
            self.url, params={"action": "getTicks", "key": self.key, "startPos": startPos, "email": email})
        if response.ok:
            return json.loads(response.content)
        else:
            return None

    def getUser(self, userId):
        response = requests.get(
            self.url, params={"action": "getUser", "key": self.key, "userId": userId})
        if response.ok:
            return json.loads(response.content)
        else:
            return None

    def getUserByEmail(self, email):
        response = requests.get(
            self.url, params={"action": "getUser", "key": self.key, "email": email})
        if response.ok:
            return json.loads(response.content)
        else:
            return None

    def search(self, query, category, offset, size):
        payload = {"q": urllib.quote_plus(
            query), "c": category, "o": offset, "s": size}
        r = requests.get(SEARCH_URL, params=payload)
        if r.ok:
            return json.loads(r.content)
        else:
            raise Exception("Search Failed")

    def search_routes(self, query, offset=0, size=100):
        return self.search(query, "Routes", offset, size)

    def search_routes_for_ids(self, query, offset=0, size=100):
        results = self.search_routes(query, offset, size)
        route_ids = []
        if results["results"]:
            for route_html in results["results"]["Routes"]:
                soup = BeautifulSoup(route_html, 'html.parser')
                link = soup.tr.td.strong.a
                route_ids.append(link.get('href').split("?")[0].split('/')[2])

        return route_ids

    def isearch_all_routes_for_ids(self, query):
        offset = 0
        new_ids = self.search_routes_for_ids(query, offset)
        while len(new_ids) != 0:
            offset += len(new_ids)
            for id in new_ids:
                yield id
            new_ids = self.search_routes_for_ids(query, offset)

    def search_all_routes_for_ids(self, query):
        return list(self.isearch_all_routes_for_ids(query))
