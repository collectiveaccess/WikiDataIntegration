# WikiData-Integration
WikiData integration tests

## Setup

1. Create [wikidata account](https://www.wikidata.org/w/index.php?title=Special:CreateAccount&returnto=Wikidata%3AMain+Page)

2. Create [wikidata bot account](https://www.wikidata.org/wiki/Special:BotPasswords)

3. install libraries

requires Python 3.6.8+

```bash
pip install -U setuptools
pip install -r requirements.txt
```

4. Edit user-config.py

Copy `user-config.sample.py` and rename it `user-config.py`. Replace 'my_username' with your wikidata username.

5. Edit user-password.py

Copy `user-password.sample.py` and rename it `user-password.py`. Replace 'my_username' with your wikidata username, 'my_username_bot' with your wikidata bot username, and 'bot_password' with your wikidata bot password.
