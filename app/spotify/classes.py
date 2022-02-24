from flask import session
from datetime import datetime, timedelta
import six
import base64
import requests
import urllib.parse
import random


class SpotifyAPI(object):
    def __init__(self, client_id, client_secret, client_url):
        self.client_id = client_id
        self.client_secret = client_secret
        self.client_url = client_url

    def authorize(self):
        client_url = urllib.parse.quote(self.client_url)
        url = 'https://accounts.spotify.com/authorize?client_id=' + self.client_id + '&response_type=code&redirect_uri=' + client_url + '&scope=user-read-playback-state user-modify-playback-state user-read-private playlist-read-private playlist-modify-public user-read-currently-playing'
        return url

    def client_authorize(self):
        try:
            OAUTH_TOKEN_URL = "https://accounts.spotify.com/api/token"
            payload = {'grant_type': 'client_credentials'}
            auth_header = base64.b64encode(six.text_type(self.client_id + ":" + self.client_secret).encode("ascii"))
            headers = {"Authorization": "Basic %s" % auth_header.decode("ascii")}
            response = requests.post(OAUTH_TOKEN_URL, data=payload, headers=headers, verify=True)

            token = response.json()['access_token']
            return token
        except KeyError:
            return "INVALID"

    def get_token(self, code):
        try:
            OAUTH_TOKEN_URL = "https://accounts.spotify.com/api/token"
            payload = {'grant_type': 'authorization_code',
                       'code': code,
                       'redirect_uri': self.client_url}
            auth_header = base64.b64encode(six.text_type(self.client_id + ":" + self.client_secret).encode("ascii"))
            headers = {"Authorization": "Basic %s" % auth_header.decode("ascii")}
            response = requests.post(OAUTH_TOKEN_URL, data=payload, headers=headers, verify=True)
            response.json()['access_token']
            return response
        except KeyError:
            return "INVALID"

    def refresh_token(self):
        try:
            OAUTH_TOKEN_URL = "https://accounts.spotify.com/api/token"
            payload = {'grant_type': 'refresh_token',
                       'refresh_token': session['refresh_token']}
            auth_header = base64.b64encode(six.text_type(self.client_id + ":" + self.client_secret).encode("ascii"))
            headers = {"Authorization": "Basic %s" % auth_header.decode("ascii")}
            response = requests.post(OAUTH_TOKEN_URL, data=payload, headers=headers, verify=True)
            token = response.json()['access_token']
            return token
        except:
            return "INVALID"

    def get_devices(self):
        try:
            endpoint_url = "https://api.spotify.com/v1/me/player/devices"
            response = requests.get(endpoint_url,
                                    headers={"Content-Type": "application/json", "Authorization": "Bearer " + session['spotify_token']})
            devices = response.json()['devices']
            return devices
        except:
            return "INVALID"

    def play_from_database(self, data):
        headers = {
            'Accept': 'application/json',
            'Content-Type': 'application/json',
            'Authorization': 'Bearer {}'.format(session['spotify_token']),
        }
        params = (
            ('device_id', session['spotify_device']),
        )
        response = requests.put('https://api.spotify.com/v1/me/player/play', headers=headers, params=params, data=data)
        return response

    def search_and_play(self, artist):
        # search for artist
        headers = {
            'Authorization': 'Bearer {}'.format(session['spotify_token']),
        }
        params = (
            ('q', artist),
            ('type', 'artist'),
            ('limit', '1'),
        )
        response = requests.get('https://api.spotify.com/v1/search', headers=headers, params=params)
        artist = response.json()['artists']['items'][0]['id']

        # play spotify artist
        headers = {
            'Accept': 'application/json',
            'Content-Type': 'application/json',
            'Authorization': 'Bearer {}'.format(session['spotify_token']),
        }
        params = (
            ('device_id', session['spotify_device']),
        )
        data = '{"context_uri":"spotify:artist:' + artist + '","position_ms":50}'
        response2 = requests.put('https://api.spotify.com/v1/me/player/play', headers=headers, params=params, data=data)
        return response2

    def preview_play(self, artist):
        # search for artist
        # headers = {
        #     'Authorization': 'Bearer {}'.format(session['app_token']),
        # }
        # params = (
        #     ('q', artist),
        #     ('type', 'track'),
        #     ('limit', '10'),
        # )
        # response = requests.get('https://api.spotify.com/v1/search', headers=headers, params=params)

        # try:
        #     i = 0
        #     preview_url = response.json()['tracks']['items'][i]['preview_url']
        #     while preview_url is None and i < len(response.json()['tracks']['items'][i]):
        #         preview_url = response.json()['tracks']['items'][i]['preview_url']
        #         # print(preview_url)
        #         i += 1
        #     return str(preview_url)
        # except:
        #     return "None"
        # search for artist
        headers = {
            'Authorization': 'Bearer {}'.format(session['app_token']),
        }
        params = (
            ('q', artist),
            ('type', 'artist'),
            ('limit', '1'),
        )
        response = requests.get('https://api.spotify.com/v1/search', headers=headers, params=params)

        artistid = response.json()['artists']['items'][0]['id']

        headers = {
            'Authorization': 'Bearer {}'.format(session['app_token']),
        }
        response2 = requests.get('https://api.spotify.com/v1/artists/' + str(artistid) + '/top-tracks?market=US', headers=headers)
        try:
            i = 0
            preview_url = None
            no_tracks = len(response2.json()['tracks'])
            while preview_url is None and i < no_tracks:
                # num = random.randint(0, no_tracks - 1)
                preview_url = response2.json()['tracks'][i]['preview_url']
                i += 1
            return str(preview_url)
        except:
            return "None"

    def pause(self):
        headers = {
            'Accept': 'application/json',
            'Content-Type': 'application/json',
            'Authorization': 'Bearer {}'.format(session['spotify_token']),
        }
        response = requests.put('https://api.spotify.com/v1/me/player/pause', headers=headers)
        return response

    def unpause(self):
        headers = {
            'Accept': 'application/json',
            'Content-Type': 'application/json',
            'Authorization': 'Bearer {}'.format(session['spotify_token']),
        }
        response = requests.put('https://api.spotify.com/v1/me/player/play', headers=headers)
        return response

    def test(self, device, track):
        headers = {
            'Accept': 'application/json',
            'Content-Type': 'application/json',
            'Authorization': 'Bearer {}'.format(session['spotify_token']),
        }
        params = (
            ('device_id', device),
        )
        data = track
        response = requests.put('https://api.spotify.com/v1/me/player/play', headers=headers, params=params, data=data)
        return response

    def search(self, search_string):
        headers = {
            'Authorization': 'Bearer {}'.format(session['app_token']),
        }
        params = (
            ('q', search_string),
            ('type', 'track'),
            ('limit', '50'),
        )
        response = requests.get('https://api.spotify.com/v1/search', headers=headers, params=params)
        return response

    def is_playing(self):
        headers = {
            'Accept': 'application/json',
            'Content-Type': 'application/json',
            'Authorization': 'Bearer {}'.format(session['spotify_token']),
        }
        response = requests.get('https://api.spotify.com/v1/me/player/currently-playing', headers=headers)
        return response

    def play_track(self, trackids):

        spotify_track = trackids
        headers = {
            'Accept': 'application/json',
            'Content-Type': 'application/json',
            'Authorization': 'Bearer {}'.format(session['spotify_token']),
        }
        params = (
            ('device_id', session['spotify_device']),
        )
        data = spotify_track
        response = requests.put('https://api.spotify.com/v1/me/player/play', headers=headers, params=params, data=data)
        return response

    def get_user(self):
        headers = {
            'Authorization': 'Bearer {}'.format(session['spotify_token']),
        }
        response = requests.get('https://api.spotify.com/v1/me', headers=headers)
        return response

    def get_playlists(self):
        headers = {
            'Authorization': 'Bearer {}'.format(session['spotify_token']),
        }
        params = (
            ('limit', '50'),
        )
        response = requests.get('https://api.spotify.com/v1/me/playlists', headers=headers, params=params)
        return response

    def create_playlist(self, new_playlist):
        headers = {
            'Accept': 'application/json',
            'Content-Type': 'application/json',
            'Authorization': 'Bearer {}'.format(session['spotify_token']),
        }
        data = '{"name":"' + new_playlist + '","description":"Playlist created with ComposerExplorer.com"}'
        response = requests.post('https://api.spotify.com/v1/users/' + session['userid'] + '/playlists', headers=headers, data=data)
        return response

    def add_to_playlist(self, playlist_id, uristring):
        headers = {
            'Accept': 'application/json',
            'Content-Type': 'application/json',
            'Authorization': 'Bearer {}'.format(session['spotify_token']),
        }
        params = (
            ('uris', uristring),
        )
        response = requests.post('https://api.spotify.com/v1/playlists/' + playlist_id + '/tracks', headers=headers, params=params)
        return response

    def next(self):
        headers = {
            'Authorization': 'Bearer {}'.format(session['spotify_token']),
        }
        response = requests.post('https://api.spotify.com/v1/me/player/next', headers=headers)
        return response

    def get_more_results(self, resultslist, nexturl, time, _id):
        stoptime = datetime.now() + timedelta(seconds=time)
        while nexturl and datetime.now() < stoptime:
            headers = {
                'Authorization': 'Bearer {}'.format(session['app_token']),
            }
            response = requests.get(nexturl, headers=headers)
            results = response.json()
            try:
                nexturl = results['tracks']['next']
            except:
                if results['error']['status'] == 429:
                    resultslist = "429"
                    return resultslist
                break
            resultslist.append(results)
        return resultslist

    def get_album(self, albumid):
        headers = {
            'Authorization': 'Bearer {}'.format(session['app_token']),
        }
        response = requests.get('https://api.spotify.com/v1/albums/' + albumid, headers=headers)
        return response

    def get_more_album(self, url):
        headers = {
            'Authorization': 'Bearer {}'.format(session['app_token']),
        }
        response = requests.get(url, headers=headers)
        return response

    def previous(self):
        headers = {
            'Authorization': 'Bearer {}'.format(session['spotify_token']),
        }
        response = requests.put('https://api.spotify.com/v1/me/player/seek?position_ms=0', headers=headers)
        return response

    def get_track(self, _id):
        headers = {
            'Authorization': 'Bearer {}'.format(session['spotify_token']),
        }
        response = requests.get('https://api.spotify.com/v1/tracks/' + _id, headers=headers)
        return response

    def get_track_preview(self, _id):
        headers = {
            'Authorization': 'Bearer {}'.format(session['app_token']),
        }
        response = requests.get('https://api.spotify.com/v1/tracks/' + _id, headers=headers)
        url = response.json()['preview_url']
        return url

    def current_track(self):
        headers = {
            'Authorization': 'Bearer {}'.format(session['spotify_token']),
        }
        response = requests.get('https://api.spotify.com/v1/me/player/currently-playing', headers=headers)
        return response

    def seek_to_position(self, position):
        headers = {
            'Authorization': 'Bearer {}'.format(session['spotify_token']),
        }
        response = requests.put('https://api.spotify.com/v1/me/player/seek?position_ms=' + str(position), headers=headers)
        return response
