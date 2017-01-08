import os
import pymysql.cursors
from flask import Flask, request, session, g, redirect, url_for, abort, \
    render_template, flash

app = Flask(__name__)
app.config.from_object(__name__)

# Load default config and override config from an environment variable
app.config.update(dict(
    SECRET_KEY='development key',
    USERNAME='admin',
    PASSWORD='default'
))
app.config.from_object("config.Config")

def connect_db():
    rv = pymysql.connect(host=app.config["DB_HOST"], user=app.config["DB_USER"], password=app.config["DB_PASSWORD"], db=app.config["DB_NAME"])
    return rv

def get_db():
    """Opens a new database connection if there is none yet for the
    current application context.
    """
    if not hasattr(g, 'mysql_db'):
        g.mysql_db = connect_db()
    return g.mysql_db


@app.teardown_appcontext
def close_db(error):
    """Closes the database again at the end of the request."""
    if hasattr(g, 'sqlite_db'):
        g.mysql_db.close()


# -----------------------------------------------------------

@app.route('/')
def index():
    if session.get('logged_in'):
        return redirect(url_for('general'))
    else:
        return redirect(url_for('login'))


@app.route('/cards')
def cards():
    if not session.get('logged_in'):
        return redirect(url_for('login'))
    db = get_db()
    with db.cursor(pymysql.cursors.DictCursor) as cur:
        query = '''
            SELECT id, type, front, back, known
            FROM cards
            ORDER BY id DESC
        '''
        cur.execute(query)
        cards = cur.fetchall()
    return render_template('cards.html', cards=cards, filter_name="all")


@app.route('/filter_cards/<filter_name>')
def filter_cards(filter_name):
    if not session.get('logged_in'):
        return redirect(url_for('login'))

    filters = {
        "all":      "where 1 = 1",
        "general":  "where type = 1",
        "code":     "where type = 2",
        "known":    "where known = 1",
        "unknown":  "where known = 0",
    }

    query = filters.get(filter_name)

    if not query:
        return redirect(url_for('cards'))

    db = get_db()
    with db.cursor(pymysql.cursors.DictCursor) as cur:
        full_query = "SELECT id, type, front, back, known FROM cards " + query + " ORDER BY id DESC"
        cur.execute(full_query)
        cards = cur.fetchall()
    return render_template('cards.html', cards=cards, filter_name=filter_name)


@app.route('/add', methods=['POST'])
def add_card():
    if not session.get('logged_in'):
        return redirect(url_for('login'))
    db = get_db()
    with db.cursor(pymysql.cursors.DictCursor) as cur:
        cur.execute('INSERT INTO cards (type, front, back) VALUES (%s, %s, %s)',
            (request.form['type'],
            request.form['front'],
            request.form['back']
            ))
    db.commit()
    flash('New card was successfully added.')
    return redirect(url_for('cards'))


@app.route('/edit/<card_id>')
def edit(card_id):
    if not session.get('logged_in'):
        return redirect(url_for('login'))
    db = get_db()
    with db.cursor(pymysql.cursors.DictCursor) as cur:
        query = '''
            SELECT id, type, front, back, known
            FROM cards
            WHERE id = %s
        '''
        cur.execute(query, (int(card_id),))
        card = cur.fetchone()
    return render_template('edit.html', card=card)


@app.route('/edit_card', methods=['POST'])
def edit_card():
    if not session.get('logged_in'):
        return redirect(url_for('login'))
    selected = request.form.getlist('known')
    known = bool(selected)
    db = get_db()

    with db.cursor(pymysql.cursors.DictCursor) as cur:
        command = '''
            UPDATE cards
            SET
            type = %s,
            front = %s,
            back = %s,
            known = %s
            WHERE id = %s
        '''
        cur.execute(command,
               [request.form['type'],
                request.form['front'],
                request.form['back'],
                known,
                request.form['card_id']
                ])
        db.commit()
        flash('Card saved.')
        return redirect(url_for('cards'))


@app.route('/delete/<card_id>')
def delete(card_id):
    if not session.get('logged_in'):
        return redirect(url_for('login'))
    db = get_db()
    with db.cursor(pymysql.cursors.DictCursor) as cur:
        cur.execute('DELETE FROM cards WHERE id = %s', (int(card_id),))
        db.commit()
        flash('Card deleted.')
        return redirect(url_for('cards'))


@app.route('/general')
@app.route('/general/<card_id>')
def general(card_id=None):
    if not session.get('logged_in'):
        return redirect(url_for('login'))
    return memorize("general", card_id)


@app.route('/code')
@app.route('/code/<card_id>')
def code(card_id=None):
    if not session.get('logged_in'):
        return redirect(url_for('login'))
    return memorize("code", card_id)


def memorize(card_type, card_id):
    if card_type == "general":
        type = 1
    elif card_type == "code":
        type = 2
    else:
        return redirect(url_for('cards'))

    if card_id:
        card = get_card_by_id(card_id)
    else:
        card = get_card(type)
    if not card:
        flash("You've learned all the " + card_type + " cards.")
        return redirect(url_for('cards'))
    short_answer = (len(card['back']) < 75)
    return render_template('memorize.html',
                           card=card,
                           card_type=card_type,
                           short_answer=short_answer)


def get_card(type):
    db = get_db()
    with db.cursor(pymysql.cursors.DictCursor) as cur:
        query = '''
        SELECT
            id, type, front, back, known
          FROM cards
          WHERE
            type = %s
            and known = 0
          ORDER BY RAND()
          LIMIT 1
        '''
        cur.execute(query, (type,))
        return cur.fetchone()


def get_card_by_id(card_id):
    db = get_db()
    with db.cursor(pymysql.cursors.DictCursor) as cur:
        query = '''
          SELECT
            id, type, front, back, known
          FROM cards
          WHERE
            id = %s
          LIMIT 1
        '''

        cur.execute(query, (int(card_id),))
        return cur.fetchone()


@app.route('/mark_known/<card_id>/<card_type>')
def mark_known(card_id, card_type):
    if not session.get('logged_in'):
        return redirect(url_for('login'))
    db = get_db()
    with db.cursor(pymysql.cursors.DictCursor) as cur:
        cur.execute('UPDATE cards SET known = 1 WHERE id = %s', (int(card_id),))
        db.commit()
        flash('Card marked as known.')
        return redirect(url_for(card_type))


@app.route('/login', methods=['GET', 'POST'])
def login():
    error = None
    if request.method == 'POST':
        if request.form['username'] != app.config['USERNAME']:
            error = 'Invalid username'
        elif request.form['password'] != app.config['PASSWORD']:
            error = 'Invalid password'
        else:
            session['logged_in'] = True
            session.permanent = True  # stay logged in
            return redirect(url_for('cards'))
    return render_template('login.html', error=error)


@app.route('/logout')
def logout():
    session.pop('logged_in', None)
    flash("You've logged out")
    return redirect(url_for('index'))


if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)