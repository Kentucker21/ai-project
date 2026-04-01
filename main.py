import flask 
import os
import sys
from forms import RegistrationForm,LoginForm,GpsForm
from flask import flash,redirect,url_for
from flask_sqlalchemy import SQLAlchemy
from road_graph import build_road_network_graph, normalize_path, build_route_edge_details

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


def refresh_prolog_data():
    prolog.consult(PROLOG_FILE)


def has_coords(place_name):
    return len(list(prolog.query(f"coords('{place_name}', _, _)"))) > 0


def get_all_places():
    """Query Prolog for all places and return as (value, label) tuples."""
    places = []
    for result in prolog.query("place(X)"):
        place_name = str(result['X']).strip("'")
        places.append((place_name, place_name))
    return sorted(places)


def populate_form_choices(form):
    """Populate GpsForm start and end choices from Prolog places."""
    places = get_all_places()
    form.start.choices = places
    form.end.choices = places
    return form

class User(db.Model):
    id=db.Column(db.Integer,primary_key=True)
    username=db.Column(db.String(20),unique=True,nullable=False)
    Password=db.Column(db.String(20),nullable=False)
    Role=db.Column(db.String(20),nullable=False,default='User')
    def __repr__(self):
        return f"<User {self.id}: {self.username}, {self.Role}>"



@app.route('/',methods=['GET', 'POST'])
def home():
    refresh_prolog_data()
    form = GpsForm()
    populate_form_choices(form)
    graph_nodes, graph_edges = build_road_network_graph(prolog)
    return flask.render_template(
        'index.html',
        form=form,
        paths=None,
        graph_nodes=graph_nodes,
        graph_edges=graph_edges,
        selected_path=[],
        selected_route_edges=[],
        algorithm_used=None
    )
    


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
    refresh_prolog_data()
    form = GpsForm()
    populate_form_choices(form)

    paths = None
    Distance = None
    Duration = None
    result = None
    algorithm_used = None
    selected_path = []
    selected_route_edges = []
    graph_nodes, graph_edges = build_road_network_graph(prolog)

    if flask.request.method == 'POST':
        start = form.start.data
        end = form.end.data
        algorithm_name = form.algorithm.data
        roadtype = form.roadtype.data
        avoid = form.avoid.data

        if algorithm_name not in ('dijkstra', 'astar', 'dfs'):
            algorithm_name = 'dijkstra'

        result_data = list(prolog.query(
            f"{algorithm_name}('{start}', '{end}', Path, Distance, Duration, '{roadtype}', '{avoid}')"
        ))

        if len(result_data) > 0:
            paths = result_data[0]['Path']
            Distance = result_data[0]['Distance']
            Duration = result_data[0]['Duration']
            selected_path = normalize_path(paths)
            selected_route_edges = build_route_edge_details(selected_path, graph_edges)
            algorithm_labels = {
                'dijkstra': 'Dijkstra',
                'astar': 'A*',
                'dfs': 'DFS'
            }
            algorithm_used = algorithm_labels.get(algorithm_name, 'Dijkstra')
        else:
            result = 'Could not find a route try again'

    return flask.render_template(
        'index.html',
        title='Roadworks',
        form=form,
        paths=paths,
        Distance=Distance,
        Duration=Duration,
        result=result,
        graph_nodes=graph_nodes,
        graph_edges=graph_edges,
        selected_path=selected_path,
        selected_route_edges=selected_route_edges,
        algorithm_used=algorithm_used
    )

  
@app.route('/clear-list')
def clear_list():
    
    return redirect(url_for('home'))




@app.route('/admin', methods=['GET', 'POST'])
def admin():
    refresh_prolog_data()
    form = GpsForm()
    populate_form_choices(form)
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

            if stripped.startswith("road("):
                inner = stripped[len("road("):-2]
                parts = [p.strip().strip("'") for p in inner.split(',')]
                # parts = [start, end, dist, type, condition, depth, dur, status, direction]

                forward_match = parts[0] == start and parts[1] == end
                reverse_two_way_match = parts[0] == end and parts[1] == start and parts[8] == 'two_way'
                if not (forward_match or reverse_two_way_match):
                    updated_lines.append(line)
                    continue
 
                if action == 'condition':
                    old_value = parts[4]
                    new_value = form.avoid.data
                    parts[4] = new_value

                elif action == 'pothole_depth':
                    old_value = parts[5]
                    new_value = str(form.pothole_depth.data if form.pothole_depth.data is not None else 0)
                    parts[5] = new_value
                    if int(new_value) > 3:
                        parts[4] = 'deep potholes'
 
                elif action == 'roadtype':
                    old_value = parts[3]
                    new_value = form.roadtype.data
                    parts[3] = new_value
 
                elif action == 'status':
                    old_value = parts[7]
                    new_value = form.status.data
                    parts[7] = new_value

                elif action == 'direction':
                    old_value = parts[8]
                    new_value = form.direction.data
                    parts[8] = new_value
 
                # status/direction are atoms in .pl file
                line = f"road('{parts[0]}','{parts[1]}',{parts[2]},'{parts[3]}','{parts[4]}',{parts[5]},{parts[6]},{parts[7]},{parts[8]}).\n"
                changed = True

            updated_lines.append(line)
 
        if changed:
            with open(pl_path, 'w') as f:
                f.writelines(updated_lines)
            prolog.consult(pl_path)
            label = {
                'condition': 'condition',
                'roadtype': 'road type',
                'status': 'status',
                'direction': 'direction',
                'pothole_depth': 'pothole depth'
            }[action]
            flash(f"Updated {label} for {start} to {end}: '{old_value}' changed to '{new_value}'")
        else:
            flash(f"Could not find road: {start} to {end}")
 
    return flask.render_template('admin.html', title='Admin page', form=form)
 

if __name__=='__main__':
 app.run(debug=True)