import argparse
import sys

# Input workaround for Python 2
try:
    input = raw_input
except NameError:
    pass

from github_repo_analyzer.presenter import GitHubRepoAnalyzePresenter


__author__ = 'Michail Vasilyev (vmm86) https://github.com/vmm86'
__email__ = 'm.vasilyev86@gmail.com'
__copyright__ = 'Copyright 2018 Michail Vasilyev (vmm86)'


if __name__ == '__main__':
    """If you run this module from command line,
    you may use it straight on with the command line arguments.
    """
    parser = argparse.ArgumentParser(
        prog='GitHub repository analyzer',
        description='GitHub repository analyzer based on GitHub REST API v3.',
        usage='You should privide arguments to analyze repository, type -h'
    )
    parser.add_argument(
        'repo_url',
        help='Repository URL, like "https://github.com/fastlane/fastlane/"',
        action='store'
    )
    parser.add_argument(
        '-f',  # '--from',
        dest='fr_date',
        metavar='from_date',
        help='Optional filters: Floor date (ISO 8601), like "2018-02-23"',
        action='store'
    )
    parser.add_argument(
        '-t',  # '--to',
        dest='to_date',
        metavar='to_date',
        help='Optional filters: Ceiling date (ISO 8601), like "2018-03-08"',
        action='store'
    )
    parser.add_argument(
        '-b',  # '--branch',
        dest='branch',
        metavar='branch',
        help='Optional filters: Branch ("master" by default)',
        action='store',
        default='master'
    )

    parser.add_argument(
        '-c',  # '--contributors-max',
        dest='contributors_max',
        metavar='contributors_max',
        help='Optional max number of contributors to show (30 by default)',
        action='store',
        default=30
    )
    parser.add_argument(
        '-p',  # '--old-pulls-days',
        dest='old_pulls_days',
        metavar='old_pulls_days',
        help='Optional number of days to mark pull as old (30 by default)',
        action='store',
        default=30
    )
    parser.add_argument(
        '-i',  # '--old-issues-days',
        dest='old_issues_days',
        metavar='old_issues_days',
        help='Optional number of days to mark issue as old (14 by default)',
        action='store',
        default=14
    )

    parser.add_argument(
        '-a',  # '--auth-token',
        dest='auth_token',
        help='Optional OAuth personal access token',
        action='store_true',
        default=False
    )

    # Parse command line arguments
    args = parser.parse_args()

    kwargs = {
        'from_date': args.fr_date,
        'to_date':   args.to_date,
        'branch':    args.branch,

        'auth_token': '4f4930c39d987f9428184efc7e3c4165051cdbdf',

        'old_pulls_days':  args.old_pulls_days,
        'old_issues_days': args.old_issues_days,

        'contributors_max': args.contributors_max,
    }

    # Get optional access token from command line input
    if args.auth_token:
        sys.stdin = open('/dev/tty')
        kwargs['auth_token'] = input('Access token: ')

    if args.auth_token and not kwargs['auth_token']:
        print('Type your access token if you have to use it.')
        print('Or use this program without an -a option.')
    else:
        # Print data to stdout
        presenter = GitHubRepoAnalyzePresenter(args.repo_url, **kwargs)
        presenter.present()
