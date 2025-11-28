from flask import Flask, request, session, redirect, url_for
from cas import CASClient

app = Flask(__name__)
app.secret_key = 'V7nlCN90LPHOTA9PGGyf'

cas_client = CASClient(
    version=3,
    service_url='http://localhost:5000/cas/login?next=%2Fcas%2Fprofile',
    server_url='http://sso.maxkey.top/sign/authz/cas/'
)


@app.route('/cas/')
def index():
    body = """<!DOCTYPE html>
<html>
  <head>
    <title>Python CAS  Demo</title>
    <meta name="viewport" content="width=device-width, height=device-height, initial-scale=1.0, minimum-scale=1.0">
  </head>
  <body>
    <h1>Welcome to python-cas Flask MaxKey Demo</h1>
    <p><a href="/cas/login">点击MaxKey登录[CAS]</a></p>
  </body>
</html>
"""
    return body


@app.route('/cas/profile')
def profile(method=['GET']):
    if 'username' in session:
        return '欢迎 %s. <a href="/cas/logout">Logout</a>' % session['username']
    return 'Login required. <a href="/cas/login">退出登录</a>', 403


@app.route('/cas/login')
def login():
    if 'username' in session:
        # Already logged in
        return redirect(url_for('profile'))

    next = request.args.get('next')
    ticket = request.args.get('ticket')
    print("ticket: ", ticket)
    if not ticket:
        # No ticket, the request come from end user, send to CAS login
        cas_login_url = cas_client.get_login_url()
        app.logger.info('CAS login URL: %s', cas_login_url)
        print('CAS login URL: %s', cas_login_url)
        return redirect(cas_login_url)

    # There is a ticket, the request come from CAS as callback.
    # need call `verify_ticket()` to validate ticket and get user profile.
    app.logger.debug('ticket: %s', ticket)
    app.logger.debug('next: %s', next)
    print('ticket: %s', ticket)
    print('next: %s', next)

    user, attributes, pgtiou = cas_client.verify_ticket(ticket)

    app.logger.debug(
        'CAS verify ticket response: user: %s, attributes: %s, pgtiou: %s', user, attributes, pgtiou)
    print(
        'CAS verify ticket response: user: %s, attributes: %s, pgtiou: %s', user, attributes, pgtiou)

    if not user:
        return 'Failed to verify ticket. <a href="/cas/login">Login</a>'
    else:  # Login successfully, redirect according `next` query parameter.
        session['username'] = user
        return redirect(next)


@app.route('/cas/logout')
def logout():
    redirect_url = url_for('logout_callback', _external=True)
    cas_logout_url = cas_client.get_logout_url(redirect_url)
    app.logger.debug('CAS logout URL: %s', cas_logout_url)
    print('CAS logout URL: %s', cas_logout_url)

    return redirect(cas_logout_url)


@app.route('/cas/logout_callback')
def logout_callback():
    # redirect from CAS logout request after CAS logout successfully
    session.pop('username', None)
    return 'Logged out from CAS. <a href="/cas/login">Login</a>'

@app.route('/cas/ping')
def ping():
    return 'pong'