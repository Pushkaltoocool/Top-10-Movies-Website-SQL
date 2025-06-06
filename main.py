from flask import Flask, render_template, redirect, url_for, request
from flask_bootstrap import Bootstrap5
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy import Integer, String, Float
from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField
from wtforms.validators import DataRequired
import requests
from typing import Optional

app = Flask(__name__)
app.config['SECRET_KEY'] = '8BYkEfBA6O6donzWlSihBXox7C0sKR6b'
Bootstrap5(app)

# CREATE DB
class Base(DeclarativeBase):
    pass

app.config['SQLALCHEMY_DATABASE_URI'] = "sqlite:///movies.db"
db = SQLAlchemy(model_class=Base)
db.init_app(app)


# CREATE TABLE
class Movies(db.Model):
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    title: Mapped[str] = mapped_column(String(250), unique=True, nullable=False)
    year: Mapped[int] = mapped_column(Integer, nullable=False)
    description: Mapped[str] = mapped_column(String(1000), nullable=False)
    rating: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    ranking: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    review: Mapped[Optional[str]] = mapped_column(String(1000), nullable=True)
    img_url: Mapped[str] = mapped_column(String(1000), nullable=False)

    def __repr__(self):
        return f'<Movie {self.title}>'

# FORMS
class AddMovieForm(FlaskForm):
    title = StringField("Movie Title", validators=[DataRequired()])
    submit = SubmitField("Add Movie")

class EditMovieForm(FlaskForm):
    rating = StringField("Your Rating Out of 10 e.g. 7.5", validators=[DataRequired()])
    review = StringField("Your Review", validators=[DataRequired()])
    submit = SubmitField("Done")

# --- TMDB API SETUP ---
API_KEY = "43250f033950cf66ac32cc9e1e58fa1d" # Your TMDB API Key
TMDB_SEARCH_URL = "https://api.themoviedb.org/3/search/movie"
TMDB_DETAILS_URL = "https://api.themoviedb.org/3/movie"
TMDB_IMAGE_URL = "https://image.tmdb.org/t/p/w500"

def search_movie(movie_name):
    params = {
        'api_key': API_KEY,
        'query': movie_name
    }
    response = requests.get(TMDB_SEARCH_URL, params=params)
    response.raise_for_status() # Will raise an error for bad status codes
    return response.json().get("results", [])

def get_movie_details(movie_api_id):
    url = f"{TMDB_DETAILS_URL}/{movie_api_id}"
    params = {'api_key': API_KEY, 'language': 'en-US'}
    response = requests.get(url, params=params)
    response.raise_for_status()
    return response.json()

# --- ROUTES ---
@app.route("/")
def home():
    # Read all movies from the database and order them by rating
    result = db.session.execute(db.select(Movies).order_by(Movies.rating.desc()))
    all_movies = result.scalars().all()
    
    # Assign rankings
    for i, movie in enumerate(all_movies):
        movie.ranking = i + 1
    db.session.commit()

    return render_template("index.html", all_movies=all_movies)

@app.route("/add", methods=["GET", "POST"])
def add():
    form = AddMovieForm()
    if form.validate_on_submit():
        movie_title = form.title.data
        search_results = search_movie(movie_title)
        return render_template('select.html', search_results=search_results)
    return render_template("add.html", form=form)

@app.route("/find")
def find_movie():
    movie_api_id = request.args.get("id")
    if movie_api_id:
        movie_data = get_movie_details(movie_api_id)
        # Create a new movie record and add it to the database
        new_movie = Movies(
            title=movie_data["title"],
            year=int(movie_data["release_date"].split("-")[0]),
            description=movie_data["overview"],
            img_url=f"{TMDB_IMAGE_URL}{movie_data['poster_path']}"
        )
        db.session.add(new_movie)
        db.session.commit()
        # Redirect to the edit page for the newly added movie
        return redirect(url_for("edit", id=new_movie.id))
    return redirect(url_for('home')) # Fallback redirect

@app.route("/edit", methods=["GET", "POST"])
def edit():
    form = EditMovieForm()
    movie_id = request.args.get('id')
    movie_to_update = db.session.get(Movies, movie_id)

    if form.validate_on_submit():
        # Update the record in the database
        movie_to_update.rating = float(form.rating.data)
        movie_to_update.review = form.review.data
        db.session.commit()
        return redirect(url_for('home'))

    return render_template("edit.html", movie=movie_to_update, form=form)

@app.route("/delete")
def delete():
    movie_id = request.args.get("id")
    movie_to_delete = db.session.get(Movies, movie_id)
    if movie_to_delete:
        db.session.delete(movie_to_delete)
        db.session.commit()
    return redirect(url_for('home'))


if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)