# tweep_tracker
Simple tracking of friend & follower comings and goings on twitter
* stores friend/follower users locally
* supports multiple screen names
* reports deltas (see who unfollowed)
* sleeps as needed for large accounts to avoid rate limit
* can be run from cron
* currently only read-only access to twitter required

## configure auths
* run once to see where auths file is expected:
 * `python trac_tweeps.py -s yourscreenname`  
* [log in to Twitter REST API](https://apps.twitter.com/)
* create an application key & secret
 * read-only is sufficient
* create an auth token and secret (at same address)
 * will be tied to your Twitter account
 * when you see references to "FOLLOWS", this means if they follow THIS account
* put all 4 of these bits into "auths.txt" in above location, as a Python dictionary
 ```python
  {
   "app_key":"YOUR_APP_KEY",
   "app_secret":"YOUR_APP_SECRET",
   "user_token":"YOUR_AUTH_TOKEN",
   "user_secret":"YOUR_USER_SECRET",
  }
```
## usage
`python track_tweeps.py -h`
will yield
```
usage: track_tweeps.py [-h] [-s SCREEN_NAMES] [-f] [-F] [-S] [-d DIR]
                       [--dump_file FNAMES] [--debug_file DFNAMES] [-l LOG]

Track 'yo tweeps, fool

optional arguments:
  -h, --help            show this help message and exit
  -s SCREEN_NAMES, --screen_name SCREEN_NAMES
                        twitter account to check
  -f, --followers       track followers
  -F, --friends         track friends
  -S, --sleep           support large accounts by sleeping to avoid timeouts
  -d DIR, --dir DIR     dir where everything is stored
  --dump_file FNAMES    file(s) to dump contents to stdout
  --debug_file DFNAMES  file to examine in debugger
  -l LOG, --log LOG     where to track activity
  ```

