from flask import render_template, flash, redirect, url_for, current_app, request
from flask_login import current_user, login_required
from app import db
from app.admin import bp
from app.albums.classes import GroupAlbums, SmartAlbums
from app.spotify.functions import search_album
from app.admin.forms import ClearComposer, SpotifyAdd, AddAlbum, SumAlbums, NullForm, FillAlbums
from app.models import Spotify, Artists, ComposerList, WorkAlbums, WorkList


@bp.route('/admin', methods=['GET', 'POST'])
@login_required
def admin():
    if not current_user.admin:
        return redirect(url_for('main.index'))

    form = NullForm()
    flash('Welcome to the administration database functions.')

    return render_template('admin/admin.html', form=form)


@bp.route('/admin_delete', methods=['GET', 'POST'])
@login_required
def admin_delete():
    if not current_user.admin:
        return redirect(url_for('main.index'))

    form = ClearComposer()
    if form.validate_on_submit():
        if form.composer.data:
            spotifyworks = db.session.query(Spotify).filter_by(composer=form.composer.data).all()
            if not spotifyworks:
                flash('Invalid entry for composer.')
                return redirect(url_for('admin.admin_delete'))
            db.session.query(Spotify).filter_by(composer=form.composer.data).delete()
            db.session.flush()
            db.session.query(Artists).filter_by(composer=form.composer.data).delete()
            db.session.flush()
            db.session.query(WorkAlbums).filter_by(composer=form.composer.data).delete()
            db.session.flush()
            db.session.commit()
            flash('Composer has been deleted.')
            return redirect(url_for('admin.admin_delete'))
        elif form.work.data:
            spotifyworks = db.session.query(Spotify).filter_by(id=form.work.data).all()
            if not spotifyworks:
                flash('Invalid entry for Work.')
                return redirect(url_for('admin.admin_delete'))
            db.session.query(Spotify).filter_by(id=form.work.data).delete()
            db.session.flush()
            db.session.query(Artists).filter_by(workid=form.work.data).delete()
            db.session.flush()
            db.session.query(WorkAlbums).filter_by(workid=form.work.data).delete()
            db.session.flush()
            db.session.commit()
            flash('Work has been deleted.')
            return redirect(url_for('admin.admin_delete'))
        elif form.album.data:
            albumwork = db.session.query(WorkAlbums).filter_by(id=form.album.data).first()
            if not albumwork:
                flash('Invalid entry for AlbumWork.')
                return redirect(url_for('admin.admin_delete'))
            db.session.query(Artists).filter_by(album_id=form.album.data).delete()
            db.session.flush()
            db.session.query(WorkAlbums).filter_by(id=form.album.data).delete()
            db.session.flush()
            db.session.commit()
            flash('Album has been deleted.')
            return redirect(url_for('admin.admin_delete'))
        else:
            flash('Nothing was entered.')
            return redirect(url_for('admin.admin_delete'))

    return render_template('admin/admin.html', form=form)


@bp.route('/admin_album_fill', methods=['GET', 'POST'])
@login_required
def admin_album_fill():
    if not current_user.admin:
        return redirect(url_for('main.index'))

    form = FillAlbums()
    if form.validate_on_submit():
        albumwork = form.work.data + form.album.data
        if albumwork:
            spotifyworks = db.session.query(WorkAlbums).filter_by(id=albumwork).all()
            if not spotifyworks:
                flash('Invalid entry.')
                return redirect(url_for('admin.admin_album_fill'))
            db.session.query(Artists).filter_by(album_id=albumwork).delete()
            db.session.flush()
            db.session.query(WorkAlbums).filter_by(id=albumwork).delete()
            db.session.flush()
            db.session.commit()

            uri = form.album.data
            work = db.session.query(WorkList).filter_by(id=form.work.data).first()

            tracks = search_album(uri, work)
            albums = GroupAlbums(tracks, work)

            flash('Album has been filled successfully.')
            return redirect(url_for('admin.admin_album_fill'))
        else:
            flash('Nothing was entered.')
            return redirect(url_for('admin.admin_album_fill'))

    return render_template('admin/admin.html', form=form)


@bp.route('/admin_easyfill', methods=['GET', 'POST'])
@login_required
def admin_easyfill():
    if not current_user.admin:
        return redirect(url_for('main.index'))

    workid = request.args.get('work', '', type=str)
    albumid = request.args.get('album', '', type=str)

    if workid and albumid:
        spotifyworks = db.session.query(WorkAlbums).filter_by(id=albumid).all()
        if not spotifyworks:
            flash('Invalid album id.', 'danger')
            return redirect(url_for('albums.albums', work_id=workid))
        db.session.query(Artists).filter_by(album_id=albumid).delete()
        db.session.flush()
        # db.session.query(WorkAlbums).filter_by(id=albumid).delete()
        # db.session.flush()
        db.session.commit()

        uri = albumid.replace(workid, "")
        work = db.session.query(WorkList).filter_by(id=workid).first()

        tracks = search_album(uri, work)
        albums = SmartAlbums(tracks, work)

        flash('Album has been filled successfully.', 'success')
        return redirect(url_for('albums.albums', work_id=workid))
    else:
        flash('No album id entered.', 'danger')
        return redirect(url_for('albums.albums', work_id=workid))

    flash('Error.', 'danger')
    return redirect(url_for('albums.albums', work_id=workid))


@bp.route('/hide_album', methods=['GET', 'POST'])
@login_required
def hide_album():
    if not current_user.admin:
        return redirect(url_for('main.index'))

    workid = request.args.get('work', '', type=str)
    albumid = request.args.get('album', '', type=str)

    if workid and albumid:
        spotifywork = db.session.query(WorkAlbums).filter_by(id=albumid).first()
        if not spotifywork:
            flash('Invalid album id.', 'danger')
            return redirect(url_for('albums.albums', work_id=workid))
        db.session.query(Artists).filter_by(album_id=albumid).delete()
        db.session.flush()
        spotifywork.hidden = True
        db.session.flush()
        db.session.commit()

        flash('Album has been hidden.', 'success')
        return redirect(url_for('albums.albums', work_id=workid))
    else:
        flash('No album id entered.', 'danger')
        return redirect(url_for('albums.albums', work_id=workid))

    flash('Error.', 'danger')
    return redirect(url_for('albums.albums', work_id=workid))

# don't use this


@bp.route('/fill_all', methods=['GET', 'POST'])
@login_required
def fill_all():
    if not current_user.admin:
        return redirect(url_for('main.index'))

    workid = request.args.get('work', '', type=str)

    i = 0

    if workid:
        workalbums = db.session.query(WorkAlbums).filter_by(workid=workid).all()
        if not workalbums:
            flash('Invalid work id.', 'danger')
            return redirect(url_for('albums.albums', work_id=workid))
        for album in workalbums:
            if i < 10:
                uri = album.album_id
                work = db.session.query(WorkList).filter_by(id=album.workid).first()

                db.session.query(Artists).filter_by(album_id=album.id).delete()
                db.session.flush()
                db.session.query(WorkAlbums).filter_by(id=album.id).delete()
                db.session.flush()
                db.session.commit()

                tracks = search_album(uri, work)
                albums = SmartAlbums(tracks, work)
                i += 1
            else:
                break

        flash('Albums have been filled successfully.', 'success')
        return redirect(url_for('albums.albums', work_id=workid))
    else:
        flash('No album id entered.', 'danger')
        return redirect(url_for('albums.albums', work_id=workid))

    flash('Error.', 'danger')
    return redirect(url_for('albums.albums', work_id=workid))


@bp.route('/admin_spotify', methods=['GET', 'POST'])
@login_required
def admin_spotify():
    if not current_user.admin:
        return redirect(url_for('main.index'))

    form = SpotifyAdd()
    if form.validate_on_submit():
        composer = db.session.query(ComposerList).filter_by(name_short=form.composer.data).first()
        if not composer:
            flash('Invalid entry for composer.')
            return redirect(url_for('admin.admin_spotify'))
        uri = form.uri.data
        offset = str(int(form.trackno.data) - 1)
        position = form.position.data
        composer.spotify = '{"context_uri": "' + uri + '", "offset": {"position": ' + offset + '}, "position_ms": ' + position + '}'
        db.session.commit()
        flash('Spotify data has been updated.')
        return redirect(url_for('admin.admin_spotify'))
    return render_template('admin/admin.html', form=form)


@bp.route('/add_album', methods=['GET', 'POST'])
@login_required
def add_album():
    if not current_user.admin:
        return redirect(url_for('main.index'))

    form = AddAlbum()
    if form.validate_on_submit():
        work = db.session.query(WorkList).filter_by(id=form.workid.data).first()
        if not work:
            flash('Invalid entry for work.')
            return redirect(url_for('admin.add_album'))
        uri = form.uri.data

        tracks = search_album(uri, work)
        albums = GroupAlbums(tracks, work)

        flash('Album has been added.')
        return redirect(url_for('admin.add_album'))
    return render_template('admin/admin.html', form=form)


@bp.route('/sum_albums', methods=['GET', 'POST'])
@login_required
def sum_albums():
    if not current_user.admin:
        return redirect(url_for('main.index'))

    form = SumAlbums()
    if form.validate_on_submit():
        works = db.session.query(WorkList).filter_by(composer=form.composer.data).all()
        if not works:
            flash('Invalid entry for composer.')
            return redirect(url_for('admin.sum_albums'))

        for work in works:
            work.album_count = work.albums.count()

        db.session.commit()
        flash('Album count has been added.')
        return redirect(url_for('admin.sum_albums'))
    return render_template('admin/admin.html', form=form)
