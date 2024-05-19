# -*- coding: utf-8 -*-
# AltStore-Proxy
# Project by https://github.com/rix1337

import multiprocessing

from altstore_proxy import run

if __name__ == '__main__':
    multiprocessing.freeze_support()
    run.main()
