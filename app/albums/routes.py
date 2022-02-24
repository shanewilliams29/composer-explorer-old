from flask import render_template, flash, redirect, url_for, request, session, current_app, abort
from flask_login import current_user, login_required
from sqlalchemy import func, text
from app import db, log
from app.albums import bp
from app.albums.forms import PostForm
from app.albums.classes import GroupAlbums, jumbotron
from app.spotify import sp
from app.spotify.functions import search_spotify_and_save
from app.models import WorkAlbums, Comment, WorkList, Spotify, Artists, AlbumLike, User
import jsonpickle


@bp.route('/albums/<work_id>', methods=['GET', 'POST'])
def albums(work_id):

    session['thispage'] = request.base_url
    page = request.args.get('page', 1, type=int)
    next_page = int(page) + 1

    # get filter and search arguments
    artistselect = request.args.get('artist')
    searchselect = request.args.get('search')
    search = None

    if artistselect:
        default = artistselect
        search = "%{}%".format(artistselect)
        searchplaceholder = ""
    elif searchselect:
        search = "%{}%".format(searchselect)
        default = "Filter by Artist"
        searchplaceholder = request.args.get('search')
    else:
        searchplaceholder = ""
        default = "Filter by Artist"

    # get work from database and spotify search table
    work = WorkList.query.filter_by(id=work_id).first_or_404()

    # user page viewing
    if current_user.is_authenticated:
        current_user.page_viewing = '<a href="' + url_for("albums.albums", work_id=work_id) + '">' + work.composer + ": " + work.title + '</a>'
        db.session.commit()

    if search:
        albums = db.session.query(WorkAlbums, func.count(AlbumLike.id).label('total')) \
            .filter(WorkAlbums.workid == work_id, WorkAlbums.hidden != True, WorkAlbums.artists.ilike(search)) \
            .outerjoin(AlbumLike).group_by(WorkAlbums) \
            .order_by(text('total DESC'), WorkAlbums.score.desc()).paginate(page, 25, False)
        albums_count = db.session.query(WorkAlbums).filter(WorkAlbums.workid == work_id, WorkAlbums.hidden != True, WorkAlbums.artists.ilike(search)).count()
    else:
        albums = db.session.query(WorkAlbums, func.count(AlbumLike.id).label('total')) \
            .filter(WorkAlbums.workid == work_id, WorkAlbums.hidden != True).outerjoin(AlbumLike).group_by(WorkAlbums) \
            .order_by(text('total DESC'), WorkAlbums.score.desc()).paginate(page, 25, False)
        albums_count = db.session.query(WorkAlbums).filter(WorkAlbums.workid == work_id, WorkAlbums.hidden != True).count()

    if not albums.items and not search and page == 1:  # prepare albums and artists if no albums, disable for pagination
        abort(404)

    work_artists = db.session.query(Artists, func.count(Artists.count).label('total')) \
        .filter(Artists.workid == work_id).group_by(Artists.name) \
        .order_by(text('total DESC'), Artists.name).all()

    if not albums.items:
        flash("No search results.", "info")

    # decode album data and append likes and hidden value
    album_list = []
    for tup in albums.items:
        item = jsonpickle.decode(tup[0].data)
        item['likes'] = tup[1]
        item['hidden'] = tup[0].hidden
        album_list.append(item)

    # split off first 5 tracks for collapsible display
    for item in album_list:
        item['firstfive'] = item['tracks'][:5]
        item['tracks'] = item['tracks'][5:]

    # create links for next and previous buttons
    workspotify = db.session.query(Spotify.id)\
        .join(WorkList, WorkList.id == Spotify.id)\
        .order_by(WorkList.order, WorkList.date, WorkList.id)\
        .filter_by(composer=work.composer).all()
    workspotify = [r for (r,) in workspotify]

    previouswork = workspotify[workspotify.index(work_id) - 1]
    try:
        nextwork = workspotify[workspotify.index(work_id) + 1]
    except IndexError:
        nextwork = workspotify[0]

    # get jumbotron image url
    imgurl = jumbotron(work)

    # play first spotify track if coming from another page
    playfirsttrack = False
    if session['premium'] and session['autoplay']:
        if session['previouspage'] != session['thispage']:
            playfirsttrack = True

    session['previouspage'] = request.base_url
    next_url = url_for('albums.albums', work_id=work_id, page=next_page,
                       artist=request.args.get('artist'), search=request.args.get('search')) if albums.has_next else None

    # commenting system
    posts = Comment.query.filter(Comment.workid == work_id).order_by(Comment.timestamp.desc()).all()
    form = PostForm()

    if form.validate_on_submit():
        if current_user.is_authenticated:
            comment = Comment(body=form.post.data, author=current_user, workid=work_id)
            db.session.add(comment)
            db.session.commit()
            flash('Your comment has been added!', "success")
            return redirect(url_for('albums.albums', work_id=work_id))
        flash('Please log in to add comments.', "danger")
        return redirect(url_for('albums.albums', work_id=work_id))

    return render_template('albums/albums.html', playfirsttrack=playfirsttrack, form=form, posts=posts, imgurl=imgurl, next_page=next_url,
                           nextwork=nextwork, previouswork=previouswork, tracks=album_list, work=work,
                           searchplaceholder=searchplaceholder, artistselect=default,
                           artists=work_artists, autoplay=session['autoplay'], current_app=current_app,
                           title=work.title, albums=albums, albums_count=albums_count)


@ bp.route('/like/<album_id>/<action>')
def like_action(album_id, action):
    if current_user.is_authenticated:
        album = WorkAlbums.query.filter_by(id=album_id).first()
        if action == 'like':
            current_user.like_album(album)
            db.session.commit()
        if action == 'unlike':
            current_user.unlike_album(album)
            db.session.commit()
        return redirect(url_for("albums.albums", work_id=album.workid))
    else:
        flash("Please log in to like albums.", "danger")
        return redirect(request.referrer)


@ bp.route('/visit/<work_id>/<action>')
def visit(work_id, action):
    if current_user.is_authenticated:
        work = WorkList.query.filter_by(id=work_id).first_or_404()
        if action == 'visit':
            current_user.visit(work)
            db.session.commit()
        if action == 'unvisit':
            current_user.unvisit(work)
            db.session.commit()
        return redirect(request.referrer)
    else:
        flash("Please log in to track works you've listened to.", "danger")
        return redirect(request.referrer)


@ bp.route('/delete_comment/<post_id>')
@ login_required
def delete_comment(post_id):
    comment = Comment.query.filter(Comment.id == post_id).first()
    if comment.user_id == current_user.id or current_user.admin:
        db.session.delete(comment)
        db.session.commit()
        flash('Comment deleted.', 'info')
    else:
        flash('You do not have the permissions to delete this comment.', 'danger')
    return redirect(request.referrer)


@bp.route('/get_album_likes', methods=['GET', 'POST'])
@ login_required
def get_album_likes():
    try:
        _id = request.form['id']
    except KeyError:
        abort(403)

    users = db.session.query(User) \
        .join(AlbumLike) \
        .filter(AlbumLike.album_id == _id) \
        .all()

    return jsonpickle.encode(users)


@ bp.route('/delete_tracks', methods=['GET', 'POST'])
@ login_required
def delete_tracks():
    if not current_user.admin:
        return "Forbidden.", 403

    tracks = request.form['tracks']
    work_id = request.form['workid']

    track_list = jsonpickle.decode(tracks)

    if not track_list:
        return "No tracks selected.", 404

    for track in track_list:
        search = "%{}%".format(track)
        album = WorkAlbums.query.filter(WorkAlbums.workid == work_id, WorkAlbums.data.ilike(search)).first()
        if not album:
            return "Album not found.", 404

        album_data = jsonpickle.decode(album.data)

        # delete the track
        i = 0
        for item in album_data['tracks']:
            if track in item[1]:
                album_data['tracks'].pop(i)
            i += 1

        # remove track from playlist in other tracks
        for item in album_data['tracks']:
            string = 'spotify:track:' + track
            item[2] = item[2].replace(string, "")

        album.data = jsonpickle.encode(album_data)
        db.session.commit()

    return "Tracks deleted successfully!"
