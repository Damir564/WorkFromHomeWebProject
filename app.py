from flask import Flask, redirect, url_for, render_template, request, session, flash
from datetime import timedelta, datetime
from flask_sqlalchemy import SQLAlchemy

app = Flask(__name__)
app.secret_key = "hello"
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///relationships.db"
app.permanent_session_lifetime = timedelta(minutes=45)

db = SQLAlchemy(app)

membs = db.Table('membs',
                 db.Column('user_id', db.Integer, db.ForeignKey('user.id')),
                 db.Column('project_id', db.Integer, db.ForeignKey('project.id'))
                 )


class User(db.Model):
    """User"""
    id = db.Column("id", db.Integer, primary_key=True)
    name = db.Column(db.String(100))
    surname = db.Column(db.String(100))
    email = db.Column(db.String(100), unique=True, nullable=False)
    password = db.Column(db.String(100), nullable=False)
    projects = db.relationship('Project', secondary=membs, backref=db.backref('members', lazy='dynamic'))
    own = db.relationship('Project', backref='owner', lazy='dynamic')


class Project(db.Model):
    """Project"""
    id = db.Column("id", db.Integer, primary_key=True)
    name = db.Column(db.String(60), unique=True)
    category = db.Column(db.String(100), nullable=True)
    description = db.Column(db.String(500), nullable=True)
    owner_email = db.Column(db.Integer, db.ForeignKey('user.id'))
    date_created = db.Column(db.DateTime)
    has = db.relationship('Work', backref='has', lazy='dynamic')


class Work(db.Model):
    """Work"""
    id = db.Column("id", db.Integer, primary_key=True)
    name = db.Column(db.String(60), unique=True)
    description = db.Column(db.Text(500), nullable=True)
    owner_project = db.Column(db.Integer, db.ForeignKey('project.id'))
    date_created = db.Column(db.DateTime)


@app.route("/", methods=["GET", "POST"])
def home():
    return render_template("index.html")


@app.route("/registration", methods=["POST", "GET"])
def registration():
    """Registration Form"""
    if request.method == 'POST':
        if request.form["first_name"] and request.form["last_name"] and \
                request.form["email"] and request.form["password"]:
            if not User.query.filter_by(email=request.form["email"]).first():
                if request.form["password"] == request.form["password_confirmation"]:
                    if len(request.form["password"]) >= 8:
                        new_user = User(
                            name=request.form["first_name"],
                            surname=request.form["last_name"],
                            email=request.form["email"],
                            password=request.form["password"], )
                        db.session.add(new_user)
                        db.session.commit()
                        return redirect('login')
                    else:
                        flash("длина пароля не должна быть меньше 8")
                else:
                    flash("Пароли не совпадают")
            else:
                flash("Этот email уже занят")
        else:
            flash("Введены не все данные")
    return render_template('registration.html')


@app.route("/login", methods=["POST", "GET"])
def login():
    """Login Form"""
    if request.method == "POST":
        session.permanent = True
        email = request.form["email"]
        found_user = User.query.filter_by(email=email).first()
        session["email"] = email
        if found_user:
            if found_user.password == request.form["password"]:
                flash(f"Добро пожаловать, {found_user.name}!")
                return redirect(url_for("user", user_email=session["email"]))
            else:
                flash("Неверный логин/пароль")
        else:
            flash("Неверный логин/пароль")
        return render_template("login.html")
    return render_template("login.html")


@app.route("/user/<user_email>", methods=["POST", "GET"])
def user(user_email):
    """User Page"""
    if session["email"] == user_email:
        return render_template("user.html")
    else:
        return render_template("login.html")


@app.route("/logout")
def logout():
    """Logout"""
    session.pop("name", None)
    session.pop("surname", None)
    session.pop("email", None)
    session.pop("password", None)
    session.pop("project.name", None)
    return redirect("login")


@app.route("/project_list")
def project_list():
    """User's avaliable projects"""
    projects = Project.query.filter_by(owner_email=session["email"]).order_by(Project.date_created.desc()).all()
    usr = User.query.filter_by(email=session["email"]).first()
    projects_all = Project.query.order_by(Project.date_created.desc()).all()
    for i in projects_all:
        if usr in i.members:
            projects.append(i)
    return render_template("project_list.html", projects=projects, username=session["email"])


@app.route("/member_list/<project_name>")
def member_list(project_name):
    """Project's member list"""
    project = Project.query.filter_by(name=project_name).first()
    members = project.members
    return render_template("member_list.html", members=members, project=project)


@app.route("/create_project", methods=["POST", "GET"])
def create_project():
    """Project Creation Form"""
    if session["email"]:
        if request.method == 'POST':
            if request.form["name"]:
                if not Project.query.filter_by(name=request.form["name"]).first():
                    if len(request.form["name"]) < 50:
                        new_project = Project(
                            name=request.form["name"],
                            category=request.form["category"],
                            description=request.form["description"],
                            owner_email=User.query.filter_by(email=session["email"]).first().email,
                            date_created=datetime.now())  # 1 cahnge
                        db.session.add(new_project)
                        db.session.commit()
                        return redirect(url_for("user", user_email=session["email"]))
                    else:
                        flash("Название должно быть менше 50 символов")
                else:
                    flash("Название проекта уже занято")
            else:
                flash("Введите название проекта")
        return render_template('create_project.html')


@app.route("/project/<project_name>", methods=["POST", "GET"])
def project(project_name):
    if session["email"]:
        session.permanent = True
        project = Project.query.filter_by(name=project_name).first()
        works = Work.query.filter_by(owner_project=project.name).all()
        session["project.name"] = project.name
    else:
        return redirect("logout")
    return render_template("project.html", works=works, project=project)


@app.route("/project/add_member/<project_name>", methods=["POST", "GET"])
def add_member(project_name):
    """Project Creation Form"""
    if session["email"] and session["email"] == Project.query.filter_by(name=project_name).first().owner_email:
        if request.method == 'POST':
            if request.form["email"]:
                if User.query.filter_by(email=request.form["email"]).first():
                    usr = User.query.filter_by(email=request.form["email"]).first()
                    pro = Project.query.filter_by(name=project_name).first()
                    if usr not in pro.members and usr.email != pro.owner_email:
                        pro.members.append(usr)
                        db.session.commit()
                        return redirect(url_for("project", project_name=project_name))
                    elif usr.email == pro.owner_email:
                        flash("Это создатель проекта")
                    else:
                        flash("Этот пользователь уже участник этого проекта")
                else:
                    flash("Такого пользователя не существует")
            else:
                flash("Введите электрооный адрес пользователя")
    else:
        return redirect("logout")
    return render_template('add_member.html', project_name=project_name)


@app.route("/project/remove_member/<project_name>", methods=["POST", "GET"])
def remove_member(project_name):
    if request.method == 'POST':
        if request.form["email"]:
            if User.query.filter_by(email=request.form["email"]).first():
                usr = User.query.filter_by(email=request.form["email"]).first()
                pro = Project.query.filter_by(name=project_name).first()
                if usr in pro.members and usr.email != pro.owner_email:
                    n = 0
                    for i in pro.members:
                        if i.email == usr.email:
                            n = i
                    ms = pro.members[:]
                    pro.members = []
                    for i in ms:
                        if i != n:
                            pro.members.append(i)
                    db.session.commit()
                    return redirect(url_for("project", project_name=project_name))
                elif usr.email == pro.owner_email:
                    flash("Это создатель проекта")
                elif usr.email == pro.owner_email:
                    flash("Этот пользователь владелец этого проекта")
                else:
                    flash("Этот пользователь не участник этого проекта")
            else:
                flash("Такого пользователя не существует")
        else:
            flash("Введите электрооный адрес пользователя")
    return render_template('remove_member.html', project_name=project_name)


@app.route("/project/leave_project/<project_name>", methods=["POST", "GET"])
def leave_project(project_name):
    pro = Project.query.filter_by(name=project_name).first()
    n = 0
    for i in pro.members:
        if i.email == session["email"]:
            n = i
    ms = pro.members[:]
    pro.members = []
    for i in ms:
        if i != n:
            pro.members.append(i)
    db.session.commit()
    return redirect(url_for("project_list"))


@app.route("/create_work/<project_name>", methods=["POST", "GET"])
def create_work(project_name):
    """Work Creation Form"""
    if request.method == 'POST':
        if request.form["name"]:
            if len(request.form["name"]) < 50:
                new_work = Work(
                    name=request.form["name"],
                    description=request.form["description"],
                    owner_project=Project.query.filter_by(name=project_name).first().name,
                    date_created=datetime.now())  # 1 cahnge
                db.session.add(new_work)
                db.session.commit()
                return redirect(url_for("project", project_name=project_name))
            else:
                flash("Название должно быть менше 50 символов")
        else:
            flash("Введите заголовок работы")
    return render_template('create_work.html')


@app.route("/project/work_description/<work_name>")
def work_description(work_name):
    """Work Description"""
    work = Work.query.filter_by(name=work_name).first()
    return render_template('work_description.html', project_name=session["project.name"],
                           work=work)


@app.route("/project/project_description/<project_name>")
def project_description(project_name):
    """Project Description"""
    project = Project.query.filter_by(name=project_name).first()
    return render_template('project_description.html', project_name=session["project.name"],
                           project=project)


@app.route("/project/work_done/<work_id>")
def work_done(work_id):
    """Marking as Done"""
    pro = Project.query.filter_by(name=session["project.name"]).first()
    work = Work.query.filter_by(id=work_id).first()
    if session["email"] == pro.owner_email:
        db.session.delete(work)
        db.session.commit()
    works = Work.query.filter_by(owner_project=pro.name).all()
    return render_template("project.html", works=works, project=pro)


@app.route("/project/project_delete/<project_name>")
def project_delete(project_name):
    """Project Deleting"""
    pro = Project.query.filter_by(name=project_name).first()
    works = Work.query.all()
    if session["email"] == pro.owner_email:
        if works:
            for i in works:
                db.session.delete(i)
        db.session.delete(pro)
        db.session.commit()
    projects = Project.query.filter_by(owner_email=session["email"]).order_by(Project.date_created.desc()).all()
    usr = User.query.filter_by(email=session["email"]).first()
    projects_all = Project.query.order_by(Project.date_created.desc()).all()
    for i in projects_all:
        if usr in i.members:
            projects.append(i)
    return render_template("project_list.html", projects=projects, username=session["email"])


if __name__ == "__main__":
    db.create_all()
    app.run(debug=True)
