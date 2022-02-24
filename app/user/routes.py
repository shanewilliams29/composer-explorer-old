from flask import render_template, flash, redirect, url_for, request, current_app
from flask_login import current_user, login_required
from app import db
from app.user import bp
from app.spotify import sp
from app.user.classes import get_avatar, upload_avatar
from app.user.forms import EditProfileForm, ClearVisits, ChangeAvatar, MessageForm
from app.models import User, ComposerList, Message, ForumComment, Comment, AlbumLike, WorkAlbums
from datetime import datetime, timedelta
import jsonpickle


@bp.route('/user/<username>')
@login_required
def user(username):
    user = User.query.filter_by(username=username).first_or_404()
    composers = user.favorited_composers().order_by(ComposerList.name_short).paginate(1, 100, False)
    albums = WorkAlbums.query.join(AlbumLike).filter_by(user_id=user.id).order_by(AlbumLike.id.desc()).limit(10)
    forum_posts = ForumComment.query.filter_by(user_id=user.id).count()
    comments = Comment.query.filter_by(user_id=user.id).count()

    album_list = []
    for album in albums:
        item = jsonpickle.decode(album.data)
        item['composer'] = album.composer
        item['work'] = album.work.title
        item['work_id'] = album.work.id
        album_list.append(item)

    return render_template('user/user.html', user=user, composers=composers.items, likes=album_list,
                           title=user.display_name, forum_posts=forum_posts, comments=comments)


@bp.route('/edit_profile', methods=['GET', 'POST'])
@login_required
def edit_profile():
    form = EditProfileForm(current_user.username)
    if form.validate_on_submit():
        current_user.display_name = form.display_name.data
        current_user.about_me = form.about_me.data
        db.session.commit()
        flash('Your changes have been saved.')
        return redirect(url_for('user.user', username=current_user.username))
    elif request.method == 'GET':
        form.display_name.data = current_user.display_name
        form.about_me.data = current_user.about_me
    return render_template('user/edit_profile.html', title='Edit Profile',
                           form=form)


@bp.route('/clear_visits', methods=['GET', 'POST'])
@login_required
def clear_visits():
    form = ClearVisits()
    if form.validate_on_submit():
        visited = current_user.all_visits()
        for item in visited:
            current_user.unvisit(item)
        db.session.commit()
        flash("You have successfully cleared all records of which works you have visited.")
        return redirect(url_for('user.user', username=current_user.username))
    return render_template('user/clear_visits.html', title='Clear Visits',
                           form=form)


@bp.route('/change_avatar', methods=['GET', 'POST'])
@login_required
def change_avatar():
    form = ChangeAvatar()
    if request.method == 'POST':
        if form.choice.data == "remove":
            current_user.img = ""
            db.session.commit()
            flash("You have removed your Spotify photo.")
        if form.choice.data == "restore":
            response = sp.get_user()
            info = response.json()
            try:
                image_url = info['images'][0]['url']
                response = get_avatar(current_user.username, image_url)
                image = response[0]
            except Exception:
                flash("Error: Could not retrieve a photo from Spotify.")
                return redirect(url_for('user.user', username=current_user.username))
            current_user.img = image
            db.session.commit()
            flash("You have restored your Spotify photo.")
        if form.choice.data == "upload":
            if form.link.data:
                response = get_avatar(current_user.username, form.link.data)
                if response[1] == 200:
                    current_user.img = response[0]
                    db.session.commit()
                    flash('Your profile picture has been changed.')
                else:
                    flash(response[0], 'danger')
                    return redirect(url_for('user.change_avatar'))
            else:
                uploaded_file = request.files['file']
                response = upload_avatar(current_user.username, uploaded_file)
                if response[1] == 200:
                    current_user.img = response[0]
                    db.session.commit()
                    flash('Your profile picture has been changed.')
                else:
                    flash(response[0], 'danger')
                    return redirect(url_for('user.change_avatar'))

        return redirect(url_for('user.user', username=current_user.username))
    return render_template('user/change_avatar.html', title='Change Profile Picture',
                           form=form)


@bp.route('/follow/<username>')
@login_required
def follow(username):
    user = User.query.filter_by(username=username).first()
    if user is None:
        flash('User {} not found.'.format(username))
        return redirect(url_for('main.index'))
    if user == current_user:
        flash('You cannot follow yourself!')
        return redirect(url_for('user.user', username=username))
    current_user.follow(user)
    db.session.commit()
    flash('You are following {}!'.format(username))
    return redirect(url_for('user.user', username=username))


@bp.route('/unfollow/<username>')
@login_required
def unfollow(username):
    user = User.query.filter_by(username=username).first()
    if user is None:
        flash('User {} not found.'.format(username))
        return redirect(url_for('main.index'))
    if user == current_user:
        flash('You cannot unfollow yourself!')
        return redirect(url_for('user.user', username=username))
    current_user.unfollow(user)
    db.session.commit()
    flash('You are not following {}.'.format(username))
    return redirect(url_for('user.user', username=username))


@bp.route('/favorites')
@login_required
def favorites():
    page = request.args.get('page', 1, type=int)
    composers = current_user.favorited_composers().order_by(ComposerList.name_short).paginate(page, 100, False)
    next_url = url_for('user.favorites', page=composers.next_num) if composers.has_next else None
    prev_url = url_for('user.favorites', page=composers.prev_num) if composers.has_prev else None
    return render_template("user/favorites.html", title='My Favorites', composers=composers.items,
                           next_url=next_url, prev_url=prev_url)


@bp.route('/fav_composer', methods=['GET', 'POST'])
def fav_composer():
    if current_user.is_authenticated:
        _id = request.form['id']
        composer = ComposerList.query.filter_by(id=_id).first()
        check = current_user.is_favorite(composer)
        if check:
            return str("Already in your favorites!")
        current_user.favorite(composer)
        db.session.commit()
        return str("Added to your favorites!")
    else:
        return 'Forbidden!', 403


@bp.route('/unfavorite_composer/<composerid>')
@login_required
def unfavorite_composer(composerid):
    composer = ComposerList.query.filter_by(id=composerid).first()
    if composer is None:
        flash('Composer with id {} not found.'.format(composerid))
        return redirect(url_for('user.favorites'))
    current_user.unfavorite(composer)
    db.session.commit()
    flash('You have removed {} from your favorites.'.format(str(composer.name_full)))
    return redirect(url_for('user.favorites'))


@bp.route('/send_message/<recipient>', methods=['GET', 'POST'])
@login_required
def send_message(recipient):
    user = User.query.filter_by(username=recipient).first_or_404()
    form = MessageForm()
    if form.validate_on_submit():
        msg = Message(author=current_user, recipient=user,
                      body=form.message.data)
        db.session.add(msg)
        db.session.commit()
        flash('Your message has been sent.', "info")
        return redirect(url_for('user.messages_sent'))
    return render_template('user/send_message.html', title=('Send Message'),
                           form=form, recipient=user.display_name)


@bp.route('/send_mass_message/', methods=['GET', 'POST'])
@login_required
def send_mass_message():
    if not current_user.admin:
        return redirect(url_for('main.index'))

    users = User.query.all()
    form = MessageForm()
    messages = []
    if form.validate_on_submit():
        for user in users:
            msg = Message(author=current_user, recipient=user,
                          body=form.message.data)
            messages.append(msg)
        db.session.add_all(messages)
        db.session.commit()
        flash('Your message has been sent.', "info")
        return redirect(url_for('user.messages_sent'))
    return render_template('user/mass_message.html', title=('Send Mass Message'),
                           form=form)


@bp.route('/messages')
@login_required
def messages():
    previous_read_time = current_user.last_message_read_time or datetime(1900, 1, 1)
    current_user.last_message_read_time = datetime.utcnow()
    db.session.commit()
    page = request.args.get('page', 1, type=int)
    messages = current_user.messages_received.filter_by(recipient_visible=True).order_by(
        Message.timestamp.desc()).paginate(
            page, 20, False)
    next_url = url_for('user.messages', page=messages.next_num) \
        if messages.has_next else None
    prev_url = url_for('user.messages', page=messages.prev_num) \
        if messages.has_prev else None
    return render_template('user/messages.html', messages=messages.items,
                           next_url=next_url, prev_url=prev_url, previous_read_time=previous_read_time,
                           title="Messages")


@bp.route('/messages_sent')
@login_required
def messages_sent():
    page = request.args.get('page', 1, type=int)
    messages = current_user.messages_sent.filter_by(sender_visible=True).order_by(
        Message.timestamp.desc()).paginate(
            page, 20, False)
    next_url = url_for('user.messages', page=messages.next_num) \
        if messages.has_next else None
    prev_url = url_for('user.messages', page=messages.prev_num) \
        if messages.has_prev else None
    return render_template('user/messages_sent.html', messages=messages.items,
                           next_url=next_url, prev_url=prev_url, title="Sent Messages")


@bp.route('/delete_mesage/<message_id>')
@login_required
def delete_message(message_id):
    message = Message.query.filter_by(id=message_id).first()
    if message is None:
        flash('Error: Message {} not found.'.format(message_id), 'danger')
        return redirect(url_for('user.messages'))
    if message.recipient_id == current_user.id:
        message = Message.query.filter_by(id=message_id).first()
        message.recipient_visible = False
        db.session.commit()
        flash('Message deleted.', 'info')
        return redirect(request.referrer)
    else:
        flash('You do not have the permissions to delete this message.', "danger")
        return redirect(request.referrer)


@bp.route('/delete_sent_message/<message_id>')
@login_required
def delete_sent_message(message_id):
    message = Message.query.filter_by(id=message_id).first()
    if message is None:
        flash('Error: Message {} not found.'.format(message_id), 'danger')
        return redirect(url_for('user.messages'))
    if message.sender_id == current_user.id:
        message = Message.query.filter_by(id=message_id).first()
        message.sender_visible = False
        db.session.commit()
        flash('Message deleted.', 'info')
        return redirect(request.referrer)
    else:
        flash('You do not have the permissions to delete this message.', "danger")
        return redirect(request.referrer)


@bp.route('/user_list')
@login_required
def user_list():
    # user page viewing
    if current_user.is_authenticated:
        current_user.page_viewing = '<a href="' + url_for("user.user_list") + '">' + 'User List' + '</a>'
        db.session.commit()

    users = User.query.order_by(User.last_seen.desc()).all()
    usercount = User.query.count()
    onlinecheck = datetime.utcnow() - timedelta(minutes=5)

    return render_template("user_list.html", title='User List', onlinecheck=onlinecheck, users=users, usercount=usercount)
