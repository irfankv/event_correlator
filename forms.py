from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField, PasswordField
from wtforms.validators import DataRequired, Length


class RegistrationForm(FlaskForm):
	machine_ip = StringField('Router IP', validators=[DataRequired(), Length(min=7, max=15)])
	device_username = StringField('Device Username', validators=[DataRequired()])
	device_password = PasswordField('Device Password', validators=[DataRequired()])
	device_name = StringField('Device Name', validators=[DataRequired()])
	device_details = StringField('Device Details (Optional)')
	submit = SubmitField('Register')

class LoginForm(FlaskForm):
	cec_username = StringField('Username', validators=[DataRequired()])
	password = PasswordField('Password', validators=[DataRequired()])
	submit = SubmitField('Login')