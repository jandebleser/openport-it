import filecmp
from time import sleep
import unittest
import os
import sys
import threading
import urllib
import urllib, urllib2

sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from apps import openport
from apps.keyhandling import get_or_create_public_key
from apps.openport_api import PortForwardResponse

import xmlrunner
print sys.path

from apps.openportit import OpenportItApp
from common.share import Share

TOKEN = 'tokentest'

class IntegrationTest(unittest.TestCase):

    def testStartShare(self):
        path = os.path.join(os.path.dirname(__file__), '../resources/logo-base.png')
        share = self.get_share(path)
        self.start_sharing(share)
        temp_file = os.path.join(os.path.dirname(__file__), os.path.basename(share.filePath))
        sleep(1)
        self.downloadAndCheckFile(share, temp_file)

    def get_share(self, path):
        share = Share()
        share.filePath = path
        share.token = TOKEN
        return share

    def start_sharing(self, share):
        self.called_back = False
        def callback(share):

            print share.as_dict()
            self.assertEquals('www.openport.be', share.server)
            self.assertTrue(share.server_port>= 2000)
           # self.assertTrue(share.server_port<= 51000)

            self.assertTrue(share.account_id > 0)
            self.assertTrue(share.key_id > 0)

            print 'called back, thanks :)'
            self.called_back = True

        def start_openport_it():
            app = OpenportItApp()
            app.open_port_file(share, callback=callback)
        thr = threading.Thread(target=start_openport_it)
        thr.setDaemon(True)
        thr.start()

        i = 0
        while i < 1000 and not self.called_back:
            i+=1
            sleep(1)
        self.assertTrue(self.called_back)
        return share


    def downloadAndCheckFile(self, share, temp_file):
        try:
            os.remove(temp_file)
        except Exception:
            pass
        print "removing file"
        self.assertFalse(os.path.exists(temp_file))
        print "file removed"
        url = share.get_link()
        print 'downloading %s' % url
        try:
            urllib.urlretrieve (url, temp_file)
        except Exception, e:
            print e
        print "file downloaded: %s" % url
        self.assertTrue(os.path.exists(temp_file))
        self.assertTrue(filecmp.cmp(share.filePath, temp_file))
        os.remove(temp_file)


    def testMultiThread(self):
        path = os.path.join(os.path.dirname(__file__), 'testfiles/WALL_DANGER_SOFTWARE.jpg')
        share = self.get_share(path)
        self.start_sharing(share)
        temp_file = os.path.join(os.path.dirname(__file__), os.path.basename(share.filePath))
        temp_file_path_1 = temp_file  + '1'
        temp_file_path_2 = temp_file  + '2'

        self.errors = []

        def download(temp_file_path):
            try:
                self.downloadAndCheckFile(share, temp_file_path)
                print "download successful: %s" % temp_file_path
            except Exception, e:
                self.errors.append(e)

        thr1 = threading.Thread(target=download, args=[temp_file_path_1])
        thr1.setDaemon(True)
        thr2 = threading.Thread(target=download, args=[temp_file_path_2])
        thr2.setDaemon(True)

        sleep(3)
        thr1.start()
        thr2.start()

        seen_both_files_at_the_same_time = False

        i = 0
        while i < 6000 and (thr1.isAlive() or thr2.isAlive()):
            sleep(0.01)
            i += 1
            if os.path.exists(temp_file_path_1) and os.path.exists(temp_file_path_2):
                seen_both_files_at_the_same_time = True

        self.assertTrue(seen_both_files_at_the_same_time)

        self.assertFalse(thr1.isAlive())
        self.assertFalse(thr2.isAlive())


        self.assertEqual(0, len(self.errors))

    def testSamePort(self):
        path = os.path.join(os.path.dirname(__file__), '../logo-base.png')
        share = self.get_share(path)
        self.success_called_back = False
        def success_callback(share):
            self.success_called_back = True
            print 'port forwarding success is called'
        share.success_observers.append(success_callback)

        self.start_sharing(share)

        i = 0
        while i < 200 and not self.success_called_back:
            i += 1
            sleep(0.01)
        print "escaped at ",i
        self.assertTrue(self.success_called_back)
        port = share.server_port

        # apparently, the request is not needed, but hey, lets keep it.
        url = 'http://www.openport.be/debug/linkSessionsToPids?key=batterycupspoon'
        req = urllib2.Request(url)
        response = urllib2.urlopen(req).read()
        self.assertEqual('done', response.strip())

        dict = openport.request_port(
            key=get_or_create_public_key(),
            restart_session_token=share.server_session_token,
            request_server_port=port
        )
        response = PortForwardResponse(dict)
        self.assertEqual(port, response.remote_port)

        dict = openport.request_port(
            key=get_or_create_public_key(),
            restart_session_token='not the same token',
            request_server_port=port
        )
        response = PortForwardResponse(dict)
        self.assertNotEqual(port, response.remote_port)



    def exceptionTest(self):
        try:
            raise ValueError
        except ValueError, TypeError:
            print "huray!"

if __name__ == '__main__':
    unittest.main(testRunner=xmlrunner.XMLTestRunner(output='test-reports'))
