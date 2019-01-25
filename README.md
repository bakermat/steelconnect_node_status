# steelconnect_node_status
Shows the status of all nodes in a SteelConnect Manager organisation. CSV import possible for multiple organisations, CSV output also possible with -c flag.

## Getting Started
USAGE:
    steelconnect_node_status.py [-s realm] [-o organisation] [-u username] [-p password] [-f file] [-c]

example.csv can be used as a template.

When using -c option, output will be comma-delimited values.

### Prerequisites
Works with Python3 only.

Requires the Requests library to be installed:
- pip3 install requests

CSV input file needs the following headers:
    scm,site,username,password

### Release notes:
2019-01-25: v1.1 - added -c option for CSV output and added state field explicitly
2018-08-11: v1.0 - initial release

## Acknowledgments
SCM interaction based on Greg Mueller's work in scrap_set_node_location.py:
https://github.com/grelleum/SteelConnection/blob/develop/examples/set_node_location.py