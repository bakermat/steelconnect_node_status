# steelconnect_node_status
Shows the status of all nodes in a SteelConnect Manager organisation. CSV import possible for multiple organisations.

## Getting Started
USAGE:
    steelconnect_node_status.py [-s scm.riverbed.cc] [-o organisation] [-u username] [-p password] [-f file]

example.csv can be used as a template.

### Prerequisites
Works with Python3 only.

Requires the Requests library to be installed:
- pip3 install requests

CSV file needs the following headers:
    scm,site,username,password

## Acknowledgments
SCM interaction based on Greg Mueller's work in scrap_set_node_location.py:
https://github.com/grelleum/SteelConnection/blob/develop/examples/set_node_location.py