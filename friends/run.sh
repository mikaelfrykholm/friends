#!/bin/bash
#setcap 'cap_net_bind_service=+ep' /path/to/program
python3 server.py --logging=debug
