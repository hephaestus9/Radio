# -*- coding: utf-8 -*-
"""Radio module"""

import sys
import os
import subprocess
import threading
from radioLib import wsgiserver
from Radio import app
import logger
from pithos import pithos
from apscheduler.scheduler import Scheduler

FULL_PATH = None
RUNDIR = None
ARGS = None
DAEMON = False
PIDFILE = None
VERBOSE = True
LOG_FILE = None
LOG_LIST = []
PORT = None
DATABASE = None
INIT_LOCK = threading.Lock()
__INITIALIZED__ = False
DEVELOPMENT = False
WEBROOT = ''
radiologger = None
pandoraplayer = None
SERVER = None
HOST = '0.0.0.0'
KIOSK = False
DATA_DIR = None
SCRIPT_DIR = None
THREADS = []
SCHEDULE = Scheduler()

UPDATER = True
CURRENT_COMMIT = None
LATEST_COMMIT = None
COMMITS_BEHIND = 0
COMMITS_COMPARE_URL = ''
FIRST_RUN = 0


def initialize():
    """Init function for this module"""
    with INIT_LOCK:

        global __INITIALIZED__, app, FULL_PATH, RUNDIR, ARGS, DAEMON, PIDFILE, VERBOSE, LOG_FILE, LOG_DIR, radiologger, PORT, SERVER, DATABASE, AUTH, \
                UPDATER, CURRENT_COMMIT, LATEST_COMMIT, COMMITS_BEHIND, COMMITS_COMPARE_URL, USE_GIT, WEBROOT, HOST, KIOSK, DATA_DIR, SCRIPT_DIR, \
                THREADS, FIRST_RUN, pandoraplayer

        if __INITIALIZED__:
            return False

        # Set up logger
        if not LOG_FILE:
            LOG_FILE = os.path.join(DATA_DIR, 'logs', 'radio.log')

        FILENAME = os.path.basename(LOG_FILE)
        LOG_DIR = LOG_FILE[:-len(FILENAME)]

        if not os.path.exists(LOG_DIR):
            try:
                os.makedirs(LOG_DIR)
            except OSError:
                if VERBOSE:
                    print 'Unable to create the log directory.'
        radiologger = logger.RadioLogger(LOG_FILE, VERBOSE)

        #set up script dir
        if not SCRIPT_DIR:
            SCRIPT_DIR = os.path.join(RUNDIR, 'scripts')

        if KIOSK:
            radiologger.log('Running in KIOSK Mode, settings disabled.', 'INFO')

        #Check if a version file exists. If not assume latest revision.
        version_file = os.path.join(DATA_DIR, 'Version.txt')
        if not os.path.exists(version_file):
            FIRST_RUN = 1

        # check if database exists or create it
        try:
            radiologger.log('Checking if PATH exists: %s' % (DATABASE), 'WARNING')
            dbpath = os.path.dirname(DATABASE)
            if not os.path.exists(dbpath):
                try:
                    radiologger.log('It does not exist, creating it...', 'WARNING')
                    os.makedirs(dbpath)
                except:
                    radiologger.log('Could not create %s.' % (DATABASE), 'CRITICAL')
                    print 'Could not create %s.' % (DATABASE)
                    quit()

        except:
            radiologger.log('Could not create %s.' % (DATABASE), 'CRITICAL')
            quit()

        radiologger.log('Database successfully initialised', 'INFO')

        # Web server settings
        from radio.config import preferences
        settings = preferences.Prefs()
        get_setting_value = settings.getRadioSettingValue

        if get_setting_value('port'):
            port_arg = False
            for arg in ARGS:
                if arg == '--port' or arg == '-p':
                    port_arg = True
            if not port_arg:
                PORT = int(get_setting_value('port'))

        # Set up web server
        if '--webroot' not in str(ARGS):
            WEBROOT = get_setting_value('webroot')
            if WEBROOT is None or DEVELOPMENT:
                WEBROOT = ''

        if WEBROOT:
            if WEBROOT[0] != '/':
                WEBROOT = '/' + WEBROOT
            d = wsgiserver.WSGIPathInfoDispatcher({WEBROOT: app})
        else:
            d = wsgiserver.WSGIPathInfoDispatcher({'/': app})
        SERVER = wsgiserver.CherryPyWSGIServer((HOST, PORT), d)

        # Start Pandora
        pandoraplayer = pithos.Pithos(radiologger)

        __INITIALIZED__ = True
        return True


def init_updater():
    from radio.updater import checkGithub, gitCurrentVersion
    global USE_GIT, CURRENT_COMMIT, COMMITS_BEHIND

    if UPDATER:
        if os.name == 'nt':
            USE_GIT = False
        else:
            USE_GIT = os.path.isdir(os.path.join(RUNDIR, '.git'))
            if USE_GIT:
                gitCurrentVersion()

        version_file = os.path.join(DATA_DIR, 'Version.txt')
        if os.path.isfile(version_file):
            f = open(version_file, 'r')
            CURRENT_COMMIT = f.read()
            f.close()
        else:
            COMMITS_BEHIND = -1

        threading.Thread(target=checkGithub).start()


def start_schedules():
    """Add all periodic jobs to the scheduler"""
    if UPDATER:
        # check every 6 hours for a new version
        from radio.updater import checkGithub
        SCHEDULE.add_interval_job(checkGithub, hours=6)

    SCHEDULE.start()


def start():
    """Start the actual server"""
    if __INITIALIZED__:

        #start_schedules()

        if not DEVELOPMENT:
            try:
                radiologger.log('Starting Radio on %s:%i%s' % (HOST, PORT, WEBROOT), 'INFO')
                SERVER.start()
                while not True:
                    pass
            except KeyboardInterrupt:
                stop()
        else:
            radiologger.log('Starting Radio development server on port: %i' % (PORT), 'INFO')
            radiologger.log(' ##### IMPORTANT : WEBROOT DOES NOT WORK UNDER THE DEV SERVER #######', 'INFO')
            app.run(debug=True, port=PORT, host=HOST)


def stop():
    """Shutdown Radio"""
    radiologger.log('Shutting down Radio...', 'INFO')

    if not DEVELOPMENT:
        SERVER.stop()
    else:
        from flask import request
        func = request.environ.get('werkzeug.server.shutdown')
        if func is None:
            raise RuntimeError('Not running with the Werkzeug Server')
        func()

    SCHEDULE.shutdown(wait=False)

    if PIDFILE:
        radiologger.log('Removing pidfile: %s' % str(PIDFILE), 'INFO')
        os.remove(PIDFILE)


def restart():
    """Restart Radio"""
    SERVER.stop()
    popen_list = [sys.executable, FULL_PATH]
    popen_list += ARGS
    radiologger.log('Restarting Radio with: %s' % popen_list, 'INFO')
    SCHEDULE.shutdown(wait=False)
    subprocess.Popen(popen_list, cwd=RUNDIR)


def daemonize():
    """Start Radio as a daemon"""
    if threading.activeCount() != 1:
        radiologger.log('There are %s active threads. Daemonizing may cause strange behavior.' % threading.activeCount(), 'WARNING')

    sys.stdout.flush()
    sys.stderr.flush()

    try:
        pid = os.fork()
        if pid == 0:
            pass
        else:
            radiologger.log('Forking once...', 'DEBUG')
            os._exit(0)
    except OSError, e:
        sys.exit('1st fork failed: %s [%d]' % (e.strerror, e.errno))

    os.chdir('/')
    os.umask(0)
    os.setsid()

    try:
        pid = os.fork()
        if pid > 0:
            radiologger.log('Forking twice...', 'DEBUG')
            os._exit(0)
    except OSError, e:
        sys.exit('2nd fork failed: %s [%d]' % (e.strerror, e.errno))

    pid = os.getpid()

    radiologger.log('Daemonized to PID: %s' % pid, 'INFO')
    if PIDFILE:
        radiologger.log('Writing PID %s to %s' % (pid, PIDFILE), 'INFO')
        file(PIDFILE, 'w').write("%s\n" % pid)


@app.context_processor
def utility_processor():
    def webroot_url(url=''):
        return WEBROOT + url
    return dict(webroot_url=webroot_url)
