from datetime import datetime, timedelta
from flask import render_template, flash, redirect, url_for, request, session, current_app
from flask_login import login_user, current_user
from app import db
from app.spotify import bp, sp
from app.spotify.forms import SpotifyForm
from app.spotify.functions import search_spotify_and_save
from app.user.classes import get_avatar
from app.models import User, ComposerList, Spotify, WorkAlbums, WorkList
import jsonpickle
from wtforms import SubmitField, RadioField
import base64
import hashlib
from sqlalchemy.orm import load_only
from sqlalchemy.sql import func
import random


@bp.route('/connect_spotify')
def connect_spotify():
    url = sp.authorize()
    return redirect(url)


@bp.route('/spotify')
def spotify():

    # get access token
    code = request.args.get('code')
    response = sp.get_token(code)
    if response == "INVALID":
        flash("Could not connect to Spotify.")
        return render_template('errors/flash.html')
    session['spotify_token'] = response.json()['access_token']
    session['refresh_token'] = response.json()['refresh_token']
    session['spotify_token_expire_time'] = datetime.now() + timedelta(hours=1)

    # get playback devices
    session['available_devices'] = sp.get_devices()
    if session['available_devices'] == "INVALID":
        session['available_devices'] = None
        flash("Could not connect to Spotify.")
        return render_template('errors/flash.html', title="Error")
    return redirect(url_for('spotify.spotify_form'))


@bp.route('/spotify_form', methods=['GET', 'POST'])
def spotify_form():
    session['spotify_device'] = ""
    if current_user.is_authenticated:
        pass
    else:
        response = sp.get_user()
        info = response.json()
        try:
            session['userid'] = info['id']
            _id = info['id'] + current_app.config['SECRET_KEY']
        except KeyError:
            flash("Could not connect to Spotify.")
            return render_template('errors/flash.html')

        if info['product'] == "premium":
            session['premium'] = True
        else:
            session['premium'] = False

        hasher = hashlib.sha1(_id.encode('utf-8'))
        username = base64.urlsafe_b64encode(hasher.digest()[:10]).decode('utf-8')
        username = ''.join(e for e in username if e.isalnum()).upper()
        user = User.query.filter_by(username=username).first()
        if user is None:
            display_name = info['display_name']
            try:
                image_url = info['images'][0]['url']
                response = get_avatar(username, image_url)
                image = response[0]
            except:
                image = None

            duplicateuser = User.query.filter_by(display_name=display_name).first()
            if duplicateuser:
                display_name = display_name + str(random.randint(1, 999))

            user = User(username=username, email=username + "@none.com", display_name=display_name, img=image)
            user.set_password(username)
            db.session.add(user)
            db.session.commit()
            login_user(user)
        login_user(user)

    devicelist = session['available_devices']
    # check if there are any devices, show form if so
    if not session['premium']:
        flash("Note: In-browser playback requires Spotify premium. With a free account, clicking on album tracks will link to the track in Spotify rather than play them directly.")
        return render_template('spotify/spotify_free.html')

    if len(devicelist) == 0:
        flash("Error: no active Spotify playback devices found.")
        form = SpotifyForm()
        return render_template('spotify/spotify_form.html', form=form)
    else:
        devices = {}
        for i in range(0, len(devicelist)):
            devices[devicelist[i]['id']] = devicelist[i]['name']
        choices = []
        for device in devices:
            choices.append((device, devices[device]))
        setattr(SpotifyForm, 'device', RadioField("device", choices=choices, default=choices[0][0]))
        setattr(SpotifyForm, 'test', SubmitField('Test'))
        setattr(SpotifyForm, 'submit', SubmitField('Select'))

    form = SpotifyForm()
    if form.validate_on_submit():
        session['spotify_device'] = form.device.data
        session['available_devices'] = []  # necessary for form to display properly
        del form.device
        return redirect(session['previouspage'])
    return render_template('spotify/spotify_form.html', form=form, title="Select Spotify Device")


@bp.route('/play_spotify', methods=['GET', 'POST'])
def play_spotify():
    # plays music for composer preview if a token exists
    if session['premium'] and session['autoplay']:
        _id = request.form['id']
        composer = ComposerList.query.filter_by(id=_id).first()
        spotify_track = composer.spotify
        if spotify_track:
            response = sp.play_from_database(spotify_track)
        else:
            response = sp.search_and_play(composer.name_full)
        return str("Premium")
    elif session['premium'] and not session['autoplay']:
        return str("Premium")
    else:
        _id = request.form['id']
        composer = ComposerList.query.filter_by(id=_id).first()
        preview_url = composer.preview_music
        return str(preview_url)


@bp.route('/play_spotify_preview_track', methods=['GET', 'POST'])
def play_spotify_preview_track():
    # plays music for composer preview if a token exists
    _id = request.form['id']
    preview_url = sp.get_track_preview(_id)
    print(preview_url)
    if preview_url is not None:
        return str(preview_url)
    return "No spotify preview available", 404


@bp.route('/pause_spotify', methods=['GET', 'POST'])
def pause_spotify():
    if session['premium'] and session['autoplay']:
        response = sp.pause()
        return str(response)
    return "No spotify token or autoplay off."


@bp.route('/unplay_spotify', methods=['GET', 'POST'])
def unplay_spotify():
    if session['premium']:
        response = sp.pause()
        return str(response)
    return "No spotify token."


@bp.route('/unpause_spotify', methods=['GET', 'POST'])
def unpause_spotify():
    if session['premium']:
        response = sp.unpause()
        return str(response)
    return "No spotify token."


@bp.route('/test_spotify', methods=['GET', 'POST'])
def test_spotify():
    if session['premium']:
        try:
            device = request.form['device']
            spotify_track = '{"uris": ["spotify:track:2q7eAC2QXXNLaEBQZfWgG5"]}'
            response = sp.test(device, spotify_track)
            return str(response)
        except:
            return "Invalid spotify token."
    return "No spotify token."


@bp.route('/search_spotify', methods=['GET', 'POST'])
def search_spotify():
    # doesn't actually search spotify anymore (moved searching to cron tasks)
    _id = request.form['id']

    existingspotify = Spotify.query.filter_by(id=_id).first()
    if existingspotify:
        return "Exists"

    return 'No Spotify tracks found.', 404


@bp.route('/play_track', methods=['GET', 'POST'])
def play_track():

    _id = request.form['id']
    urilist = {}
    urilist['uris'] = _id.split()
    jsonlist = jsonpickle.encode(urilist)

    first_track_id = urilist['uris'][0].replace("spotify:track:", "")

    if session['premium']:
        response = sp.play_track(jsonlist)
        trackjson = sp.get_track(first_track_id)
        track = trackjson.json()
        track_length = track['duration_ms']
        return str(track_length)
    return "Connect with Spotify to play tracks.", 403


@bp.route('/seek_track', methods=['GET', 'POST'])
def seek_track():

    position = request.form['position']

    if session['premium']:
        response = sp.seek_to_position(position)
        response2 = sp.unpause()
        return str(response)
    return "Connect with Spotify to play tracks.", 403


@bp.route('/next_track')
def next_track():

    response = sp.next()
    trackjson = sp.current_track()
    track = trackjson.json()
    track_length = track['item']['duration_ms']
    return str(track_length)


@bp.route('/previous_track')
def previous_track():

    response = sp.previous()
    trackjson = sp.current_track()
    track = trackjson.json()
    track_length = track['item']['duration_ms']
    return str(track_length)


@bp.route('/get_playlists')
def get_playlists():
    if session['spotify_token']:
        try:
            # first get user's profile info
            response = sp.get_user()
            userid = response.json()['id']
            session['userid'] = userid

            # then get user's playlists
            response = sp.get_playlists()
            playlists = response.json()['items']

            playlistlist = []
            reverse_dict = {}
            for playlist in playlists:
                playuserid = playlist['owner']['id']
                if playuserid == userid:
                    playlistlist.append(playlist['name'])
                    reverse_dict[playlist['name']] = playlist['id']

            session['user_playlists'] = reverse_dict
            return jsonpickle.encode(playlistlist)
        except:
            return "Error with token.", 500
    return "Connect with Spotify to create and add music to playlists.", 403


@bp.route('/playlist_add')
def playlist_add():

    if session['spotify_token']:
        new_playlist = request.args.get('new-playlist')
        existing_playlist = request.args.get('existing-playlist')
        tracks = request.args.get('tracks')

        if len(tracks) == 2:  # if [] is empty
            flash("Error: No tracks were selected.", "danger")
            return redirect(session['thispage'])

        if new_playlist:
            playlist_name = new_playlist
            try:
                response = sp.create_playlist(new_playlist)
                playlist_id = response.json()['id']
            except:
                return "Issue with token."

        elif existing_playlist == "Choose":
            flash("Error: No playlist was selected or created.", "danger")
            return redirect(session['thispage'])
        else:
            playlist_name = existing_playlist
            playlist_id = session['user_playlists'][existing_playlist]  # won't work for duplicate named playlists

        # submit tracks to spotify
        tracklist = jsonpickle.decode(tracks)
        uristring = ""
        for track in tracklist:
            track = "spotify:track:" + track + ","
            uristring = uristring + track
        response = sp.add_to_playlist(playlist_id, uristring)
        flash("Success. Tracks have been added to playlist \"" + playlist_name + "\".", "success")
        return redirect(session['thispage'])
    flash("You must be logged in with Spotify to do that!", "danger")
    return redirect(session['thispage'])


@bp.route('/are_you_playing')
def are_you_playing():
    isplaying = ""
    if session['premium']:
        try:
            response_list = []
            responsejson = sp.is_playing()
            response = responsejson.json()
            isplaying = str(response['is_playing'])
            track = str(response['item']['id'])
            progress = str(response['progress_ms'])
            duration = str(response['item']['duration_ms'])
            title = str(response['item']['name'])
            try:
                img = str(response['item']['album']['images'][2]['url'])
            except:
                img = "/static/album_placeholder.png"
            response_list.append(track)
            response_list.append(progress)
            response_list.append(duration)
            response_list.append(title)
            response_list.append(img)
        except:
            return "Invalid spotify token."
    else:
        return "No spotify token."

    if isplaying == "True":
        return jsonpickle.encode(response_list)
    else:
        return 'No!', 403


@bp.route('/autoplay', methods=['GET', 'POST'])
def autoplay():
    value = request.form['value']
    if value == "True":
        session['autoplay'] = True
    else:
        session['autoplay'] = False
    return str(session['autoplay'])


@bp.route('/composer_playlist')
def composer_playlist():

    if session['spotify_token']:
        composer = request.args.get('composer')
        name = request.args.get('name')
        grouping = request.args.get('grouping')
        popularity = request.args.get('popularity')
        operas = request.args.get('operas', False)

        num_tracks = 50

        # create plylist
        try:
            response = sp.create_playlist(name)
            playlist_id = response.json()['id']
        except:
            return "Issue with token."

        # filtering
        if operas:
            if popularity == "obscure":
                albums = db.session.query(WorkAlbums).join(WorkList).filter(WorkAlbums.composer == composer, WorkList.recommend == None).order_by(func.random()).limit(num_tracks).all()
            elif popularity == "recommend":
                albums = db.session.query(WorkAlbums).join(WorkList).filter(WorkAlbums.composer == composer, WorkList.recommend).order_by(func.random()).limit(num_tracks).all()
            else:
                albums = db.session.query(WorkAlbums).filter_by(composer=composer).order_by(func.random()).limit(num_tracks).all()
        else:
            if popularity == "obscure":
                albums = db.session.query(WorkAlbums).join(WorkList).filter(WorkAlbums.composer == composer, WorkList.recommend == None, WorkList.genre != "Opera").order_by(func.random()).limit(num_tracks).all()
            elif popularity == "recommend":
                albums = db.session.query(WorkAlbums).join(WorkList).filter(WorkAlbums.composer == composer, WorkList.recommend, WorkList.genre != "Opera").order_by(func.random()).limit(num_tracks).all()
            else:
                albums = db.session.query(WorkAlbums).join(WorkList).filter(WorkAlbums.composer == composer, WorkList.genre != "Opera").order_by(func.random()).limit(num_tracks).all()

        tracklist = []

        # grouping
        if grouping == "tracks":
            for album in albums:
                album = jsonpickle.decode(album.data)

                random_index = random.randint(0, len(album['tracks']) - 1)
                track = album['tracks'][random_index]
                tracklist.append(track[1])
        else:
            for album in albums:
                album = jsonpickle.decode(album.data)

                for track in album['tracks']:
                    tracklist.append(track[1])

        # submit tracks to spotify
        uristring = ""
        for track in tracklist[:num_tracks]:
            track = "spotify:track:" + track + ","
            uristring = uristring + track

        response = sp.add_to_playlist(playlist_id, uristring)

        flash("Success. Tracks have been added to playlist \"" + name + "\".")
        return redirect(request.referrer)
    flash("You must be logged in with Spotify to do that!")
    return playlist_id
