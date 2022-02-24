from flask import render_template, redirect, url_for, request, session, abort
from flask_login import current_user
from app import db
from app.composeralbums import bp
from app.spotify import sp
from app.models import ComposerList, WorkList, ArtistAlbums
import jsonpickle
import collections


@bp.route('/composeralbums/<name>/<page>')
def composeralbums(name, page):
    session['thispage'] = request.url

    # get filter and search arguments
    artistselect = request.args.get('artist')
    default = artistselect
    if not artistselect:
        artistselect = ""
        default = "Filter by Artist"

    searchselect = request.args.get('search')
    searchplaceholder = searchselect
    if not searchselect:
        searchselect = ""
        searchplaceholder = "Search for Work"

    # get composer
    composer = ComposerList.query.filter_by(name_short=name).first_or_404()

    # user page viewing
    if current_user.is_authenticated:
        current_user.page_viewing = '<a href="' + url_for("composeralbums.composeralbums", name=name, page=page) + '">' + composer.name_full + '</a>'
        db.session.commit()

    # get from the database
    spotifywork = ArtistAlbums.query.filter_by(id=name).first()

    if spotifywork:
        newlist = jsonpickle.decode(spotifywork.results)
        alist = jsonpickle.decode(spotifywork.artists)

        # search and filter
        albumartists = []
        cleanlist = []
        for item in newlist:
            if artistselect in str(item['artists']) and searchselect.lower() in str(item['firstfive']).lower():
                cleanlist.append(item)
                artists = item['artists']
                for artist in artists:
                    for art in artist.split(", "):
                        albumartists.append(art)
            counter = collections.Counter(albumartists)
            item['artists'] = ", ".join(list(dict(counter.most_common(2)).keys()))
            item['all_artists'] = ", ".join(list(set((dict(counter.most_common(8)).keys())) - set(dict(counter.most_common(2)).keys())))
            albumartists = []
        newlist = cleanlist

        # pagination
        current_page = page
        next_page = int(page) + 1
        items_per_page = 25
        from_page = int(current_page) * items_per_page - items_per_page  # 36 per page
        upto_page = int(current_page) * items_per_page
        list_part = newlist[from_page:upto_page]
        url = request.url
        baseurl = request.base_url
        arguments = url.replace(baseurl, "")
        path = str(next_page) + arguments

        return render_template('composeralbums/composeralbums.html', title=name, next_page=path, tracks=list_part, artistselect=default, searchplaceholder=searchplaceholder, composer=composer, artists=alist, autoplay=session['autoplay'])
    return redirect(url_for('main.index'))


@bp.route('/background_load', methods=['GET', 'POST'])
def background_load():
    _id = request.form['id']
    composer = ComposerList.query.filter_by(id=_id).first_or_404()
    work = WorkList.query.filter_by(composer=composer.name_short).first()
    if work:
        return 'EXPLORE', 200

    spotifywork = ArtistAlbums.query.filter_by(id=composer.name_short).first()
    if spotifywork:
        return 'ALBUMS', 200

    # search spotify otherwise
    search_string = composer.name_full
    response = sp.search(search_string)
    results = response.json()
    resultslist = []
    resultslist.append(results)

    try:
        items = results['tracks']['items']
    except:
        return 'ERROR', 403

    # get more results
    nexturl = results['tracks']['next']
    seconds = 10

    resultslist = sp.get_more_results(resultslist, nexturl, seconds, _id)

    # loop to extract data from results
    tracklist = []
    artistlist = []
    for results in resultslist:
        items = results['tracks']['items']
        track = {}

        for item in items:
            # check that composer appears in artists and skip if not
            artists = item['artists']
            checklist = []
            for artist in artists:
                checklist.append(artist['name'])
            checkstring = ' '.join(checklist)
            if not composer.name_full in checkstring:  # CHANGED TO FULL get last part of name_short (ie. for CPE Bach)
                continue

            # get rest of the info
            try:
                track['track_name'] = item['name']
                track['album_name'] = item['album']['name']
                track['release_date'] = item['album']['release_date']
                track['album_id'] = item['album']['id']
                track['album_uri'] = item['album']['uri']
                track['album_img'] = item['album']['images'][1]['url']
                track['popularity'] = item['popularity']
                track['disc_no'] = item['disc_number']
                track['track_no'] = item['track_number']
                track['track_id'] = item['id']
                track['track_uri'] = item['uri']
            except:
                continue

            # get album year only
            year = track['release_date'].split('-')[0]
            track['release_date'] = year

            # get list of album artists but remove composer
            count = 0
            for artist in artists:
                if count < 4:
                    if not composer.name_full in artist['name']:
                        artistlist.append(artist['name'])
                    count += 1
            track['track_artists'] = ', '.join(artistlist)
            if not track['track_artists']:
                track['track_artists'] = composer.name_full
            tracklist.append(track)
            track = {}
            artistlist = []

    # end of for loop. check if any results and return error if none
    if not tracklist:
        abort(403)

    # sort
    tracklist = sorted(tracklist, key=lambda i: (i['album_id'], i['disc_no'], i['track_no']))

    # get unique tracks
    newtracks = []
    for i in range(0, len(tracklist)):
        if i > 0:
            if tracklist[i]['track_id'] != tracklist[i - 1]['track_id']:
                newtracks.append(tracklist[i])
        else:
            newtracks.append(tracklist[i])
    tracks = newtracks

    # get unique albums
    newlist = []
    for i in range(0, len(tracks)):
        if i > 0:
            if tracks[i]['album_id'] != tracks[i - 1]['album_id']:
                newlist.append(tracks[i])
        else:
            newlist.append(tracks[i])

    # score in terms of popularity and track list length and sort
    artistlist = []
    for item in newlist:
        item['tracks'] = []
        item['queue'] = []
        item['artists'] = []
        item['track_count'] = 0
        item['popularity'] = 0
        item['track_count_score'] = 0

        for i in range(0, len(tracks)):
            if item['album_id'] == tracks[i]['album_id']:
                item['queue'].append("spotify:track:" + tracks[i]['track_id'])
                item['tracks'].append([tracks[i]['track_name'], tracks[i]['track_id']])
                item['artists'].append(tracks[i]['track_artists'])
                item['track_count'] += 1
                artists = tracks[i]['track_artists'].split(', ')
                for artist in artists:
                    artistlist.append(artist)

                if tracks[i]['popularity'] > item['popularity']:
                    item['popularity'] = tracks[i]['popularity']

        if item['track_count'] > 3:
            item['track_count_score'] = 3
        else:
            item['track_count_score'] = item['track_count']

        item['track_count_score'] = (item['track_count_score'] / 4) * 100
        item['score'] = item['track_count_score'] + item['popularity']

    newlist = sorted(newlist, key=lambda i: i['score'], reverse=True)

    # queue up the songs
    for item in newlist:
        for i in range(1, len(item['queue']) + 1):
            item['tracks'][-i].append(" ".join(item['queue'][-i:]))

    # create list of artists
    artistlist.sort()
    newartists = []
    count = 0
    countlist = []

    # create ranked list of artists
    for i in range(0, len(artistlist)):
        if i > 0:
            if artistlist[i] != artistlist[i - 1]:
                newartists.append(artistlist[i])
                countlist.append(count)
                count = 0
            else:
                pass
        else:
            newartists.append(artistlist[i])
        count += 1
    countlist.append(count)

    artists = dict(zip(newartists, countlist))  # is this a good method to use?
    alist = []
    for artist in artists:
        alist.append([artist, artists[artist]])
    alist.sort(key=lambda x: x[1], reverse=True)

    # split off first 5 tracks for collapsible display
    for item in newlist:
        item['firstfive'] = item['tracks'][:5]
        item['tracks'] = item['tracks'][5:]

    # encode and store in database.
    jsontracklist = jsonpickle.encode(newlist)
    jsonartistlist = jsonpickle.encode(alist)
    existingspotify = ArtistAlbums.query.filter_by(id=composer.name_short).first()
    if existingspotify:
        existingspotify.results = jsontracklist
        existingspotify.artists = jsonartistlist
        db.session.commit()
    else:
        spotifydata = ArtistAlbums(id=composer.name_short, results=jsontracklist, artists=jsonartistlist)
        db.session.add(spotifydata)
        db.session.commit()

    return "ALBUMS", 200
