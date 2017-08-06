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
    SEARCH_URL = ROOT_URL + "/ajax/public/search/results/category"
    DATA_URL = ROOT_URL + "/data"
    UP_AREA_IMG = "https://cdn.apstatic.com/mp-img/up.gif"

    def __init__(self, key):
        self.key = key

    def get_routes(self, routeIds):
        """
        Get all route information for a given set of routeIds
        """
        routes = None
        for route_set in grouper(100, routeIds):
            route_set = filter(None, route_set)
            response = requests.get(
                self.DATA_URL, params={"action": "getRoutes", "key": self.key, "routeIds": ",".join(route_set)})
            if response.ok:
                content = json.loads(response.text)
                if routes:
                    routes["routes"] += content["routes"]
                else:
                    routes = content
            else:
                return None
        return routes

    def _scrape_fa_from_route(self, soup):
        """
        Extract the First Ascent information for the route.
        """
        try:
            return soup.find("td", text=u"FA:\xA0").nextSibling.text
        except:
            return ""

    def _get_parent_area_link(self, soup):
        """
        Look for a link with the UP_AREA_IMG to get the url to the parent
        """
        return self.ROOT_URL + soup.find(
            "img", {"src": self.UP_AREA_IMG}).parent.get('href')

    def _get_gps_from_area(self, soup):
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

    def _get_nearest_gps(self, soup):
        """
        Search through areas looking for the first one with a GPS tag
        """
        coordinates = []

        while not coordinates:
            response = requests.get(self._get_parent_area_link(soup))
            if response.ok:
                soup = BeautifulSoup(response.text, 'html.parser')
                coordinates = self._get_gps_from_area(soup)
            else:
                raise Exception("Network Connection Failed")

        return coordinates

    def enrich_route(self, route):
        """
        Scrape MountainProject.com for the first ascent and nearest
        gps data adding that information to the route object.
        """
        response = requests.get(route["url"])
        if response.ok:
            soup = BeautifulSoup(response.text, 'html.parser')
            route["fa"] = self._scrape_fa_from_route(soup)
            route["gps"] = self._get_nearest_gps(soup)
        return route

    def enrich_routes(self, routes):
        """
        Run enrich route in parallel for all routes.
        """
        # Enrich all of the routes in parallel
        routes["routes"] = parmap(self.enrich_route, routes["routes"])
        return routes

    def get_todos(self, userId, startPos=0):
        """
        Get the users Todo items by userId
        """
        response = requests.get(
            self.DATA_URL, params={"action": "getToDos", "key": self.key, "startPos": startPos, "userId": userId})
        if response.ok:
            return json.loads(response.text)
        else:
            return None

    def get_todos_by_email(self, email, startPos=0):
        """
        Get the users Todo items by email address
        """
        response = requests.get(
            self.DATA_URL, params={"action": "getToDos", "key": self.key, "startPos": startPos, "email": email})
        if response.ok:
            return json.loads(response.text)
        else:
            return None

    def get_ticks(self, userId, startPos=0):
        """
        Get the users ticks by userId
        """
        response = requests.get(
            self.DATA_URL, params={"action": "getTicks", "key": self.key, "startPos": startPos, "userId": userId})
        if response.ok:
            return json.loads(response.text)
        else:
            return None

    def get_ticks_by_email(self, email, startPos=0):
        """
        Get the users ticks by email
        """
        response = requests.get(
            self.DATA_URL, params={"action": "getTicks", "key": self.key, "startPos": startPos, "email": email})
        if response.ok:
            return json.loads(response.text)
        else:
            return None

    def get_user(self, userId):
        """
        Get the user information by userId
        """
        response = requests.get(
            self.DATA_URL, params={"action": "getUser", "key": self.key, "userId": userId})
        if response.ok:
            return json.loads(response.text)
        else:
            return None

    def get_user_by_email(self, email):
        """
        Get the user information by email address
        """
        response = requests.get(
            self.DATA_URL, params={"action": "getUser", "key": self.key, "email": email})
        if response.ok:
            return json.loads(response.text)
        else:
            return None

    def search(self, query, category, offset, size):
        payload = {"q": urllib.parse.quote_plus(
            query), "c": category, "o": offset, "s": size}
        r = requests.get(self.SEARCH_URL, params=payload)
        if r.ok:
            return json.loads(r.text)
        else:
            raise Exception("Search Failed")

    def _search_routes(self, query, offset=0, size=100):
        return self.search(query, "Routes", offset, size)

    def search_routes_for_ids(self, query, offset=0, size=100):
        results = self._search_routes(query, offset, size)
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

    def search_routes(self, query):
        return self.get_routes(self.search_all_routes_for_ids(query))
