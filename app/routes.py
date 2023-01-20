# coding=utf-8
from datetime import datetime
from werkzeug.utils import secure_filename
import os
from flask import render_template, flash, redirect, session, url_for, request, g, Markup,Response
import psycopg2  # pip install psycopg2
import psycopg2.extras
import re
from werkzeug.security import generate_password_hash, check_password_hash
from flask_mail import Mail, Message
from fpdf import FPDF
from detecto import core, utils, visualize
import urllib.request

from app import app
DB_HOST = "localhost"
DB_NAME = "webserver"
DB_USER = "postgres"
DB_PASS = "185101"

conn = psycopg2.connect(dbname=DB_NAME, user=DB_USER, password=DB_PASS, host=DB_HOST)
UPLOAD_FOLDER = 'app/static/uploads'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

ALLOWED_EXTENSIONS = set(['png', 'jpg', 'jpeg', 'gif'])
app.config['MAIL_SERVER']='smtp.gmail.com'
app.config['MAIL_PORT']=465
app.config['MAIL_USERNAME']="bivduong@gmail.com"
app.config['MAIL_PASSWORD']="Dvbi185101"
app.config['MAIL_USE_TLS']=False
app.config['MAIL_USE_SSL']=True
mail=Mail(app)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS
@app.route('/')
def index():
    cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
    s = "SELECT * FROM animal limit 5"
    cur.execute(s)  # Execute the SQL
    list_users = cur.fetchall()

    return render_template('index.html',list=list_users)
@app.route('/animallist')
def list_animal():
    cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
    s = "SELECT * FROM animal"
    cur.execute(s)  # Execute the SQL
    list_users = cur.fetchall()
    return render_template('animal.html',list=list_users)
@app.route('/detailanimal/<id>', methods=['POST', 'GET'])
def detailanimal(id):
    cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)

    cur.execute('SELECT * FROM animal where id = %s', (id,))
    data = cur.fetchall()
    cur.close()
    print(data[0])
    return render_template('detailanimal.html', animal_detail=data[0])
@app.route('/contact' )
def contact():
        return render_template('contact.html')
@app.route('/addcontact', methods=['POST'])
def addcontact():
    cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
    if request.method == 'POST':
        username= request.form['username']
        email = request.form['email']
        messages = request.form['messages']
        fphone = request.form['fphone']
        cur.execute("INSERT INTO contactusmesseger(username,email,messages,fphone) VALUES (%s,%s,%s,%s)", [username,email,messages,fphone])
        conn.commit()
        flash('Added successfully')
        return redirect(url_for('contact'))

@app.route('/about')
def about():
        return render_template('about.html')


@app.route('/implement')
def gam():
    return render_template('classified.html')
@app.route('/profile')
def profile():
    cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)

    # Check if user is loggedin
    if 'loggedin' in session:
        cursor.execute('SELECT * FROM account WHERE id = %s', [session['id']])
        account = cursor.fetchone()
        # Show the profile page with account info
        return render_template('profile.html', account=account)
    return redirect(url_for('login'))
@app.route('/success', methods=['POST'])
def success():
    if request.method == 'POST':
        f = request.files['file']
        basepath = os.path.dirname(__file__)
        file_path = os.path.join(basepath, secure_filename(f.filename))

        f.save(file_path)
        model = core.Model.load('app/model_weights.pth', ['tiger', 'elephant', 'panda'])
        image = utils.read_image(file_path)
        predictions = model.predict(image)

        labels, boxes, scores = predictions

        scores = scores

        alt_score = []
        for i in scores:
            alt_score.append(float(i))

        ele = [0]
        tig = [0]
        pan = [0]
        j = 0
        for i in labels:
            if i == "elephant":
                ele.append(alt_score[j])
            elif i == "tiger":
                tig.append(alt_score[j])
            elif i == "panda":
                pan.append(alt_score[j])
            j = j + 1
        final = []
        elephant_score = max(ele)
        tiger_score = max(tig)
        panda_score = max(pan)

        elephant_score = round(elephant_score * 100, 2)
        tiger_score = round(tiger_score * 100, 2)
        panda_score = round(panda_score * 100, 2)
        if (elephant_score > 75):
            final.append("Elephant")
        if (tiger_score > 75):
            final.append("Tiger")
        if (panda_score > 75):
            final.append("Panda")

        return render_template("classified.html", elephant_score=elephant_score, tiger_score=tiger_score,
                               panda_score=panda_score, final=final, len=len(final))
        final = []
@app.route('/login', methods=['GET', 'POST'])
def login_user():
    cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)

    # Check if "username" and "password" POST requests exist (user submitted form)
    if request.method == 'POST' and 'username' in request.form and 'password' in request.form:
        username = request.form['username']
        password = request.form['password']
        print(password)
        cursor.execute("SELECT * FROM account WHERE username = %s and level IN ('3')", (username,))
        # Fetch one record and return result
        account = cursor.fetchone()

        if account:
            password_rs = account['password']
            print(password_rs)
            # If account exists in users table in out database
            if check_password_hash(password_rs, password):
                # Create session data, we can access this data in other routes
                session['loggedin'] = True
                session['id'] = account['id']
                session['username'] = account['username']
                session['level'] = account['level']
                # Redirect to home page
                return redirect(url_for('index'))
            else:
                # Account doesnt exist or username/password incorrect
                flash('Incorrect username/password')
        else:
            # Account doesnt exist or username/password incorrect
            flash('Incorrect username/password')
    return render_template('login.html')
@app.route('/logout')
def logout():
    # Remove session data, this will log the user out
    session.pop('loggedin', None)
    session.pop('id', None)
    session.pop('username', None)
    # Redirect to login page
    return redirect(url_for('index'))
@app.route('/register', methods=['GET', 'POST'])
def register():
    cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)

    # Check if "username", "password" and "email" POST requests exist (user submitted form)
    if request.method == 'POST' and 'username' in request.form and 'password' in request.form and 'email' in request.form and 'phone' in request.form and 'level' in request.form:
        # Create variables for easy access
        fullname = request.form['fullname']
        username = request.form['username']
        password = request.form['password']
        email = request.form['email']
        phone = request.form['phone']
        level = request.form['level']

        _hashed_password = generate_password_hash(password)

        # Check if account exists using MySQL
        cursor.execute('SELECT * FROM account WHERE username = %s', (username,))
        account = cursor.fetchone()
        print(account)
        # If account exists show error and validation checks
        if account:
            flash('Account already exists!')
        elif not re.match(r'[^@]+@[^@]+\.[^@]+', email):
            flash('Invalid email address!')
        elif not re.match(r'[A-Za-z0-9]+', username):
            flash('Username must contain only characters and numbers!')
        elif not username or not password or not email:
            flash('Please fill out the form!')
        else:
            # Account doesnt exists and the form data is valid, now insert new account into users table
            cursor.execute(
                "INSERT INTO account(fullname, username, password, email,phone,level) VALUES (%s,%s,%s,%s,%s,%s)",
                (fullname, username, _hashed_password, email, phone, level))
            conn.commit()
            flash('You have successfully registered!')
    elif request.method == 'POST':
        # Form is empty... (no POST data)
        flash('Please fill out the form!')
    # Show registration form with message (if any)
    return render_template('register.html')
##########################
@app.route('/admin')
def admin_home():
    # Check if user is loggedin
    if 'loggedin' in session:
        # User is loggedin show them the home page
        return render_template('admin/home.html', username=session['username'])
    # User is not loggedin redirect to login page
    return redirect(url_for('admin_login'))
@app.route('/admin/login/', methods=['GET', 'POST'])
def admin_login():
    cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)

    # Check if "username" and "password" POST requests exist (user submitted form)
    if request.method == 'POST' and 'username' in request.form and 'password' in request.form:
        username = request.form['username']
        password = request.form['password']
        print(password)
        cursor.execute("SELECT * FROM account WHERE username = %s and level NOT IN ('3')", (username,))
        # Fetch one record and return result
        account = cursor.fetchone()

        if account:
            password_rs = account['password']
            print(password_rs)
            # If account exists in users table in out database
            if check_password_hash(password_rs, password):
                # Create session data, we can access this data in other routes
                session['loggedin'] = True
                session['id'] = account['id']
                session['username'] = account['username']
                session['level'] = account['level']
                # Redirect to home page
                return redirect(url_for('admin_home'))
            else:
                # Account doesnt exist or username/password incorrect
                flash('Incorrect username/password')
        else:
            # Account doesnt exist or username/password incorrect
            flash('Incorrect username/password')
    return render_template('admin/login.html')
@app.route('/admin/logout')
def admin_logout():
    # Remove session data, this will log the user out
    session.pop('loggedin', None)
    session.pop('id', None)
    session.pop('username', None)
    # Redirect to login page
    return redirect(url_for('admin_login'))
@app.route('/admin/register', methods=['GET', 'POST'])
def admin_register():
    cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)

    # Check if "username", "password" and "email" POST requests exist (user submitted form)
    if request.method == 'POST' and 'username' in request.form and 'password' in request.form and 'email' in request.form and 'phone' in request.form and 'level' in request.form:
        # Create variables for easy access
        fullname = request.form['fullname']
        username = request.form['username']
        password = request.form['password']
        email = request.form['email']
        phone = request.form['phone']
        level = request.form['level']

        _hashed_password = generate_password_hash(password)

        # Check if account exists using MySQL
        cursor.execute('SELECT * FROM account WHERE username = %s', (username,))
        account = cursor.fetchone()
        print(account)
        # If account exists show error and validation checks
        if account:
            flash('Account already exists!')
        elif not re.match(r'[^@]+@[^@]+\.[^@]+', email):
            flash('Invalid email address!')
        elif not re.match(r'[A-Za-z0-9]+', username):
            flash('Username must contain only characters and numbers!')
        elif not username or not password or not email:
            flash('Please fill out the form!')
        else:
            # Account doesnt exists and the form data is valid, now insert new account into users table
            cursor.execute(
                "INSERT INTO account(fullname, username, password, email,phone,level) VALUES (%s,%s,%s,%s,%s,%s)",
                (fullname, username, _hashed_password, email, phone, level))
            conn.commit()
            flash('You have successfully registered!')
    elif request.method == 'POST':
        # Form is empty... (no POST data)
        flash('Please fill out the form!')
    # Show registration form with message (if any)
    return render_template('admin/registeradmin.html')
@app.route('/admin/infonhanvien')
def info_nhanvien():
    cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
    s = "SELECT * FROM account where level NOT IN ('3')"
    cur.execute(s)  # Execute the SQL
    list_users = cur.fetchall()
    return render_template('admin/profile_info_nhanvien.html', list_users=list_users)


@app.route('/admin/download/report/pdf')
def download_report():
    try:
        cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)

        cursor.execute("SELECT * FROM account where level NOT IN ('3')")
        result = cursor.fetchall()

        pdf = FPDF()
        pdf.add_page()

        page_width = pdf.w - 2 * pdf.l_margin

        pdf.set_font('Times', 'B', 14.0)
        pdf.cell(page_width, 0.0, 'Employee Data', align='C')
        pdf.ln(10)

        pdf.set_font('Courier', '', 12)

        col_width = page_width / 4

        pdf.ln(1)

        th = pdf.font_size

        for row in result:
            pdf.cell(col_width, th, str(row['id']), border=1)
            pdf.cell(col_width, th, row['fullname'], border=1)
            pdf.cell(col_width, th, row['email'], border=1)
            pdf.cell(col_width, th, row['phone'], border=1)
            pdf.ln(th)

        pdf.ln(10)

        pdf.set_font('Times', '', 10.0)
        pdf.cell(page_width, 0.0, '- end of report -', align='C')

        return Response(pdf.output(dest='S').encode('latin-1'), mimetype='application/pdf',
                        headers={'Content-Disposition': 'attachment;filename=employee_report.pdf'})
    except Exception as e:
        print(e)
    finally:
        cursor.close()
        conn.close()


@app.route('/admin/deletenhanvien/<string:id>', methods=['POST', 'GET'])
def delete_nhanvien(id):
    cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)

    cur.execute('DELETE FROM  account where id = {0}'.format(id))
    conn.commit()
    flash(' Removed Successfully')
    return redirect(url_for('info_nhanvien'))
@app.route('/admin/profileadmin')
def profile_admin():
    cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)

    # Check if user is loggedin
    if 'loggedin' in session:
        cursor.execute('SELECT * FROM account WHERE id = %s', [session['id']])
        account = cursor.fetchone()
        # Show the profile page with account info
        return render_template('admin/profile.html', account=account)
    return redirect(url_for('admin_login'))
@app.route('/admin/animal')
def animal():
    cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
    curs = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
    s = "SELECT * FROM type"
    cur.execute(s)  # Execute the SQL
    list_users = cur.fetchall()
    ss = "SELECT * FROM branch"
    curs.execute(ss)  # Execute the SQL
    list_userss = curs.fetchall()
    return render_template('admin/animaladd.html',list=list_users,li=list_userss)
@app.route('/admin/animaladd', methods=["POST","GET"])
def animal_add():
    cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
    fname = request.form['fname']
    ltype = request.form['ltype']
    decription = request.form['decription']
    branch = request.form['branch']

    now = datetime.now()
    print(now)
    if request.method == 'POST':
        files = request.files.getlist('files[]')
        # print(files)
        for file in files:
            if file and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
                cur.execute(
                    "INSERT INTO animal (file_name, uploaded_on,fname,ltype,decription,branch) VALUES (%s,%s,%s,%s,%s,%s)",
                    [filename, now, fname, ltype, decription, branch])
                conn.commit()
            print(file)
        cur.close()
        flash('File(s) successfully uploaded')
    return redirect(url_for('animal'))
@app.route('/admin/animaldetail/' )
def animal_detail():
        cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
        cur.execute("SELECT * FROM animal ")
        countrylist = cur.fetchall()
        return render_template('admin/animaldetail.html', countrylist=countrylist)
@app.route('/admin/deleteanimal/<string:id>', methods=['POST', 'GET'])
def delete_animal(id):
    cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)

    cur.execute('DELETE FROM  animal where id = {0}'.format(id))
    conn.commit()
    flash(' Removed Successfully')
    return redirect(url_for('animal_detail'))
@app.route('/admin/detailtype' )
def detailtype():
        cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
        cur.execute("SELECT * FROM type ")
        countrylist = cur.fetchall()
        return render_template('admin/addtypeanimal.html', countrylist=countrylist)
@app.route('/admin/addtypeanimal', methods=['POST'])
def addtypeanimal():
    cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
    if request.method == 'POST':
        name_type= request.form['name_type']

        cur.execute("INSERT INTO type(name_type) VALUES (%s)", [name_type])
        conn.commit()
        flash(' Added successfully')
        return redirect(url_for('detailtype'))
@app.route('/admin/detaitypeanimal/' )
def typeanime_detail():
        cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
        cur.execute("SELECT * FROM type ")
        countrylist = cur.fetchall()
        return render_template('admin/detailtypeanimal.html', countrylist=countrylist)
@app.route('/admin/deletetypeanimal/<string:id>', methods=['POST', 'GET'])
def deletenhanvien(id):
        cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)

        cur.execute('DELETE FROM  type where id = {0}'.format(id))
        conn.commit()
        flash('Student Removed Successfully')
        return redirect(url_for('typeanime_detail'))
@app.route('/admin/updatetypeanimal/<id>', methods=['POST', 'GET'])
def updatetypeanimal(id):
    cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)

    cur.execute('SELECT * FROM type WHERE id = %s', (id))
    data = cur.fetchall()
    cur.close()
    print(data[0])
    return render_template('admin/updatetypeanimal.html', edacoount=data[0])
@app.route('/admin/eupdatetypeanimal/<id>', methods=['POST'])
def eupdatetypeanimal(id):
    if request.method == 'POST':
        name_type = request.form['name_type']

        cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
        cur.execute("""
            UPDATE type
            SET 
            name_type = %s
            WHERE id = %s
        """, (name_type,id))
        flash(' Updated Successfully')
        conn.commit()
        return redirect(url_for('typeanime_detail'))
@app.route('/admin/counttypeanimal' )
def count_type_animal():
        cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
        cur.execute("SELECT ltype, COUNT(ltype) FROM animal GROUP BY ltype ")
        countrylist = cur.fetchall()
        return render_template('admin/counttypeanimal.html', countrylist=countrylist)
@app.route('/admin/customer' )
def customer_list():
        cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
        cur.execute("SELECT *from account where level IN ('3') ")
        countrylist = cur.fetchall()
        return render_template('admin/customer.html', countrylist=countrylist)
@app.route('/admin/inboxmail' )
def inboxmail():
    cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
    cur.execute("SELECT *from contactusmesseger")
    countrylist = cur.fetchall()
    return render_template('admin/inboxmail.html', countrylist=countrylist)
@app.route('/admin/fullemail/<id>', methods=['POST', 'GET'])
def fullemail(id):
    cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)

    cur.execute('SELECT * FROM contactusmesseger WHERE id = %s', (id))
    data = cur.fetchall()
    cur.close()
    print(data[0])
    return render_template('admin/emailread.html', edacoount=data[0])

@app.route('/admin/copmpose', methods=['POST', 'GET'])
def composemail():
    if request.method=="POST":
        email=request.form['email']
        subject=request.form['subject']
        msg=request.form['message']
        message=Message(subject,sender="bivduong@gmail.com",recipients=[email])
        message.body=msg
        mail.send(message)
        flash('You have successfully registered!')
    return render_template('admin/composemail.html')

#branch
@app.route('/admin/detailbranch' )
def detailbranch():
        cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
        cur.execute("SELECT * FROM branch ")
        countrylist = cur.fetchall()
        return render_template('admin/addbranch.html', countrylist=countrylist)
@app.route('/admin/addbranch', methods=['POST'])
def addbranch():
    cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
    if request.method == 'POST':
        name_branch= request.form['name_branch']

        cur.execute("INSERT INTO branch(name_branch) VALUES (%s)", [name_branch])
        conn.commit()
        flash('Added successfully')
        return redirect(url_for('detailbranch'))
@app.route('/admin/detaibranchanimal/' )
def branchanime_detail():
        cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
        cur.execute("SELECT * FROM branch ")
        countrylist = cur.fetchall()
        return render_template('admin/detailbranchanimal.html', countrylist=countrylist)
@app.route('/admin/deletebranch/<string:id>', methods=['POST', 'GET'])
def deletebranchanimal(id):
        cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)

        cur.execute('DELETE FROM  branch where id = {0}'.format(id))
        conn.commit()
        flash('Removed Successfully')
        return redirect(url_for('branchanime_detail'))
@app.route('/admin/updatebranch/<id>', methods=['POST', 'GET'])
def updatebranch(id):
    cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)

    cur.execute('SELECT * FROM branch WHERE id = %s', (id))
    data = cur.fetchall()
    cur.close()
    print(data[0])
    return render_template('admin/updatebranch.html', edacoount=data[0])
@app.route('/admin/eupdatebranch/<id>', methods=['POST'])
def eupdatebranch(id):
    if request.method == 'POST':
        name_type = request.form['name_branch']

        cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
        cur.execute("""
            UPDATE branch
            SET 
            name_branch = %s
            WHERE id = %s
        """, (name_type,id))
        flash(' Updated Successfully')
        conn.commit()
        return redirect(url_for('branchanime_detail'))

@app.route('/admin/countbranch')
def count_branch_animal():
    cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
    cur.execute("SELECT branch, COUNT(branch) FROM animal GROUP BY branch ")
    countrylist = cur.fetchall()
    return render_template('admin/countbranch.html', countrylist=countrylist)

















