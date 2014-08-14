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
# This widget also requires the dateutil.parser module.
# If you get a strange "AttributeError: 'module' object has no attribute
# GoogleCalendar" error, you are probably missing a module. Check
# carefully.
#
# Also, note that the first time you run the widget, you will need to
# authenticate. The widget will automatically pop an authentication  web
# page. Add your calendar login/password and authorize the widget to
# access your calendar data and you are good to go. Depending on the
# lifetime of the Google refresh_token, you may be required to
# re-authenticate periodically (shouldn't be more than every two weeks
# or so). After you are authenticated, the calendar data will be
# refreshed every 'update_interval' seconds.
#
# Thanks to the creator of the YahooWeather widget (dmpayton). This code
# borrows liberally from that one.
###################################################################

from . import base
import httplib2
import datetime
import re
import dateutil.parser
import threading

from apiclient.discovery import build
from oauth2client.client import OAuth2WebServerFlow
from oauth2client.tools import run
import oauth2client.file

from libqtile import utils

class GoogleCalendar(base.ThreadedPollText):
    ''' This widget will display the next appointment on your Google calendar
        in the qtile status bar. Appointments within the "reminder" time will
        be highlighted. Authentication credentials are stored in a file on
        disk.
    '''

    defaults = [
        ('calendar', 'primary', 'calendar to use'),
        (
            'format',
            ' {next_event} ',
            'text to display - leave this at the default for now...'
        ),
        (
            'storage_file',
            None,
            'absolute path of secrets file - must be set'
        ),
        (
            'reminder_color',
            'FF0000',
            'color of calendar entries during reminder time'
        ),
        ('www_group', 'www', 'group to open browser into'),
        ('www_screen', 0, 'screen to open group on'),
        (
            'browser_cmd',
            '/usr/bin/firefox -url calendar.google.com',
            'command or script to execute on click'
        ),
    ]

    def __init__(self, **config):
        base.ThreadedPollText.__init__(self, **config)
        self.text = 'Calendar not initialized.'
        self.cred_init()
        # confirm credentials every hour
        self.timeout_add(3600, self.cred_init)

    def _configure(self, qtile, bar):
        base.ThreadedPollText._configure(self, qtile, bar)
        self.add_defaults(GoogleCalendar.defaults)
        self.layout = self.drawer.textlayout(
            self.text,
            self.foreground,
            self.font,
            self.fontsize,
            self.fontshadow,
            markup=True
        )

    def cred_init(self):
        # this is the main method for obtaining credentials
        self.log.info('refreshing GC credentials')

        # Set up a Flow object to be used for authentication.
        FLOW = OAuth2WebServerFlow(
            client_id='196949979762-5m3j4orcn9heesoh6td942gb2bph424q.'
            'apps.googleusercontent.com',
            client_secret='3H1-w_9gX4DFx3bC9c-whEBs',
            scope='https://www.googleapis.com/auth/calendar',
            user_agent='Qtile Google Calendar Widget/Version 0.3'
        )

        # storage is the location of our authentication credentials
        storage = oauth2client.file.Storage(self.storage_file)

        # get the credentials, and update if necessary
        # this method will write the new creds back to disk if they are updated
        self.credentials = storage.get()

        # if the credentials don't exist or are invalid, get new ones from FLOW
        # FLOW must be run in a different thread or it blocks qtile
        # when it tries to pop the authentication web page
        def get_from_flow(creds, storage):
            if creds is None or creds.invalid:
                self.credentials = run(FLOW, storage)
        threading.Thread(
            target=get_from_flow,
            args=(self.credentials, storage)
        ).start()

        return True

    def cal_updater(self):
        self.log.info('adding GC widget timer')

        def cal_getter():  # get cal data in thread, write it in main loop
            data = self.fetch_calendar()
            self.qtile._eventloop.call_soon(self.update, data)
        threading.Thread(target=cal_getter).start()
        return True

    def button_press(self, x, y, button):
        base.ThreadedPollText.button_press(self, x, y, button)
        if hasattr(self, 'credentials'):
            self.qtile.addGroup(self.www_group)
            self.qtile.groupMap[self.www_group].cmd_toscreen(self.www_screen)
            self.qtile.cmd_spawn(self.browser_cmd)

    def poll(self):
        # if we don't have valid credentials, update them
        if not hasattr(self, 'credentials') or self.credentials.invalid:
            self.cred_init()
            data = {'next_event': 'Credentials updating'}
            return data

        # Create an httplib2.Http object to handle our HTTP requests and
        # authorize it with our credentials from self.cred_init
        http = httplib2.Http()
        http = self.credentials.authorize(http)

        service = build('calendar', 'v3', http=http)

        # current timestamp
        now = datetime.datetime.utcnow().isoformat('T') + 'Z'
        data = {}

        # grab the next event
        events = service.events().list(
            calendarId=self.calendar,
            singleEvents=True,
            timeMin=now,
            maxResults='1',
            orderBy='startTime'
        ).execute()

        # get items list
        try:
            event = events.get('items', [])[0]
        except IndexError:
            data = {'next_event': 'No appointments scheduled'}
            return data

        # get reminder time
        try:
            remindertime = datetime.timedelta(
                0,
                int(
                    event.get('reminders').get('overrides')[0].get('minutes')
                ) * 60
            )
        except (IndexError, ValueError, AttributeError):
            remindertime = datetime.timedelta(0, 0)

        # format the data
        data = {
            'next_event': event['summary'] +
            ' ' +
            re.sub(
                ':.{2}-.*$',
                '',
                event['start']['dateTime'].replace('T', ' ')
            )
        }
        parse_result = dateutil.parser.parse(event['start']['dateTime'], ignoretz=True)
        if parse_result - remindertime <= datetime.datetime.now():
            data = {
                'next_event': '<span color="' +
                utils.hex(self.reminder_color) +
                '">' +
                data['next_event'] +
                '</span>'
            }

        # return the data
        return data
