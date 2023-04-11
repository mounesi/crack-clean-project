# coding=utf-8

import getopt
import multiprocessing
import sys

from .cc_app_console import CcAppConsole
from .cc_app_gui import CcAppGui
from .const import Const


def usage(exit_code):
    print("USAGE:")
    print("  " + appname + " PARAMS")
    print("")
    print("REQUIRED PARAMS:")
    print("")
    print("OPTIONAL PARAMS:")
    print("  -c, --console     run the console version of the application")
    print("  -h, --help        show this usage synopsis")
    print("  -n, --noimages    don't display camera images (GUI mode)")
    print("  -p, --period      update period (ms)")
    print("")
    sys.exit(exit_code)


def main(argv):
    console = False
    noimages = False
    period = None
    try:
        (opts, args) = getopt.getopt(
            argv,
            "chnp:",
            [
                "console",
                "help",
                "noimages",
                "period="
            ]
        )
    except getopt.GetoptError:
        usage(1)
    for opt, arg in opts:
        if opt in ("-c", "--console"):
            console = True
        elif opt in ("-h", "--help"):
            usage(0)
        elif opt in ("-n", "--noimages"):
            noimages = True
        elif opt in ("-p", "--period"):
            period = int(arg)

    if (console and noimages):
        usage(1)

    #context = multiprocessing.get_context('spawn')
    #context = multiprocessing.get_context('fork')
    context = multiprocessing.get_context('forkserver')

    if console:
        if period is None:
            period = Const.APP_CONSOLE_DEFAULT_UPDATE_PERIOD_MS
        app = CcAppConsole(context, period)
    else:
        if period is None:
            period = Const.APP_GUI_DEFAULT_UPDATE_PERIOD_MS
        app = CcAppGui(context, (not noimages), period)
    app.run()
    sys.exit(0)


if __name__ == '__main__':
    appname = sys.argv[0]
    main(sys.argv[1:])

