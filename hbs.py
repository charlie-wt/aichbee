import time

# specify sites
blocklist = [
    'reddit.com',
    'twitch.tv',
    'twitter.com',
    'youtube.com'
]

# add alternate forms
blocklist += [ 'www.' + item for item in blocklist ]


# schedule action to repeat once every n seconds
starttime = time.time()
period = 10.0
while True:
#    print('tick @', time.time())
    time.sleep(period - ((time.time() - starttime) % period))

    # get the data from the file
    with open('testhosts', 'r') as f:
        data = f.readlines()

    # construct lines of new file
    blockentries = [ '127.0.0.1\t'+i+'\n' for i in blocklist ]
    newdata = data
    for entry in blockentries:
        if entry not in data:
            if '#'+entry in data:
                # uncomment the line
                newdata[data.index('#'+entry)] = entry
            else:
                # add the line
                newdata.append(entry)

    # update the file
    with open('newtesthosts', 'w') as f:
        f.writelines(newdata)