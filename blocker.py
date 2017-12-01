import time
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

prnt = True
blocklist = [
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
dir = '.'
fname = 'testhosts'

class HostsHandler (FileSystemEventHandler):
    fixed = False

    def on_any_event (self, event ):
        if event.src_path == dir + '/' + fname:
            if prnt: print(event.src_path+' was '+event.event_type+'!')

    def on_modified (self, event):
        filename = event.src_path
        global fname
        global dir
        if filename == dir + '/' + fname:
            if not self.fixed:
                refresh(filename)
                self.fixed = True
            else:
                self.fixed = False
                if prnt: print('already fixed.')

def refresh (filename):
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
                newdata[data.index('#'+entry)] = entry
            else:
                # add the line
                newdata.append(entry)

    if data == newdata:
        # file has not changed - don't bother writing
        if prnt: print('nothing\'s changed!')
    else:
        # update the file
        with open(filename, 'w') as f:
            f.writelines(newdata)

        if prnt: print('refreshed')

def main ():
    # specify sites
    global blocklist
    global fname
    global dir
    # add alternate forms
    orig = blocklist[:]
    blocklist += [ 'www.' + item for item in orig if not item.startswith('www.') ]
    blocklist += [ item[4:] for item in orig if item.startswith('www.') ]

    # do an initial refresh, to get things going
    refresh(fname)

    # start watching file
    observer = Observer()
    handler = HostsHandler()
    observer.schedule(handler, dir, recursive=True)
    observer.start()
    if prnt: print('observer started.')
    # wait for keyboard interrupt
    try:
        while True:
            # check on a 1 minute timer as well, in case of undetected edits.
            time.sleep(60*1)
            refresh(fname)
    except KeyboardInterrupt:
        observer.stop()
    observer.join()

if __name__ == '__main__':
    main()