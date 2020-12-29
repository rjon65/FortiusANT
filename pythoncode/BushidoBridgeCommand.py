#-------------------------------------------------------------------------------
# Version info
#-------------------------------------------------------------------------------
__version__ = "2020-20-19"
# 2020-12-19    Initial version based on ExplorAntCommaand

#-------------------------------------------------------------------------------
import argparse
import debug
import logfile

#-------------------------------------------------------------------------------
# E x p l o r   A N T   -   C o m m a n d L i n e V a r i a b l e s
#-------------------------------------------------------------------------------
class CommandLineVariables(object):

    args            = None

    csvExport       = False
    debug           = 0
    dongle          = -1
    deviceNr        = 6666          # Device number to use as master
    bridgeHU        = False         # Bridge type: HU instead of VT (brake)

    #---------------------------------------------------------------------------
    # Define and process command line
    #---------------------------------------------------------------------------
    def __init__(self):
        #-----------------------------------------------------------------------
        # Define and process command line
        #-----------------------------------------------------------------------
        parser = argparse.ArgumentParser(description='Program capturing all ANT traffic')
        parser.add_argument('-d','--debug',         help='Show debugging data',                 required=False, default=False)
        parser.add_argument('-D','--dongle',        help='Use this ANT dongle',                 required=False, default=False)
        parser.add_argument('-H','--bridgeHU',      help='Bridge HU device type (TTS4 -> HU)',  required=False, action='store_true')
        parser.add_argument('-N','--deviceNr',      help='Device number to use as master',      required=False, default=False)
        parser.add_argument('-C','--csvExport',     help='Export data pages to CSV file',       required=False, action='store_true')
        args                 = parser.parse_args()
        self.args            = args

        #-----------------------------------------------------------------------
        # Booleans; either True or False
        #-----------------------------------------------------------------------

        self.csvExport       = args.csvExport

        #-----------------------------------------------------------------------
        # Get debug-flags, used in debug module
        #-----------------------------------------------------------------------
        if args.debug:
            try:
                self.debug = int(args.debug)
            except:
                logfile.Console('Command line error; -d incorrect debugging flags=%s' % args.debug)

        #-----------------------------------------------------------------------
        # Get ANTdongle
        #-----------------------------------------------------------------------
        if args.dongle:
            try:
                self.dongle = int(args.dongle)
            except:
                logfile.Console('Command line error; -D incorrect dongle=%s' % args.dongle)

        # -----------------------------------------------------------------------
        # Get Master Device Number
        # -----------------------------------------------------------------------
        if args.deviceNr:
            try:
                self.deviceNr = int(args.deviceNr)
            except:
                logfile.Console('Command line error; -N incorrect Device number=%s' % args.fe)

        #-----------------------------------------------------------------------
        # Get Device type to bridge
        #-----------------------------------------------------------------------
        if args.bridgeHU:
            try:
                self.bridgeHU = args.bridgeHU
            except:
                logfile.Console('Command line error; -H incorrect Device type=%s' % args.fe)

    def print(self):
        try:
            v = debug.on(debug.Any)     # Verbose: print all command-line variables with values
            if      self.csvExport:          logfile.Console ("-C")
            if v or self.args.debug:         logfile.Console ("-d %s (%s)" % (self.debug,      bin(self.debug  ) ) )
            if v or self.args.dongle:        logfile.Console ("-D %s (%s)" % (self.dongle,     hex(self.dongle ) ) )
            if v or self.args.deviceNr:      logfile.Console ("-N %s (%s)" % (self.deviceNr,   hex(self.deviceNr) ) )
            if v or self.args.bridgeHU:      logfile.Console ("-H %s (%s)" % (self.bridgeHU,   hex(self.bridgeHU) ) )
        except:
            pass # May occur when incorrect command line parameters, error already given before

#-------------------------------------------------------------------------------
# Main program to test the previous functions
#-------------------------------------------------------------------------------
if __name__ == "__main__":
    clv = CommandLineVariables()
    clv.print()