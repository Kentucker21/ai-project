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


def normalize_place_type(place_type):
    if place_type in ('parish', 'town', 'city'):
        return place_type
    return 'parish'


def parse_road_parts(stripped_line):
    inner = stripped_line[len("road("):-2]
    return [part.strip().strip("'") for part in inner.split(',')]


def build_road_line(parts):
    return f"road('{parts[0]}','{parts[1]}',{parts[2]},'{parts[3]}','{parts[4]}',{parts[5]},{parts[6]},{parts[7]},{parts[8]}).\n"


def insert_after_last_prefix(lines, prefix, new_line):
    last_index = -1
    block_started = False
    for index, line in enumerate(lines):
        stripped = line.strip()

        if prefix in ("road(", "place_info(") and block_started and not stripped.startswith(prefix + "'"):
            break

        if not (stripped.startswith(prefix) and stripped.endswith(').')):
            continue

        if prefix in ("road(", "place_info(") and not stripped.startswith(prefix + "'"):
            continue

        if prefix == "road(" and ":-" in stripped:
            continue

        if prefix == "place_info(" and ":-" in stripped:
            continue

        if prefix in ("road(", "place_info("):
            block_started = True

        last_index = index

    if last_index >= 0:
        lines.insert(last_index + 1, new_line)
    else:
        lines.append(new_line)


def add_road(lines, from_place, to_place, distance, road_type, condition, depth, duration, status, direction):
    if not from_place or not to_place:
        return lines, False, "Both From and To places are required"
    if from_place == to_place:
        return lines, False, "From and To must be different places"
    if distance is None or distance <= 0:
        return lines, False, "Distance must be a positive number"
    if duration is None or duration <= 0:
        return lines, False, "Travel time must be a positive number"

    # Check for duplicate road
    for line in lines:
        stripped = line.strip()
        if stripped.startswith("road("):
            parts = parse_road_parts(stripped)
            if (parts[0] == from_place and parts[1] == to_place) or \
               (parts[0] == to_place and parts[1] == from_place and parts[8] == 'two_way'):
                return lines, False, f"A road between '{from_place}' and '{to_place}' already exists"

    cond_atom = f"'{condition}'" if condition in ('deep potholes', 'broken cistern') else 'none'
    new_road = f"road('{from_place}','{to_place}',{distance},'{road_type}',{cond_atom},{depth},{duration},{status},{direction}).\n"
    updated_lines = list(lines)
    insert_after_last_prefix(updated_lines, "road(", new_road)
    return updated_lines, True, f"Added road '{from_place}' → '{to_place}'"


def add_place(lines, place_name, place_type, coord_x, coord_y):
    if not place_name:
        return lines, False, "Place name is required"
    if coord_x is None or coord_y is None:
        return lines, False, "X and Y coordinates are required"

    for line in lines:
        if line.strip().startswith(f"place_info('{place_name}',"):
            return lines, False, f"Place '{place_name}' already exists"

    updated_lines = list(lines)
    place_type_normalized = normalize_place_type(place_type)
    new_place_info = f"place_info('{place_name}', {place_type_normalized}, {int(coord_x)}, {int(coord_y)}).\n"
    insert_after_last_prefix(updated_lines, "place_info(", new_place_info)
    return updated_lines, True, f"Added place '{place_name}'"


def edit_place(lines, current_name, new_name, place_type, coord_x, coord_y):
    if not current_name:
        return lines, False, "Select a place to edit"

    final_name = new_name.strip() if new_name and new_name.strip() else current_name
    final_type = normalize_place_type(place_type)

    current_info = None
    place_found = False
    for line in lines:
        stripped = line.strip()
        if stripped.startswith(f"place_info('{current_name}',"):
            place_found = True
            inner = stripped[len(f"place_info('{current_name}',"):-2]
            parts = [p.strip() for p in inner.split(',')]
            if len(parts) == 3:
                current_info = parts

    if not place_found:
        return lines, False, f"Could not find place '{current_name}'"

    if coord_x is None or coord_y is None:
        if current_info is None:
            return lines, False, "Coordinates are required for this place"
        final_x, final_y = current_info[1], current_info[2]
    else:
        final_x, final_y = str(int(coord_x)), str(int(coord_y))

    updated_lines = []
    place_info_found = False

    for line in lines:
        stripped = line.strip()

        if stripped.startswith(f"place_info('{current_name}',"):
            updated_lines.append(f"place_info('{final_name}', {final_type}, {final_x}, {final_y}).\n")
            place_info_found = True
            continue

        if stripped.startswith("road("):
            parts = parse_road_parts(stripped)
            if parts[0] == current_name:
                parts[0] = final_name
            if parts[1] == current_name:
                parts[1] = final_name
            updated_lines.append(build_road_line(parts))
            continue

        updated_lines.append(line)

    if not place_info_found:
        insert_after_last_prefix(updated_lines, "place_info(", f"place_info('{final_name}', {final_type}, {final_x}, {final_y}).\n")

    return updated_lines, True, f"Updated place '{current_name}'"


def remove_place(lines, place_name):
    if not place_name:
        return lines, False, "Select a place to remove"

    updated_lines = []
    changed = False

    for line in lines:
        stripped = line.strip()

        if stripped.startswith(f"place_info('{place_name}',"):
            changed = True
            continue

        if stripped.startswith("road("):
            parts = parse_road_parts(stripped)
            if parts[0] == place_name or parts[1] == place_name:
                changed = True
                continue

        updated_lines.append(line)

    if not changed:
        return lines, False, f"Could not find place '{place_name}'"

    return updated_lines, True, f"Removed place '{place_name}' and related roads"

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

        if action == 'add_road':
            from_place = start
            to_place   = end
            distance   = form.road_distance.data
            road_type  = form.roadtype.data
            condition  = form.avoid.data
            depth      = form.pothole_depth.data or 0
            duration   = form.road_duration.data
            status     = form.status.data
            direction  = form.direction.data
            updated_lines, changed, message = add_road(
                lines, from_place, to_place, distance,
                road_type, condition, depth, duration, status, direction
            )
            if changed:
                with open(pl_path, 'w') as f:
                    f.writelines(updated_lines)
                prolog.consult(pl_path)
            flash(message)
            return redirect(url_for('admin'))

        if action == 'add_place':
            place_name = (form.place_name.data or '').strip()
            place_type = form.place_type.data
            coord_x = form.coord_x.data
            coord_y = form.coord_y.data
            if coord_x is not None and not (0 <= coord_x <= 860):
                flash('X coordinate must be between 0 and 860')
                return redirect(url_for('admin'))
            if coord_y is not None and not (0 <= coord_y <= 580):
                flash('Y coordinate must be between 0 and 580')
                return redirect(url_for('admin'))
            updated_lines, changed, message = add_place(lines, place_name, place_type, coord_x, coord_y)

            if changed:
                with open(pl_path, 'w') as f:
                    f.writelines(updated_lines)
                prolog.consult(pl_path)
                flash(message)
            else:
                flash(message)

            return redirect(url_for('admin'))

        if action == 'edit_place':
            current_name = start
            new_name = (form.new_place_name.data or '').strip()
            place_type = form.place_type.data
            coord_x = form.coord_x.data
            coord_y = form.coord_y.data
            if coord_x is not None and not (0 <= coord_x <= 860):
                flash('X coordinate must be between 0 and 860')
                return redirect(url_for('admin'))
            if coord_y is not None and not (0 <= coord_y <= 580):
                flash('Y coordinate must be between 0 and 580')
                return redirect(url_for('admin'))
            updated_lines, changed, message = edit_place(lines, current_name, new_name, place_type, coord_x, coord_y)

            if changed:
                with open(pl_path, 'w') as f:
                    f.writelines(updated_lines)
                prolog.consult(pl_path)
                flash(message)
            else:
                flash(message)

            return redirect(url_for('admin'))

        if action == 'remove_place':
            target_place = start
            updated_lines, changed, message = remove_place(lines, target_place)

            if changed:
                with open(pl_path, 'w') as f:
                    f.writelines(updated_lines)
                prolog.consult(pl_path)
                flash(message)
            else:
                flash(message)

            return redirect(url_for('admin'))

        updated_lines = []
        changed = False
        old_value = None
        new_value = None

        for line in lines:
            stripped = line.strip()

            if stripped.startswith("road("):
                parts = parse_road_parts(stripped)
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

                line = build_road_line(parts)
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
            }.get(action, action)
            flash(f"Updated {label} for {start} to {end}: '{old_value}' changed to '{new_value}'")
        else:
            flash(f"Could not find road: {start} to {end}")
 
    return flask.render_template('admin.html', title='Admin page', form=form)
 

if __name__=='__main__':
 app.run(debug=True)