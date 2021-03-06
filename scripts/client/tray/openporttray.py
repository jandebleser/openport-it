import json
import os
import sys
import threading
import time
import datetime
import urllib2
import traceback
from time import sleep
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
from tray import dbhandler

from tray.server import start_server_thread, start_server
from tray.dbhandler import DBHandler
from services import osinteraction
from tray.globals import Globals
from services.logger_service import get_logger, set_log_level
from common.share import Share
from common.session import Session
from services.utils import nonBlockRead

logger = get_logger('OpenPortDispatcher')

class OpenPortDispatcher(object):

    def __init__(self):
        self.share_processes = {}
        self.dbhandler = dbhandler.getInstance()
        self.os_interaction = osinteraction.getInstance()
        self.globals = Globals()
        self.start_account_checking()
        if self.os_interaction.is_compiled():
            sys.stdout = open(self.os_interaction.get_app_data_path('application.out.log'), 'a')
            sys.stderr = open(self.os_interaction.get_app_data_path('application.error.log'), 'a')

    def exitApp(self,event):
        for pid in self.share_processes:
            p = self.os_interaction.kill_pid(pid)
            logger.info("kill pid %s successful: %s" % (pid, p))
        sys.exit()

    def restart_sharing(self):
        shares = self.dbhandler.get_shares()
        logger.debug('restarting shares - amount: %s' % len(list(shares)))
        for share in shares:
            if self.os_interaction.pid_is_running(share.pid):
                logger.debug('share still running: %s' % share.restart_command)
                self.onNewShare(share)
            else:
                try:
                    logger.debug('starting share: %s' % share.restart_command)
                    p = self.os_interaction.start_openport_process(share)
                    sleep(1)
                    if p.poll() is not None:
                        logger.debug('could not start openport process: StdOut:%s\nStdErr:%s' %
                                     (nonBlockRead(p.stdout), nonBlockRead(p.stderr) ) )
                    else:
                        logger.debug('started app %s' % share.restart_command)

                    self.share_processes[p.pid]=p
                except Exception, e:
                    tb = traceback.format_exc()
                    logger.error(tb)

    def stop_sharing(self,share):
        logger.info("stopping %s" % share.id)
        self.os_interaction.kill_pid(share.pid)
        self.dbhandler.stop_share(share)

    def onNewShare(self, share):
        logger.info( "adding share %s" % share.id )
        logger.debug( share.restart_command)
        share.success_observers.append(self.onShareSuccess)
        share.error_observers.append(self.onShareError)
        share.stop_observers.append(self.stop_sharing)

        self.share_processes[share.pid] = None

    def onShareError(self, share):
        pass

    def onShareSuccess(self, share):
        pass

    def start_account_checking(self):

        def check_account_loop():
            while True:
                if self.globals.account_id == -1:
                    time.sleep(1)
                else:
                    try:
                        dict = self.check_account()
                        self.show_account_status(dict)
                    except Exception, detail:
                        logger.error( "An error has occurred while communicating the the openport servers. %s" % detail )
                        pass

                    time.sleep(60)
        t = threading.Thread(target=check_account_loop)
        t.setDaemon(True)
        t.start()

    def check_account(self):
        url = 'http://www.openport.be/api/v1/account/%s/%s' %(self.globals.account_id, self.globals.key_id)
        logger.debug('checking account: %s' % url)
        try:
            req = urllib2.Request(url)
            response = urllib2.urlopen(req).read()
            logger.debug( response )
            dict = json.loads(response)
            if 'error' in dict:
                logger.error( dict['error'] )
            return dict
        except Exception, detail:
            logger.error( "An error has occurred while communicating the the openport servers. %s" % detail )
            raise detail
            #sys.exit(9)

    def show_account_status(self, dict):
        pass #catching a signal and showing info? #logging to /proc ?

    def startOpenportItProcess (self, path):
        share = Share()
        share.filePath = path
        app_dir = self.os_interaction.get_application_dir()
        if self.os_interaction.is_compiled():
            share.restart_command = [os.path.join(app_dir, 'openportit.exe'), path]
        else:
            share.restart_command = ['python', os.path.join(app_dir, 'apps/openportit.py'), path]

        self.os_interaction.start_openport_process(share, hide_message=False, no_clipboard=False)

    def startOpenportProcess (self, port):
        session = Session()
        app_dir = self.os_interaction.get_application_dir()
        if self.os_interaction.is_compiled():
            session.restart_command = [os.path.join(app_dir, 'openport_app.exe'), '--local-port', '%s' % port]
        else:
            session.restart_command = ['python', os.path.join(app_dir,'apps/openport_app.py'), '--local-port', '%s' % port]
        logger.debug(session.restart_command)

        self.os_interaction.start_openport_process(session, hide_message=False, no_clipboard=False)

class GuiOpenPortDispatcher(OpenPortDispatcher):
    def __init__(self):
        super(GuiOpenPortDispatcher, self).__init__()
        from tray.shares_frame import SharesFrame
        self.shares_frame = SharesFrame(None, -1, "OpenPort", self)
        self.viewShares(None)

    def stop_sharing(self,share):
        super(GuiOpenPortDispatcher, self).stop_sharing(share)
        wx.CallAfter( self.shares_frame.remove_share, share)

    def viewShares(self, event):
        self.shares_frame.Show(True)

    def onShareError(self, share):
        super(GuiOpenPortDispatcher, self).onShareError(share)
        wx.CallAfter( self.shares_frame.notify_error, share)

    def onShareSuccess(self, share):
        super(GuiOpenPortDispatcher, self).onShareSuccess(share)
        wx.CallAfter( self.shares_frame.notify_success, share)

    def onNewShare(self, share):
        super(GuiOpenPortDispatcher, self).onNewShare(share)
        callbacks = {'stop': self.stop_sharing}
        wx.CallAfter( self.shares_frame.add_share, share, callbacks )

    def show_account_status(self, dict):
        wx.CallAfter( self.shares_frame.update_account,
            bytes_this_month = dict['bytes_this_month'],
            next_counter_reset_time = utc_epoch_to_local_datetime(dict['next_counter_reset_time']),
            max_bytes = dict['max_bytes']
        )

def utc_epoch_to_local_datetime(utc_epoch):
    return datetime.datetime(*time.localtime(utc_epoch)[0:6])

if __name__ == '__main__':
    logger.debug('server pid:%s' % os.getpid() )

    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--dont-restart-shares', action='store_false', dest='restart_shares', help='Restart all active shares.')
    parser.add_argument('--no-gui', action='store_true', help='Start the application headless.')
    parser.add_argument('--verbose', action='store_true', help='Be verbose.')
    parser.add_argument('--database', '-d', action='store', help='Use the following database file.', default='')
    #    parser.add_argument('--tray-port', type=int, default=8001, help='Specify the port to run on.')
    args = parser.parse_args()

    dbhandler.db_location = args.database

    if args.verbose:
        from logging import DEBUG
        set_log_level(DEBUG)
        logger.debug('You are seeing debug output.')

    if args.no_gui:
        # import daemon
        #  with daemon.DaemonContext():
        dispatcher = OpenPortDispatcher()
    else:
        import wx
        app = wx.App(False)
        dispatcher = GuiOpenPortDispatcher()

    start_server_thread(onNewShare=dispatcher.onNewShare)

    if args.restart_shares:
        dispatcher.restart_sharing()

    import signal
    def handleSigTERM(signum, frame):
        logger.debug('got a signal %s, frame %s going down' % (signum, frame))
        dispatcher.exitApp(None)
    signal.signal(signal.SIGTERM, handleSigTERM)
    signal.signal(signal.SIGINT, handleSigTERM)


    if args.no_gui:
        while True:
            sleep(1)
    else:
        app.MainLoop()


