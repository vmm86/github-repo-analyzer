from __future__ import print_function, unicode_literals

import json
import re

from datetime import datetime
# Conditional urllib imports for both Python 2 and Python 3
try:
    from urllib.parse import parse_qsl, urlencode, urlparse, urlsplit
    from urllib.request import urlopen, Request
    from urllib.error import HTTPError
except ImportError:
    from urlparse import parse_qsl, urlparse, urlsplit
    from urllib import urlencode
    from urllib2 import urlopen, Request, HTTPError


class GitHubAPIWrapper():
    """A wrapper class for GitHub REST API v3 requests.

    GitHub REST API v3 docs: https://developer.github.com/v3/

    It's recommended to use OAuth personal access token by default
    due to possible blocking of frequent API requests from the same IP address.

    Attributes:
        repo (dict): GitHub repository information.

            repo contents:
                repo_url (str): Full URL of GitHub repository.
                repo_owner (str): GitHub user that've created the repo.
                repo_title (str): Repository title.

        filters (dict): Optional filters for repository data.

            filters contents:
                from_date (datetime.date|None): Date filtering floor.
                to_date (datetime.date|None): Date filtering ceiling.
                branch (str): Project branch to analyze.

        exceptions (dict): Possible exceptions of parsing date filters.

            exceptions contents:
                from_date (bool): If floor date exception has occured.
                to_date (bool): If ceiling date exception has occured.
    """
    def __init__(self, repo_url,
                 from_date=None, to_date=None, branch='master',
                 auth_token=None):
        # Parse repository URL to validate and get its owner and title
        self.repo = {}

        result = urlparse(repo_url)
        if result.scheme and result.netloc and result.path:
            self.repo['url'] = repo_url

            parsed_repo_url = repo_url.split('//')[1].split('/')
            self.repo['owner'] = parsed_repo_url[1]
            self.repo['title'] = parsed_repo_url[2]
        else:
            self.repo['url'] = None
            self.repo['owner'] = None
            self.repo['title'] = None

        # Parse optional filters by date
        self.filters = {}
        self.filters['from_date'] = None
        self.filters['to_date'] = None

        self.exceptions = {}
        self.exceptions['from_date'] = None
        self.exceptions['to_date'] = False

        if from_date:
            try:
                self.filters['from_date'] = datetime.strptime(
                    from_date, '%Y-%m-%d'
                ).date()
            except ValueError:
                self.exceptions['from_date'] = True

        if to_date:
            try:
                self.filters['to_date'] = datetime.strptime(
                    to_date, '%Y-%m-%d'
                ).date()
            except ValueError:
                self.exceptions['to_date'] = True

        self.filters['branch'] = branch

        # Optional OAuth personal access token
        self._auth_token = auth_token

    def _compose_full_api_request_url(self, resource, qs=None):
        """Compose full URL for a given API resource.

        Args:
            resource (str): API resource title.
            qs (dict, optional): Data for GET request query string.

        Returns:
            str: Full URL for a given API resource.
        """
        full_url = '{root}/repos/{owner}/{title}/{resource}'.format(
            root='https://api.github.com',
            owner=self.repo['owner'],
            title=self.repo['title'],
            resource=resource
        )

        if qs:
            qs = urlencode(qs)
            full_url = '{}?{}'.format(full_url, qs)

        return full_url

    def _get_pages_count(self, value):
        """Get Pages count parsed from a given `Link` header.

        Args:
            value (str): Description

        Returns:
            int: Pages count.
        """
        replace_chars = " '\""

        for val in re.split(", *<", value):
            try:
                url, params = val.split(";", 1)
            except ValueError:
                url, params = val, ''

            link = {}

            link['url'] = url.strip("<> '\"")

            for param in params.split(";"):
                try:
                    key, value = param.split("=")
                except ValueError:
                    break

                link[key.strip(replace_chars)] = value.strip(replace_chars)
                parsed_result = dict(parse_qsl(urlsplit(link['url']).query))

                if link['rel'] == 'last':
                    pages_count = int(parsed_result['page'])

        return pages_count

    def _api_request(self, url, method='GET', qs=None):
        """Wrapper for requests to API resources.

        Args:
            url (str): A given API resource URL.
            method (str): HTTP method (HEAD, GET).
            qs (dict, optional): Query string.

        Returns:
            list|dict: Response object parsed from JSON.

        Returns in case of error:
            dict: Error information.

            dict contents:
                * `success` (bool): `False` for error response.
                * `message` (str): Error message.
        """
        full_url = self._compose_full_api_request_url(url, qs=qs)

        # Optional OAuth authorization token
        headers = {}
        if self._auth_token:
            headers['Authorization'] = 'token {}'.format(self._auth_token)

        # Ugly workaround for Python 2 `(
        try:
            request = Request(full_url, method=method, headers=headers)
        except TypeError:
            request = Request(full_url, headers=headers)
            request.get_method = lambda: method

        try:
            response = urlopen(request)
        except HTTPError as e:
            message = ('{message}.'.format(message=e))

            if e.code == 403:
                ban_info = 'You`ve been banned by GitHub. ' \
                           'Wait a while or use -a for OAuth access token.'
                message = '{}\n{}'.format(message, ban_info)

            response = {
                'success': False,
                'code': e.code,
                'message': message,
            }
            return response
        else:
            if method == 'HEAD':
                try:
                    link_header = response.info().dict.get('link', None)
                except AttributeError:
                    link_header = response.getheader('Link')

                pages_count = (
                    self._get_pages_count(link_header) if
                    link_header else
                    0
                )

                return pages_count

            return json.loads(response.read().decode('utf-8'))

    def get_commits(self):
        """Get commits list for a given repository.

        Returns:
            dict: Dictionary with information about repo contributors.

            dict contents:
                * `success` (bool): `True` for successful response.
                * `commits` (list): Contributors data.

        Returns in case of error:
            dict: Error information.

            dict contents:
                * `success` (bool): `False` for error response.
                * `message` (str): Error message.
        """
        # Compose HEAD request to get pagination info
        qs = {}
        qs['per_page'] = 100

        if self.filters['from_date']:
            qs['since'] = datetime.strftime(
                self.filters['from_date'], '%Y-%m-%dT%H:%M:%SZ'
            )
        if self.filters['to_date']:
            qs['until'] = datetime.strftime(
                self.filters['to_date'], '%Y-%m-%dT%H:%M:%SZ'
            )
        qs['sha'] = self.filters['branch']

        # Get pages count for possible request pagination
        pages_count = self._api_request('commits', method='HEAD', qs=qs)

        # Catch possible mistyped URLs or other network issues
        if isinstance(pages_count, dict) and not pages_count['success']:
            return pages_count

        commits = []

        # If pages count exists - make requests for every page
        if pages_count > 0:
            for page in range(pages_count):
                qs['page'] = page + 1
                co = self._api_request('commits', qs=qs)
                commits += co
        # If there`s no pages count - make one request
        else:
            commits = self._api_request('commits', qs=qs)

        # print('commits len:', len(commits))

        return commits

    def get_resources(self, res_name):
        """Get resources for a given repository.

        Resource may be either a pull request or an issue.

        Args:
            res_name (str): Resource name (`pulls` or `issues`).

        Returns:
            dict: Counter of resources.

            dict contents:
                * `success` (bool): Successful response or not.
                * `pulls` or `issues` (collections.Counter): Counter.
        """
        # Compose resource API request
        qs = {}
        qs['state'] = 'all'
        qs['per_page'] = 100

        if self.filters['from_date']:
            qs['since'] = datetime.strftime(
                self.filters['from_date'], '%Y-%m-%dT%H:%M:%SZ'
            )
        if self.filters['to_date']:
            qs['until'] = datetime.strftime(
                self.filters['to_date'], '%Y-%m-%dT%H:%M:%SZ'
            )
        qs['base'] = self.filters['branch']  # `head` or `base` ?

        # Get pages count for possible request pagination
        pages_count = self._api_request(res_name, method='HEAD', qs=qs)

        # Catch possible mistyped URLs or other network issues
        if isinstance(pages_count, dict) and not pages_count['success']:
            return pages_count

        resources = []

        # If pages count exists - make requests for every page
        if pages_count > 0:
            for page in range(pages_count):
                qs['page'] = page + 1
                res = self._api_request(res_name, qs=qs)
                resources += res
        # If there`s no pages count - make one request
        else:
            resources = self._api_request(res_name, qs=qs)

        # print('{} len:'.format(res_name), len(resources))

        return resources
