#/usr/bin/env python
# -*- coding: utf-8 -*-
import sys, os, errno
import datetime
import requests
from requests_oauthlib import OAuth1
import pickle
import argparse
import pdb

def format_user_info(user):
    return u'@%s -- following: %s, (follows %d, has %d followers, is%s verified): %s' \
           % (user['screen_name'],
              u'YES' if user['following'] else u'NO',
              user['friends_count'],
              user['followers_count'],
              u' ' if user['verified'] else u' NOT',
              user['description'])

def fetch_current_followers(screen_name, auth, max_pages=20, log=sys.stdout):

    url = "https://api.twitter.com/1.1/followers/list.json?screen_name=%s&skip_status=true&include_user_entities=false&cursor=%s"

    followers = []

    next_cursor="-1"
    for x in range(max_pages):
        page_url = url % (screen_name, next_cursor)
        followers_chunk = requests.get(page_url, auth=auth).json()
        if 'errors' in followers_chunk:
            log.write('%s\n' % followers_chunk['errors'])
            sys.exit(1)

        followers.extend(followers_chunk['users'])
        log.write('%s\n' % "Followers is now %d" % len(followers))

        next_cursor = followers_chunk.get('next_cursor', None)
        if not next_cursor:
            break

    return followers


def show_contents(f):
    print "User summaries in", f
    if os.path.exists(f):
        for f in pickle.load(file(f, 'r')):
            user_str = u'%s\n' % u'USER %s' % format_user_info(f)
            sys.stdout.write(user_str.encode('utf-8'))
        

def debug_contents(f):
    print "User dicts in", f
    if os.path.exists(f):
        users = pickle.load(file(f, 'r'))
        print "Examining %d users" % len(users)
        pdb.set_trace()


def track_deltas(screen_name, auth, log=sys.stdout):

    # prevent API usage limits by not querying
    # test_mode = True
    test_mode = False

    now = datetime.datetime.now().strftime('%Y%m%d_%H:%M:%S')
    pdir=os.path.dirname(sys.argv[0])

    out_dir = os.path.join(pdir, 'followers', screen_name)

    followers_file = os.path.join(out_dir, 'followers.db')
    quitters_file = os.path.join(out_dir, 'quitters-%s.db' % now)
    newbies_file = os.path.join(out_dir, 'newbies-%s.db' % now)

    try:
        os.makedirs(out_dir)
    except OSError, e:
        if e.errno != errno.EEXIST:
            raise
    last_screens = set([])
    if os.path.exists(followers_file):
        last_followers = pickle.load(file(followers_file, 'r'))
        last_xformed = dict([(f['screen_name'], f) for f in last_followers])
        last_screens = set(last_xformed.keys())

    now_screens = set([])
    if not test_mode:
        now_followers = fetch_current_followers(screen_name, auth, log=log)
        now_xformed = dict([(f['screen_name'], f) for f in now_followers])
        now_screens = set(now_xformed.keys())

    quitters_screens = last_screens - now_screens
    newbies_screens = now_screens - last_screens

    if not len(quitters_screens) and not len(newbies_screens):
        log.write("No change - %s has %d followers\n" \
                  % (screen_name, len(last_screens)))

    else:
        log.write("%s HAD %d followers\n" % (screen_name, len(last_screens)))
        log.write("%s HAS %d followers\n" % (screen_name, len(now_screens)))

        if len(quitters_screens):
            log.write("%s lost: %s\n" % (screen_name, quitters_screens))
            quitters = [last_xformed[q] for q in quitters_screens]
            for q in quitters:
                log.write('GOODBYE %s\n' % format_user_info(q))
            with open(quitters_file, 'w') as qf:
                pickle.dump(quitters, qf)
           
        if len(newbies_screens):
            log.write("%s got: %s\n" % (screen_name, newbies_screens))
            newbies = [now_xformed[n] for n in newbies_screens]
            for n in newbies:
                log.write('HELLO %s\n' % format_user_info(n))
            with open(newbies_file, 'w') as nf:
                pickle.dump(newbies, nf)

        if now_followers and not test_mode:
            with open(followers_file, 'w') as ff:
                pickle.dump(now_followers, ff)
   

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Track twitter followers')
    parser.add_argument('auth', default="auth.txt",
                        type=argparse.FileType('r'),
                        help='file where auth and user keys are stored')
    parser.add_argument('-s', '--screen_name', dest='screen_names', action='append',
                        help='twitter account to check')
    parser.add_argument('-f', '--fname', dest='fnames', action='append',
                        help='file to dump')
    parser.add_argument('-d', '--debugfname', dest='dfnames', action='append',
                        help='file to debug')
    parser.add_argument('-l', '--log', default=sys.stdout,
                        type=argparse.FileType('a'),
                        help='file where the activity should be stored')
    args = parser.parse_args()
 
    if args.fnames:
        for fname in args.fnames:
            show_contents(fname)
    if args.dfnames:
        for fname in args.dfnames:
            debug_contents(fname)

    if args.screen_names:

        auths = eval(args.auth.read())

        auth = OAuth1(auths["app_key"],
                      auths["app_secret"],
                      auths["user_token"],
                      auths["user_secret"])
        for screen_name in args.screen_names:
            track_deltas(screen_name, auth, log=args.log)

    args.log.close()
