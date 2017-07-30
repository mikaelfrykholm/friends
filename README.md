friends
=======
```bash
virtualenv -p python3 venv
. venv/bin/activate
pip3 install -e ./
```
#optionally to run on port <1024
sudo setcap cap_net_bind_service=+ep venv/bin/python3
