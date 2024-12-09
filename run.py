from flask import (Flask,request,jsonify,render_template,redirect,url_for,session,flash,)
from flask_mysqldb import MySQL
from flask_login import current_user, login_required
from werkzeug.security import check_password_hash
from flask_login import LoginManager, login_user, login_required, logout_user, UserMixin
from datetime import datetime
import MySQLdb
import os
from datetime import datetime
from werkzeug.utils import secure_filename


app = Flask(__name__)

import os

app.config["SECRET_KEY"] = os.urandom(24)
app.config["MYSQL_HOST"] = "localhost"
app.config["MYSQL_USER"] = "root"
app.config["MYSQL_PASSWORD"] = ""
app.config["MYSQL_DB"] = "red_social"
app.config['UPLOAD_FOLDER'] = 'uploads/posts'  # Carpeta donde se almacenarán las imágenes
app.config['ALLOWED_EXTENSIONS'] = {'jpeg', 'png', 'jpg', 'gif'}
app.config['MAX_CONTENT_LENGTH'] = 2 * 1024 * 1024 


mysql = MySQL(app)
login_manager = LoginManager(app)
login_manager.login_view = "login"  # Redirigir usuarios no autenticados al login


# Modelo de usuario
class User(UserMixin):
    def __init__(self, id, email):
        self.id = id  # Flask-Login requiere este atributo
        self.email = email

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']


@login_manager.user_loader
def load_user(user_id):
    cursor = mysql.connection.cursor()
    cursor.execute(
        "SELECT id_usuario, email, passwordd FROM Usuario WHERE id_usuario = %s",
        (user_id,),
    )
    user_data = cursor.fetchone()
    cursor.close()

    if user_data:
        return User(id=user_data[0], email=user_data[1])
    return None


# Ruta de inicio (pantalla de login)
@app.route("/")
@app.route("/", methods=["GET", "POST"])
def login():
    if request.method == "GET":
        return render_template("login.html")

    email = request.form.get("email")
    password = request.form.get("password")

    if not email or not password:
        flash("Email y contraseña son obligatorios.", "error")
        return redirect(url_for("login"))

    try:
        cursor = mysql.connection.cursor()
        cursor.callproc("Usuarios_Logeo", (email,))
        result = cursor.fetchall()
        cursor.close()

        if len(result) > 0:
            user_data = result[0]
            stored_password = user_data[6]

            # Comparar contraseñas directamente
            if stored_password.strip() == password.strip():
                user = User(id=user_data[0], email=user_data[5])
                login_user(user)
                return redirect(url_for("feed"))  # Redirige al feed
            else:
                flash("Credenciales incorrectas.", "error")
        else:
            flash("Usuario no encontrado.", "error")

    except Exception as e:
        flash(f"Error interno: {str(e)}", "error")
        print(f"Detalles del error: {e}")  # Detalles del error en la consola
        return redirect(url_for("login"))

@app.route('/nuevo_feed', methods=['POST'])
@login_required
def nuevo_feed():
    if not current_user.is_authenticated:
        flash('Debes iniciar sesión para publicar.', 'error')
        return redirect(url_for('login'))  # Redirige a la ruta de inicio de sesión

    # Validar los datos del formulario
    content = request.form.get('content')
    if not content or len(content) > 500:
        flash('El contenido es obligatorio y no debe exceder los 500 caracteres.', 'error')
        return redirect(url_for('feed'))  # O redirige a la página del feed

    # Procesar la imagen si existe
    image_path = None
    if 'imagen' in request.files:
        imagen = request.files['imagen']
        if imagen and allowed_file(imagen.filename):
            try:
                # Guardar la imagen con un nombre único
                filename = secure_filename(imagen.filename)
                image_name = f"{int(datetime.now().timestamp())}_{filename}"
                image_path = os.path.join(app.config['UPLOAD_FOLDER'], image_name).replace("\\", "/")
                imagen.save(image_path)
            except Exception as e:
                flash(f'Error al subir la imagen: {str(e)}', 'error')
                return redirect(url_for('feed'))  # O redirige a la página del feed

    try:
        # Insertar la publicación en la base de datos
        cur = mysql.connection.cursor()
        cur.callproc('Crear_Publicacion', (current_user.id, content, image_path, datetime.utcnow()))
        mysql.connection.commit()
        cur.close()

        flash('Publicación creada exitosamente.', 'success')
        return redirect(url_for('feed')) 

    except Exception as e:
        mysql.connection.rollback()  # Deshacer cambios en caso de error
        flash(f'Error al crear la publicación: {str(e)}', 'error')
        return redirect(url_for('feed'))  # O redirige a la página del feed

# Ruta protegida (feed)
@app.route("/feed")
@login_required
def feed():
    # Obtener al usuario autenticado
    usuario = current_user

    if not usuario.is_authenticated:
        flash("Usuario no autenticado.", "error")
        return redirect(url_for("login"))

    try:
        # Obtener las publicaciones llamando al procedimiento almacenado
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        cursor.callproc("obtener_publicaciones")
        publicaciones = cursor.fetchall()
        cursor.close()

        # Procesar cada publicación para incluir la reacción del usuario
        for publicacion in publicaciones:
            cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
            cursor.execute(
                """
                SELECT reaccion 
                FROM likes 
                WHERE id_usuario = %s AND id_publicacion = %s
            """,
                (usuario.id, publicacion["id_publicacion"]),
            )
            reaccion = cursor.fetchone()
            cursor.close()

            publicacion["reaccion_usuario"] = reaccion["reaccion"] if reaccion else None

        # Inicializar estructuras para comentarios y reacciones
        comentarios = {}
        reacciones = {}

        for publicacion in publicaciones:
            id_publicacion = publicacion["id_publicacion"]

            # Obtener los comentarios de cada publicación
            cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
            cursor.callproc("obtener_comentarios", (id_publicacion,))
            comentarios[id_publicacion] = cursor.fetchall()
            cursor.close()

            # Obtener las reacciones de cada publicación
            cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
            cursor.callproc("ObtenerReacciones", (id_publicacion,))
            reacciones[id_publicacion] = cursor.fetchall()
            cursor.close()

        # Renderizar la plantilla con las publicaciones, comentarios y reacciones
        return render_template(
            "feed.html",
            publicaciones=publicaciones,
            comentarios=comentarios,
            reacciones=reacciones,
        )

    except Exception as e:
        flash(f"Error interno: {str(e)}", "error")
        return redirect(url_for("login"))


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        # Validaciones del formulario
        nombres = request.form.get("Nombres")
        apellidos = request.form.get("Apellidos")
        birthday_day = request.form.get("birthday_day")
        birthday_month = request.form.get("birthday_month")
        birthday_year = request.form.get("birthday_year")
        sex = request.form.get("sex")
        email = request.form.get("email")
        password = request.form.get("password")
        password_confirm = request.form.get("password_confirmation")

        # Validación básica
        if (
            not nombres
            or not apellidos
            or not birthday_day
            or not birthday_month
            or not birthday_year
            or not sex
            or not email
            or not password
        ):
            flash("Todos los campos son obligatorios.", "error")
            return redirect(url_for("register"))

        if password != password_confirm:
            flash("Las contraseñas no coinciden.", "error")
            return redirect(url_for("register"))

        # Formato de fecha
        try:
            birthday = datetime(
                year=int(birthday_year),
                month=int(birthday_month),
                day=int(birthday_day),
            ).strftime("%Y-%m-%d")
        except ValueError:
            flash("Fecha de nacimiento no válida.", "error")
            return redirect(url_for("register"))
        try:
            cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
            cursor.callproc(
                "Crear_Nuevo_usuario",
                [nombres, apellidos, birthday, sex, email, password],
            )
            mysql.connection.commit()  # Confirmar la transacción
            cursor.close()

            flash("Registro exitoso", "success")
            return redirect(url_for("login"))

        except Exception as e:
            flash(f"Error al registrar el usuario: {str(e)}", "error")
            return redirect(url_for("register"))

    return render_template("register.html")


@app.route("/reaccionar/<int:id_publicacion>", methods=["POST"])
@login_required
def reaccionar(id_publicacion):
    id_usuario = current_user.id
    tipo_reaccion = request.form.get("tipo")

    try:
        cursor = mysql.connection.cursor()

        # Ejecutamos el procedimiento almacenado para agregar la reacción
        cursor.callproc(
            "agregar_reacciones", (tipo_reaccion, id_usuario, id_publicacion)
        )
        mysql.connection.commit()

        # Contamos las reacciones
        cursor.execute(
            "SELECT COUNT(*) FROM likes WHERE id_publicacion = %s AND reaccion = %s",
            (id_publicacion, "me gusta"),
        )
        me_gusta = cursor.fetchone()[0]

        cursor.execute(
            "SELECT COUNT(*) FROM likes WHERE id_publicacion = %s AND reaccion = %s",
            (id_publicacion, "me encanta"),
        )
        me_encanta = cursor.fetchone()[0]

        cursor.close()

        flash("Reacción agregada correctamente.", "success")

        return redirect(url_for("feed"))
    except Exception as e:
        flash(f"Hubo un problema al agregar la reacción: {str(e)}", "error")
        return redirect(url_for("feed"))


@app.route("/comentar/<int:id_publicacion>", methods=["POST"])
@login_required
def comentar(id_publicacion):
    contenido = request.form.get("contenido")
    id_usuario = current_user.id  # Obtener el id del usuario autenticado

    # Verificar que el contenido no esté vacío
    if not contenido:
        flash("El contenido del comentario es obligatorio.", "error")
        return redirect(
            url_for("feed")
        )  # O la página donde se está mostrando la publicación

    try:
        # Establecer conexión con la base de datos
        cursor = mysql.connection.cursor()

        # Llamar al procedimiento almacenado para agregar el comentario
        cursor.callproc(
            "Agregar_Comentario",
            (
                id_publicacion,
                id_usuario,
                contenido,
                datetime.now().strftime("%Y-%m-%d"),
            ),
        )

        # Confirmar la transacción
        mysql.connection.commit()

        # Cerrar el cursor
        cursor.close()

        # Mensaje de éxito
        flash("Comentario agregado correctamente.", "success")
        return redirect(
            url_for("feed")
        )  # O redirige a la página de la publicación donde se hizo el comentario

    except Exception as e:
        # Si ocurre un error, mostrar mensaje de error
        flash(f"Hubo un problema al agregar el comentario: {str(e)}", "error")
        return redirect(url_for("feed"))


# Ruta de cierre de sesión
@app.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for("login"))


if __name__ == "__main__":
    app.run(debug=True)
