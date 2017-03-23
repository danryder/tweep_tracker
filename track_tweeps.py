#/usr/bin/env python
# -*- coding: utf-8 -*-

import sys, os, errno
import time, datetime
import requests
from requests_oauthlib import OAuth1
import pickle
import argparse
import pdb

def format_user_info(user):
    val = u'@%s -- following: %s, (follows %d, has %d followers, is%s verified): %s' \
           % (user['screen_name'],
              u'YES' if user['following'] else u'NO',
              user['friends_count'],
              user['followers_count'],
              u' ' if user['verified'] else u' NOT',
              user['description'])
    return val.encode('utf-8')

def _fetch_current_associates(screen_name, auth, track_type,
                              max_calls=15, sleep=15,
                              allow_slow=False, log=sys.stdout):

    show_url = "https://api.twitter.com/1.1/users/show.json?screen_name=%s" % screen_name
    total_count = requests.get(show_url, auth=auth).json()['followers_count']

    # TODO: XXX - NOT YET SUPPORTED
    # RETURNS 5,000 at a time (but only the ids)
    # ids_url = "https://api.twitter.com/1.1/followers/ids.json?screen_name=%s&cursor=%s"

    # These calls max out at 200
    count = 200

    url = "https://api.twitter.com/1.1/%s/list.json?screen_name=%s&skip_status=true&include_user_entities=false&cursor=%s&count=%d"
    list_calls = (total_count / count) + 1
    if list_calls > max_calls:
        warning = "%s has %d %s, exceeds %d" \
                  % (screen_name, total_count, track_type, max_calls * 200)
        if not allow_slow:
            raise Exception(warning)

        log.write(warning + ' - slow mode enabled...\n')
        estimate = sleep * (total_count / (count * max_calls))
        log.write("This will take about %d minutes\n" % estimate)
        log.write("Sleeping for %d minutes every %d calls...\n" \
                   % (sleep, max_calls))

    associates = []

    next_cursor="-1"
    calls = 0
    sleeps = 0

    while(1):
        if calls >= max_calls:
            now = datetime.datetime.now().strftime('%Y%m%d_%H:%M:%S')
            done_pct = (100.0 * (sleeps + 1) * max_calls) / (list_calls + 1)
            log.write("At %s, %5.2f%% done, sleeping for %d minutes...\n" \
                      % (now, done_pct, sleep))
            time.sleep(60 * sleep)
            calls = 0
            sleeps = sleeps + 1

        page_url = url % (track_type, screen_name, next_cursor, count)

        associates_chunk = requests.get(page_url, auth=auth).json()
        if 'errors' in associates_chunk:
            log.write('%s\n' % associates_chunk['errors'])
            sys.exit(1)

        calls = calls + 1
        associates.extend(associates_chunk['users'])

        next_cursor = associates_chunk.get('next_cursor', None)
        if not next_cursor:
            return associates

    return associates


def show_contents(f):
    print "User summaries in", f
    if os.path.exists(f):
        for f in pickle.load(file(f, 'r')):
            user_str = u'%s\n' % u'USER %s' % format_user_info(f).decode('utf-8')
            sys.stdout.write(user_str.encode('utf-8'))


def debug_contents(f):
    print "User dicts in", f
    if os.path.exists(f):
        users = pickle.load(file(f, 'r'))
        print "Examining %d users" % len(users)
        pdb.set_trace()


def track_deltas(screen_name, auth, tweeps_dir,
                 track_type, allow_slow, log=sys.stdout):

    track_types = {'followers': {'add':'gained',
                                 'del':'lost'
                                },
                   'friends':   {'add':'added',
                                 'del':'removed'
                                }
                  }
    if track_type not in track_types:
        raise Exception("Valid track types: %s" % str(track_types))

    # prevent API usage limits by not querying
    # test_mode = True
    test_mode = False

    now = datetime.datetime.now().strftime('%Y%m%d_%H:%M:%S')

    out_dir = os.path.join(tweeps_dir, screen_name)

    dbfile = os.path.join(out_dir, '%s.db' % track_type)

    try:
        os.makedirs(out_dir)
    except OSError, e:
        if e.errno != errno.EEXIST:
            raise

    last_screens = set([])
    if os.path.exists(dbfile):
        last_assoc = pickle.load(file(dbfile, 'r'))
        last_xformed = dict([(f['screen_name'], f) for f in last_assoc])
        last_screens = set(last_xformed.keys())

    now_screens = set([])
    if not test_mode:
        now_assoc = _fetch_current_associates(screen_name, auth,
                                              track_type, allow_slow=allow_slow,
                                              log=log)
        now_xformed = dict([(f['screen_name'], f) for f in now_assoc])
        now_screens = set(now_xformed.keys())

    del_screens = last_screens - now_screens
    add_screens = now_screens - last_screens

    if not len(del_screens) and not len(add_screens):
        log.write("At %s, no change - @%s has the same %d %s\n" \
                  % (now, screen_name, len(last_screens), track_type))

    else:
        delta = len(now_screens) - len(last_screens)
        change = '='
        if delta < 0:
            change = '%d' % delta
        elif delta > 0:
            change = '+%d' % delta
        log.write("At %s, @%s has %d(%s) total %s\n" % (now, screen_name,
                                                       len(now_screens),
                                                       change, track_type))
        if len(del_screens):
            log.write("@%s %s %d %s: %s\n" % (screen_name,
                      track_types[track_type]['del'],
                      len(del_screens), track_type, del_screens))
            assoc_del = [last_xformed[x] for x in del_screens]
            for x in assoc_del:
                log.write('- GOODBYE %s\n' % format_user_info(x))
            del_file = os.path.join(out_dir, '%s_%s_del-%d.db' \
                       % (now, track_type, len(del_screens)))
            with open(del_file, 'w') as df:
                pickle.dump(assoc_del, df)

        if len(add_screens):
            log.write("@%s %s %d %s: %s\n" % (screen_name,
                      track_types[track_type]['add'],
                      len(add_screens), track_type, add_screens))
            assoc_add = [now_xformed[x] for x in add_screens]
            for x in assoc_add:
                log.write('+ HELLO %s\n' % format_user_info(x))
            add_file = os.path.join(out_dir, '%s_%s_add-%d.db' \
                       % (now, track_type, len(add_screens)))
            with open(add_file, 'w') as af:
                pickle.dump(assoc_add, af)

        if now_assoc and not test_mode:
            with open(dbfile, 'w') as ff:
                pickle.dump(now_assoc, ff)


def load_oauth(d):
    req_keys = ('app_key', 'app_secret', 'user_token', 'user_secret')
    auths_file = os.path.join(d, 'auths.txt')
    if not os.path.exists(auths_file):
        raise Exception("Create %s with dict of required keys: %s" \
                        % (auths_file, ', '.join(req_keys)))

    auths = eval(file(auths_file, 'r').read())
    missing_keys = [x for x in req_keys if x not in auths]
    if missing_keys:
        raise Exception("Missing auth keys: %s" % ', '.join(missing_keys))

    return OAuth1(auths["app_key"],
                  auths["app_secret"],
                  auths["user_token"],
                  auths["user_secret"])

def parse_args():
    parser = argparse.ArgumentParser(description="Track 'yo tweeps, fool")
    parser.add_argument('-s', '--screen_name', dest='screen_names',
                        action='append',
                        help='twitter account to check')
    parser.add_argument('-f', '--followers', action='store_true',
                        help='track followers')
    parser.add_argument('-F', '--friends', action='store_true',
                        help='track friends')
    parser.add_argument('-S', '--sleep', action='store_true',
                        help='support large accounts by sleeping to avoid timeouts')
    parser.add_argument('-d', '--dir', dest='dir', default=None,
                        help='dir where everything is stored')
    parser.add_argument('--dump_file', dest='fnames', action='append',
                        help='file(s) to dump contents to stdout')
    parser.add_argument('--debug_file', dest='dfnames', action='append',
                        help='file to examine in debugger')
    parser.add_argument('-l', '--log', default=sys.stdout,
                        type=argparse.FileType('a'),
                        help='where to track activity')
    args = parser.parse_args()

    if (args.friends or args.followers) and not args.screen_names:
        log.write("Specified friends or followers switch but no screen names\n")
        sys.exit(1)

    if not args.friends and not args.followers and args.screen_names:
        args.log.write("Specified screen name, defaulting to followers\n")
        args.followers = True

    if not args.dir:
        proggy = os.path.splitext(os.path.basename(sys.argv[0]))[0]
        default_dir = os.path.join(os.path.expanduser("~"), '.'+proggy)
        args.log.write("Using default dir: %s\n" % default_dir)
        args.dir = default_dir
    return args

if __name__ == '__main__':

    args = parse_args()

    if args.fnames:
        for fname in args.fnames:
            show_contents(fname)
    if args.dfnames:
        for fname in args.dfnames:
            debug_contents(fname)

    if args.screen_names:

        # will store info here
        try:
            os.makedirs(args.dir)
        except OSError, e:
            if e.errno != errno.EEXIST:
                raise

        # will need OAuth to make API calls
        auth = load_oauth(args.dir)

        for screen_name in args.screen_names:
            if args.followers:
                track_deltas(screen_name, auth, args.dir,
                             'followers', args.sleep, log=args.log)
            if args.friends:
                track_deltas(screen_name, auth, args.dir,
                             'friends', args.sleep, log=args.log)

    args.log.close()
