from flask_wtf import FlaskForm
from wtforms import StringField,PasswordField,SubmitField,SelectField
from wtforms.validators import DataRequired,Length,Email,EqualTo


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
    start=SelectField('Start',choices=[('Kingston','Kingston'),
    ('St.Catherine','St.Catherine'),
    ('Portland','Portland'),
    ('St.andrew','St.andrew')
    
    ],validators=[DataRequired()])
    end=SelectField('end',choices=[('Kingston','Kingston'),
    ('St.Catherine','St.Catherine'),
    ('Portland','Portland'),
    ('St.andrew','St.andrew')
    
    ],validators=[DataRequired()])

    roadtype=SelectField('road type',choices=[
     ('paved','paved'),
     ('unpaved','unpaved')
    ],validators=[DataRequired()])

    avoid=SelectField('Avoid',choices=[
        ('broken cistern','broken cistern'),
        ('deep potholes','deep potholes'),
        ('none','none')
    ],validators=[DataRequired()])

    submit=SubmitField('Confirm')

