from flask import Flask, render_template, json, flash, request, redirect, session, jsonify
from flaskext.mysql import MySQL
from werkzeug import generate_password_hash, check_password_hash
import os
import uuid
import get_latlong
from flask import Flask, render_template
from flask_googlemaps import GoogleMaps
from flask_googlemaps import Map
from flask_sslify import SSLify
from OpenSSL import SSL
context = SSL.Context(SSL.SSLv23_METHOD)
context.use_privatekey_file('../ssl/server.key')
context.use_certificate_file('../ssl/server.crt')
# you can set key as config

mysql = MySQL()
app = Flask(__name__)
app = application
app.config['GOOGLEMAPS_KEY'] = "Your Maps API KEY"
GoogleMaps(app)

#if 'DYNO' in os.environ: # only trigger SSLify if the app is running on Heroku
#sslify = SSLify(app)
app.secret_key = 'DECEPTACON'

# MySQL configurations
app.config['MYSQL_DATABASE_USER'] = 'admin'
app.config['MYSQL_DATABASE_PASSWORD'] = 'password'
app.config['MYSQL_DATABASE_DB'] = 'flaskdb'
app.config['MYSQL_DATABASE_HOST'] = 'aws db location'
mysql.init_app(app)

@app.route('/')
def main():
    return render_template('index.html')

@app.route('/showSignUp')
def showSignUp():
    return render_template('signup.html')


@app.route('/showAddWish')
def showAddWish():
    return render_template('addWish.html')


@app.route('/showSignin')
def showSignin():
    if session.get('user'):
        return render_template('userHome.html')
    else:
        return render_template('signin.html')


@app.route('/userHome')
def userHome():
    if session.get('user'):
        return render_template('userHome.html')
    else:
        return render_template('error.html', error='Unauthorized Access')


@app.route('/logout')
def logout():
    session.pop('user', None)
    return redirect('/')

"""populate current user's story from db"""
@app.route('/getWish')
def getWish():
    try:
        if session.get('user'):
            _user = session.get('user')
            #print(getUserName())
            con = mysql.connect()
            cursor = con.cursor()
            cursor.execute("select * from tbl_wish where wish_user_id = %s;",(_user))
            wishes = cursor.fetchall()

            wishes_dict = []
            for wish in wishes:
                wish_dict = {
                    'Id': wish[0],
                    'Title': wish[1],
                    'Description': wish[2],
                    'User': wish[3],
                    'Date': wish[4],
                    'FilePath': wish[5],
                    'Lat': wish[6],
                    'Lon': wish[7]}
                wishes_dict.insert(0, wish_dict)
            return json.dumps(wishes_dict)

        else:
            return render_template('error.html', error='Unauthorized Access')
    except Exception as e:
        return render_template('error.html', error=str(e))


def getUserName(usr):
    con = mysql.connect()
    cursor = con.cursor()
    cursor.execute("SELECT DISTINCT user_name, user_id, wish_user_id \
FROM tbl_user, tbl_wish \
WHERE user_id = wish_user_id")
    result = cursor.fetchall()
    for r in result:
        if r[1] == usr:
            return r[0]
        print(r[0])
    cursor.close()

"""lat and long are appended to each wish_dict, then each wish_dict is added to wishes_dic[]"""
@app.route('/getAllWishes')
def getAllWishes():
    try:
        if session.get('user'):

            conn = mysql.connect()
            cursor = conn.cursor()
            cursor.execute("select wish_id,wish_title,wish_description,wish_file_path,wish_date,wish_lat,wish_lon,wish_username from tbl_wish")
            result = cursor.fetchall()

            wishes_dict = []
            latlon = ()
            for wish in result:
                wish_dict = {
                    'Id': wish[0],
                    'Title': wish[1],
                    'Description': wish[2],
                    'Date': wish[4],
                    'FilePath': wish[3],
                    'Lat': wish[5],
                    'Lon': wish[6],
                    'User': wish[7]
                }
                #appending latitude and long from photos if not in db
                if wish[5] is None:
                    latlon = get_latlong.get_coords(wish[3])
                    if latlon is not None:
                        lat, lon = latlon
                        print(lat)
                        wish_dict['Lat'] = lat
                        wish_dict['Lon'] = lon
                wishes_dict.append(wish_dict)
                print(wish_dict)
                print(wishes_dict)
            return json.dumps(wishes_dict)
        else:
            print('error')
            return render_template('error.html', error='Unauthorized Access')
    except Exception as e:
        return render_template('error.html', error=str(e))


@app.route('/upload', methods=['GET', 'POST'])
def upload():
    if request.method == 'POST':
        file = request.files['file']
        extension = os.path.splitext(file.filename)[1]
        f_name = str(uuid.uuid4()) + extension
        app.config['UPLOAD_FOLDER'] = 'static/Uploads'
        file.save(os.path.join(app.config['UPLOAD_FOLDER'], f_name))
        return json.dumps({'filename': f_name})

@app.route('/showFeed')
def showFeed():
    return render_template('feed.html')

@app.route('/showDashboard')
def showDashboard():
    return render_template('dashboard.html')


@app.route('/addWish', methods=['POST'])
def addWish():
    insertWishSql="""
    insert into tbl_wish(
        wish_description,
        wish_user_id,
        wish_date,
        wish_file_path,
        wish_lat,
        wish_lon
    )
    values
    (
        %s,
        %s,
        NOW(),
        %s,
        %s,
        %s
    );
    """
    linkUsernameSql="""
    update tbl_wish 
    SET tbl_wish.wish_username = (
        SELECT DISTINCT tbl_user.user_name
        FROM tbl_user
        WHERE tbl_user.user_id = tbl_wish.wish_user_id
        );
    """
    print(linkUsernameSql)
    conn = mysql.connect()
    cursor = conn.cursor()

    _lat = ()
    _lon = ()
    try:
        if request.form.get('filePath') is None:
            _filePath = ''
        else:
            _filePath = request.form.get('filePath')
#if there is no filepath to get coords from call js location
        if session.get('user'):

            _description = request.form['inputDescription']
            _user = session.get('user')

            if _filePath != '':
                latlon = get_latlong.get_coords(_filePath)
                if latlon is not None:
                    _lat, _lon = latlon
            else:
                    _lat = request.form['lat']
                    _lon = request.form['lon']
            cursor.execute(insertWishSql,(_description, _user, _filePath, _lat, _lon))
            cursor.execute(linkUsernameSql)
            data = cursor.fetchall()

            if len(data) is 0:
                conn.commit()
                return redirect('/showDashboard')
            else:
                return render_template('error.html', error='An error occurred!')

        else:
            return render_template('error.html', error='Unauthorized Access')
    except Exception as e:
        return render_template('error.html', error=str(e))
    finally:
        cursor.close()
        conn.close()


@app.route('/validateLogin', methods=['POST'])
def validateLogin():
    con = mysql.connect()
    cursor = con.cursor()
    try:
        _username = request.form['inputEmail']
        _password = request.form['inputPassword']

        # connect to mysql
        cursor.execute("select * from tbl_user where user_username = %s",(_username))
        data = cursor.fetchall()

        if len(data) > 0:
            if check_password_hash(str(data[0][3]), _password):
                session['user'] = data[0][0]
                return redirect('/userHome')
            else:
                return render_template('error.html', error='Wrong Email address or Password.')
        else:
            return render_template('error.html', error='Wrong Email address or Password.')

    except Exception as e:
        return render_template('error.html', error=str(e))
    finally:
        cursor.close()
        con.close()


@app.route('/signUp', methods=['POST'])
def signUp():
    conn = mysql.connect()
    cursor = conn.cursor()
    try:
        _name = request.form['inputName']
        _email = request.form['inputEmail']
        _password = request.form['inputPassword']

        # validate the received values
        if _name and _email and _password:

            # All Good, let's call MySQL

            _hashed_password = generate_password_hash(_password)
            cursor.execute("select 1 from tbl_user where user_username = %s", (_name))
            data = cursor.fetchall()
            if len(data) is 0:
                cursor.execute("insert into tbl_user(user_name, user_username, user_password) values(%s,%s,%s)", (_name, _email, _hashed_password))
                conn.commit()
                return redirect('/showSignin')
                #return json.dumps('User created successfully !')
            else:
                return json.dumps({'error': 'user exists'})
    except Exception as e:
        return json.dumps({'error': str(e)})
    finally:
        cursor.close()
        conn.close()

try:
    if __name__ == "__main__":
        #port = int(os.environ.get('PORT', 3306))
        context = ('../../ssl/server.crt', '../../ssl/server.key')
        #app.run(host='0.0.0.0', port=80)
        app.run(host='0.0.0.0', port=443, ssl_context=context, threaded=True, debug=True)
        #app.run('localhost',3305)
except Exception as e:
    print(e)
