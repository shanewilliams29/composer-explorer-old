from datetime import datetime, timedelta
from flask import current_app, jsonify, render_template, flash, url_for, request, session, send_from_directory, abort, redirect
from flask_login import current_user, login_required
from wtforms import SelectField, SubmitField
# from google.cloud import logging
from app import db, cache
from app.main import bp
from app.main.forms import DatabaseForm
from app.spotify import sp
from app.models import ComposerList, WorkList, Artists, User, WorkAlbums, AlbumLike
from app.main.classes import ComposerChart, SortFilter, SearchObject, Artist
import json
import jsonpickle
from sqlalchemy import func, text
import math


@bp.before_app_request
def before_request():
    # redirect to https
    if "localhost:5000" in request.url:
        pass
    else:
        if not request.is_secure:
            url = request.url.replace('http://', 'https://', 1)
            code = 301
            return redirect(url, code=code)

    # get spotify token
    if not session.get('spotify_token'):
        session['spotify_token'] = None

    if not session.get('app_token'):
        session['app_token'] = sp.client_authorize()
        session['app_token_expire_time'] = datetime.now() + timedelta(hours=1)

    # token expiry and refresh
    if session['app_token_expire_time'] < datetime.now():
        session['app_token'] = sp.client_authorize()
        session['app_token_expire_time'] = datetime.now() + timedelta(hours=1)
    if session['spotify_token']:
        if session['spotify_token_expire_time'] < datetime.now():
            session['spotify_token'] = sp.refresh_token()
            session['spotify_token_expire_time'] = datetime.now() + timedelta(hours=1)

    # initialize session variables
    if not session.get('previouspage'):
        session['previouspage'] = url_for('main.index')
    try:
        session['autoplay']
    except Exception:
        session['autoplay'] = True
    if not session.get('premium'):
        session['premium'] = False

    # user last seen
    if current_user.is_authenticated:
        session['welcome_off'] = True
        current_user.last_seen = datetime.utcnow()
        # current_user.page_viewing = ""
        db.session.commit()


@bp.route('/robots.txt')
def static_from_root():
    return send_from_directory('static', 'robots.txt')


@bp.route('/disclaimer')
def diclaimer():
    return render_template('disclaimer.html', title='Disclaimer')


@bp.route('/', methods=['GET', 'POST'])
@bp.route('/index', methods=['GET', 'POST'])
def index():
    # view routing
    view = request.args.get('view')
    if view:
        session['home_view'] = view

    if session.get('home_view') is None:
        if request.MOBILE:
            session['home_view'] = "tables"
        else:
            session['home_view'] = "tables"

    if session['home_view'] == "tables":
        return redirect(url_for('main.tables'))

    # user page viewing
    if current_user.is_authenticated:
        current_user.page_viewing = '<a href="' + url_for("main.index") + '">' + 'Home' + '</a>'
        db.session.commit()

    # for highlighting catalogued composers
    distinct = []
    for value in db.session.query(WorkList.composer).distinct():
        str(distinct.append(value[0]))

    # default values on first load
    if session.get('sortmethod') is None:
        session['sortmethod'] = "region"
    if session.get('erafilter') is None:
        session['erafilter'] = "Common"

    # stop Spotify playback
    if session['premium'] and session['autoplay']:
        sp.pause()

    # sort disable, disable for some filters
    disable_sort = False

    # look for search item
    search_item = request.args.get('search')
    composer_filter = request.args.get('filter')

    if search_item:
        search = "%{}%".format(search_item)
        composers = ComposerList.query \
            .filter(ComposerList.name_norm.ilike(search)) \
            .order_by(ComposerList.born).all()
        datemin = 1000
        datemax = 2200
        if len(composers) < 1:
            flash("No search results.")

    elif composer_filter:
        disable_sort = True
        if composer_filter == "women":
            composers = ComposerList.query \
                .filter(ComposerList.female == True) \
                .order_by(ComposerList.born).all()
            datemin = 1000
            datemax = 2200
        if composer_filter == "catalogued":
            composers = db.session.query(ComposerList)\
                .join(WorkList, ComposerList.name_short == WorkList.composer)\
                .order_by(ComposerList.born).all()
            datemin = 1500
            datemax = 2200
    else:
        # look for era from url
        era = request.args.get('era')
        if era:
            session['erafilter'] = era

        # get min and max dates for filter, default sort method from era
        sortfilter = SortFilter()
        date_minmax_sort = sortfilter.get_era_filter(session['erafilter'])
        datemin = date_minmax_sort[0]
        datemax = date_minmax_sort[1]
        session['sortmethod'] = date_minmax_sort[2]

        # override sort method if argument in URL
        method = request.args.get('sort')
        if method:
            session['sortmethod'] = method

        # perform database query based on above parameters
        if session['sortmethod'] == 'region':
            composers = ComposerList.query \
                .filter(ComposerList.born >= datemin, ComposerList.born < datemax) \
                .order_by(ComposerList.region, ComposerList.born).all()
        elif session['sortmethod'] == 'birth':
            composers = ComposerList.query \
                .filter(ComposerList.born >= datemin, ComposerList.born < datemax) \
                .order_by(ComposerList.born).all()
        elif session['sortmethod'] == 'death':
            composers = ComposerList.query \
                .filter(ComposerList.born >= datemin, ComposerList.born < datemax) \
                .order_by(ComposerList.died).all()
        elif session['sortmethod'] == 'popularity':
            composers = ComposerList.query \
                .filter(ComposerList.born >= datemin, ComposerList.born < datemax) \
                .order_by(ComposerList.clicks.desc(), ComposerList.rank.desc(), ComposerList.born).all()
        else:
            pass

        # get min and max dates for view range
        date_minmax_sort = sortfilter.get_era_view(session['erafilter'])
        datemin = date_minmax_sort[0]
        datemax = date_minmax_sort[1]

    # create the SVG chart
    chart = ComposerChart(composers, datemin, datemax)
    chart.create_chart()
    years = chart.generate_dates()
    eras = chart.generate_eras()

    # get composer order list for previous and next buttons
    composer_order = []
    for composer in composers:
        composer_order.append(composer.id)
    session['composer_id_list'] = composer_order

    now_year = datetime.now().year
    current_year = chart.get_x_position(now_year)

    if search_item:
        search = search_item
    else:
        search = ""

    return render_template('index.html', disable_sort=disable_sort, distinct=distinct, title='Home',
                           chart=chart,
                           search=search, eras=eras, years=years, composers=chart.composers,
                           current_year=current_year)


@ bp.route('/close_welcome')
def close_welcome():
    session['welcome_off'] = True
    return redirect(url_for('main.index'))


@ bp.route('/close_patreon')
def close_patreon():
    session['patreon_off'] = True
    return redirect(request.referrer)


@ bp.route('/disable_patreon_link')
@ login_required
def disable_patreon_link():
    if current_user.is_authenticated:
        user = User.query.filter(User.id == current_user.id).first_or_404()
        user.patreon = True
        db.session.commit()
        flash("Patreon banner has been disabled for your account.")
        return redirect(url_for('user.user', username=current_user.username))
    return redirect(url_for('main.index'))


@ bp.route('/search')
def search():
    page = request.args.get('page', 1, type=int)

    fields = SearchObject(request.args.get('composer', "", type=str),
                          request.args.get('genre', "", type=str),
                          request.args.get('title', "", type=str),
                          request.args.get('cat', "", type=str))

    composer = "%{}%".format(fields.composer)
    genre = "%{}%".format(fields.genre)
    genre = genre.replace(" ", "%")
    title = "%{}%".format(fields.title)
    title = title.replace(" ", "%")
    cat = '%'.join(e for e in fields.cat if e.isalnum())
    cat = "%{}%".format(cat)

    if request.args.get('composer'):
        comp = ComposerList.query.filter(ComposerList.name_norm.ilike(composer)).first()
        if comp:
            name = comp.name_short
        else:
            name = ""
    else:
        name = "%%"
    results = WorkList.query \
        .filter(WorkList.composer.ilike(name),
                WorkList.genre.ilike(genre),
                WorkList.title.ilike(title),
                WorkList.cat.ilike(cat)) \
        .order_by(WorkList.composer,
                  WorkList.order,
                  WorkList.title).paginate(page, 100, False)

    if not results.items and not title:
        title = genre
        genre = "%%"
        results = WorkList.query \
            .filter(WorkList.composer.ilike(name),
                    WorkList.genre.ilike(genre),
                    WorkList.title.ilike(title),
                    WorkList.cat.ilike(cat)) \
            .order_by(WorkList.composer,
                      WorkList.order,
                      WorkList.title).paginate(page, 100, False)

    if not results.items:
        flash("No search results.")

    # composer list for typeahead
    composers = db.session.query(ComposerList.name_short)\
        .join(WorkList, ComposerList.name_short == WorkList.composer)\
        .order_by(ComposerList.name_short).distinct()

    next_url = url_for('main.search',
                       page=results.next_num,
                       composer=request.args.get('composer'),
                       genre=request.args.get('genre'),
                       title=request.args.get('title'),
                       cat=request.args.get('cat')) if results.has_next else None

    return render_template('search.html', next_page=next_url, composers=composers, results=results, fields=fields, title=' Work Search')


@bp.route('/artists')
def artists():
    page = request.args.get('page', 1, type=int)

    fields = Artist(request.args.get('artist', "", type=str),
                    request.args.get('composer', "", type=str),
                    request.args.get('genre', "", type=str),
                    request.args.get('title', "", type=str),
                    request.args.get('cat', "", type=str))

    # artist list for typeahead
    artist_list = db.session.query(Artists.name)\
        .distinct()

    if not fields.check:
        return render_template('search_artists.html', artist_list=artist_list, fields=fields, results=None, title='Artist Search')

    # artistname = "%{}%".format(fields.artist)
    artistname = fields.artist
    composer = "%{}%".format(fields.composer)
    genre = "%{}%".format(fields.genre)
    genre = genre.replace(" ", "%")
    title = "%{}%".format(fields.title)
    title = title.replace(" ", "%")
    cat = '%'.join(e for e in fields.cat if e.isalnum())
    cat = "%{}%".format(cat)

    results = db.session.query(Artists).join(WorkList) \
        .filter(Artists.name == artistname,
                WorkList.composer.ilike(composer),
                WorkList.genre.ilike(genre),
                WorkList.title.ilike(title),
                WorkList.cat.ilike(cat))\
        .group_by(Artists.name, WorkList.id) \
        .order_by(Artists.name,
                  WorkList.composer,
                  WorkList.order,
                  WorkList.title).paginate(page, 100, False)

    if not results.items and not title:
        title = genre
        genre = "%%"
        results = db.session.query(Artists).join(WorkList) \
            .filter(Artists.name == artistname,
                    WorkList.composer.ilike(composer),
                    WorkList.genre.ilike(genre),
                    WorkList.title.ilike(title),
                    WorkList.cat.ilike(cat)) \
            .group_by(Artists.name, WorkList.id) \
            .order_by(Artists.name,
                      WorkList.composer,
                      WorkList.order,
                      WorkList.title).paginate(page, 100, False)

    if not results.items:
        flash("No search results.")

    next_url = url_for('main.artists', page=results.next_num, artist=request.args.get('artist'),
                       composer=request.args.get('composer'), genre=request.args.get('genre'),
                       title=request.args.get('title'),
                       cat=request.args.get('cat')) if results.has_next else None

    return render_template('search_artists.html', artist_list=artist_list, next_page=next_url, results=results, fields=fields, title='Artist Search')


@bp.route('/get_composer', methods=['GET', 'POST'])
def get_composer():
    try:
        _id = request.form['id']
    except KeyError:
        abort(403)
    composer = ComposerList.query.filter_by(id=_id).first_or_404()
    composer.clicks = composer.clicks + 1
    db.session.commit()

    # get flag
    with open('app/static/countries.json') as f:
        flags = json.load(f)
    flag = flags[composer.nationality].lower()
    composer.flagimg = 'flags/1x1/{}.svg'.format(flag)

    # get next and previous composer
    for i in range(len(session['composer_id_list'])):
        if session['composer_id_list'][i] == composer.id:
            if len(session['composer_id_list']) == 1:
                composer.previous = "break"
                composer.next = "break"
            elif i == 0:
                composer.previous = "break"
                composer.next = session['composer_id_list'][i + 1]
            elif i == (len(session['composer_id_list']) - 1):
                composer.previous = session['composer_id_list'][i - 1]
                composer.next = "break"
            else:
                composer.previous = session['composer_id_list'][i - 1]
                composer.next = session['composer_id_list'][i + 1]
    return jsonpickle.encode(composer)


@bp.route('/database', methods=['GET', 'POST'])
@login_required
def database():
    current_app.config['JSON_AS_ASCII'] = False

    # get catalogued composers
    distinct = []
    for value in db.session.query(WorkList.composer).distinct():
        str(distinct.append(value[0]))

    form = DatabaseForm()
    choices = []
    for item in distinct:
        choices.append((item, item))
    setattr(DatabaseForm, 'composer', SelectField("Select Composer", choices=choices))
    setattr(DatabaseForm, 'submit', SubmitField('Select'))

    if form.validate_on_submit():
        results = WorkList.query \
            .filter(WorkList.composer == form.composer.data) \
            .order_by(WorkList.composer,
                      WorkList.order,
                      WorkList.title).all()
        del form
        return jsonify(results)

    return render_template('database.html', form=form, title='Database')


@bp.route('/top_composers')
def top_composers():
    users = request.args.get('users', "", type=int)

    if users:
        composers = db.session.query(ComposerList, func.count(ComposerList.id).label('total')) \
            .join(User, ComposerList.favorites).group_by(ComposerList) \
            .order_by(text('total DESC')).all()
    else:
        composers = db.session.query(WorkList, func.count(WorkList.id).label('total')) \
            .join(WorkAlbums) \
            .group_by(WorkList.composer) \
            .order_by(text('total DESC')).limit(150).all()

    print(len(composers))
    ranking = []
    this_rank = 1
    ranking.append(this_rank)
    for i in range(1, len(composers)):
        if composers[i][1] == composers[i - 1][1]:
            ranking.append(this_rank)
        else:
            this_rank += 1
            ranking.append(this_rank)

    print(str(ranking))

    return render_template("top_composers.html", title='Top Composers', users=users, composers=composers, ranking=ranking)


@bp.route('/top_works')
def top_works():
    users = request.args.get('users', "", type=int)

    if users:
        works = db.session.query(WorkList, func.count(WorkList.id).label('total')) \
            .join(WorkAlbums) \
            .join(AlbumLike) \
            .group_by(WorkList) \
            .order_by(text('total DESC')).limit(150).all()
    else:
        works = db.session.query(WorkList, func.count(WorkList.id).label('total')) \
            .join(WorkAlbums) \
            .group_by(WorkList) \
            .order_by(text('total DESC')).limit(150).all()

    ranking = []
    this_rank = 1
    ranking.append(this_rank)
    for i in range(1, len(works)):
        if works[i][1] == works[i - 1][1]:
            ranking.append(this_rank)
        else:
            this_rank += 1
            ranking.append(this_rank)

    return render_template("top_works.html", users=users, title='Top Works', works=works, ranking=ranking)


@bp.route('/top_performances')
@cache.cached(timeout=3600)
def top_performances():
    albums = db.session.query(WorkAlbums, func.count(AlbumLike.id).label('total')) \
        .join(AlbumLike).group_by(WorkAlbums) \
        .order_by(text('total DESC'), WorkAlbums.score.desc()).paginate(1, 150, False)

    album_list = []
    for tup in albums.items:
        item = jsonpickle.decode(tup[0].data)
        item['likes'] = tup[1]
        item['composer'] = tup[0].composer
        item['work'] = tup[0].work.title
        item['work_id'] = tup[0].work.id
        album_list.append(item)

    ranking = []
    this_rank = 1
    ranking.append(this_rank)
    for i in range(1, len(album_list)):
        if album_list[i]['likes'] == album_list[i - 1]['likes']:
            ranking.append(this_rank)
        else:
            this_rank += 1
            ranking.append(this_rank)

    return render_template("top_performances.html", title='Top Performances', albums=album_list, ranking=ranking)


@bp.route('/top_artists')
@cache.cached(timeout=604800)
def top_artists():
    # albums = db.session.query(WorkAlbums, func.count(AlbumLike.id).label('total')) \
    #     .join(AlbumLike).group_by(WorkAlbums) \
    #     .order_by(text('total DESC'), WorkAlbums.score.desc()).paginate(1, 100, False)

    artists = db.session.query(Artists, func.count(Artists.id).label('total'))\
        .group_by(Artists.name).order_by(text('total DESC')).paginate(1, 100, False)

    artist_list = []
    for artist in artists.items:
        item = {}
        item['name'] = artist[0].name
        item['recordings'] = artist[1]
        artist_list.append(item)

    ranking = []
    this_rank = 1
    ranking.append(this_rank)
    for i in range(1, len(artist_list)):
        if artist_list[i]['recordings'] == artist_list[i - 1]['recordings']:
            ranking.append(this_rank)
        else:
            this_rank += 1
            ranking.append(this_rank)

    return render_template("top_artists.html", title='Top Artists', artist_list=artist_list, artists=artists, ranking=ranking)


@bp.route('/tables', methods=['GET', 'POST'])
def tables():
    # view routing
    session['home_view'] = "tables"

    # user page viewing
    if current_user.is_authenticated:
        current_user.page_viewing = '<a href="' + url_for("main.tables") + '">' + 'Home' + '</a>'
        db.session.commit()

    # for highlighting catalogued composers, add this?
    # distinct = []
    # for value in db.session.query(WorkList.composer).distinct():
    #     str(distinct.append(value[0]))

    # stop Spotify playback
    if session['premium'] and session['autoplay']:
        sp.pause()

    # look for search item
    search_item = request.args.get('search')
    composer_filter = request.args.get('filter')
    composer_era = request.args.get('era')

    # default to popular if no criteria
    if not search_item and not composer_filter and not composer_era:
        composer_filter = "popular"

    if search_item:
        search = "%{}%".format(search_item)
        composers = ComposerList.query \
            .filter(ComposerList.name_norm.ilike(search)) \
            .order_by(ComposerList.region, ComposerList.born).all()
        datemin = 1000
        datemax = 2200
        title = 'Composers matching "' + search_item + '"'
        if len(composers) < 1:
            flash("No search results.")

    elif composer_filter:
        if composer_filter == "women":
            title = "Women Composers"
            composers = ComposerList.query \
                .filter(ComposerList.female == True) \
                .order_by(ComposerList.region, ComposerList.born).all()
        if composer_filter == "catalogued":
            title = "Catalogued Composers"
            composers = db.session.query(ComposerList)\
                .join(WorkList, ComposerList.name_short == WorkList.composer)\
                .order_by(ComposerList.region, ComposerList.born).all()

        if composer_filter == "popular":
            title = "Popular Composers"
            composers = db.session.query(ComposerList)\
                .filter(ComposerList.catalogued == True) \
                .order_by(ComposerList.region, ComposerList.born).all()

    else:
        # look for era from url
        era = request.args.get('era')
        if era:
            session['tables_erafilter'] = era
            if era.lower() == "common":
                title = "Common Practice Composers"
            else:
                title = era.capitalize() + " Composers"

        # get min and max dates for filter, default sort method from era
        sortfilter = SortFilter()
        date_minmax_sort = sortfilter.get_era_filter(session['tables_erafilter'])
        datemin = date_minmax_sort[0]
        datemax = date_minmax_sort[1]

        # perform database query based on above parameters
        composers = ComposerList.query \
            .filter(ComposerList.born >= datemin, ComposerList.born < datemax) \
            .order_by(ComposerList.region, ComposerList.born).all()

    # get flag icons and proper region names
    with open('app/static/countries.json') as f:
        flags = json.load(f)

    with open('app/static/regions.json') as f:
        region_names = json.load(f)

    for composer in composers:
        composer.region_name = region_names[composer.region]
        composer.flag = flags[composer.nationality].lower()

    # get era
    with open('app/static/eras.json') as f:
        eras = json.load(f)
    for composer in composers:
        median_age = (composer.died - composer.born) / 2
        median_year = median_age + composer.born
        for era in eras:
            if median_year > era[1]:
                composer.era = era[1]
                composer.era_colour = era[3]

# region split for display rendering
    if len(composers) > 60:
        collapse = True
    else:
        collapse = False

    regions = []
    for composer in composers:
        regions.append(composer.region)
    distinct_regions = set(regions)
    distinct_regions = sorted(list(distinct_regions))

    if collapse == True:
        num_regions = len(distinct_regions)
        median_region_num = int(math.ceil(num_regions / 2))
        split_region = distinct_regions[median_region_num]
    else:
        if len(composers) > 1:
            num_composers = len(composers)
            median_composer_region_num = int(math.ceil(num_composers / 2))
            median_composer_region = composers[median_composer_region_num].region
        else:
            median_composer_region = composers[0].region

        i = 0
        for region in distinct_regions:
            i += 1
            if region == median_composer_region:
                break
        if len(distinct_regions) > 1:
            try:
                split_region = distinct_regions[i]
            except IndexError:
                split_region = distinct_regions[i - 1]
        else:
            split_region = distinct_regions[0]

    composer_order = []
    for composer in composers:
        composer_order.append(composer.id)
    session['composer_id_list'] = composer_order

    if search_item:
        search = search_item
    else:
        search = ""

    return render_template('tables.html', collapse=collapse, title='Home',
                           page_title=title, search=search, composers=composers, split_region=split_region, composer_filter=composer_filter)


@bp.route('/artistfinder')
def artistfinder():
    if not session.get('artistfinder_artist'):
        session['artistfinder_artist'] = "Herbert von Karajan"

    artist_name = request.args.get('artist', "Herbert von Karajan")
    composer = request.args.get('composer', "")

    # composer = ComposerList.query.filter_by(name_short=composer_name).first()
    artist = Artists.query.filter_by(name=artist_name).all()
    if artist:
        if artist_name != session['artistfinder_artist']:
            session['artistfinder_artist'] = artist_name
            composer = ""

        composers = []
        for value in db.session.query(Artists.composer).filter(Artists.name == artist_name).order_by(Artists.composer).distinct():
            composers.append(value[0])

        if not composer:
            composer = composers[0]

        # works = WorkList.query \
        #     .filter(WorkList.composer == composer_name,
        #             WorkList.genre == genre) \
        #     .order_by(WorkList.composer,
        #               WorkList.order,
        #               WorkList.genre,
        #               WorkList.id).all()
        works = db.session.query(WorkList).join(Artists) \
            .filter(Artists.name == artist_name,
                    WorkList.composer == composer)\
            .order_by(WorkList.order,
                      WorkList.id).all()

        # get artists list
        with open('app/static/artists.json') as f:
            artists = json.load(f)

        # generates artist list
        # artists = db.session.query(Artists.name)\
        #     .order_by(Artists.name).distinct()

        # artist_list = []
        # for artist in artists:
        #     artist_list.append(artist.name)
        # return jsonpickle.encode(artist_list)

        if not works:
            abort(404)

        return render_template('artistfinder.html',
                               composer1=composer, composers=composers, artist_name=artist_name, artist=artist, artists=artists, math=math, works=works, title="ArtistFinder")

  # composer list for typeahead
    with open('app/static/artists.json') as f:
        artists = json.load(f)
    flash("No search results.")
    return render_template('artistfinder.html',
                           artists=artists, composer="", artist_name=artist_name, math=math, title="ArtistFinder")


# @bp.route('/normalize')
# def normalize():
#     composers = ComposerList.query.all()

#     for composer in composers:
#         word = composer.name_full
#         equivalent = unidecode.unidecode(word)
#         composer.name_norm = equivalent

#     db.session.commit()

#     return "Done"


# @bp.route('/add_preview_music')
# def normalize():
#     composers = ComposerList.query.all()

#     for composer in composers:
#         composer.preview_music = sp.preview_play(composer.name_full)

#     db.session.commit()

#     return "Done"


# @bp.route('/delete_clicks')
# def delete_clicks():
#     composers = ComposerList.query.all()

#     for composer in composers:
#         composer.clicks = 0

#     db.session.commit()
#     return "Done"
