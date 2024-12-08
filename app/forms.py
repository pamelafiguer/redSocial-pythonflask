
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField
from wtforms.validators import DataRequired
from wtforms import StringField, PasswordField, SelectField, RadioField
from wtforms.validators import DataRequired, Email, EqualTo

class LoginForm(FlaskForm):
    email = StringField('Correo electrónico', validators=[DataRequired()])
    password = PasswordField('Contraseña', validators=[DataRequired()])
    
    
class RegisterForm(FlaskForm):
    name = StringField('Nombres', validators=[DataRequired()])
    lastname = StringField('Apellidos', validators=[DataRequired()])
    email = StringField('Correo electrónico', validators=[DataRequired(), Email()])
    password = PasswordField('Contraseña', validators=[DataRequired()])
    password_confirmation = PasswordField('Confirmar Contraseña', validators=[DataRequired(), EqualTo('password')])
    sex = RadioField('Género', choices=[('Femenino', 'Femenino'), ('Masculino', 'Masculino'), ('Personalizado', 'Personalizado')], validators=[DataRequired()])
    birthday_day = SelectField( 'class=custom-select-1','Dia', choices=[(str(i), str(i)) for i in range(1, 32)], render_kw={"class": "custom-select-1"})
    birthday_month = SelectField('class=custom-select-2','Mes', choices=[(str(i), month) for i, month in enumerate([
        'Enero', 'Febrero', 'Marzo', 'Abril', 'Mayo', 'Junio', 'Julio', 'Agosto', 'Septiembre', 'Octubre', 'Noviembre', 'Diciembre'], 1)], render_kw={"class": "custom-select-2"})
    birthday_year = SelectField('class=custom-select-3','Año', choices=[(str(year), str(year)) for year in range(2024, 1904, -1)],render_kw={"class": "custom-select-3"})

