import base64
from flask import Flask, render_template, redirect, url_for, session, flash, request, make_response
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField
from wtforms.validators import DataRequired, Email, ValidationError
import bcrypt
from flask_mysqldb import MySQL

# Function to decode the encoded secrets
def decode_secret(encoded_string):
    decoded_bytes = base64.b64decode(encoded_string)
    return decoded_bytes.decode('utf-8')

app = Flask(__name__)

# MySQL Configuration (using base64 encoded secrets)
app.config['MYSQL_HOST'] = decode_secret('bG9jYWxob3N0')  # localhost (base64 encoded)
app.config['MYSQL_USER'] = decode_secret('cm9vdA==')  # root (base64 encoded)
app.config['MYSQL_PASSWORD'] = decode_secret('RGVlcGFrQDEyMw==')  # Deepak@123 (base64 encoded)
app.config['MYSQL_DB'] = decode_secret('TXlkYXRhYmFzZQ==')  # Mydatabase (base64 encoded)
app.secret_key = decode_secret('eW91cl9zZWNyZXRfa2V5X2hlcmU=')  # your_secret_key_here (base64 encoded)

mysql = MySQL(app)

# Password Policy Validator
def password_policy(form, field):
    password = field.data
    if len(password) < 8:
        raise ValidationError("Password must be at least 8 characters long.")
    if not any(char.isdigit() for char in password):
        raise ValidationError("Password must include at least one number.")
    if not any(char.isupper() for char in password):
        raise ValidationError("Password must include at least one uppercase letter.")
    if not any(char.islower() for char in password):
        raise ValidationError("Password must include at least one lowercase letter.")
    if not any(char in "!@#$%^&*()-_+=<>?/.,:;" for char in password):
        raise ValidationError("Password must include at least one special character.")

class RegisterForm(FlaskForm):
    name = StringField("Name", validators=[DataRequired()])
    email = StringField("Email", validators=[DataRequired(), Email()])
    password = PasswordField("Password", validators=[DataRequired(), password_policy])
    submit = SubmitField("Register")

    def validate_email(self, field):
        cursor = mysql.connection.cursor()
        cursor.execute("SELECT * FROM users WHERE email=%s", (field.data,))
        user = cursor.fetchone()
        cursor.close()
        if user:
            raise ValidationError('Email Already Taken')


class LoginForm(FlaskForm):
    email = StringField("Email", validators=[DataRequired(), Email()])
    password = PasswordField("Password", validators=[DataRequired()])
    submit = SubmitField("Login")

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    form = RegisterForm()
    if form.validate_on_submit():
        name = form.name.data
        email = form.email.data
        password = form.password.data

        hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())

        # Store data into the database
        cursor = mysql.connection.cursor()
        cursor.execute("INSERT INTO users (name, email, password) VALUES (%s, %s, %s)", (name, email, hashed_password))
        mysql.connection.commit()
        cursor.close()

        return redirect(url_for('login'))

    return render_template('register.html', form=form)

@app.route('/login', methods=['GET', 'POST'])
def login():
    form = LoginForm()

    # Check for email cookie and pre-fill the email field
    if 'email' in request.cookies:
        form.email.data = request.cookies.get('email')

    if form.validate_on_submit():
        email = form.email.data
        password = form.password.data

        cursor = mysql.connection.cursor()
        cursor.execute("SELECT * FROM users WHERE email=%s", (email,))
        user = cursor.fetchone()
        cursor.close()
        
        if user and bcrypt.checkpw(password.encode('utf-8'), user[3].encode('utf-8')):
            session['user_id'] = user[0]

            # Set a cookie for the email to remember for the next login
            response = make_response(redirect(url_for('dashboard')))
            response.set_cookie('email', email, max_age=30*24*60*60)  # Cookie valid for 30 days
            return response
        else:
            flash("Login failed. Please check your email and password")
            return redirect(url_for('login'))

    return render_template('login.html', form=form)

@app.route('/dashboard')
def dashboard():
    if 'user_id' in session:
        user_id = session['user_id']

        cursor = mysql.connection.cursor()
        cursor.execute("SELECT * FROM users WHERE id=%s", (user_id,))
        user = cursor.fetchone()
        cursor.close()

        if user:
            return render_template('dashboard.html', user=user)

    return redirect(url_for('login'))

@app.route('/logout')
def logout():
    session.pop('user_id', None)
    flash("You have been logged out successfully.")
    
    # Clear the email cookie on logout
    response = make_response(redirect(url_for('login')))
    response.set_cookie('email', '', expires=0)  # Expire the cookie immediately
    return response


if __name__ == '__main__':
    app.run(debug=True)
