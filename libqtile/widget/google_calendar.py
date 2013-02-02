# -*- coding: utf-8 -*-
#
###################################################################
# Some of this code is ...
#
# Copyright (C) 2012 Google Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#            http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
###################################################################
# INSTRUCTIONS:
#
# This widget will display the next appointment on your calendar in
# the qtile status bar. Appointments within the "reminder" time will be
# highlighted. Authentication credentials can be stored in a
# keyring or on disk depending on the setting of the 'keyring'
# parameter (default is to store in the keyring).
#
# To use this widget, you will need to install the Google API oauth2
# dependencies. This can be accomplished by executing the following
# command:
#
# easy_install --upgrade google-api-python-client
#
# Installing the Google API oauth2 dependencies should be done before
# running the widget.
#
# Other packages that this widget requires are dateutil and getpass
# If you get a strange "AttributeError: 'module' object has no attribute
# GoogleCalendar" error, you are probably missing a package. Check
# carefully.
#
# If you choose to store your authentication credentials on disk rather
# than in a keyring, the widget 'storage' parameter must be an absolute
# path to the file that you store your authentication credentials in.
#
# Also, note that the first time you run the widget, you will need to
# authenticate - the widget will pop a web page for this purpose.  
# Add your calendar login/password and authorize the widget to access your
# calendar data and you are good to go.
#
# Thanks to the creator of the YahooWeather widget (dmpayton). This code
# borrows liberally from that one.
###################################################################

from .. import bar, utils
import base
import gflags
import httplib2
import logging
import os
import pprint
import sys
import datetime
import re
import getpass
import dateutil.parser
import threading
import gobject

from apiclient.discovery import build
from oauth2client.client import AccessTokenRefreshError
from oauth2client.client import OAuth2WebServerFlow
from custom_tools import run
import oauth2client.keyring_storage
import oauth2client.file

class GoogleCalendar(base._TextBox):
    ''' This widget will display the next appointment on your Google calendar in
        the qtile status bar. Appointments within the "reminder" time will be
        highlighted. Authentication credentials can be stored in a
        keyring or on disk depending on the setting of the 'keyring'
        parameter (default is to store in the keyring).
    '''

    defaults = [
        ('calendar', 'primary', 'calendar to use'),
        ('update_interval', 900, 'update interval'),
        ('format', '{next_event}',
         'calendar output - leave this at the default for now...'),
        ('keyring', True,
         'use keyring to store credentials - if false, storage_file must be set'),
        ('storage_file', None,
         'absolute path of secrets file if keyring=False'),
        ('reminder_color', 'FF0000',
         'color of calendar entries during reminder time'),
        ('www_group', 'www', 'group to open browser into'),
        ('www_screen', 0, 'screen to open group on'),
        ('browser_cmd', '/usr/bin/firefox -url calendar.google.com',
         'command or script to execute on click'),
    ]

    def __init__(self, **config):
        base._TextBox.__init__(self, 'Calendar not initialized',
                               width=bar.CALCULATED, **config)
        self.timeout_add(3600, self.cred_updater) # update credentials once per hour
        self.timeout_add(self.update_interval, self.cal_updater)

    def _configure(self, qtile, bar):
        base._TextBox._configure(self, qtile, bar)
        self.add_defaults(GoogleCalendar.defaults)
        self.layout = self.drawer.textlayout(
            self.text, self.foreground, self.font,
            self.fontsize, self.fontshadow, markup=True)

    def cred_updater(self):
        def updater(): # get credentials in thread, save them in main loop
            (creds, storage) = self.cred_init()
            gobject.idle_add(self.cred_save, creds, storage)
        threading.Thread(target=updater).start()
        return True

    def cred_init(self):
        #this is the main method for obtaining credentials

        # Set up a Flow object to be used for authentication.
        FLOW = OAuth2WebServerFlow(
                   client_id=
                   '196949979762-5m3j4orcn9heesoh6td942gb2bph424q.apps.googleusercontent.com',
                   client_secret='3H1-w_9gX4DFx3bC9c-whEBs',
                   scope='https://www.googleapis.com/auth/calendar',
                   user_agent='Qtile Google Calendar Widget/Version 0.3')

        # storage is the location of our authentication credentials
        self.log.info('Keyring: %s' % self.keyring)
        if self.keyring:
            storage = oauth2client.keyring_storage.Storage('qtile_cal', getpass.getuser())
        else:
            storage = oauth2client.file.Storage(self.storage_file)

        creds = storage.get()

        if creds is None or creds.invalid:
            creds = run(FLOW, storage) # must be run in different thread or it blocks qtile

        return creds, storage

    def cred_save(self, creds, storage):
        storage.put(creds)
        self.credentials = creds
        return False

    def cal_updater(self):
        self.log.info('adding GC widget timer')
        def cal_getter(): # get cal data in thread, write it in main loop
            data = self.fetch_calendar()
            gobject.idle_add(self.update, data)
        threading.Thread(target=cal_getter).start()
        return True

    def update(self, data):
        if data:
            self.text = self.format.format(**data)
        else:
            self.text = 'No calendar data available'
        self.bar.draw()
        return False

    def button_press(self, x, y, button):
        self.update(self.fetch_calendar())
        self.qtile.addGroup(self.www_group)
        self.qtile.groupMap[self.www_group].cmd_toscreen(self.www_screen)
        self.qtile.cmd_spawn(self.browser_cmd)

    def fetch_calendar(self):
        # if we don't have valid credentials, update them
        self.log.info('fetch_calendar: before')
        if not hasattr(self, 'credentials') or self.credentials.invalid:
            self.cred_updater()
            self.log.info('fetch_calendar: after')
            data = {'next_event': 'Credentials updating'}
            return data

        # Create an httplib2.Http object to handle our HTTP requests and
        # authorize it with our credentials from self.cred_init
        http = httplib2.Http()
        http = self.credentials.authorize(http)

        service = build('calendar', 'v3', http=http)

        # current timestamp
        now = datetime.datetime.utcnow().isoformat('T')+'Z'
        data = {}

        # grab the next event
        events = service.events().list(calendarId=self.calendar,
                 singleEvents=True, timeMin=now, maxResults='1',
                 orderBy='startTime').execute()

        # get items list
        try:
            event = events.get('items', [])[0]
        except (IndexError):
            data = {'next_event': 'No appointments scheduled'}
            return data

        # get reminder time
        try:
            remindertime = datetime.timedelta(0,
            int(event.get('reminders').get('overrides')[0].get('minutes')) * 60)
        except:
            remindertime = datetime.timedelta(0,0)

        #format the data
        data = {'next_event': event['summary']+' '+re.sub(':.{2}-.*$',
                '', event['start']['dateTime'].replace('T', ' '))}
        if dateutil.parser.parse(event['start']['dateTime'],
                ignoretz=True)-remindertime <= datetime.datetime.now():
            data = {'next_event': '<span color="'+utils.hex(self.reminder_color)+
                    '">'+data['next_event']+'</span>'}

        # return the data
        return data
