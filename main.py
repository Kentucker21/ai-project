import flask 
from forms import RegistrationForm,LoginForm,GpsForm
from flask import flash,redirect,url_for
from flask_sqlalchemy import SQLAlchemy
from pyswip import Prolog

app=flask.Flask(__name__)

prolog=Prolog()
prolog.consult(r"C:\Users\kenei\OneDrive\Desktop\new coding journey 2026\AI_project\AIprolog.pl")


app.config['SECRET_KEY']='7a1dd0ea230da38fed228844abc489fa'
app.config['SQLALCHEMY_DATABASE_URI']='sqlite:///site.db'

db=SQLAlchemy(app)

class User(db.Model):
    id=db.Column(db.Integer,primary_key=True)
    username=db.Column(db.String(20),unique=True,nullable=False)
    Password=db.Column(db.String(20),nullable=False)
    Role=db.Column(db.String(20),nullable=False,default='User')
    def __repr__(self):
        return f"<User {self.id}: {self.username}, {self.Role}>"



@app.route('/',methods=['GET', 'POST'])
def home():
    form = GpsForm()
    return flask.render_template('index.html', form=form, paths=None)
    


@app.route('/register',methods=['GET', 'POST'])

def register():
 form = RegistrationForm()
 if form.validate_on_submit():
        get_data=User(username=form.username.data,Password=form.password.data)
        db.session.add(get_data)
        db.session.commit()
        
        flash(f'Account created for {form.username.data}!', 'success')
        return redirect(url_for('login'))
 else:
        print("FORM ERRORS:", form.errors)  

 return flask.render_template("register.html", title='register', form=form)


@app.route('/login' ,methods=['GET', 'POST'])

def login():
    form=LoginForm()
    if form.validate_on_submit():
         all_users=User.query.all()
         for user in all_users:
               if form.username.data==user.username and form.password.data == user.Password and user.Role=='admin':
                      flash('You have been logged in','success')
                      return redirect(url_for('admin'))
               elif form.username.data ==user.username and form.password.data == user.Password and user.Role=='User':
                   flash('You have been logged in','success')
                   return redirect(url_for('mainapp'))
    
                   
         
    return flask.render_template("login.html",title='login',form=form)




@app.route('/mainapp', methods=['GET', 'POST'])
def mainapp():
    form = GpsForm()

    paths = None
    Distance = None
    Duration = None
    result = None

    if form.validate_on_submit():
        result_data = list(prolog.query(
            f"dijkstra('{form.start.data}', '{form.end.data}', Path, Distance, Duration, '{form.roadtype.data}', '{form.avoid.data}')"
        ))

        if len(result_data) > 0:
            paths = result_data[0]['Path']
            Distance = result_data[0]['Distance']
            Duration = result_data[0]['Duration']
        else:
            result = 'Could not find a route try again'

    return flask.render_template(
        'index.html',
        title='Roadworks',
        form=form,
        paths=paths,
        Distance=Distance,
        Duration=Duration,
        result=result
    )

  
@app.route('/clear-list')
def clear_list():
    # This is the magic part: it sends the user back to the blank home page
    return redirect(url_for('home'))

@app.route('/admin',methods=['GET', 'POST'])
def admin():
     
     return flask.render_template('admin.html',title='admin page')


if __name__=='__main__':
 app.run(debug=True)