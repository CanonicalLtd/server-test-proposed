#!/usr/bin/env python3
"""Generate list of packages from the server team that uploaded to proposed.

Copyright 2017 Canonical Ltd.
Robbie Basak <robie.basak@canonical.com>
Joshua Powers <josh.powers@canonical.com>
"""
import argparse
from datetime import datetime, timedelta
import glob
import json
import os
import shlex
import subprocess
import sys
import urllib.request

from launchpadlib.launchpad import Launchpad

LP = Launchpad.login_anonymously('metrics', 'production', version='devel')


def run(cmd):
    """Wrapper function around subprocess."""
    process = subprocess.Popen(shlex.split(cmd),
                               stdout=subprocess.PIPE,
                               stderr=subprocess.PIPE)
    out, err = process.communicate()
    return out, err


def get_team_packages(team='ubuntu-server'):
    """Return a team's packages based on package-team mapping."""
    url = ("http://people.canonical.com/~ubuntu-archive/"
           "package-team-mapping.json")
    with urllib.request.urlopen(url) as url:
        data = json.loads(url.read().decode())

    return data[team]


def get_series_name(series_link):
    """Return series name."""
    return LP.load(series_link).name


def get_person_name(person_link):
    """Return person name."""
    if person_link:
        return LP.load(person_link).name

    return None


def get_binary_packages(src):
    """Return list of binary packages produced by a source package."""
    binaries = []
    out, _ = run('rmadison -S %s' % src)
    lines = out.splitlines()
    for line in lines:
        binaries.append(line.split()[0])

    return list(set(binaries))


def find_proposed_uploads(release, date):
    """Given a date, get uploads for that day."""
    uploads = []

    ubuntu = LP.distributions['ubuntu']
    archive = ubuntu.main_archive

    packages = get_team_packages()
    for package in packages:
        pkgs = archive.getPublishedSources(
            created_since_date=date,
            # essential ordering for migration detection
            order_by_date=True,
            source_name=package,
            exact_match=True,
            distro_series=ubuntu.getSeries(name_or_version=release),
            pocket='Proposed',
            status='Published'
        )

        # sucessful SRU upload to specific release and Proposed
        for pkg in pkgs:
            print('%s (%s)' % (pkg.source_package_name,
                               pkg.source_package_version))
            uploads.append(pkg.source_package_name)

    return uploads


def generate_report(release, date=None):
    """Generate report of uploads to proposed."""
    if not date:
        date = (datetime.now().date() - timedelta(days=1)).strftime('%Y-%m-%d')

    print('Searching for proposed uploads to %s on %s:' % (release, date))
    uploads = find_proposed_uploads(release, date)

    if not uploads:
        print('No uploads to test. Exiting.')
        sys.exit(0)

    print('Finding binaries to test:')
    report = {}
    for upload in uploads:
        report[upload] = get_binary_packages(upload)

    print(report)
    return report


def find_tests(report):
    """Find tests in repo."""
    print('Finding tests...')
    tests = {}

    for file in glob.glob('*.py'):
        with open(file) as test_file:
            for line in test_file:
                if "# QRT-Packages:" in line:
                    for k, v in report.items():
                        if any(pkg.decode("utf-8") in line for pkg in v):
                            if k not in tests:
                                tests[k] = []
                            tests[k].append(file)

    return tests


def generate_tests(report):
    """Find tests, if any, archive them."""
    print('Checking out qa-regression-testing repo...')
    run('git clone https://git.launchpad.net/qa-regression-testing/')
    os.chdir('qa-regression-testing/scripts')
    tests = find_tests(report)

    print(tests)
    if not tests:
        print('No tests to run. Exiting.')
        sys.exit(0)

    return tests


def execute_test(release, test):
    """Execute a single test."""
    result = 'not_run'
    return result


def run_tests(release, tests):
    """Go through and run tests, collecting results."""
    results = {}
    for src, tests in tests.items():
        if src not in results:
            results[src] = {}

        for test in tests:
            results[src][test] = execute_test(release, test)

    print(results)


def test_proposed(release, date):
    """Main function to create report and genereate tests."""
    report = generate_report(release, date)
    tests = generate_tests(report)
    run_tests(release, tests)


if __name__ == '__main__':
    PARSER = argparse.ArgumentParser()
    PARSER.add_argument('-d', '--date', help='date to review')
    PARSER.add_argument('-r', '--release', help='release to check for',
                        required=True)
    ARGS = PARSER.parse_args()
    test_proposed(ARGS.release, ARGS.date)
