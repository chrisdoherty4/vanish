import requests
import os
import tempfile
import zipfile
import re
import shutil
import json
import subprocess
import sys


class GeoJson(object):
    def __init__(self, url, cache_path):
        self._url = url
        self._cache_path = cache_path

        if not os.path.exists(self._cache_path):
            self.update()
        else:
            with open(self._cache_path) as f:
                self.servers = json.load(f)

    def update(self):
        response = requests.get(self._url, allow_redirects=True).json()

        servers = []
        for server in response:
            properties = server["properties"]

            properties.pop("marker-color")
            properties.pop("marker-cluster-small")

            # The GB code isn't present in the ovpn configurations so upgrade
            # to UK which includes GB.
            if properties['countryCode'] == "GB":
                properties.update({"countryCode": "UK"})

            servers.append(properties)

        try:
            with open(self._cache_path, 'w+') as h:
                json.dump(servers, h, indent=4)
        except FileNotFoundError as e:
            print("Invalid path {}".format(self._cache_path), file=sys.stderr)
            raise e

        self.servers = servers


class OvpnConfigs(object):
    def __init__(self, url, path):
        """OvpnConfigs.

        :param url: URL ovpn configs zip file.
        :param path: Path to write ovpn configs.
        """
        self._url = url
        self._path = path

    def update(self):
        working_dir = tempfile.mkdtemp()

        if os.path.exists(self._path):
            shutil.rmtree(self._path)

        response = requests.get(self._url)

        new_configs = os.path.join(working_dir, 'configs.zip')

        with open(new_configs, 'w+b') as h:
            h.write(response.content)

        with zipfile.ZipFile(new_configs, 'r') as zip:
            zip.extractall(self._path)

        for file in os.listdir(self._path):
            if "ovpn" in file:
                parts = re.search(
                    '^ipvanish-([A-Z]{2})-.+-([a-z]{3}-[a-c]{1}[0-9]{2}.ovpn)$',
                    file
                )
                dest = "-".join([parts.group(1), parts.group(2)]).lower()

                os.rename(
                    os.path.join(self._path, file),
                    os.path.join(self._path, dest)
                )

        shutil.rmtree(working_dir)


class Vanish(object):
    @staticmethod
    def connect(config_file, ca_file, *kargs):
        """Connect to IPVanishs servers.

        :param config_file: The ovpn configuration file
        :param ca_file: The certificate file for IPVanishs servers.
        :param *kargs: Any additional arguments to pass to openvpn command.
        """
        command = [
            'openvpn',
            '--config', config_file,
            '--ca', ca_file
        ]

        command.extend(kargs)

        try:
            subprocess.check_call(command)
        except subprocess.CalledProcessError:
            print("Failed to run openvpn command:")
            print("\t" + " ".join(command))
        except KeyboardInterrupt:
            print("Disconnected")

    @staticmethod
    def ping(servers):
        for i, server in enumerate(servers):
            try:
                response = subprocess.check_output(
                    ['ping', '-c', '1', '-W', '1', server['ip']])

                response_time = re.search(
                    "(?<=time=)([\d\.]+)", response.decode('utf-8'))

                servers[i]['rtt'] = float(response_time.group(0))

            except subprocess.CalledProcessError:
                print("Failed to ping {}".format(server['hostname']))

        return servers


class ServerContainer(object):
    def __init__(self, geojson):
        self._servers = geojson.servers

    def getServers(self,
                   continents=None,
                   countries=None,
                   regions=None,
                   cities=None):
        '''
        Retrieve a list of servers and their associated information.

        You can optionally filter the list using the continents, countries,
        regions, and cities parameters.

        :param continents: A list of continent names or codes
        :param countries: A list of country names or codes
        :param regions: A list of region names, codes, or abbreviations
        :param cities: A list of city names
        :return: A list of servers.
        '''
        servers = self._servers

        if continents:
            servers = self._filterContinents(servers, continents)

        if countries:
            servers = self._filterCountries(servers, countries)

        if regions:
            servers = self._filterRegions(servers, regions)

        if cities:
            servers = self._filterCities(servers, cities)

        return list(servers)

    def getContinents(self):
        '''
        Retrieve a dictionary of continents.

        :return: A dictionary of continents {code: name}
        '''
        codes = []
        continents = []

        for s in self._servers:
            if s['continentCode'] not in codes:
                codes.append(s['continentCode'])
                continents.append((s['continent'], s['continentCode']))

        return continents

    def getCountries(self, continents=None):
        '''
        Retrieve a dictionary of countries.

        :param continents: A list of continent names or codes
        :return: A dictionary of countries {code: name}
        '''
        servers = self._servers

        if continents:
            servers = self._filterContinents(servers, continents)

        codes = []
        countries = []

        for s in servers:
            if s['countryCode'] not in codes:
                codes.append(s["countryCode"])
                countries.append(
                    (s['continent'], s['country'], s['countryCode'])
                    )

        return countries

    def getRegions(self, continents=None, countries=None):
        '''
        Retrieve a dictionary of regions.

        :param continents: A list of continent names or codes
        :param countries: A list of country names of codes
        :return: A dictionary of regions {code: name}
        '''
        servers = self._servers

        if continents:
            servers = self._filterContinents(servers, continents)

        if countries:
            servers = self._filterCountries(servers, countries)

        codes = []
        regions = []

        for s in servers:
            if s['region'] and s['regionCode'] not in codes:
                codes.append(s['regionCode'])
                regions.append((
                    s['country'],
                    s['region'],
                    s['regionCode']
                    ))

        return regions

    def getCities(self, continents=None, countries=None, regions=None):
        '''
        Retrieve cities with optional filters.

        :param continents: A list of continent names or codes
        :param countries: A list of country names of codes
        :param regions: A list of region names, codes, or abbreviations
        :return: A unique set of cities.
        '''
        servers = self._servers

        if continents:
            servers = self._filterContinents(servers, continents)

        if countries:
            servers = self._filterCountries(servers, countries)

        if regions:
            servers = self._filterRegions(servers, regions)

        cities_added = []
        cities = []

        for s in servers:
            if s['city'] not in cities_added:
                cities_added.append(s['city'])
                cities.append((
                    s['continent'],
                    s['country'],
                    s['city']
                    ))

        return cities

    def _filterContinents(self, servers, continents):
        continents = list(map(lambda c: c.lower(), continents))
        return filter(lambda s: s['continent'].lower() in continents
            or s['continentCode'].lower() in continents, servers)

    def _filterCountries(self, servers, countries):
        countries = list(map(lambda c: c.lower(), countries))
        return filter(lambda s: s['country'].lower() in countries
            or s['countryCode'].lower() in countries, servers)

    def _filterRegions(self, servers, regions):
        regions = list(map(lambda c: c.lower(), regions))
        return filter(lambda s: s['region'].lower() in regions
            or s['regionCode'].lower() in regions
            or s['regionAbbr'].lower() in regions, servers)

    def _filterCities(self, servers, cities):
        cities = list(map(lambda c: c.lower(), cities))
        return filter(lambda x: x['city'].lower() in cities, servers)
