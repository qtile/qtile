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
# You will also need to pre-authenticate your access to your Google
# calendar before using the widget. This is because the widget currently
# updates in the main qtile thread. As a result, if you do not
# pre-authenticate, qtile will hang while waiting for the authentication
# process to complete.
#
# Pre-authentication is easy, and only needs to be done once. Download
# and unzip the pre-authentication archive at:
#
# http://dave.tycho.ws/pre-auth.zip
#
# Edit the pre-auth.py script to reflect whether you want to store
# your credentials in a keyring or on disk. Default is to store
# your credentials in a keyring.
#
# Change into the calendar-v3-python-cmd-line directory and run the 
# pre-auth script:
#
# ./pre-auth.py
#
# This will pop a web page to the Google calendar authentication server.
# Enter your login credentials. Google will return a page that says
# "Authentication process complete" and the pre-auth.py script
# will store your credentials in either your keyring or on disk, depending
# on how you configured it.
#
# Installing the Google API oauth2 dependencies and pre-authentication
# should both be done before running the widget.
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

from apiclient.discovery import build
from oauth2client.client import AccessTokenRefreshError
from oauth2client.client import OAuth2WebServerFlow
from oauth2client.tools import run

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
         'use keyring to store credentials - if false, storage must be set'),
        ('storage', None, 'absolute path of secrets file if keyring=False'),
        ('reminder_color', 'FF0000', 'color of calendar entries during reminder time'),
        ('www_group', 'www', 'group to open browser into'),
        ('www_screen', 0, 'screen to open group on'),
        ('browser_cmd', '/usr/bin/firefox -url calendar.google.com',
         'browser command to execute on click'),
    ]

    def __init__(self, **config):
        base._TextBox.__init__(self, 'Calendar not initialized',
                               width=bar.CALCULATED, **config)

    def _configure(self, qtile, bar):
        base._TextBox._configure(self, qtile, bar)
        self.add_defaults(GoogleCalendar.defaults)
        self.layout = self.drawer.textlayout(
            self.text, self.foreground, self.font,
            self.fontsize, self.fontshadow, markup=True)
        self.timeout_add(self.update_interval, self.cal_update)

    def button_press(self, x, y, button):
        self.update(self.fetch_calendar())
        self.qtile.addGroup(self.www_group)
        self.qtile.groupMap[self.www_group].cmd_toscreen(self.www_screen)
        self.qtile.cmd_spawn(self.browser_cmd)

    def cal_update(self):
        self.update(self.fetch_calendar())
        return True

    def update(self, data):
        if data:
            self.text = self.format.format(**data)
        else:
            self.text = 'No calendar data available'
        self.bar.draw()
        return False

    def fetch_calendar(self):

        # Set up a Flow object to be used for authentication.
        # Add one or more of the following scopes. PLEASE ONLY ADD THE SCOPES YOU
        # NEED. For more information on using scopes please see
        # <https://developers.google.com/+/best-practices>.
        FLOW = OAuth2WebServerFlow(
                client_id='196949979762-5m3j4orcn9heesoh6td942gb2bph424q.apps.googleusercontent.com',
                client_secret='3H1-w_9gX4DFx3bC9c-whEBs',
                scope='https://www.googleapis.com/auth/calendar',
                user_agent='Qtile Google Calendar Widget/Version 0.2')


        # storage is the location of your authentication credentials
        if self.keyring:
            from oauth2client.keyring_storage import Storage
            storage = Storage('qtile_cal', getpass.getuser())
        else:
            from oauth2client.file import Storage
            storage = Storage(self.storage)

        credentials = storage.get()

        if credentials is None or credentials.invalid:
            credentials = run(FLOW, storage)

        # Create an httplib2.Http object to handle our HTTP requests and
        # authorize it with our good Credentials.
        http = httplib2.Http()
        http = credentials.authorize(http)

        service = build('calendar', 'v3', http=http)

        # end of authentication code
        #######################################################
        # beginning of widget code

        now = datetime.datetime.utcnow().isoformat('T')+'Z'
        data = {}

        events = service.events().list(calendarId=self.calendar,
                 singleEvents=True, timeMin=now, maxResults='1',
                 orderBy='startTime').execute()
        try:
            event = events.get('items', [])[0]
        except (IndexError):
            data = {'next_event': 'No appointments scheduled'}
            return data
        try:
            remindertime = datetime.timedelta(0,
            int(event.get('reminders').get('overrides')[0].get('minutes')) * 60)
        except:
            remindertime = datetime.timedelta(0,0)

        data = {'next_event': event['summary']+' '+re.sub(':.{2}-.*$',
                '', event['start']['dateTime'].replace('T', ' '))}
        if dateutil.parser.parse(event['start']['dateTime'],
                ignoretz=True)-remindertime <= datetime.datetime.now():
            data = {'next_event': '<span color="'+utils.hex(self.reminder_color)+
                    '">'+data['next_event']+'</span>'}

        return data
