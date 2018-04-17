from __future__ import print_function, unicode_literals

from operator import itemgetter
from unicodedata import normalize

from .wrapper import GitHubAPIWrapper
from .analyzer import GitHubRepoAnalyzer


class GitHubRepoAnalyzePresenter():
    """Compose GitHub repo analyze presentation and print it to stdout.

    Attributes:
        wrapper (GitHubAPIWrapper): API wrapper instance.
        analyzer (GitHubRepoAnalyzer): Data analyzer instance.

        counters (dict): Resources counters.
        contributors_list (list): Contributors list to render in table.
        commits_sum (int): Overall sum of contributors' commits in repo.

        contributors_max (int): Max number of authors to show.
        old_pulls_days (int): Days to mark pull as old.
        old_issues_days (int): Days to mark issue as old.
    """
    def __init__(self, repo_url,
                 from_date=None, to_date=None, branch='master',
                 auth_token=None,
                 old_pulls_days=30, old_issues_days=14,
                 contributors_max=30):
        self.wrapper = GitHubAPIWrapper(
            repo_url, from_date=from_date, to_date=to_date, branch=branch,
            auth_token=auth_token
        )

        # Catch possible formatting errors
        exceptions = self.wrapper.exceptions
        if exceptions['from_date'] or exceptions['to_date']:
            date_error = 'You`ve made a mistake in ISO 8601 date format!'
            print(date_error)
            if exceptions['from_date'] and exceptions['to_date']:
                no_date_filter = (
                    'Both floor and ceiling dates won`t be used as filters.'
                )
            else:
                if exceptions['from_date']:
                    no_date_filter = ('Floor date won`t be used as filter, '
                                      'only the ceiling date will be used.')
                elif exceptions['to_date']:
                    no_date_filter = ('Ceiling date won`t be used as filter, '
                                      'only the floor date will be used.')
            print(no_date_filter)
            print('You should use "YYYY-MM-DD" pattern to filter by date.\n')

        # Check if ceiling date is later than the floor date
        if (
            (self.wrapper.filters['to_date'] and self.wrapper.filters['from_date']) and
            self.wrapper.filters['to_date'] < self.wrapper.filters['from_date']
        ):
            message = ('Ceiling date is earlier than the floor date. '
                       'You won`t be able to filter anything by date.')
            print(message)

        self.analyzer = GitHubRepoAnalyzer()

        # Resource counters options
        self.old_pulls_days = int(old_pulls_days)
        self.old_issues_days = int(old_issues_days)

        self.counters = {}
        self.counters['contributors'] = None
        self.counters['pulls'] = None
        self.counters['issues'] = None

        # Output data
        self.contributors_list = []
        self.commits_sum = 0

        # Output options
        self.contributors_max = int(contributors_max)

    def _create_contributors_list(self, contributors):
        """Create contributors list.

        List of dicts with author as key and commits as value.

        Args:
            collections.Counter: Contributors counter.
        """
        for author, commits in self.counters['contributors'].items():
            self.commits_sum += commits
            contributor = {'author': author, 'commits': commits}
            self.contributors_list.append(contributor)

        # Sort contributors list by commits DESC and authors ASC
        self.contributors_list = sorted(
            self.contributors_list, key=itemgetter('author')
        )
        self.contributors_list = sorted(
            self.contributors_list, key=itemgetter('commits'), reverse=True
        )

    def _safe_str(self, obj):
        """Safe str for Python 2 backwards compatibility.

        Returns the same string with Python 3.
        Returns the string converted to ASCII symbols with Python 2.

        Args:
            obj (str): Input string.

        Returns:
            unicode|str: Output string.
        """
        try:
            return normalize('NFC', str(obj))
        except (UnicodeEncodeError, TypeError):
            return normalize('NFKD', obj).encode(
                'ascii', 'ignore'
            ).decode('ascii')
        return ''

    def _print_table(self, data, cols=None):
        """Print a list of dictionaries as a dynamically sized table."""
        if not cols:
            cols = list(data[0].keys() if data else [])
        lst = [cols]

        output = ''

        for item in data:
            item['author'] = self._safe_str(item['author'])
            lst.append([str(item[col.lower()] or '') for col in cols])

        cols_size = [max(map(len, col)) for col in zip(*lst)]

        border_str = '-|-'.join(['-' * i for i in cols_size])
        header_str = '=|='.join(['=' * i for i in cols_size])

        row_str = ' | '.join(['{{:<{row}}}'.format(row=i) for i in cols_size])

        lst.insert(0, ['-' * i for i in cols_size])
        lst.insert(2, ['-' * i for i in cols_size])
        lst.append(['-' * i for i in cols_size])

        for num, item in enumerate(lst):
            if num == 0:
                output += '+-' + border_str.format(*cols_size) + '-+' + '\n'
                continue
            elif num == 2:
                output += '+=' + header_str.format(*cols_size) + '=+' + '\n'
                continue
            elif num == len(lst) - 1:
                output += '+-' + border_str.format(*cols_size) + '-+'
                continue

            output += '| ' + row_str.format(*item) + ' |' + '\n'

        print(output)

    def _prepare(self):
        """Summary"""
        commits_data = self.wrapper.get_commits()
        # print('commits_data:', commits_data)
        if not isinstance(commits_data, list):
            print(commits_data['message'])
            return False

        pulls_data = self.wrapper.get_resources('pulls')
        # print('pulls_data:', pulls_data)
        if not isinstance(pulls_data, list):
            print(pulls_data['message'])
            return False

        issues_data = self.wrapper.get_resources('issues')
        # print('issues_data:', issues_data)
        if not isinstance(issues_data, list):
            print(issues_data['message'])
            return False

        self.counters['contributors'] = self.analyzer.count_contributors(
            commits_data
        )
        self.counters['pulls'] = self.analyzer.count_resources(
            'pulls', pulls_data, self.old_pulls_days
        )
        self.counters['issues'] = self.analyzer.count_resources(
            'issues', issues_data, self.old_issues_days
        )

        # Create contributors list
        self._create_contributors_list(self.counters['contributors'])

        return True

    def present(self):
        """Print repository analysis to stdout:

        * Table of the most active contributors.

            * Table with 2 columns: contributor login, commits count.
            * Table rows ordered by commits count ascending.
            * There should not be more than 30 rows.

        * Count of opened and closed pull requests.
        * Count of old pull requests (still open for 30 days or more).

        * Count of opened and closed issues.
        * Count of old issues (still open for 14 days or more).
        """
        prepare = self._prepare()

        if prepare:
            print('GitHub repository analysis')
            print('==========================')
            print('Repository:', self.wrapper.repo['title'])
            print('Created by:', self.wrapper.repo['owner'])
            print('')

            # Table of the most active contributors
            if self.contributors_list:
                print('Contributors')
                print('^^^^^^^^^^^^')
                print('Commits:', self.commits_sum)

                table_header = ('Author', 'Commits',)
                self._print_table(
                    self.contributors_list[:self.contributors_max],
                    cols=table_header
                )
            else:
                print('No contributions found.')

            print('')

            # Count of opened, closed and old pull requests
            if self.counters['pulls']:
                print('Pulls')
                print('^^^^^')
                print('opened:', self.counters['pulls']['opened'])
                print('closed:', self.counters['pulls']['closed'])
                print('   old:', self.counters['pulls']['old'])
            else:
                print('No pull requests found.')

            print('')

            # Count of opened, closed and old issues
            if self.counters['issues']:
                print('Issues')
                print('^^^^^^')
                print('opened:', self.counters['issues']['opened'])
                print('closed:', self.counters['issues']['closed'])
                print('   old:', self.counters['issues']['old'])
            else:
                print('No issues found.')

            print('')
