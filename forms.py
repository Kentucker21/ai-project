from flask_wtf import FlaskForm
from wtforms import StringField,PasswordField,SubmitField,SelectField,IntegerField,FloatField
from wtforms.validators import DataRequired,Length,Email,EqualTo,NumberRange,Optional


class RegistrationForm(FlaskForm):
    username=StringField('Username',validators=[DataRequired(),Length(min=2,max=20)])
    
    password=PasswordField('Password',validators=[DataRequired()])

    confirm_password=PasswordField('Confirm Password',validators=[DataRequired(),EqualTo('password')])

    submit=SubmitField('Sign Up')


class LoginForm(FlaskForm):
    username=StringField('Username',validators=[DataRequired(),Length(min=2,max=20)])

    password=PasswordField('Password',validators=[DataRequired()])
    
    submit=SubmitField('Log in')


class GpsForm(FlaskForm):
    start=SelectField('Start',choices=[],validators=[DataRequired()])
    end=SelectField('end',choices=[],validators=[DataRequired()])

    algorithm=SelectField('Search Algorithm',choices=[
        ('dijkstra','Dijkstra'),
        ('astar','A*'),
        ('dfs','DFS')
    ],default='dijkstra')

    roadtype=SelectField('road type',choices=[
     ('paved','paved'),
     ('unpaved','unpaved')
    ],validators=[DataRequired()])

    avoid=SelectField('Avoid',choices=[
        ('broken cistern','broken cistern'),
        ('deep potholes','deep potholes'),
        ('none','none')
    ],validators=[DataRequired()])


    status=SelectField('Road Status',choices=[
        ('open','open'),
        ('closed','closed'),
        ('seasonal_blocked','seasonal_blocked')
    ])

    direction=SelectField('Road Direction',choices=[
        ('two_way','two_way'),
        ('one_way','one_way')
    ])

    pothole_depth=IntegerField('Pothole depth (inches)')

    road_distance=FloatField('Distance (km)', validators=[Optional()])
    road_duration=IntegerField('Travel time (min)', validators=[Optional()])

    place_name=StringField('Place name')
    new_place_name=StringField('New place name')
    place_type=SelectField('Place type',choices=[
        ('parish','parish'),
        ('town','town'),
        ('city','city')
    ],default='parish')
    coord_x=IntegerField('X coordinate', validators=[Optional(), NumberRange(min=0, max=860, message='X must be between 0 and 860')])
    coord_y=IntegerField('Y coordinate', validators=[Optional(), NumberRange(min=0, max=580, message='Y must be between 0 and 580')])

    submit=SubmitField('Confirm')

