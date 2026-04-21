from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField, SelectField, IntegerField, FloatField
from wtforms.validators import DataRequired, Length, Email, EqualTo, NumberRange, Optional


# Form for creating a new user account
class RegistrationForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired(), Length(min=2, max=20)])
    password = PasswordField('Password', validators=[DataRequired()])
    confirm_password = PasswordField('Confirm Password', validators=[DataRequired(), EqualTo('password')])
    submit = SubmitField('Sign Up')


# Form for logging in
class LoginForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired(), Length(min=2, max=20)])
    password = PasswordField('Password', validators=[DataRequired()])
    submit = SubmitField('Log in')


# Main form used on both the route-finding page and the admin panel.
# Covers: route search inputs, road management fields, and place management fields.
class GpsForm(FlaskForm):

    # Route search – start and end dropdowns are populated dynamically from Prolog
    start = SelectField('Start', choices=[], validators=[DataRequired()])
    end = SelectField('end', choices=[], validators=[DataRequired()])

    # Algorithm choice: Dijkstra (shortest path), A* (heuristic), DFS (first valid path)
    algorithm = SelectField('Search Algorithm', choices=[
        ('dijkstra', 'Dijkstra'),
        ('astar', 'A*'),
        ('dfs', 'DFS')
    ], default='dijkstra')

    # Filter: only traverse roads of this surface type
    roadtype = SelectField('road type', choices=[
        ('paved', 'paved'),
        ('unpaved', 'unpaved')
    ], validators=[DataRequired()])

    # Filter: skip roads with this condition
    avoid = SelectField('Avoid', choices=[
        ('broken cistern', 'broken cistern'),
        ('deep potholes', 'deep potholes'),
        ('none', 'none')
    ], validators=[DataRequired()])

    # Road attribute fields – used by admin when adding or updating a road
    status = SelectField('Road Status', choices=[
        ('open', 'open'),
        ('closed', 'closed'),
        ('seasonal_blocked', 'seasonal_blocked')
    ])

    direction = SelectField('Road Direction', choices=[
        ('two_way', 'two_way'),
        ('one_way', 'one_way')
    ])

    pothole_depth = IntegerField('Pothole depth (inches)')
    road_distance = FloatField('Distance (km)', validators=[Optional()])
    road_duration = IntegerField('Travel time (min)', validators=[Optional()])

    # Place management fields – used by admin when adding or editing a place
    place_name = StringField('Place name')
    new_place_name = StringField('New place name')
    place_type = SelectField('Place type', choices=[
        ('parish', 'parish'),
        ('town', 'town'),
        ('city', 'city')
    ], default='parish')

    # Map pixel coordinates for placing the node on the canvas (max 860 x 580)
    coord_x = IntegerField('X coordinate', validators=[Optional(), NumberRange(min=0, max=860, message='X must be between 0 and 860')])
    coord_y = IntegerField('Y coordinate', validators=[Optional(), NumberRange(min=0, max=580, message='Y must be between 0 and 580')])

    submit = SubmitField('Confirm')
