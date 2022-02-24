from flask import render_template, redirect, url_for, request, session, abort, flash
from flask_login import current_user
from sqlalchemy.orm import load_only
from app import db
from app.composer import bp
from app.spotify import sp
from app.models import ComposerList, WorkList, Spotify, ArtistAlbums
from app.composer.classes import ComposerHeader, BornDied, Masterpieces
import json
import random
import math


@bp.route('/composer_router/<name>')
def composer_router(name):
    if not session.get('composer_view'):
        if request.MOBILE:
            session['composer_view'] = "tables"
        else:
            session['composer_view'] = "tables"

    if session['composer_view'] == "timeline":
        return redirect(url_for('composer.composer', name=name))

    return redirect(url_for('composer.composerpanels', name=name))


@bp.route('/composer/<name>')
def composer(name):
    session['composer_view'] = "timeline"

    filter_method = request.args.get('filter', "playable")
    search = request.args.get('search', "")

    # check if composer has been catalogued or redirect to albums page
    try:
        work = WorkList.query.filter_by(composer=name).first_or_404()
    except:
        return redirect('/composeralbums/' + name + '/1')

    try:
        # get composer information
        composer = ComposerList.query.filter_by(name_short=name).first_or_404()
    except Exception:
        return redirect(url_for('main.index'))

    # user page viewing
    if current_user.is_authenticated:
        current_user.page_viewing = '<a href="' + url_for("composer.composer", name=name) + '">' + composer.name_full + '</a>'
        db.session.commit()

    # get flag
    with open('app/static/countries.json') as f:
        flags = json.load(f)
    flag = flags[composer.nationality]
    flag = flag.lower()
    composer.flagimg = 'flags/1x1/' + flag + '.svg'

    # get masterpieces
    with open('app/static/masterpieces.json') as f:
        masterpiece_list = json.load(f)

    # create chart
    array = []
    array.append(composer)
    header = ComposerHeader(array, composer.born, composer.died)  # change back
    years = header.generate_dates(composer)
    ages = header.generate_ages(years, composer.born, composer.died)
    eras = header.generate_eras()
    yearlist = list(years.keys())
    borndied = BornDied(composer.born, composer.died, yearlist[0], yearlist[-1])
    master = Masterpieces(masterpiece_list, yearlist[0], yearlist[-1])
    masterpieces = master.generate_masterpieces()
    # retrieve all composer works
    catalogued = []

    if search:
        search_term = "%{}%".format(search)
        filter_method = 'all'
        works = WorkList.query.filter_by(composer=name)\
            .filter(WorkList.genre.ilike(search_term)) \
            .order_by(WorkList.order, WorkList.genre, WorkList.date, WorkList.cat, WorkList.id).all()
        if not works:
            works = WorkList.query.filter_by(composer=name)\
                .filter(WorkList.title.ilike(search_term)) \
                .order_by(WorkList.order, WorkList.genre, WorkList.date, WorkList.cat, WorkList.id).all()
        if not works:
            works = WorkList.query.filter_by(composer=name)\
                .filter(WorkList.cat.ilike(search_term)) \
                .order_by(WorkList.order, WorkList.genre, WorkList.date, WorkList.cat, WorkList.id).all()
        if not works:
            filter_method = 'playable'
            works = db.session.query(WorkList)\
                .join(Spotify, WorkList.id == Spotify.id)\
                .filter_by(composer=name)\
                .order_by(WorkList.order, WorkList.genre, WorkList.date, WorkList.cat, WorkList.id).all()
        workspotify = db.session.query(Spotify)\
            .join(WorkList, WorkList.id == Spotify.id)\
            .options(load_only(Spotify.id))\
            .filter_by(composer=name)
        for item in workspotify:
            catalogued.append(item.id)

    else:
        if filter_method == "recommended":
            works = WorkList.query.filter_by(composer=name, recommend=True).order_by(WorkList.order, WorkList.genre, WorkList.date, WorkList.cat, WorkList.id).all()
        elif filter_method == "playable":
            works = db.session.query(WorkList)\
                .join(Spotify, WorkList.id == Spotify.id)\
                .filter_by(composer=name)\
                .order_by(WorkList.order, WorkList.genre, WorkList.date, WorkList.cat, WorkList.id).all()
        else:
            works = WorkList.query.filter_by(composer=name)\
                .order_by(WorkList.order, WorkList.genre, WorkList.date, WorkList.cat, WorkList.id).all()
            workspotify = db.session.query(Spotify)\
                .join(WorkList, WorkList.id == Spotify.id)\
                .options(load_only(Spotify.id))\
                .filter_by(composer=name)
            for item in workspotify:
                catalogued.append(item.id)

    if not works:
        abort(404)

    workslist = header.create_chart(works)

    # for random work
    num = random.randint(0, len(workslist) - 1)
    random_work = workslist[num].id

    # get list of which works has_visited
    visitlist = []
    if current_user.is_authenticated:
        has_visited = current_user.all_visits()
        for item in has_visited:
            if item.composer == composer.name_short:
                visitlist.append(item.id)

    return render_template('composer/composer.html',
                           visitlist=visitlist, search=search, random_work=random_work, filter_method=filter_method,
                           composer=composer, catalogued=catalogued, borndied=borndied, eras=eras, math=math,
                           years=years, svgheight=header.svgheight, works=workslist, title=name, ages=ages, masterpieces=masterpieces)


@bp.route('/composerpanels/<name>')
def composerpanels(name):
    session['composer_view'] = "tables"

    filter_method = request.args.get('filter', "recommended")

    # check if composer has been catalogued or redirect to albums page
    try:
        work = WorkList.query.filter_by(composer=name).first_or_404()
    except:
        return redirect('/composeralbums/' + name + '/1')

    try:
        # get composer information
        composer = ComposerList.query.filter_by(name_short=name).first_or_404()
    except Exception:
        return redirect(url_for('main.index'))

    # user page viewing
    if current_user.is_authenticated:
        current_user.page_viewing = '<a href="' + url_for("composer.composer", name=name) + '">' + composer.name_full + '</a>'
        db.session.commit()

    # get flag
    with open('app/static/countries.json') as f:
        flags = json.load(f)
    flag = flags[composer.nationality]
    flag = flag.lower()
    composer.flagimg = 'flags/1x1/' + flag + '.svg'

    # create chart
    array = []
    array.append(composer)
    header = ComposerHeader(array, composer.born, composer.died)  # change back
    eras = header.generate_eras()
    # retrieve all composer works
    catalogued = []

    if filter_method == "recommended":
        works = WorkList.query.filter_by(composer=name, recommend=True).order_by(WorkList.order, WorkList.genre, WorkList.id).all()
        genre_list = db.session.query(WorkList.genre.distinct()).order_by(WorkList.order, WorkList.genre, WorkList.id)\
            .filter(WorkList.composer == composer.name_short, WorkList.recommend == True)
    elif filter_method == "playable":
        works = db.session.query(WorkList)\
            .join(Spotify, WorkList.id == Spotify.id)\
            .filter_by(composer=name)\
            .order_by(WorkList.order, WorkList.genre, WorkList.id).all()
        # improve this later if less genres than all
        genre_list = db.session.query(WorkList.genre.distinct()).order_by(WorkList.order, WorkList.genre, WorkList.id)\
            .filter(WorkList.composer == composer.name_short)
    else:
        works = WorkList.query.filter_by(composer=name)\
            .order_by(WorkList.order, WorkList.genre, WorkList.id).all()
        workspotify = db.session.query(Spotify)\
            .join(WorkList, WorkList.id == Spotify.id)\
            .options(load_only(Spotify.id))\
            .filter_by(composer=name)
        genre_list = db.session.query(WorkList.genre.distinct()).order_by(WorkList.order, WorkList.genre, WorkList.id)\
            .filter(WorkList.composer == composer.name_short)
        for item in workspotify:
            catalogued.append(item.id)

    if not works:
        abort(404)

    workslist = header.create_chart(works)

    # genre list

    # for random work
    num = random.randint(0, len(workslist) - 1)
    random_work = workslist[num].id

    # get list of which works has_visited
    visitlist = []
    if current_user.is_authenticated:
        has_visited = current_user.all_visits()
        for item in has_visited:
            if item.composer == composer.name_short:
                visitlist.append(item.id)

    # genre split for display rendering
    if filter_method == "recommended":
        num_works = len(works)
        median_work_num = int(math.ceil(num_works / 2))
        median_work_genre = works[median_work_num].genre

        i = 0
        for genre in genre_list:
            i += 1
            if genre[0] == median_work_genre:
                break
        if genre_list.count() > 1:
            split_work_genre = genre_list[i][0]
        else:
            split_work_genre = genre_list[0][0]
    else:
        num_genres = genre_list.count()
        median_genre_num = int(math.ceil(num_genres / 2))
        split_work_genre = genre_list[median_genre_num][0]

    return render_template('composer/composerpanels.html',
                           visitlist=visitlist, random_work=random_work, median_work_genre=split_work_genre, filter_method=filter_method,
                           composer=composer, catalogued=catalogued, eras=eras, math=math,
                           svgheight=header.svgheight, works=workslist, title=name)


@bp.route('/workfinder')
def workfinder():
    if not session.get('workfinder_composer'):
        session['workfinder_composer'] = "Beethoven"

    composer_name = request.args.get('composer', "Beethoven")
    genre = request.args.get('genre', "")

    composer = ComposerList.query.filter_by(name_short=composer_name).first()

    if composer:
        if composer_name != session['workfinder_composer']:
            session['workfinder_composer'] = composer_name
            genre = ""

        genres = []
        for value in db.session.query(WorkList.genre).filter(WorkList.composer == composer_name).order_by(WorkList.order).distinct():
            genres.append(value[0])

        if not genre:
            genre = genres[0]

        works = WorkList.query \
            .filter(WorkList.composer == composer_name,
                    WorkList.genre == genre) \
            .order_by(WorkList.composer,
                      WorkList.order,
                      WorkList.genre,
                      WorkList.id).all()

        # composer list for typeahead
        composers = db.session.query(ComposerList.name_short)\
            .join(WorkList, ComposerList.name_short == WorkList.composer)\
            .order_by(ComposerList.name_short).distinct()

        if not works:
            abort(404)

        return render_template('composer/workfinder.html',
                               genre1=genre, genres=genres, composer_name=composer_name, composer=composer, composers=composers, math=math, works=works, title="WorkFinder")

  # composer list for typeahead
    composers = db.session.query(ComposerList.name_short)\
        .join(WorkList, ComposerList.name_short == WorkList.composer)\
        .order_by(ComposerList.name_short).distinct()
    flash("No search results.")
    return render_template('composer/workfinder.html',
                           composers=composers, composer="", composer_name=composer_name, math=math, title="WorkFinder")
