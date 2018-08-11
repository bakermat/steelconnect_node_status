#!/usr/bin/env python3
"""
Displays node status of SteelConnect nodes: green = online, red = offline.

Designed for Python3, and requires the Requests library.

When CSV file used for multiple realms,the following headers are required:
    scm,username,password,org (optional)

USAGE:
    steelconnect_node_status.py [-s scm.riverbed.cc] [-o organisation]
                                 [-u username] [-p password] [-f file]

SCM interaction based on Greg Mueller's work in scrap_set_node_location.py:
https://github.com/grelleum/SteelConnection/blob/develop/examples/set_node_location.py
"""

from time import time
import argparse
import collections
import csv
import getpass
import json
import requests
import sys
import operator
import re


def main(argv):
    """  Open CSV file if specified, then check sites and node status"""
    args = arguments(argv)
    nodes = []
    sites = []
    # Open CSV file if specified
    if args.file:
        orgs_csv = open_csv(args.file)
        result = []
        for orgs in orgs_csv:
            scm = orgs['scm']
            username = orgs['username']
            password = orgs['password']
            org = orgs['org']
            baseurl_reporting = 'https://' + scm + '/api/scm.reporting/1.0/'
            baseurl_config = 'https://' + scm + '/api/scm.config/1.0/'
            auth = (username, password)
            # get information from SCM and calculate latency in ms
            time_before = time()
            org = find_org(baseurl_config, auth, org)
            time_after = time()
            time_taken = round((time_after-time_before)*1000, 2)
            # create objects for sites and nodes for retrieval later
            realm_fw = get_realm_fw(baseurl_config, auth, scm)
            sites.extend(get_sites(baseurl_config, auth, scm, org))
            nodes.extend(get_nodes(baseurl_reporting, auth, scm, org))
            print("Checking {}, version {} ({}ms)..."
                  .format(scm, realm_fw, time_taken))
    else:  # no CSV file, specific realm specified
        scm = args.scm if args.scm else get_scm()
        org = args.organisation if args.organisation else get_organisation()
        username = args.username if args.username else get_username()
        password = args.password if args.password else get_password(username)
        auth = (username, password)
        baseurl_reporting = 'https://' + scm + '/api/scm.reporting/1.0/'
        baseurl_config = 'https://' + scm + '/api/scm.config/1.0/'
        time_before = time()
        org_id = find_org(baseurl_config, auth, org)
        time_after = time()
        time_taken = round((time_after-time_before)*1000, 2)
        realm_fw = get_realm_fw(baseurl_config, auth, scm)
        sites = get_sites(baseurl_config, auth, scm, org_id)
        nodes = get_nodes(baseurl_reporting, auth, scm, org_id)
        print("Checking {}, version {} ({}ms)..."
              .format(scm, realm_fw, time_taken))

    # print layout for overview
    print('*' * 145)
    print(' {0:25} {1:15} {2:61} {3:10} {4:12} {5:16}'
          .format('SCM Realm', 'Organisation', 'Site',
                  'Model', 'Firmware', 'Serial'))
    print('*' * 145)
    # instead of showing the codenames, show the actual product names
    model = {
        'aardvark': 'SDI-S12',
        'baloo': 'SDI-SH',
        'beorn': 'SDI-ZAKSH',
        'booboo': 'SDI-AWS',
        'cx3070': '3070-SD',
        'cx570': '570-SD',
        'cx770': '770-SD',
        'ewok': 'SDI-330',
        'fozzy': 'SDI-USB',
        'grizzly': 'SDI-1030',
        'koala': 'SDI-AP5',
        'kodiak': 'SDI-S48',
        'misha': 'SDI-AZURE-SH',
        'paddington': 'SDI-AZURE',
        'panda': 'SDI-130',
        'panther': 'SDI-5030',
        'raccoon': 'SDI-AP3',
        'sloth': 'SDI-S24',
        'tiger1g': 'SDI-2030',
        'ursus': 'SDI-AP5r',
        'xirrusap': 'Xirrus AP',
        'yogi': 'SDI-VGW'
    }

    node_counter_total = 0
    node_counter_offline = 0
    node_counter_online = 0

    for site in sites:
        for node in nodes:
            # make sure a serial is specified and ignore shadow appliances
            if node.serial:
                if (node.site_id == site.site_id):
                    node_counter_total += 1
                    # remove the codenames from the node's firmware version
                    firmware_version = re.sub('-[a-z].*', '', node.fw_version)
                    # node = offline
                    if (node.state != "online"):
                        node_counter_offline += 1
                        # use red colour for offline nodes
                        print("\033[91m {0:25} {1:15} {2:61} "
                              "{3:10} {4:12} {5:16}\033[00m"
                              .format(node.scm, site.org_name, site.longname,
                                      str(model.get(node.model, "unknown")),
                                      firmware_version, node.serial))
                    # else: node = online
                    else:
                        node_counter_online += 1
                        # use green colour for online nodes
                        print("\033[0;32m {0:25} {1:15} {2:61} "
                              "{3:10} {4:12} {5:16}\033[00m"
                              .format(node.scm, site.org_name, site.longname,
                                      str(model.get(node.model, "unknown")),
                                      firmware_version, node.serial))
    # print total amount of nodes
    print("\nTotal: {} nodes ({} online, "
          "{} offline)\n".format(str(node_counter_total),
                                 str(node_counter_online),
                                 str(node_counter_offline)))


def find_org(url, auth, organisation):
    """Find the org id for the specified organisation."""
    orgs = get(url + 'orgs', auth=auth)
    org_found = [org for org in orgs if org['name'] == organisation]
    if not org_found:
        org_found = [org for org in orgs if org['longname'] == organisation]
    if not org_found:
        print("\nCould not find and org with name '{0}'".format(organisation))
        sys.exit(1)
    org = org_found[0]
    Org = collections.namedtuple('Org', ['id', 'name'])
    org = Org(org['id'], org['name'])
    return org


def get_sites(url, auth, scm, org):
    """Get list of sites for specified organisation."""
    sites = get(url + 'org/' + org.id + '/sites', auth=auth)
    Site = collections.namedtuple('Site', ['scm', 'site_id', 'name',
                                  'longname', 'city', 'org_id', 'org_name'])
    site = [Site(scm, site['id'], site['name'], site['longname'],
                 site['city'], site['org'], org.name) for site in sites]
    site.sort(key=lambda x: x.longname.casefold())
    return site


def get_nodes(url, auth, scm, org):
    """Get list of nodes for specified organisation."""
    nodes = get(url + 'org/' + org.id + '/nodes', auth=auth)
    Node = collections.namedtuple(
        'Node', ['scm', 'node_id', 'serial', 'state', 'model',
                 'site_id', 'org_id', 'fw_version'])
    node = [Node(scm, node['id'], node['serial'], node['state'],
            node['model'], node['site'], node['org'],
            node['firmware_version'] or 'N/A') for node in nodes]
    return node


def get_realm_fw(url, auth, scm):
    """Get firmware for specified realm."""
    status = get(url + 'status', auth=auth, single=True)
    if status:
        realm_fw = status['scm_version'] + '-' + status['scm_build']
    else:
        realm_fw = "< 2.9"
    return realm_fw


def open_csv(file):
    """Import CSV file with auth details, sort on SCM"""
    try:
        with open(file, "rt") as f:
            orgs = [row for row in csv.DictReader(f)]
            orgs = sorted(orgs, key=lambda d: (d['scm']))
    except IOError:
        print('Error: File {0} does not exist.'. format(file))
    else:
        return orgs


def arguments(argv):
    """Get command line arguments."""
    description = (
        'Get node status from SCM.'
    )
    parser = argparse.ArgumentParser(description=description)
    parser.add_argument(
        '-s',
        '--scm',
        type=str,
        help='Domain name of SteelConnect Manager',
    )
    parser.add_argument(
        '-o',
        '--organisation',
        type=str,
        help='Name of target organisation',
    )
    parser.add_argument(
        '-u',
        '--username',
        help='Username for SteelConnect Manager: prompted if not supplied',
    )
    parser.add_argument(
        '-p',
        '--password',
        help='Password for SteelConnect Manager: prompted if not supplied',
    )
    parser.add_argument(
        '-f',
        '--file',
        help='CSV file to import',
    )
    return parser.parse_args()


def get_scm(scm=None):
    """Get SCM in a Python 3 compatible way."""
    prompt = 'Enter SCM realm (e.g. mydemo.riverbed.cc): '
    while not scm:
        scm = input(prompt)
    return scm


def get_organisation(org=None):
    """Get organisation name in a Python 3 compatible way."""
    prompt = 'Enter organisation: '
    while not org:
        org = input(prompt)
    return org


def get_username(username=None):
    """Get username in a Python 3 compatible way."""
    prompt = 'Enter SCM username: '
    while not username:
        username = input(prompt)
    return username


def get_password(username, password=None):
    """Get password from terminal with discretion."""
    prompt = 'Enter SCM password for {0}:'.format(username)
    while not password:
        password = getpass.getpass(prompt)
    return password


def get(url, auth, single=False):
    """Return the items request from the SC REST API"""
    try:
        response = requests.get(url, auth=auth)
        response.raise_for_status()
    except requests.HTTPError as errh:
        if single:
            return None
        else:
            print('\nERROR:', errh)
            sys.exit(1)
    except requests.ConnectionError as errc:
        print('\nERROR: Failed to connect to SCM, '
              'please check your credentials.')
        sys.exit(1)
    except requests.RequestException as e:
        print(e)
        sys.exit(1)
    else:
        if response.status_code == 200:
            if single:
                return response.json()
            else:
                return response.json()['items']
        else:
            print('=' * 79, file=sys.stderr)
            print('Access to SteelConnect Manager failed:', file=sys.stderr)
            print(response, response.content, file=sys.stderr)
            print('=' * 79, file=sys.stderr)
            sys.exit(1)


if __name__ == '__main__':
    result = main(sys.argv[1:])
