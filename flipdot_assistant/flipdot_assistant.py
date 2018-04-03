# -*- coding: utf-8 -*-

"""Main module."""
from __future__ import print_function

import click
import os.path
import json

import google.auth.transport.requests
import google.oauth2.credentials

from google.assistant.library import Assistant
from google.assistant.library.event import EventType
from geopy.geocoders import Nominatim

from flipapps.flipapps import FlipApps, Sign

# from flipdot_assistant.power import Power


DEVICE_API_URL = 'https://embeddedassistant.googleapis.com/v1alpha2'
ADDRESS = 1
WIDTH = 84
HEIGHT = 7
MIN_WRITE_INTERVAL_S = 2
DEFAULT_CREDENTIALS_FILE = os.path.join(
    os.path.expanduser('~/.config'),
    'google-oauthlib-tool',
    'credentials.json'
)


class FlipdotAssistant(object):
    def __init__(self, port: str, sign: Sign, credentials, device_model_id, project_id=None):
        # Create a google assistant client
        self.assistant = Assistant(credentials, device_model_id)

        # Register device if necessary
        if project_id:
            self.register_device(
                project_id,
                credentials,
                device_model_id,
                self.assistant.device_id)

        # Create flip apps suite
        self.flipapps = FlipApps(port, sign)

    def __enter__(self):
        self.flipapps.__enter__()
        self.assistant.__enter__()
        return self

    def __exit__(self, type, value, traceback):
        self.assistant.__exit__(type, value, traceback)
        self.flipapps.__exit__(type, value, traceback)

    def run(self):
        events = self.assistant.start()
        for event in events:
            self.process_event(event, self.assistant.device_id)

    def show_weather(self, params):
        coordinates = None
        if params['location']:
            location_query = params['location']
            geolocator = Nominatim()
            location = geolocator.geocode(location_query)
            coordinates = (location.latitude, location.longitude)
        self.flipapps.weather(coordinates=coordinates)

    def show_time(self, _):
        self.flipapps.clock()

    def show_message(self, params):
        text = params['message']
        self.flipapps.text(text)

    def process_event(self, event, device_id):
        """Pretty prints events.
        Prints all events that occur with two spaces between each new
        conversation and a single space between turns of a conversation.
        Args:
            event(event.Event): The current event to process.
            device_id(str): The device ID of the new instance.
        """
        if event.type == EventType.ON_CONVERSATION_TURN_STARTED:
            print()
        print(event)

        if (event.type == EventType.ON_CONVERSATION_TURN_FINISHED and
                event.args and not event.args['with_follow_on_turn']):
            print()
        if event.type == EventType.ON_DEVICE_ACTION:
            for command, params in FlipdotAssistant.process_device_actions(
                    event, device_id):
                print('Do command', command, 'with params', str(params))

                if command == "com.briggysmalls.commands.show_weather":
                    self.show_weather(params)
                elif command == "com.briggysmalls.commands.show_time":
                    self.show_time(params)
                elif command == "com.briggysmalls.commands.show_message":
                    self.show_message(params)

    @staticmethod
    def process_device_actions(event, device_id):
        if 'inputs' in event.args:
            for i in event.args['inputs']:
                if i['intent'] == 'action.devices.EXECUTE':
                    for c in i['payload']['commands']:
                        for device in c['devices']:
                            if device['id'] == device_id:
                                if 'execution' in c:
                                    for e in c['execution']:
                                        if 'params' in e:
                                            yield e['command'], e['params']
                                        else:
                                            yield e['command'], None

    @staticmethod
    def register_device(project_id, credentials, device_model_id, device_id):
        """Register the device if needed.
        Registers a new assistant device if an instance with the given id
        does not already exists for this model.
        Args:
           project_id(str): The project ID used to register device instance.
           credentials(google.oauth2.credentials.Credentials): The Google
                    OAuth2 credentials of the user to associate the device
                    instance with.
           device_model_id(str): The registered device model ID.
           device_id(str): The device ID of the new instance.
        """
        base_url = '/'.join([DEVICE_API_URL, 'projects', project_id, 'devices'])
        device_url = '/'.join([base_url, device_id])
        session = google.auth.transport.requests.AuthorizedSession(credentials)
        r = session.get(device_url)
        print(device_url, r.status_code)
        if r.status_code == 404:
            print('Registering....')
            r = session.post(base_url, data=json.dumps({
                'id': device_id,
                'model_id': device_model_id,
                'client_type': 'SDK_LIBRARY'
            }))
            if r.status_code != 200:
                raise Exception('failed to register device: ' + r.text)
            print('\rDevice registered.')


@click.command()
@click.option(
    '--credentials',
    default=DEFAULT_CREDENTIALS_FILE,
    help='Path to store and read OAuth2 credentials')
@click.option(
    '--device_model_id', help='The device model ID registered with Google')
@click.option(
    '--project_id',
    help='The project ID used to register device instances.')
@click.option(
    '--port', help='The USB port to connect to the sign over')
@click.version_option()
def main(credentials, device_model_id, project_id, port):
    with open(credentials, 'r') as credentials_file:
        credentials = google.oauth2.credentials.Credentials(
            token=None, **json.load(credentials_file))

    sign = Sign(
        ADDRESS,
        WIDTH,
        HEIGHT,
        flip=True,
        min_write_inteval=MIN_WRITE_INTERVAL_S)
    with FlipdotAssistant(port,
                          sign,
                          credentials,
                          device_model_id,
                          project_id) as assistant:
        assistant.run()


if __name__ == '__main__':
    main()
