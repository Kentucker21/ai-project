import flask 
import os
import sys
from forms import RegistrationForm,LoginForm,GpsForm
from flask import flash,redirect,url_for
from flask_sqlalchemy import SQLAlchemy

try:
    from pyswip import Prolog
except Exception as exc:
    if exc.__class__.__name__ == "SwiPrologNotFoundError":
        print(
            "Error: SWI-Prolog not found. Install SWI-Prolog and add its bin folder to PATH.\n"
            "Download: https://www.swi-prolog.org/download/stable"
        )
        sys.exit(1)
    raise

app=flask.Flask(__name__)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PROLOG_FILE = os.path.join(BASE_DIR, "AIprolog.pl")

if not os.path.exists(PROLOG_FILE):
    print(f"Error: Prolog knowledge base not found at: {PROLOG_FILE}")
    sys.exit(1)

try:
    prolog=Prolog()
    prolog.consult(PROLOG_FILE)
except Exception as exc:
    if exc.__class__.__name__ != "SwiPrologNotFoundError":
        raise
    print(
        "Error: SWI-Prolog not found. Install SWI-Prolog and add its bin folder to PATH.\n"
        "Download: https://www.swi-prolog.org/download/stable"
    )
    sys.exit(1)


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

    if flask.request.method == 'POST':
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
    
    return redirect(url_for('home'))




@app.route('/admin', methods=['GET', 'POST'])
def admin():
    form = GpsForm()
    if flask.request.method == 'POST':
        start = form.start.data
        end = form.end.data
        action = flask.request.form.get('action')
        pl_path = PROLOG_FILE
 
        with open(pl_path, 'r') as f:
            lines = f.readlines()
 
        updated_lines = []
        changed = False
        old_value = None
        new_value = None
 
        for line in lines:
            stripped = line.strip()
 
            if stripped.startswith(f"road('{start}','{end}',"):
                inner = stripped[len("road("):-2]
                parts = [p.strip().strip("'") for p in inner.split(',')]
                # parts = [start, end, dist, type, condition, dur, status]
 
                if action == 'condition':
                    old_value = parts[4]
                    new_value = form.avoid.data
                    parts[4] = new_value
 
                elif action == 'roadtype':
                    old_value = parts[3]
                    new_value = form.roadtype.data
                    parts[3] = new_value
 
                elif action == 'status':
                    old_value = parts[6]
                    new_value = form.status.data
                    parts[6] = new_value
 
                # status has no quotes in the .pl file (it's an atom like open/closed)
                line = f"road('{parts[0]}','{parts[1]}',{parts[2]},'{parts[3]}','{parts[4]}',{parts[5]},{parts[6]}).\n"
                changed = True
 
            updated_lines.append(line)
 
        if changed:
            with open(pl_path, 'w') as f:
                f.writelines(updated_lines)
            prolog.consult(pl_path)
            label = {'condition': 'condition', 'roadtype': 'road type', 'status': 'status'}[action]
            flash(f"Updated {label} for {start} to {end}: '{old_value}' changed to '{new_value}'")
        else:
            flash(f"Could not find road: {start} to {end}")
 
    return flask.render_template('admin.html', title='Admin page', form=form)
 

if __name__=='__main__':
 app.run(debug=True)