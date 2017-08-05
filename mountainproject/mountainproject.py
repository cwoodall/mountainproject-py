# -*- coding: utf-8 -*-
from .util import grouper, parmap
import requests
import json
import urllib
from bs4 import BeautifulSoup

class Api(object):
    """
    """
    ROOT_URL = "https://www.mountainproject.com"
    self.SEARCH_URL = self.ROOT_URL + "/ajax/public/search/results/category"
    DATA_URL = self.ROOT_URL + "/data"
    UP_AREA_IMG = "https://cdn.apstatic.com/mp-img/up.gif"

    def __init__(self, key):
        self.key = key

    def getRoutes(self, routeIds):
        """
        Get all route information for a given set of routeIds
        """
        routes = None
        for route_set in grouper(100, routeIds):
            route_set = filter(None, route_set)
            response = requests.get(
                self.DATA_URL, params={"action": "getRoutes", "key": self.key, "routeIds": ",".join(route_set)})
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
        """
        Extract the First Ascent information for the route.
        """
        try:
            return soup.find("td", text=u"FA:\xA0").nextSibling.text
        except:
            return ""

    def _getParentAreaLink(self, soup):
        """
        Look for a link with the UP_AREA_IMG to get the url to the parent
        """
        return self.ROOT_URL + soup.find(
            "img", {"src": self.UP_AREA_IMG}).parent.get('href')

    def _getGPSCoordinatesFromArea(self, soup):
        """
        Search through a BeautifulSoup interpretation of a webpage looking
        for <td>Location: </td> if that exists then parse the next table element to get
        the GPS in the format LAT, LONG
        """
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
        """
        Search through areas looking for the first one with a GPS tag
        """
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
        """
        Scrape MountainProject.com for the first ascent and nearest
        gps data adding that information to the route object.
        """
        response = requests.get(route["url"])
        if response.ok:
            soup = BeautifulSoup(response.content, 'html.parser')
            route["fa"] = self._getFAFromRouteHTML(soup)
            route["gps"] = self._getNearestGPSCoordinateFromRoute(soup)
        return route

    def enrichRoutes(self, routes):
        """
        Run enrich route in parallel for all routes.
        """
        # Enrich all of the routes in parallel
        routes["routes"] = parmap(self.enrichRoute, routes["routes"])
        return routes

    def getToDos(self, startPos, userId):
        """
        Get the users Todo items by userId
        """
        response = requests.get(
            self.DATA_URL, params={"action": "getToDos", "key": self.key, "startPos": startPos, "userId": userId})
        if response.ok:
            return json.loads(response.content)
        else:
            return None

    def getToDosByEmail(self, startPos, email):
        """
        Get the users Todo items by email address
        """
        response = requests.get(
            self.DATA_URL, params={"action": "getToDos", "key": self.key, "startPos": startPos, "email": email})
        if response.ok:
            return json.loads(response.content)
        else:
            return None

    def getTicks(self, startPos, userId):
        """
        Get the users ticks by userId
        """
        response = requests.get(
            self.DATA_URL, params={"action": "getTicks", "key": self.key, "startPos": startPos, "userId": userId})
        if response.ok:
            return json.loads(response.content)
        else:
            return None

    def getTicksByEmail(self, startPos, email):
        """
        Get the users ticks by email
        """
        response = requests.get(
            self.DATA_URL, params={"action": "getTicks", "key": self.key, "startPos": startPos, "email": email})
        if response.ok:
            return json.loads(response.content)
        else:
            return None

    def getUser(self, userId):
        """
        Get the user information by userId
        """
        response = requests.get(
            self.DATA_URL, params={"action": "getUser", "key": self.key, "userId": userId})
        if response.ok:
            return json.loads(response.content)
        else:
            return None

    def getUserByEmail(self, email):
        """
        Get the user information by email address
        """
        response = requests.get(
            self.DATA_URL, params={"action": "getUser", "key": self.key, "email": email})
        if response.ok:
            return json.loads(response.content)
        else:
            return None

    def search(self, query, category, offset, size):
        payload = {"q": urllib.quote_plus(
            query), "c": category, "o": offset, "s": size}
        r = requests.get(self.SEARCH_URL, params=payload)
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
