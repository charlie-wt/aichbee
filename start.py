#!/usr/bin/env python3

import os
import time
import main

def main ():
    # TODO #bug: this whole thing is probably far from what I want
    try:
        main.main()
        os.fork()
    except:
        time.sleep(5)

if __name__=='__main__':
    main()
