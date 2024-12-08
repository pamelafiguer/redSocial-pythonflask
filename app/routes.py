from flask import Blueprint, render_template, redirect, url_for, request, flash
from flask_login import login_user, current_user, logout_user, login_required
from app.models import User
from .forms import LoginForm, RegisterForm
from app import db

# Define the Blueprint
main = Blueprint("main", __name__)

@main.route("/", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("main.feed"))
    
    form = LoginForm()
    if form.validate_on_submit():
        email = form.email.data
        password = form.password.data

        try:
            result = db.session.execute(
                "CALL sp_login_user(:email, :password)",
                {"email": email, "password": password},
            ).fetchone()

            if result:
                user = User.query.get(result["id"])
                login_user(user)
                return redirect(url_for("main.feed"))
            else:
                flash("Credenciales incorrectas.", "error")
        except Exception as e:
            flash(f"Error al procesar la solicitud: {str(e)}", "error")

    return render_template("login.html", form=form)


@main.route("/register", methods=["GET", "POST"])
def register():
    if current_user.is_authenticated:
        return redirect(url_for("main.feed"))

    form = RegisterForm()
    if form.validate_on_submit():
        nombres = form.name.data
        apellidos = form.lastname.data
        email = form.email.data
        password = form.password.data
        birthday = f"{form.birthday_year.data}-{form.birthday_month.data}-{form.birthday_day.data}"
        sex = form.sex.data

        try:
            db.session.execute(
                "CALL Crear_Nuevo_usuario(:nombres, :apellidos, :birthday, :sex, :email, :password)",
                {
                    "nombres": nombres,
                    "apellidos": apellidos,
                    "birthday": birthday,
                    "sex": sex,
                    "email": email,
                    "password": password,
                },
            )
            db.session.commit()
            flash("Registro exitoso.", "success")
            return redirect(url_for("main.login"))
        except Exception as e:
            flash(f"Error al registrar usuario: {str(e)}", "error")

    return render_template("register.html", form=form)


@main.route("/feed")
@login_required
def feed():
    try:
        publicaciones = db.session.execute("CALL obtener_publicaciones()").fetchall()
        comentarios = {}
        reacciones = {}

        for publicacion in publicaciones:
            # Obtener comentarios
            comentarios[publicacion.id] = db.session.execute(
                "CALL obtener_comentarios(:id_publicacion)", {"id_publicacion": publicacion.id}
            ).fetchall()

            # Obtener reacciones
            reacciones[publicacion.id] = db.session.execute(
                "CALL ObtenerReacciones(:id_publicacion)", {"id_publicacion": publicacion.id}
            ).fetchall()

        return render_template(
            "feed.html", 
            publicaciones=publicaciones, 
            comentarios=comentarios, 
            reacciones=reacciones
        )
    except Exception as e:
        flash(f"Error al obtener datos de las publicaciones: {str(e)}", "error")
        return redirect(url_for("main.error"))


@main.route("/logout")
@login_required
def logout():
    logout_user()
    flash("Sesión cerrada correctamente.", "success")
    return redirect(url_for("main.login"))
