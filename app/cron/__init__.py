from flask import render_template, flash, redirect, url_for, request, session, current_app
from flask import Blueprint
import time
import click
from app import db, log
from datetime import datetime, timedelta
from app.albums.classes import GroupAlbums, SmartAlbums
from app.spotify import sp
from app.models import User, WorkList, Spotify, WorkAlbums, Artists
from app.spotify.functions import search_spotify_and_save
import jsonpickle
from app.spotify.functions import search_album

import os
# from twilio.rest import Client

bp = Blueprint('cron', __name__)

log_name = "fillalbums-log"
logger = log.logger(log_name)

# # Inital Spotify search and fill for Albums and Artists
# @bp.cli.command()
# @click.argument("name")


def spotifygenerate(name):
    start_time = datetime.utcnow()
    ctx = current_app.test_request_context()
    ctx.push()

    # get spotify token
    if not session.get('app_token'):
        session['app_token'] = sp.client_authorize()
        session['app_token_expire_time'] = datetime.now() + timedelta(minutes=59)

    notfound_count = 0
    error_count = 0
    errors = True
    while errors is True:
        errors = False
        i = 1
        composer = name
        # get works not in Spotify table
        works = db.session.query(WorkList).outerjoin(Spotify, Spotify.id == WorkList.id).filter(WorkList.composer == composer, Spotify.updated == None).all()
        # works = WorkList.query.filter_by(composer=composer).all()
        num_works = str(len(works))
        for work in works:
            # token expiry and refreshing
            if session['app_token_expire_time'] < datetime.now():
                session['app_token'] = sp.client_authorize()
                session['app_token_expire_time'] = datetime.now() + timedelta(minutes=59)

            tracks = search_spotify_and_save(work.id)
            try:
                GroupAlbums(tracks, work)
                print("SUCCESS" + " " + work.id + " " + work.title + " <" + str(i) + " of " + num_works + ">")
            except:
                output = "SPOTIFY GENERATE FAIL - " + work.id + " " + str(tracks) + " " + work.title
                output2 = "SPOTIFY GENERATE FAIL - " + work.id + " " + work.title
                if str(tracks[1]) == "429":
                    print(output)
                    errors = True
                    logger.log_text("429 " + output)
                elif str(tracks[1]) == "404":
                    print(output)
                    logger.log_text("404 " + output)
                    notfound_count += 1
                else:
                    print(output2)
                    logger.log_text("500" + output2, severity="ERROR")
                    error_count += 1
            i += 1

    # sum album counts
    works = db.session.query(WorkList).filter_by(composer=name).all()

    for work in works:
        work.album_count = work.albums.count()
    db.session.commit()

    # finish
    ctx.pop()
    end_time = datetime.utcnow()
    elapsed_time = end_time - start_time
    minutes = divmod(elapsed_time.total_seconds(), 60)

    message = "Initial load complete for " + name + ", " + str(error_count) + " unresolved errors, " + str(notfound_count) + " works not found. Took " + str(minutes[0]) + " minutes, " + str(minutes[1]) + " seconds."
    logger.log_text(message, severity="NOTICE")
    print(message)


# Fill in albums with all tracks
# @bp.cli.command()
# @click.argument("name")
def fillalbums(name):
    start_time = datetime.utcnow()
    ctx = current_app.test_request_context()
    ctx.push()

    # get spotify token
    if not session.get('app_token'):
        session['app_token'] = sp.client_authorize()
        session['app_token_expire_time'] = datetime.now() + timedelta(minutes=59)

    errors = True
    limit_exceeded_error = 0
    while errors is True:
        i = 1
        error_count = 0
        composer = name
        errors = False
        albums = WorkAlbums.query.filter_by(composer=composer, filled=False).all()

        for album in albums:
            # token expiry and refresh
            if session['app_token_expire_time'] < datetime.now():
                session['app_token'] = sp.client_authorize()
                session['app_token_expire_time'] = datetime.now() + timedelta(minutes=59)

            db.session.query(Artists).filter_by(album_id=album.id).delete()
            db.session.commit()

            try:
                work = db.session.query(WorkList).filter_by(id=album.workid).first()
                tracks = search_album(album.album_id, work)
                SmartAlbums(tracks, work)

            except:
                print("FILL ERROR " + work.id + " " + work.title + " " + album.album_id + " " + str(tracks))
                logtext = "FILL ERROR " + work.id + " " + work.title + " " + album.album_id + " " + str(tracks)
                logger.log_text(logtext, severity="ERROR")
                try:
                    int(tracks)
                    if int(tracks) == 429:
                        errors = True
                        limit_exceeded_error += 1
                        continue
                except:
                    error_count += 1
                    continue

            print("Success " + work.id + " " + work.title + " <" + str(i) + " of " + str(len(albums)) + ">")
            i += 1

    ctx.pop()
    end_time = datetime.utcnow()
    elapsed_time = end_time - start_time
    minutes = divmod(elapsed_time.total_seconds(), 60)
    message = "Album fill complete for " + name + ", " + str(error_count) + " unresolved errors, " + str(limit_exceeded_error) + " resolved 429 errors. Took " + str(minutes[0]) + " minutes, " + str(minutes[1]) + " seconds."
    logger.log_text(message, severity="NOTICE")
    print(message)


# Check Spotify for new albums
# @ bp.cli.command()
# @ click.argument("name")
def refreshalbums(name):
    ctx = current_app.test_request_context()
    ctx.push()

    # get spotify token
    if not session.get('app_token'):
        session['app_token'] = sp.client_authorize()
        session['app_token_expire_time'] = datetime.now() + timedelta(minutes=59)

    # get work list
    works = WorkList.query.filter_by(composer=name).all()
    num_works = str(len(works))

    # get new catalogued albums
    i = 1

    for work in works:
        newtracks = []
        tracks = []

        # token expiry and refreshing
        if session['app_token_expire_time'] < datetime.now():
            session['app_token'] = sp.client_authorize()
            session['app_token_expire_time'] = datetime.now() + timedelta(minutes=59)

        try:
            tracks = search_spotify_and_save(work.id)
            test = tracks[0]['album_id']
        except:
            output = "SPOTIFY REFRESH FAIL - " + work.id + " " + work.title
            if str(tracks[1]) == "429":
                print("429 " + output)
                logger.log_text("429 " + output, severity="ERROR")
            elif str(tracks[1]) == "404":
                print("404 " + output)
                logger.log_text("404 " + output)
            else:
                print("500 " + output)
                logger.log_text("500 " + output, severity="ERROR")
            i += 1
            continue

        for track in tracks:
            albumworkid = work.id + track['album_id']
            exists = db.session.query(WorkAlbums.id).filter_by(id=albumworkid).first() is not None

            if not exists:
                newtracks.append(track)

        if newtracks:
            GroupAlbums(newtracks, work)
            print("NEW ALBUMS " + " " + work.id + " " + work.title + " <" + str(i) + " of " + num_works + ">")
            logger.log_text("NEW ALBUMS " + " " + work.id + " " + work.title)
        else:
            print("No New Albums" + " " + work.id + " " + work.title + " <" + str(i) + " of " + num_works + ">")
        i += 1

    ctx.pop()
    print('Done!')


def cleanup(name):
    # delete albums with no tracks.
    db.session.query(WorkAlbums).filter(WorkAlbums.composer == name, WorkAlbums.score == 0).delete()
    db.session.commit()
    # delete spotify table records if no albums
    noalbums = db.session.query(Spotify).outerjoin(WorkAlbums, Spotify.id == WorkAlbums.workid).filter(WorkAlbums.id == None).all()
    for album in noalbums:
        db.session.query(Spotify).filter(Spotify.id == album.id).delete()
        db.session.commit()

    # re-sum album counts
    works = db.session.query(WorkList).filter_by(composer=name).all()

    for work in works:
        work.album_count = work.albums.count()
    db.session.commit()


@ bp.cli.command()
@ click.argument("name")
def loadnew(name):
    spotifygenerate(name)
    fillalbums(name)
    cleanup(name)
    print("LOAD COMPLETE!")


@ bp.cli.command()
@ click.argument("name")
def refresh(name):
    refreshalbums(name)
    fillalbums(name)
    cleanup(name)
    print("REFRESH COMPLETE!")


@ bp.cli.command()
@ click.argument("name")
def splitsongs(name):
    works = db.session.query(WorkList).filter_by(composer=name)

    for work in works:
        title = work.title
        splitlist = title.split("(\"")
        try:
            lyrics = splitlist[1]
            lyrics = lyrics.replace("\")", "")
            title = splitlist[0].strip()
            work.nickname = lyrics
            work.title = title

        except:
            pass

    db.session.commit()


@ bp.cli.command()
@ click.argument("name")
def splitsongs2(name):
    works = db.session.query(WorkList).filter_by(composer=name)

    for work in works:
        title = work.title
        splitlist = title.split("(")
        try:
            lyrics = splitlist[1]
            lyrics = lyrics.replace(")", "")
            title = splitlist[0].strip()
            work.nickname = lyrics
            work.title = title

        except:
            pass

    db.session.commit()


@ bp.cli.command()
@ click.argument("name")
def trimtitles(name):
    works = db.session.query(WorkList).filter_by(composer=name)

    for work in works:
        title = work.title
        trimmed = title.strip()
        work.title = trimmed
        print(work.title)

    db.session.commit()

# @bp.cli.command()
# def deletealldata():
#     db.session.query(WorkAlbums).delete()
#     db.session.flush()
#     db.session.commit()
#     print('Deleted all data.')
