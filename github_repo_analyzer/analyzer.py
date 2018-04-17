from __future__ import print_function, unicode_literals

from collections import Counter
from datetime import datetime


class GitHubRepoAnalyzer():
    """GitHub repository analyzer.

    It takes input data from GitHubAPIWrapper and makes necessary computations.

    Attributes:
        counters (dict): Resources counters.
    """
    def __init__(self):
        # Counters container
        self.counters = {}

    @property
    def _now(self):
        """Current datetime.

        Returns:
            datetime.datetime: Current datetime.
        """
        return datetime.now()

    def count_contributors(self, contributors):
        """Count contributors.

        contributors (list): Contributors info.

        Returns:
            collections.Counter: Contributors counter.
        """
        self.counters['contributors'] = Counter()

        authors = []

        for co in contributors:
            author = (
                co['author']['login']
                if isinstance(co['author'], list) else
                co['commit']['author']['name']
            )
            authors.append(author)

        self.counters['contributors'].update(authors)

        return self.counters['contributors']

    def count_resources(self, res_name, resources, max_days):
        """Count opened, closed and old resources for a given repository.

        Resource may be either pull request or issue.

        Args:
            res_name (str): Resource name (`pulls` or `issues`).
            resources (list): Resources list.
            max_days (int): Days number to treat resource as old.

        Returns:
            collections.Counter: Resource counter.
        """
        self.counters[res_name] = Counter()
        self.counters[res_name]['opened'] = 0
        self.counters[res_name]['closed'] = 0
        self.counters[res_name]['old'] = 0

        for res in resources:
            state = res['state']
            created = datetime.strptime(
                res['created_at'], '%Y-%m-%dT%H:%M:%SZ'
            )

            # Count opened, closed and old resources
            if state == 'open':
                self.counters[res_name]['opened'] += 1

                delta = (self._now - created).days
                if delta > max_days:
                    self.counters[res_name]['old'] += 1
            elif state == 'closed':
                self.counters[res_name]['closed'] += 1

        # Set counter to None if there is nothing to count
        if (
            not self.counters[res_name]['opened'] and
            not self.counters[res_name]['closed'] and
            not self.counters[res_name]['old']
        ):
            self.counters[res_name] = None

        return self.counters[res_name]
