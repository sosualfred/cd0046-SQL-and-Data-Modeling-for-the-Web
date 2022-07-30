# ----------------------------------------------------------------------------#
# Imports
# ----------------------------------------------------------------------------#

import json
import dateutil.parser
import babel
from flask import Flask, render_template, request, Response, flash, redirect, url_for, abort
from flask_moment import Moment
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
import logging
from logging import Formatter, FileHandler
from flask_wtf import Form
from forms import *
import sys

# ----------------------------------------------------------------------------#
# App Config.
# ----------------------------------------------------------------------------#

app = Flask(__name__)
moment = Moment(app)
app.config.from_object('config')

db = SQLAlchemy(app)
migrate = Migrate(app, db)


# ----------------------------------------------------------------------------#
# Models.
# ----------------------------------------------------------------------------#

class Venue(db.Model):
    __tablename__ = 'venues'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String, nullable=False)
    city = db.Column(db.String(120), nullable=False)
    state = db.Column(db.String(120), nullable=False)
    address = db.Column(db.String(120), nullable=False)
    phone = db.Column(db.String(120), nullable=False)
    genres = db.Column(db.String(120), nullable=False)
    facebook_link = db.Column(db.String(120))
    image_link = db.Column(db.String(500))
    website = db.Column(db.String(120))
    seeking_talent = db.Column(db.Boolean, default=False)
    description = db.Column(db.String(1500))
    shows = db.relationship('Show', backref='venue', lazy=True)


artist_show = db.Table('artist_show',
                       db.Column('artist_id', db.Integer,
                                 db.ForeignKey('artists.id')),
                       db.Column('show_id', db.Integer, db.ForeignKey('shows.id'))
                       )


class Artist(db.Model):
    __tablename__ = 'artists'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String)
    city = db.Column(db.String(120), nullable=False)
    state = db.Column(db.String(120), nullable=False)
    phone = db.Column(db.String(120), nullable=False)
    genres = db.Column(db.String(120), nullable=False)
    facebook_link = db.Column(db.String(120))
    image_link = db.Column(db.String(500))
    website = db.Column(db.String(120))
    seeking_venue = db.Column(db.Boolean, default=False)
    description = db.Column(db.String(1500))
    shows = db.relationship('Show', backref='artist', lazy=True)


class Show(db.Model):
    __tablename__ = 'shows'
    id = db.Column(db.Integer, primary_key=True)
    artist_id = db.Column(db.Integer, db.ForeignKey(
        'artists.id'), nullable=False)
    venue_id = db.Column(db.Integer, db.ForeignKey(
        'venues.id'), nullable=False)
    start_time = db.Column(db.DateTime, nullable=False)
    artists = db.relationship('Artist', secondary=artist_show, lazy=True)

# ----------------------------------------------------------------------------#
# Filters.
# ----------------------------------------------------------------------------#


def format_datetime(value, format='medium'):
    date = dateutil.parser.parse(value)
    if format == 'full':
        format = "EEEE MMMM, d, y 'at' h:mma"
    elif format == 'medium':
        format = "EE MM, dd, y h:mma"
    return babel.dates.format_datetime(date, format, locale='en')


app.jinja_env.filters['datetime'] = format_datetime


# ----------------------------------------------------------------------------#
# Controllers.
# ----------------------------------------------------------------------------#

@app.route('/')
def index():
    return render_template('pages/home.html')


#  Venues
#  ----------------------------------------------------------------

@app.route('/venues')
def venues():
    data = []
    unique_city_with_states = Venue.query.distinct(
        Venue.city, Venue.state).all()

    for location in unique_city_with_states:
        city_state = {
            "city": location.city,
            "state": location.state,
        }

        venues = Venue.query.filter_by(
            city=location.city, state=location.state).all()

        location_venues = []
        for venue in venues:
            pending_shows = len(Show.query.filter_by(venue_id=venue.id).filter(
                Show.start_time > datetime.now()).all())
            location_venues.append({
                "id": venue.id,
                "name": venue.name,
                "num_upcoming_shows": pending_shows
            })
        city_state["venues"] = location_venues
        data.append(city_state)

    return render_template('pages/venues.html', areas=data)


@app.route('/venues/search', methods=['POST'])
def search_venues():
    real_search = {}
    search_term = request.form.get('search_term', '')
    real_search['search_term'] = search_term
    venues = Venue.query.filter(Venue.name.ilike(
        '%' + search_term + '%')).all()
    real_search['count'] = len(venues)
    real_search['data'] = []
    for venue in venues:
        real_search['data'].append({
            "id": venue.id,
            "name": venue.name,
            "num_upcoming_shows": len(Show.query.filter_by(
                venue_id=venue.id).filter(Show.start_time > datetime.now()).all())
        })

    return render_template('pages/search_venues.html', results=real_search,
                           search_term=request.form.get('search_term', ''))


@app.route('/venues/<int:venue_id>')
def show_venue(venue_id):
    real_data = {}
    venue = Venue.query.get(venue_id)
    real_data["id"] = venue.id
    real_data["name"] = venue.name
    real_data["genres"] = venue.genres.strip("{").strip("}").split(",")
    real_data["address"] = venue.address
    real_data["city"] = venue.city
    real_data["state"] = venue.state
    real_data["phone"] = venue.phone
    real_data["website"] = venue.website
    real_data["facebook_link"] = venue.facebook_link
    real_data["seeking_talent"] = venue.seeking_talent
    real_data["image_link"] = venue.image_link
    real_data["description"] = venue.description
    real_data["past_shows"] = []
    real_data["upcoming_shows"] = []
    for show in venue.shows:
        if show.start_time < datetime.now():
            real_data["past_shows"].append({
                "artist_id": show.artist_id,
                "artist_name": show.artist.name,
                "artist_image_link": show.artist.image_link,
                "start_time": show.start_time.strftime("%Y-%m-%d %H:%M:%S")
            })
        else:
            real_data["upcoming_shows"].append({
                "artist_id": show.artist_id,
                "artist_name": show.artist.name,
                "artist_image_link": show.artist.image_link,
                "start_time": show.start_time.strftime("%Y-%m-%d %H:%M:%S")
            })
    past_shows_count = len(real_data["past_shows"])
    upcoming_shows_count = len(real_data["upcoming_shows"])

    return render_template('pages/show_venue.html', venue=real_data)


#  Create Venue
#  ----------------------------------------------------------------

@app.route('/venues/create', methods=['GET'])
def create_venue_form():
    form = VenueForm()
    return render_template('forms/new_venue.html', form=form)


@app.route('/venues/create', methods=['POST'])
def create_venue_submission():
    venueData = VenueForm(request.form).data
    error = False
    try:
        venue = Venue(
            name=venueData["name"],
            city=venueData["city"],
            state=venueData["state"],
            address=venueData["address"],
            phone=venueData["phone"],
            genres=venueData["genres"],
            facebook_link=venueData["facebook_link"],
            image_link=venueData["image_link"],
            website=venueData["website"],
            seeking_talent=venueData["seeking_talent"],
            description=venueData["description"]
        )
        db.session.add(venue)
        db.session.commit()
    except:
        error = True
        db.session.rollback()
        print(sys.exc_info())
    finally:
        db.session.close()
    if error:
        flash('An error occurred. Venue ' +
              request.form['name'] + ' could not be listed.')
        abort(500)
    else:
        flash('Venue ' + request.form['name'] + ' was successfully listed!')
        return render_template('pages/home.html')


@app.route('/venues/<venue_id>', methods=['DELETE'])
def delete_venue(venue_id):
    error = False
    try:
        venue = Venue.query.get(venue_id)
        db.session.delete(venue)
        db.session.commit()
    except:
        error = True
        db.session.rollback()
        print(sys.exc_info())
    finally:
        db.session.close()

    if error:
        flash('An error occurred. Venue ' +
              request.form['name'] + ' could not be deleted.')
        abort(500)
    else:
        flash('Venue ' + request.form['name'] + ' was successfully deleted!')
        return render_template('pages/home.html')

    # BONUS CHALLENGE: Implement a button to delete a Venue on a Venue Page, have it so that
    # clicking that button delete it from the db then redirect the user to the homepage
    return None


#  Artists
#  ----------------------------------------------------------------
@app.route('/artists')
def artists():
    real_data = []
    for artist in Artist.query.all():
        real_data.append({
            "id": artist.id,
            "name": artist.name,
        })

    return render_template('pages/artists.html', artists=real_data)


@app.route('/artists/search', methods=['POST'])
def search_artists():
    real_response = {}
    search_term = request.form.get('search_term', '')
    artists = Artist.query.filter(Artist.name.ilike(
        '%' + search_term + '%')).all()
    real_response['count'] = len(artists)
    real_response['data'] = []
    for artist in artists:
        real_response['data'].append({
            "id": artist.id,
            "name": artist.name,
            "num_upcoming_shows": len(Show.query.filter_by(
                artist_id=artist.id).filter(Show.start_time > datetime.now()).all())
        })

    return render_template('pages/search_artists.html', results=real_response,
                           search_term=request.form.get('search_term', ''))


@app.route('/artists/<int:artist_id>')
def show_artist(artist_id):
    # shows the artist page with the given artist_id
    real_data = {}
    artist = Artist.query.get(artist_id)
    real_data["id"] = artist.id
    real_data["name"] = artist.name
    real_data["genres"] = artist.genres.strip("{").strip("}").split(",")
    real_data["city"] = artist.city
    real_data["state"] = artist.state
    real_data["phone"] = artist.phone
    real_data["facebook_link"] = artist.facebook_link
    real_data["image_link"] = artist.image_link
    real_data["website"] = artist.website
    real_data["seeking_venue"] = artist.seeking_venue
    real_data["description"] = artist.description
    real_data["upcoming_shows"] = []
    real_data["past_shows"] = []
    for show in artist.shows:
        if show.start_time > datetime.now():
            real_data["upcoming_shows"].append({
                "venue_id": show.venue_id,
                "venue_name": show.venue.name,
                "venue_image_link": show.venue.image_link,
                "start_time": show.start_time.strftime('%Y-%m-%d %H:%M:%S')
            })
        else:
            real_data["past_shows"].append({
                "venue_id": show.venue_id,
                "venue_name": show.venue.name,
                "venue_image_link": show.venue.image_link,
                "start_time": show.start_time.strftime('%Y-%m-%d %H:%M:%S')
            })
    real_data["past_shows_count"] = len(real_data["past_shows"])
    real_data["upcoming_shows_count"] = len(real_data["upcoming_shows"])

    return render_template('pages/show_artist.html', artist=real_data)


#  Update
#  ----------------------------------------------------------------
@app.route('/artists/<int:artist_id>/edit', methods=['GET'])
def edit_artist(artist_id):
    real_artist = Artist.query.get(artist_id)
    form = ArtistForm(obj=real_artist)

    return render_template('forms/edit_artist.html', form=form, artist=real_artist)


@app.route('/artists/<int:artist_id>/edit', methods=['POST'])
def edit_artist_submission(artist_id):
    artistData = ArtistForm(request.form).data
    error = False
    try:
        artist = Artist.query.get(artist_id)
        artist.name = artistData["name"]
        artist.city = artistData["city"]
        artist.state = artistData["state"]
        artist.phone = artistData["phone"]
        artist.facebook_link = artistData["facebook_link"]
        artist.genres = artistData["genres"]
        artist.image_link = artistData["image_link"]
        artist.website = artistData["website"]
        artist.seeking_venue = artistData["seeking_venue"]
        artist.description = artistData["description"]
        db.session.commit()
    except:
        error = True
        db.session.rollback()
        print(sys.exc_info())
    finally:
        db.session.close()

    if error:
        flash('An error occurred. Artist ' +
              request.form['name'] + ' could not be updated.')
        abort(500)
    else:
        flash('Artist ' + request.form['name'] + ' was successfully updated!')
        return redirect(url_for('show_artist', artist_id=artist_id))


@app.route('/venues/<int:venue_id>/edit', methods=['GET'])
def edit_venue(venue_id):
    real_venue = Venue.query.get(venue_id)
    form = VenueForm(obj=real_venue)
    return render_template('forms/edit_venue.html', form=form, venue=real_venue)


@app.route('/venues/<int:venue_id>/edit', methods=['POST'])
def edit_venue_submission(venue_id):
    venueData = VenueForm(request.form).data
    error = False
    try:
        venue = Venue.query.get(venue_id)
        venue.name = venueData["name"]
        venue.city = venueData["city"]
        venue.state = venueData["state"]
        venue.phone = venueData["phone"]
        venue.facebook_link = venueData["facebook_link"]
        venue.image_link = venueData["image_link"]
        venue.website = venueData["website"]
        venue.seeking_talent = venueData["seeking_talent"]
        venue.description = venueData["description"]
        db.session.commit()
    except:
        error = True
        db.session.rollback()
        print(sys.exc_info())
    finally:
        db.session.close()

    if error:
        flash('An error occurred. Venue ' +
              request.form['name'] + ' could not be updated.')
        abort(500)
    else:
        flash('Venue ' + request.form['name'] + ' was successfully updated!')
        return redirect(url_for('show_venue', venue_id=venue_id))


#  Create Artist
#  ----------------------------------------------------------------

@app.route('/artists/create', methods=['GET'])
def create_artist_form():
    form = ArtistForm()
    return render_template('forms/new_artist.html', form=form)


@app.route('/artists/create', methods=['POST'])
def create_artist_submission():
    artistData = ArtistForm(request.form).data
    error = False
    try:
        artist = Artist(
            name=artistData["name"],
            city=artistData["city"],
            state=artistData["state"],
            phone=artistData["phone"],
            genres=artistData["genres"],
            facebook_link=artistData["facebook_link"],
            image_link=artistData["image_link"],
            website=artistData["website"],
            seeking_venue=artistData["seeking_venue"],
            description=artistData["description"]
        )
        db.session.add(artist)
        db.session.commit()
    except:
        error = True
        db.session.rollback()
        print(sys.exc_info())
    finally:
        db.session.close()
    if error:
        flash('An error occurred. Artist ' +
              data.name + ' could not be listed.')
        abort(500)
    else:
        flash('Artist ' + request.form['name'] + ' was successfully listed!')
        return render_template('pages/home.html')


#  Shows
#  ----------------------------------------------------------------

@app.route('/shows')
def shows():
    shows = Show.query.all()
    real_data = []
    for show in shows:
        real_data.append({
            "venue_id": show.venue_id,
            "venue_name": show.venue.name,
            "artist_id": show.artist_id,
            "artist_name": show.artist.name,
            "artist_image_link": show.artist.image_link,
            "start_time": show.start_time.strftime('%Y-%m-%d %H:%M:%S')
        })
    return render_template('pages/shows.html', shows=real_data)


@app.route('/shows/create')
def create_shows():
    # renders form. do not touch.
    form = ShowForm()
    return render_template('forms/new_show.html', form=form)


@app.route('/shows/create', methods=['POST'])
def create_show_submission():
    showData = ShowForm(request.form).data
    error = False
    try:
        show = Show(
            venue_id=showData["venue_id"],
            artist_id=showData["artist_id"],
            start_time=showData["start_time"]
        )
        db.session.add(show)
        db.session.commit()
    except:
        error = True
        db.session.rollback()
        print(sys.exc_info())
    finally:
        db.session.close()
    if error:
        flash('An error occurred. Show could not be listed.')
        abort(500)
    else:
        flash('Show was successfully listed!')
        return render_template('pages/home.html')


@app.errorhandler(404)
def not_found_error(error):
    return render_template('errors/404.html'), 404


@app.errorhandler(500)
def server_error(error):
    return render_template('errors/500.html'), 500


if not app.debug:
    file_handler = FileHandler('error.log')
    file_handler.setFormatter(
        Formatter(
            '%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]')
    )
    app.logger.setLevel(logging.INFO)
    file_handler.setLevel(logging.INFO)
    app.logger.addHandler(file_handler)
    app.logger.info('errors')

# ----------------------------------------------------------------------------#
# Launch.
# ----------------------------------------------------------------------------#

# Default port:
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=3000, debug=True)
