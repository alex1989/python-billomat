#!/usr/bin/env python
# coding: utf-8

# BEGIN --- required only for testing, remove in real world code --- BEGIN
import os
import sys
THISDIR = os.path.dirname(os.path.abspath(__file__))
APPDIR = os.path.abspath(os.path.join(THISDIR, os.path.pardir))
sys.path.insert(0, APPDIR)
# END --- required only for testing, remove in real world code --- END


import pybillomat

conn = pybillomat.Connection(
    billomat_id = "<BillomatId>",
    billomat_api_key = "<BillomatApiKey",
)

# CAUTION! This example fetches ALL (really ALL) clients

clients = pybillomat.Clients(conn = conn)
clients.search(fetch_all = True, allow_empty_filter = True)

for client in clients:
    assert isinstance(client, pybillomat.Client)
    print client.id
    print client.name
# --> TESTFIRMA
# TESTFIRMA 2
# ...
