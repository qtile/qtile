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
# highlighted. Authentication credentials are stored on disk.
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
# Finally, you need to turn on your own Google Calendar API. You can do
# this by following step 1 from here:
# https://developers.google.com/google-apps/calendar/quickstart/python
# However, save the client_secret.json file to ~/.credentials (the
# storage_file credentials file is also located in ~/.credentials).
#
# Once you have completed the preliminary steps, when you start qtile
# with the GoogleCalendar widget configured, the widget will
# automatically pop an authentication web page. Input your calendar
# login/password and authorize the widget to access your calendar
# data. After you authenticate, you may need to click on the
# "Calendar not initialized." text once to start the calendar
# updating. After you are authenticated, the calendar data will be
# refreshed every 'update_interval' seconds.
#
# You should only need to perform the oauth2 authentication process
# once (unless the credentials file gets destroyed). After the first
# time, reauthentication takes place automatically.
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
import os

from apiclient import discovery
import oauth2client
from oauth2client import client, tools

from libqtile import utils

try:
    import argparse
    flags = argparse.ArgumentParser(parents=[tools.argparser]).parse_args()
except ImportError:
    flags = None

SCOPES = 'https://www.googleapis.com/auth/calendar'
CLIENT_SECRET_FILE = 'client_secret.json'
APPLICATION_NAME = 'Qtile Google Calendar Widget/Version 0.4'

class GoogleCalendar(base.ThreadedPollText):
    '''
        This widget will display the next appointment on your Google calendar
        in the qtile status bar. Appointments within the "reminder" time will
        be highlighted. Authentication credentials are stored in a file on
        disk.
    '''
    orientations = base.ORIENTATION_HORIZONTAL
    defaults = [
        ('calendar', 'primary', 'calendar to use'),
        (
            'storage_file',
            'google-calendar-widget.json',
            'credentials file name'
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
        self.add_defaults(GoogleCalendar.defaults)
        self.text = 'Calendar not initialized.'
        self.default_foreground = self.foreground

    def cred_init(self):
        """Gets valid user credentials from storage.

        If nothing has been stored, or if the stored credentials are invalid,
        the OAuth2 flow is completed to obtain the new credentials.
        """
        home_dir = os.path.expanduser('~')
        credential_dir = os.path.join(home_dir, '.credentials')
        if not os.path.exists(credential_dir):
            os.makedirs(credential_dir)
        credential_path = os.path.join(credential_dir,
                                       self.storage_file)
        secret_path = os.path.join(credential_dir, CLIENT_SECRET_FILE)

        storage = oauth2client.file.Storage(credential_path)
        self.credentials = storage.get()
        flow = client.flow_from_clientsecrets(secret_path, SCOPES)
        flow.user_agent = APPLICATION_NAME

        def get_from_flow(creds, storage):
            if flags:
                self.credentials = tools.run_flow(flow, storage, flags)
            else:
                self.credentials = tools.run(flow, storage)

        if not self.credentials or self.credentials.invalid:
            threading.Timer(
                # wait two seconds for qtile to start...
                2.0,
                get_from_flow,
                args=(self.credentials, storage)
            ).start()

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

        # Create an httplib2.Http object to handle our HTTP requests and
        # authorize it with our credentials from self.cred_init
        http = self.credentials.authorize(httplib2.Http())
        service = discovery.build('calendar', 'v3', http=http)

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
        self.qtile.log.info('calendar json data: %s' % str(events))

        # get items list
        try:
            event = events.get('items', [])[0]
        except IndexError:
            return 'No appointments scheduled'

        # get reminder time
        try:
            remindertime = datetime.timedelta(
                0,
                int(
                    event['reminders']['overrides'][0]['minutes']
                ) * 60
            )
        except (IndexError, ValueError, AttributeError, KeyError):
            remindertime = datetime.timedelta(0, 0)

        time = re.sub(
            ':.{2}-.*$',
            '',
            event['start']['dateTime'].replace('T', ' ')
        )

        data = event['summary'] + ' ' + time

        # colorize the event if it is upcoming
        parse_result = dateutil.parser.parse(event['start']['dateTime'], ignoretz=True)
        if parse_result - remindertime <= datetime.datetime.now():
            self.foreground = utils.hex(self.reminder_color)
        else:
            self.foreground = self.default_foreground

        # XXX: FIXME: qtile dies completely silently if we return unicode here
        # in python2.
        return str(data)
