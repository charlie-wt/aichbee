#!/usr/bin/env python3

import time
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

testing = True
prnt = False
default_blocklist = [
    'reddit.com',
    'youtube.com',
    'twitter.com',
    'tumblr.com',
    'twitch.tv',
    '4chan.org',
    'medium.com',
    'vimeo.com',
    'dailymotion.com'
]
# dir = '/etc'
dir = '.' if testing else '/etc'
fname = 'hosts'
done_times = 0
after = 1

class HostsHandler (FileSystemEventHandler):
    ''' class to handle file system events, specifically for the hosts file. '''
    # otherwise watchdog recognises itself as an edit and gets stuck responding
    # infinitely
    fixed = False

    def __init__ (self, blocklist):
        self.blocklist = blocklist

    def on_any_event (self, event):
        ''' simple print '''
        if event.src_path == dir + '/' + fname:
            if prnt: print(event.src_path+' was '+event.event_type+'!')

    def on_modified (self, event):
        ''' if a file's been modified: if ti's the right file and we've not
        already fixed it since the last change, fix it.
        '''
        filename = event.src_path
        global fname
        global dir
        if filename == dir + '/' + fname:
            if not self.fixed:
                refresh(filename, self.blocklist)
                self.fixed = True
            else:
                self.fixed = False
                if prnt: print('already fixed.')

def read_block_file (filename):
    ''' read a list of domains to block (like 'blocklist'), from a file '''
    blocklist = []

    # get the data from the file
    with open(filename, 'r') as f:
        data = f.readlines()

    # get just the blocked domains
    reading_blocks = False
    for line in data:
        if line[-1] == '\n':
            line = line[:-1]
        if line == '= DOMAINS':
            reading_blocks = True
        elif reading_blocks:
            if line == '===':
                reading_blocks = False
            else:
                blocklist.append(line)

    # return results
    return blocklist

def refresh (filename, blocklist):
    ''' main function to correct the hosts file. '''
    global done_times
    global after
    if prnt: print('refreshing')
    # get the data from the file
    with open(filename, 'r') as f:
        data = f.readlines()

    # construct lines of new file
    blockentries = [ '0.0.0.0\t'+i+'\n' for i in blocklist ]
    newdata = data[:]
    for entry in blockentries:
        if entry not in data:
            if '#'+entry in data:
                # uncomment the line
                if prnt: print(entry[:-1], 'is commented at line', data.index('#'+entry))
                newdata[data.index('#'+entry)] = entry
            else:
                # add the line
                if prnt: print(entry[:-1], 'is missing')
                newdata.append(entry)
        else:
            if prnt: print(entry[:-1], 'is present, at line', data.index(entry))

    if data == newdata:
        # file has not changed - don't bother writing
        if prnt: print('nothing\'s changed!')
    else:
        # update the file
        with open(filename, 'w') as f:
            f.writelines(newdata)
        if prnt: print('refreshed')

    # testing lol
    if testing:
        if done_times > after:
            with open(filename, 'w') as f:
                newdata.append('# also hello')
                f.writelines(newdata)
        done_times += 1

def main ():
    # specify sites
    blocklist = []
    try:
        blocklist = read_block_file('blocklist.txt')
    except:
        blocklist = default_blocklist
    global fname
    global dir
    filename = dir+'/'+fname if not dir[-1] == '/' else dir+filename
    # add alternate forms
    orig = blocklist[:]
    blocklist += [ 'www.' + item for item in orig if not item.startswith('www.') ]
    blocklist += [ item[4:] for item in orig if item.startswith('www.') ]

    # do an initial refresh, to get things going
    refresh(filename, blocklist)

    # start watching file
    observer = Observer()
    handler = HostsHandler(blocklist)
    observer.schedule(handler, dir, recursive=True)
    observer.start()
    if prnt: print('observer started.')
    # wait for keyboard interrupt
    try:
        while True:
            # check on a 1 minute timer as well, in case of undetected edits.
            time.sleep(6*1)
            refresh(filename, blocklist)
    except KeyboardInterrupt:
        observer.stop()
    observer.join()

if __name__ == '__main__':
    main()