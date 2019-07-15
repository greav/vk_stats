import datetime
import calendar
import vk_api
import io
import base64
import pandas as pd
import seaborn as sns

from app import app, vk
from .forms import DownloadForm, StatisticsForm

from flask import render_template, request, Response, redirect, url_for, flash
from matplotlib import pyplot as plt
from collections import OrderedDict

execute_get_wall_posts = vk_api.execute.VkFunction(args=('get_args', 'offset', 'timestamp', 'n_request'),
                                                   code="""
    var get_args = %(get_args)s;
    var posts = [];
    var i = 0;
    while (i < %(n_request)s){
        get_args.offset = %(offset)s + i*100;
        var response = API.wall.get(get_args).items;
        posts = posts + response;
        if (response.length < 100)
            return posts;
        i = i + 1;
    }

    return posts;                                               
""")


def get_wall_posts(id_, date):
    date = datetime.datetime.strptime(date, '%Y-%m-%d')
    # timestamp correction for Moscow time
    timestamp = calendar.timegm(date.utctimetuple()) - 3 * 60 * 60

    if isinstance(id_, int):
        get_args = {'owner_id': id_}
    else:
        get_args = {'domain': id_}

    try:
        post = vk.wall.get(**get_args, count=1)
    except vk_api.ApiError:
        return []

    posts_count = post['count']

    if posts_count == 0:
        return []

    valid_posts = []

    # check if pinned post satisfies the timestamp
    if post['items'][0]['date'] > timestamp:
        valid_posts.append(post['items'][0])

    get_args["count"] = 100
    step = 500
    n_request = step / 100
    for offset in range(1, posts_count, step):
        try:
            posts = execute_get_wall_posts(vk, get_args, offset=offset, timestamp=timestamp, n_request=n_request)
        except vk_api.ApiError:
            return []

        # if last post of response satisfies the timestamp then continue with new API request
        if posts[-1]['date'] > timestamp:
            valid_posts.extend(posts)
            continue

        for i, post in enumerate(posts):
            if post['date'] < timestamp:
                valid_posts.extend(posts[:i])
                return valid_posts

    return valid_posts


@app.route('/')
def about():
    return render_template('about.html')


@app.route('/download')
def download():
    form = DownloadForm()
    return render_template('download.html', form=form)


@app.route('/download/data.csv', methods=['POST'])
def generate_csv():
    # process id_ or domain
    id_ = request.form.get('id_')
    if id_.lstrip('-').isdigit():
        id_ = int(id_)

    date = request.form.get('date')

    checked_fields = OrderedDict()
    # get states of checkbuttons
    checked_fields['post_id'] = bool(request.form.get('post_id_checked'))
    checked_fields['text'] = bool(request.form.get('text_checked'))
    checked_fields['attachments'] = bool(request.form.get('attachments_checked'))
    checked_fields['n_attachments'] = bool(request.form.get('n_attachments_checked'))
    checked_fields['n_likes'] = bool(request.form.get('n_likes_checked'))
    checked_fields['n_reposts'] = bool(request.form.get('n_reposts_checked'))
    checked_fields['n_comments'] = bool(request.form.get('n_comments_checked'))

    # not any checkbutton selected
    if not any(checked_fields.values()):
        flash('You should choose at least one of the options above')
        return redirect(url_for('download'))

    posts = get_wall_posts(id_, date)

    if not posts:
        flash('No posts for this user. Try another date or ID')
        return redirect(url_for('download'))

    # generator for csv file
    def generate(valid_posts):
        header = [key for key, value in checked_fields.items() if value]
        yield ','.join(header) + '\n'
        for post in valid_posts:
            row = []
            if checked_fields['post_id']:
                row.append(str(post['id']))
            if checked_fields['text']:
                text = post['text']
                row.append(f'"{text}"')
            if checked_fields['attachments']:
                attachments = get_attachments(post)
                row.append(f'"{attachments}"')
            if checked_fields['n_attachments']:
                if not checked_fields['attachments']:
                    attachments = get_attachments(post)
                    n_attachments = len(attachments)
                else:
                    n_attachments = len(attachments)
                row.append(str(n_attachments))
            if checked_fields['n_likes']:
                row.append(str(post['likes']['count']))
            if checked_fields['n_comments']:
                row.append(str(post['comments']['count']))
            if checked_fields['n_reposts']:
                row.append(str(post['reposts']['count']))

            yield ','.join(row) + '\n'

    return Response(generate(posts), mimetype='text/csv')


def get_attachments(post):
    attachments = post.get('attachments')
    attachments_urls = []
    if attachments:
        for attachment in attachments:
            if attachment.get('type') == 'photo':
                for photocopy in attachment['photo']['sizes']:
                    if photocopy['type'] == 'x':
                        attachments_urls.append(photocopy['url'])
                        break
                continue
            if attachment.get('type') == 'link':
                attachments_urls.append(attachment['link']['url'])
                continue
            elif attachment.get('type') == 'doc':
                attachments_urls.append(attachment['doc']['url'])
                continue
            elif attachment.get('type') == 'video':
                video = attachment['video']
                # if the video is on other platforms
                if video.get('platform'):
                    video_url = get_video_url(video)
                else:
                    video_id = video['id']
                    owner_id = video['owner_id']
                    video_url = f'https://vk.com/video{owner_id}_{video_id}'
                attachments_urls.append(video_url)
    elif post.get('copy_history'):
        repost = post['copy_history'][0]
        post_id = repost['id']
        owner_id = repost['owner_id']
        repost_url = f'https://vk.com/wall{owner_id}_{post_id}'
        attachments_urls.append(repost_url)

    return attachments_urls


def get_video_url(video):
    video_id = video['id']
    owner_id = video['owner_id']
    access_key = video['access_key']
    video_url = vk.video.get(owner_id=owner_id, videos=f'{owner_id}_{video_id}_{access_key}')["items"][0]['player']
    return video_url


@app.route('/statistics', methods=['GET', 'POST'])
def statistics():
    form = StatisticsForm()

    if request.method == 'POST':
        # process id_ or user domain
        id_ = request.form.get('id_')
        if id_.lstrip('-').isdigit():
            id_ = int(id_)

        date = request.form.get('date')
        radio_button = request.form.get('radio')

        posts = filter_posts(get_wall_posts(id_, date))
        if not posts:
            flash('No data to draw. Try another date or ID')
            return redirect(request.url)

        plot_url = get_plot_url(posts, radio_button)

        return render_template('statistics.html', form=form, figure=plot_url)

    return render_template('statistics.html', form=form, figure=None)


def filter_posts(posts):
    valid_posts = []
    for post in posts:
        post_id = post['id']
        date = post['date']
        n_likes = post['likes']['count']
        n_comments = post['comments']['count']
        n_reposts = post['reposts']['count']

        valid_post = [post_id, date, n_likes, n_comments, n_reposts]
        valid_posts.append(valid_post)

    return valid_posts


def get_plot_url(valid_posts, radio_button):
    img = io.BytesIO()

    df = pd.DataFrame(data=valid_posts, columns=['post_id', 'date', 'n_likes', 'n_comments', 'n_reposts'])
    df['date'] = pd.to_datetime(df['date'], unit='s')

    if radio_button == 'hour':
        gb = df.groupby(lambda i: df.loc[i, 'date'].hour)[['n_likes', 'n_comments', 'n_reposts']].agg(
            ['mean', 'count'])
        rotation = 0
        x, x_label = gb.index, 'hour'
    elif radio_button == 'dow':
        gb = df.groupby(lambda i: df.loc[i, 'date'].dayofweek)[['n_likes', 'n_comments', 'n_reposts']].agg(
            ['mean', 'count'])
        x = gb.index.map({0: 'Mon', 1: 'Tue', 2: 'Wed', 3: 'Thu', 4: 'Fri', 5: 'Sat', 6: 'Sun'})
        rotation = 0
        x_label = 'day of week'
    elif radio_button == 'month':
        gb = df.groupby(lambda i: df.loc[i, 'date'].month)[['n_likes', 'n_comments', 'n_reposts']].agg(
            ['mean', 'count'])
        x = gb.index.map({1: 'Jan', 2: 'Feb', 3: 'Mar', 4: 'Apr', 5: 'May', 6: 'June', 7: 'July', 8: 'Aug', 9: 'Sept',
                          10: 'Oct', 11: 'Nov', 12: 'Dec'})
        rotation = 90
        x_label = 'month'
    else:
        gb = df.groupby(lambda i: df.loc[i, 'date'].year)[['n_likes', 'n_comments', 'n_reposts']].agg(
            ['mean', 'count'])
        rotation = 0
        x, x_label = gb.index, 'year'

    fig, axs = plt.subplots(nrows=2, ncols=2, figsize=(12, 12))

    draw_barplot(gb, x, ('n_likes', 'count'), axs[0, 0], x_label, y_label='count',
                 title='Number of posts', rotation=rotation)
    draw_barplot(gb, x, ('n_likes', 'mean'), axs[0, 1], x_label, y_label='avg',
                 title='Average number of likes', rotation=rotation)
    draw_barplot(gb, x, ('n_comments', 'mean'), axs[1, 0], x_label, y_label='avg',
                 title='Average number of comments', rotation=rotation)
    draw_barplot(gb, x, ('n_reposts', 'mean'), axs[1, 1], x_label, y_label='avg',
                 title='Average number of reposts', rotation=rotation)

    fig.savefig(img, format='png')
    img.seek(0)
    plot_url = base64.b64encode(img.getvalue()).decode()

    return plot_url


def draw_barplot(df, x, y, ax, x_label, y_label, title, rotation=0):
    g = sns.barplot(x, df[y], ax=ax)
    g.set_xticklabels(x, rotation=rotation, axes=ax)
    ax.set_ylabel(y_label)
    ax.set_xlabel(x_label)
    ax.set_title(title)
