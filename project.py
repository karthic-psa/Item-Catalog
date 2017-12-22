#!/usr/bin/python
# -*- coding: utf-8 -*-
from flask import Flask, render_template, request, redirect, jsonify, \
    url_for, flash
from sqlalchemy import create_engine, asc
from sqlalchemy.orm import sessionmaker
from database_setup import Base, Restaurant, MenuItem, User
from flask import session as login_session
from oauth2client.client import flow_from_clientsecrets
from oauth2client.client import FlowExchangeError
import os
import random
import string
import datetime
import json
import httplib2
import requests
from flask import make_response

app = Flask(__name__)

CLIENT_ID = json.loads(open('client_secrets.json', 'r').read())['web'
                                                                ]['client_id']
APPLICATION_NAME = 'Item-Catalog'

engine = create_engine('sqlite:///restaurantmenuwithusers.db')
Base.metadata.bind = engine

DBSession = sessionmaker(bind=engine)
session = DBSession()


@app.route('/login')
def showLogin():
    state = ''.join(random.choice(string.ascii_uppercase
                                  + string.digits) for x in xrange(32))
    login_session['state'] = state

    # return "The current session state is %s" % login_session['state']

    return render_template('login.html', STATE=state)


def createUser(login_session):
    newUser = User(name=login_session['username'],
                   email=login_session['email'],
                   picture=login_session['picture'])
    session.add(newUser)
    session.commit()
    user = session.query(User).filter_by(email=login_session['email'
                                                             ]).one()
    return user.id


def getUserInfo(user_id):
    user = session.query(User).filter_by(id=user_id).one()
    return user


def getUserID(email):
    try:
        user = session.query(User).filter_by(email=email).one()
        return user.id
    except:
        return None


@app.route('/gconnect', methods=['POST'])
def gconnect():

    # Validate state token

    if request.args.get('state') != login_session['state']:
        response = make_response(json.dumps('Invalid state parameter.'
                                            ), 401)
        response.headers['Content-Type'] = 'application/json'
        return response

    # Obtain authorization code

    code = request.data

    try:

        # Upgrade the authorization code into a credentials object

        oauth_flow = flow_from_clientsecrets('client_secrets.json',
                                             scope='')
        oauth_flow.redirect_uri = 'postmessage'
        credentials = oauth_flow.step2_exchange(code)
    except FlowExchangeError:
        response = \
            make_response(json.dumps('Failed to upgrade authorization code.'
                                     ), 401)
        response.headers['Content-Type'] = 'application/json'
        return response

    # Check that the access token is valid.

    access_token = credentials.access_token
    url = \
        'https://www.googleapis.com/oauth2/v1/tokeninfo?access_token=%s' \
        % access_token
    h = httplib2.Http()
    result = json.loads(h.request(url, 'GET')[1])

    # If there was an error in the access token info, abort.

    if result.get('error') is not None:
        response = make_response(json.dumps(result.get('error')), 500)
        response.headers['Content-Type'] = 'application/json'
        return response

    # Verify that the access token is used for the intended user.

    gplus_id = credentials.id_token['sub']
    if result['user_id'] != gplus_id:
        response = \
            make_response(json.dumps("Token's user ID not match given user ID."
                                     ), 401)
        response.headers['Content-Type'] = 'application/json'
        return response

    # Verify that the access token is valid for this app.

    if result['issued_to'] != CLIENT_ID:
        response = \
            make_response(json.dumps("Token's client ID does not match app's."
                                     ), 401)
        print "Token's client ID does not match app's."
        response.headers['Content-Type'] = 'application/json'
        return response

    stored_access_token = login_session.get('access_token')
    stored_gplus_id = login_session.get('gplus_id')
    if stored_access_token is not None and gplus_id == stored_gplus_id:
        response = \
            make_response(json.dumps('Current user is already connected.'
                                     ), 200)
        response.headers['Content-Type'] = 'application/json'
        return response

    # Store the access token in the session for later use.

    login_session['access_token'] = access_token
    login_session['gplus_id'] = gplus_id

    # Get user info

    userinfo_url = 'https://www.googleapis.com/oauth2/v1/userinfo'
    params = {'access_token': credentials.access_token, 'alt': 'json'}
    answer = requests.get(userinfo_url, params=params)

    data = answer.json()

    login_session['username'] = data['name']
    login_session['picture'] = data['picture']
    login_session['email'] = data['email']

    user_id = getUserID(login_session['email'])
    if not user_id:
        user_id = createUser(login_session)
    login_session['user_id'] = user_id

    output = ''
    output += '<h1>Welcome, '
    output += login_session['username']
    output += '!</h1>'
    output += '<img src="'
    output += login_session['picture']
    output += \
        ' " style = "width: 300px; height: 300px;border-radius: 150px;-webkit-border-radius: 150px;-moz-border-radius: 150px;"> '
    flash('you are now logged in as %s' % login_session['username'])
    print 'done!'
    return output

    # DISCONNECT - Revoke a current user's token and reset their login_session


@app.route('/gdisconnect')
def gdisconnect():
    access_token = login_session['access_token']
    print 'In gdisconnect access token is %s', access_token
    print 'User name is: '
    print login_session['username']
    if access_token is None:
        print 'Access Token is None'
        response = \
            make_response(json.dumps('Current user not connected.'),
                          401)
        response.headers['Content-Type'] = 'application/json'
        return response
    url = 'https://accounts.google.com/o/oauth2/revoke?token=%s' \
        % login_session['access_token']
    h = httplib2.Http()
    result = h.request(url, 'GET')[0]
    print 'result is '
    print result
    if result['status'] == '200':
        del login_session['access_token']
        del login_session['gplus_id']
        del login_session['username']
        del login_session['email']
        del login_session['picture']
        response = redirect(url_for('restaurantsName'))
        flash('You are now logged out.')
        #response = make_response(json.dumps('Successfully disconnected.'), 200)
        #response.headers['Content-Type'] = 'application/json'

        return response
    else:

        response = \
            make_response(json.dumps(
                'Failed to revoke token for given user.', 400))
        response.headers['Content-Type'] = 'application/json'
        return response

# Created route to get JSON responses here


@app.route('/restaurants/JSON/')
def restaurantsJSON():
    restaurants = session.query(Restaurant).all()
    return jsonify(restaurants=[r.serialize for r in restaurants])


@app.route('/restaurants/<int:restaurant_id>/menu/JSON/')
def restaurantMenuJSON(restaurant_id):
    restaurant = \
        session.query(Restaurant).filter_by(id=restaurant_id).one()
    items = \
        session.query(MenuItem).filter_by(restaurant_id=restaurant_id).all()
    return jsonify(MenuItems=[i.serialize for i in items])


@app.route('/restaurants/<int:restaurant_id>/menu/<int:menu_id>/JSON/')
def menuItemJSON(restaurant_id, menu_id):
    MItem = session.query(MenuItem).filter_by(id=menu_id).one()
    return jsonify(MenuItems=[MItem.serialize])

# Created route to Show all restaurant here


@app.route('/')
@app.route('/restaurants/')
def restaurantsName():
    restaurant = session.query(Restaurant).all()
    return render_template('restaurantNoLogin.html',
                           restaurant=restaurant)


@app.route('/restaurantsL/')
def restaurantsNameL():
    if 'username' not in login_session:
        return redirect('/login')
    restaurant = session.query(Restaurant).all()
    currUser = getUserInfo(login_session['user_id'])
    return render_template('restaurants.html', restaurant=restaurant, user=currUser)

# Created route for New restaurant function here


@app.route('/restaurantsL/new', methods=['GET', 'POST'])
def restaurantNew():
    if 'username' not in login_session:
        return redirect('/login')
    if request.method == 'POST':
        newRest = Restaurant(
            name=request.form['name'], user_id=login_session['user_id'])
        session.add(newRest)
        session.commit()
        return redirect(url_for('restaurantsNameL'))
    else:
        currUser = getUserInfo(login_session['user_id'])
        return render_template('newRestaurant.html', user=currUser)

# Created route for Edit restaurant function here


@app.route('/restaurantsL/<int:restaurant_id>/edit', methods=['GET',
                                                              'POST'])
def restaurantsEdit(restaurant_id):

    if 'username' not in login_session:
        return redirect('/login')
    editRestaurants = \
        session.query(Restaurant).filter_by(id=restaurant_id).one()
    owner = getUserInfo(editRestaurants.user_id)
    currUser = getUserInfo(login_session['user_id'])
    if owner.id != login_session['user_id']:
        flash("You cannot edit this item. This item belongs to %s" %
              owner.name)
        return redirect(url_for('restaurantsNameL'))
    if request.method == 'POST':
        if request.form['name']:
            editRestaurants.name = request.form['name']
        session.add(editRestaurants)
        session.commit()
        return redirect(url_for('restaurantsNameL'))
    else:
        return render_template('editRestaurant.html',
                               restaurant_id=restaurant_id,
                               restaurant=editRestaurants)

# Created route for Delete restaurant function here


@app.route('/restaurantsL/<int:restaurant_id>/delete', methods=['GET',
                                                                'POST'])
def restaurantsDelete(restaurant_id):
    if 'username' not in login_session:
        return redirect('/login')
    delRes = session.query(Restaurant).filter_by(id=restaurant_id).one()
    owner = getUserInfo(delRes.user_id)
    currUser = getUserInfo(login_session['user_id'])
    if owner.id != login_session['user_id']:
        flash("You cannot delete this item. This item belongs to %s" %
              owner.name)
        return redirect(url_for('restaurantsNameL'))
    if request.method == 'POST':
        session.delete(delRes)
        session.commit()
        flash('Item has been deleted')
        return redirect(url_for('restaurantsNameL'))
    else:

        return render_template('deleteRestaurant.html',
                               restaurant_id=restaurant_id,
                               restaurant=delRes)


@app.route('/restaurants/<int:restaurant_id>/menu')
def restaurantMenu(restaurant_id):
    restaurant = \
        session.query(Restaurant).filter_by(id=restaurant_id).one()
    items = \
        session.query(MenuItem).filter_by(restaurant_id=restaurant.id)
    return render_template('menuNoLogin.html', restaurant=restaurant,
                           items=items)


@app.route('/restaurantsL/<int:restaurant_id>/menuL')
def restaurantMenuL(restaurant_id):
    if 'username' not in login_session:
        return redirect('/login')
    restaurant = \
        session.query(Restaurant).filter_by(id=restaurant_id).one()
    items = \
        session.query(MenuItem).filter_by(restaurant_id=restaurant.id)
    currUser = getUserInfo(login_session['user_id'])
    return render_template('menu.html', restaurant=restaurant,
                           items=items, user=currUser)


# Created route for newMenuItem function here

@app.route('/restaurantsL/<int:restaurant_id>/menuL/new/',
           methods=['GET', 'POST'])
def newMenuItem(restaurant_id):
    if 'username' not in login_session:
        return redirect('/login')
    restaurant = \
        session.query(Restaurant).filter_by(id=restaurant_id).one()
    owner = getUserInfo(restaurant.user_id)
    currUser = getUserInfo(login_session['user_id'])
    if owner.id != login_session['user_id']:
        flash("You cannot add items here. This item belongs to %s" %
              owner.name)
        return redirect(url_for('restaurantMenuL', restaurant_id=restaurant_id))
    if request.method == 'POST':
        newItem = MenuItem(name=request.form['name'],
                           description=request.form['description'],
                           price=request.form['price'],
                           course=request.form['course'],
                           user_id=login_session['user_id'],
                           restaurant_id=restaurant_id)
        session.add(newItem)
        session.commit()
        flash('New Menu %s Item Successfully Created' % newItem.name)
        return redirect(url_for('restaurantMenuL',
                                restaurant_id=restaurant_id))
    else:
        return render_template('newmenuitem.html',
                               restaurant_id=restaurant_id)


# Created route for editMenuItem function here

@app.route('/restaurantsL/<int:restaurant_id>/menuL/<int:menu_id>/edit/', methods=['GET', 'POST'])
def editMenuItem(restaurant_id, menu_id):
    if 'username' not in login_session:
        return redirect('/login')
    editMItem = session.query(MenuItem).filter_by(id=menu_id).one()
    owner = getUserInfo(editMItem.user_id)
    currUser = getUserInfo(login_session['user_id'])
    if owner.id != login_session['user_id']:
        flash("You cannot edit this item. This item belongs to %s" %
              owner.name)
        return redirect(url_for('restaurantMenuL', restaurant_id=restaurant_id))
    if request.method == 'POST':
        if request.form['name']:
            editMItem.name = request.form['name']
        if request.form['description']:
            editMItem.description = request.form['description']
        if request.form['price']:
            editMItem.price = request.form['price']
        if request.form['course']:
            editMItem.course = request.form['course']
        session.add(editMItem)
        session.commit()
        flash('Item has been edited')
        return redirect(url_for('restaurantMenuL',
                                restaurant_id=restaurant_id))
    else:

        return render_template('editmenuitem.html',
                               restaurant_id=restaurant_id,
                               MenuID=menu_id, item=editMItem)


# Created a route for deleteMenuItem function here

@app.route('/restaurantsL/<int:restaurant_id>/menuL/<int:menu_id>/delete', methods=['GET', 'POST'])
def deleteMenuItem(restaurant_id, menu_id):
    if 'username' not in login_session:
        return redirect('/login')
    delMItem = session.query(MenuItem).filter_by(id=menu_id).one()
    owner = getUserInfo(delMItem.user_id)
    currUser = getUserInfo(login_session['user_id'])
    if owner.id != login_session['user_id']:
        flash("You cannot delete this item. This item belongs to %s" %
              owner.name)
        return redirect(url_for('restaurantMenuL', restaurant_id=restaurant_id))
    if request.method == 'POST':
        session.delete(delMItem)
        session.commit()
        flash('Item has been deleted')
        return redirect(url_for('restaurantMenuL',
                                restaurant_id=restaurant_id))
    else:

        return render_template('deletemenuitem.html',
                               restaurant_id=restaurant_id,
                               MenuID=menu_id, item=delMItem)


if __name__ == '__main__':
    app.secret_key = 'super_secret_key'
    app.debug = True
    app.run(host='0.0.0.0', port=5000)
