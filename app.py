from flask import Flask, render_template, request, flash, redirect, url_for, session
from PIL import Image
import pendulum

import db
import os
import sys
import helper_functions
import route_functions
from form_classes import BuyForm, AddListingForm, LoginForm, MemberForm
from werkzeug.utils import secure_filename

app = Flask('Gardener\'s Exchange')
app.config['SECRET_KEY'] = 'gardener-exchange'
app.config['UPLOAD_FOLDER'] = 'images/uploaded-images/'
app.config['SCRIPT_LOCATION'] = os.path.dirname(os.path.realpath(sys.argv[0]))


@app.before_request
def before_request():
    db.open_db()
    if 'user_id' in session:
        if not session['zipcode']:
            session['zipcode'] = db.get_user_address(session['user_id'])[4]
    if not session.get('zipcode'):
        session['zipcode'] = '46989'


def after_request():
    db.close_db()


@app.route('/')
def index():
    listings = db.all_listings()
    for listing in listings:
        listing['price_per_unit'] = '${:,.2f}'.format(
            listing['price_per_unit'])
    return render_template('index.html', listings=listings)


@app.route('/search')
def search():
    q = request.args.get('search')
    filter_value = request.args.get('filter')
    results = {'listings': [], 'categories': [], 'users': []}
    c_flag = False

    if q is not None:
        results = route_functions.search(results, q)
    else:
        q = ''

    if filter_value is not None:
        results, c_flag = route_functions.filter_by(results, int(filter_value), q)

    return render_template('search.html', results=results, q=q, c_flag=c_flag)


@app.route('/listing/<int:listing_id>')
def listing_detail(listing_id):
    rel_link = helper_functions.relative_link(request.path, request.referrer)
    listing = db.get_one_listing(listing_id)
    user = db.get_one_user(listing['seller_id'])
    # buyer_address = session['zipcode']
    # seller_address = helper_functions.address_string(listing['seller_id'])
    # url = "https://maps.googleapis.com/maps/api/directions/json?origin={}&destination={}&key={}".format(
    #     buyer_address, seller_address[1], google_maps_key())
    # result = simplejson.load(urllib.request.urlopen(url))
    # result_dist = result['routes'][0]['legs'][0]['distance']['text']
    # result_time = result['routes'][0]['legs'][0]['duration']['text']
    # time_dist = [result_time, result_dist]
    time_dist = ['10 mins', '4.5 mi']

    return render_template(
        'listing-detail.html',
        listing=listing,
        user=user,
        rel_link=rel_link,
        time_dist=time_dist)


@app.route('/listing/buy/<int:listing_id>', methods=['GET', 'POST'])
def listing_purchase(listing_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))
    rel_link = helper_functions.relative_link(request.path, request.referrer)
    listing = db.get_one_listing(listing_id)
    buy_item = BuyForm()
    ppu = listing['price_per_unit']
    total_price = "${:.2f}".format(float(listing['price_per_unit']) * 1)
    qty_purchased = buy_item.quantity.data

    if buy_item.validate_on_submit(
    ) and qty_purchased <= listing['available_quantity']:
        db.update_available_quantity(qty_purchased, listing_id)
        total_cost = round(
            float(listing['price_per_unit']) * int(qty_purchased))
        order_created = db.add_new_order(listing_id, qty_purchased, total_cost,
                                         session['user_id'])

        if order_created == 1:
            listing_detail = db.get_listing_details_for_confirmation_page(
                listing_id)
            order = {
                'listing_detail': listing_detail,
                'qty': qty_purchased,
                'total_price': "${:.2f}".format(total_cost)
            }
            name = '{} {}'.format(order['listing_detail'][3].capitalize(),
                                  order['listing_detail'][4].capitalize())
        else:
            flash('FAILED TO CREATE ORDER')
        return render_template(
            'listing-confirmation.html',
            listing_id=listing_id,
            order=order,
            name=name,
            unit=listing['unit_type'])

    elif buy_item.validate_on_submit(
    ) and qty_purchased > listing['available_quantity']:
        flash('Please select no more than the quantity that is available.')
    elif buy_item.validate_on_submit():
        flash('Unable to purchase item')

    return render_template(
        'listing-purchase.html',
        listing=listing,
        form=buy_item,
        rel_link=rel_link,
        total_price=total_price,
        ppu=ppu)


@app.route('/listing/confirmation/<int:listing_id>', methods=['GET', 'POST'])
def listing_confirmation(listing_id):
    return render_template('listing-confirmation.html')


@app.route('/listing/add', methods=['GET', 'POST'])
def listing_new():
    rel_link = helper_functions.relative_link(request.path, request.referrer)
    if 'user_id' in session:  # checks to see if someone is logged in
        listing_form = AddListingForm()
        if request.method == 'POST':
            if listing_form.submit.data and listing_form.validate_on_submit():
                # Upload seller's photo
                approved_file_extensions = {
                    'jpg', 'jpeg', 'png', 'tiff', 'tif', 'bmp'
                }
                file_name = secure_filename(listing_form.photo.data.filename)
                file_extension = file_name.split('.')[-1].lower()

                if file_extension in approved_file_extensions:
                    directory_created = os.path.join('{}'.format(
                        app.config['SCRIPT_LOCATION']), 'static', 'images',
                        'uploaded-images',
                        '{}'.format(
                            session['user_id']))
                    if not os.path.exists(directory_created):
                        os.mkdir(directory_created)
                    file_path = os.path.join(directory_created, file_name)
                    listing_form.photo.data.save(file_path)

                    # Generate new filename to prevent overwrites
                    current_time = pendulum.now('America/Indianapolis').format(
                        r'%Y%m%dT%H%M%S')
                    proc_name = '{}.{}'.format(current_time, file_extension)
                    os.chdir(directory_created)
                    os.rename(file_name, proc_name)
                    pic_location = 'images/uploaded-images/{}/{}'.format(
                        session['user_id'], proc_name)

                    # Resize photo to width < 1024 and compress file size
                    img = Image.open(proc_name)
                    maxsize = (1024, 1024)
                    img.thumbnail(maxsize, Image.ANTIALIAS)
                    img.save(proc_name, optimize=True, quality=50)

                    # Properly calculate monetary values
                    ppu = float(
                        format(float(listing_form.price_per_unit.data), '.2f'))
                    ogq = float(
                        format(
                            float(listing_form.original_quantity.data), '.2f'))
                    total_price = float(format(ppu * ogq, '.2f'))
                    category_id = int(listing_form.category_id.data)
                    rowcount = db.add_listing({
                        'seller_id':
                            session['user_id'],
                        'title':
                            listing_form.title.data,
                        'photo':
                            pic_location,
                        'description':
                            listing_form.description.data,
                        'original_quantity':
                            int(listing_form.original_quantity.data),
                        'available_quantity':
                            int(listing_form.original_quantity.data),
                        'unit_type':
                            listing_form.unit_type.data,
                        'price_per_unit':
                            ppu,
                        'total_price':
                            total_price,
                        'category_id':
                            category_id,
                        'date_harvested':
                            listing_form.date_harvested.data,
                        'is_tradeable':
                            listing_form.is_tradeable.data
                    })

                    if rowcount == 1:
                        flash('New listing for {0} created.'.format(
                            listing_form.title.data))
                        return redirect(url_for('index'))
                    else:
                        flash('New listing not created.')
                else:
                    flash(
                        'Invalid image file format, please use PNG, JPG, or JPEG.'
                    )
    else:
        return redirect(url_for('login'))
    return render_template(
        'listing-new.html', form=listing_form, rel_link=rel_link)


@app.route('/user/<int:user_id>')
def user_profile(user_id):
    rel_link = helper_functions.relative_link(request.path, request.referrer)
    user = db.get_one_user(user_id)
    listings = db.get_user_listings(user_id)
    address = helper_functions.address_string(user_id)
    map_url = helper_functions.address_url(address[1])
    name = '{} {}'.format(user['first_name'].capitalize(),
                          user['last_name'].capitalize())

    return render_template(
        'profile.html',
        rel_link=rel_link,
        name=name,
        user=user,
        listings=listings,
        location_address=address[0],
        location_link=map_url)


@app.route('/user/edit/<int:user_id>', methods=['GET', 'PUT'])
def user_edit(user_id):
    if request.method == 'PUT':
        print('PUT')
    user_form = MemberForm()
    user_form.address_state.choices = helper_functions.get_usa_states()

    if user_form.validate_on_submit():
        member = db.find_user(user_form.email.data)

        if member is not None:
            flash("Member {} already exists".format(user_form.email.data))
        else:
            approved_file_extensions = {
                'jpg', 'jpeg', 'png', 'tiff', 'tif', 'bmp'
            }
            file_name = ''
            file_extension = ''
            allow_create = True

            if user_form.photo.data:
                file_name = secure_filename(user_form.photo.data.filename)
                file_extension = file_name.split('.')[-1].lower()

            if user_form.photo.data and file_extension in approved_file_extensions:
                user_id = db.get_latest_user_id()
                directory_created = os.path.join('{}'.format(
                    app.config['SCRIPT_LOCATION']), 'static', 'images',
                    'uploaded-images',
                    '{}'.format(user_id))
                if not os.path.exists(directory_created):
                    os.mkdir(directory_created)
                file_path = os.path.join(directory_created, file_name)
                user_form.photo.data.save(file_path)

                current_time = pendulum.now('America/Indianapolis').format(
                    r'%Y%m%dT%H%M%S')
                proc_name = '{}.{}'.format(current_time, file_extension)
                os.chdir(directory_created)
                os.rename(file_name, proc_name)
                pic_location = 'images/uploaded-images/{}/{}'.format(
                    user_id, proc_name)

                img = Image.open(proc_name)
                maxsize = (1024, 1024)
                img.thumbnail(maxsize, Image.ANTIALIAS)
                img.save(proc_name, optimize=True, quality=50)
            elif user_form.photo.data and file_extension not in approved_file_extensions:
                flash(
                    'Invalid picture format, please choose a JPG, JPEG, or PNG.'
                )
                allow_create = False
            elif not user_form.photo.data:
                user_id = db.get_latest_user_id()
                directory_created = os.path.join('{}'.format(
                    app.config['SCRIPT_LOCATION']), 'static', 'images',
                    'uploaded-images',
                    '{}'.format(user_id))
                if not os.path.exists(directory_created):
                    os.mkdir(directory_created)
                pic_location = ''
            else:
                pass

            if allow_create:
                address_id = db.create_new_address({
                    'street':
                        str(user_form.address_street.data).strip(),
                    'city':
                        str(user_form.address_city.data).strip(),
                    'state':
                        str(user_form.address_state.data).strip(),
                    'zipcode':
                        user_form.address_zipcode.data
                })

                if address_id[0] == 1:
                    rowcount = db.create_user({
                        'address_id':
                            int(address_id[1][0]),
                        'email':
                            str(user_form.email.data).strip(),
                        'first':
                            str(user_form.first_name.data).strip(),
                        'last':
                            str(user_form.last_name.data).strip(),
                        'photo':
                            pic_location,
                        'pass':
                            user_form.password.data,
                        'bio':
                            user_form.bio.data
                    })
                else:
                    flash('Invalid address fields.')

                if rowcount == 1:
                    user = db.get_one_login(user_form.email.data)
                    session['email'] = request.form['email']
                    session['user_id'] = user['user_id']
                    flash('Your new account was created.')
                    return redirect(url_for('index'))
                else:
                    flash('New user not created.')

    return render_template('account-edit.html', form=user_form)


@app.route('/account')
def account():
    if 'user_id' in session:
        user = db.get_one_user(session['user_id'])
        name = '{} {}'.format(user['first_name'].capitalize(),
                              user['last_name'].capitalize())
        address = helper_functions.address_string(session['user_id'])
        map_url = helper_functions.address_url(address[1])
        listings = db.get_user_listings(session['user_id'])
        orders = db.get_user_orders(session['user_id'])
        for listing in listings:
            listing['price_per_unit'] = '${:,.2f}'.format(
                listing['price_per_unit'])
        for order in orders:
            order['total_cost'] = '${:,.2f}'.format(order['total_cost'])
            order['time_placed'] = 'Purchased on {}'.format(
                order['time_placed'].strftime('%B %e'))
        tab_choice = request.args.get('type')
        return render_template(
            'account-main.html',
            user=user,
            name=name,
            location_address=address[0],
            location_link=map_url,
            tab_choice=tab_choice,
            listings=listings,
            orders=orders)
    else:
        return redirect(url_for('login'))


@app.route('/settings')
def settings():
    if 'user_id' in session:
        return render_template('settings.html')
    else:
        return redirect(url_for('login'))


@app.route('/login', methods=['GET', 'POST'])
def login():
    loginform = LoginForm()
    if loginform.validate_on_submit():
        # If we get here, we've received a POST request and
        # our login form has been validated.
        user = db.get_one_login(loginform.email.data)
        if user == None:
            # Bogus password
            flash('Invalid email')
        elif loginform.password.data != user['password']:
            # Bogus password
            flash('Invalid password')
        else:
            # Correct password. Add a value to the session object
            # to show that the user is logged in. Redirect to home page.
            session['email'] = loginform.email.data
            session['user_id'] = user['user_id']
            session['role'] = user['role']
            # session['remember'] = loginform.remember.data
            flash('User {} logged in'.format(session['email']))
            return redirect(url_for('index'))

    # Render the form if:
    # 1. This is a GET request and we want to send the empty form.
    # 2. This is a POST request and the form failed to validate.
    # 3. The form validated but the password was wrong.

    return render_template('account-login.html', form=loginform)


@app.route('/logout')
def logout():
    # Remove the 'email' entry from the session.
    # The pop() method behaves as follows:
    # 1. If 'email' is in the session, remove it and return its value.
    #    The value will be the user name stored there by the login() view function.
    #    Removing the email from the session has the effect of logging out the user.
    # 2. If 'email' is not in the session, return the second argument (None)
    # session.pop('remember', None)
    email = session.pop('email', None)
    session.clear()
    flash('User {} logged out'.format(email))
    return redirect(url_for('index'))


@app.route('/account/create', methods=['GET', 'POST'])
def create_account():
    user_form = MemberForm()
    user_form.address_state.choices = helper_functions.get_usa_states()

    if user_form.validate_on_submit():
        member = db.find_user(user_form.email.data)

        if member is not None:
            flash("Member {} already exists".format(user_form.email.data))
        else:
            approved_file_extensions = {
                'jpg', 'jpeg', 'png', 'tiff', 'tif', 'bmp'
            }
            file_name = ''
            file_extension = ''
            allow_create = True

            if user_form.photo.data:
                file_name = secure_filename(user_form.photo.data.filename)
                file_extension = file_name.split('.')[-1].lower()

            if user_form.photo.data and file_extension in approved_file_extensions:
                user_id = db.get_latest_user_id()
                directory_created = os.path.join('{}'.format(
                    app.config['SCRIPT_LOCATION']), 'static', 'images',
                    'uploaded-images',
                    '{}'.format(user_id))
                if not os.path.exists(directory_created):
                    os.mkdir(directory_created)
                file_path = os.path.join(directory_created, file_name)
                user_form.photo.data.save(file_path)

                current_time = pendulum.now('America/Indianapolis').format(
                    r'%Y%m%dT%H%M%S')
                proc_name = '{}.{}'.format(current_time, file_extension)
                os.chdir(directory_created)
                os.rename(file_name, proc_name)
                pic_location = 'images/uploaded-images/{}/{}'.format(
                    user_id, proc_name)

                img = Image.open(proc_name)
                maxsize = (1024, 1024)
                img.thumbnail(maxsize, Image.ANTIALIAS)
                img.save(proc_name, optimize=True, quality=50)
            elif user_form.photo.data and file_extension not in approved_file_extensions:
                flash(
                    'Invalid picture format, please choose a JPG, JPEG, or PNG.'
                )
                allow_create = False
            elif not user_form.photo.data:
                user_id = db.get_latest_user_id()
                directory_created = os.path.join('{}'.format(
                    app.config['SCRIPT_LOCATION']), 'static', 'images',
                    'uploaded-images',
                    '{}'.format(user_id))
                if not os.path.exists(directory_created):
                    os.mkdir(directory_created)
                pic_location = ''
            else:
                pass

            if allow_create:
                address_id = db.create_new_address({
                    'street':
                        str(user_form.address_street.data).strip(),
                    'city':
                        str(user_form.address_city.data).strip(),
                    'state':
                        str(user_form.address_state.data).strip(),
                    'zipcode':
                        user_form.address_zipcode.data
                })

                if address_id[0] == 1:
                    rowcount = db.create_user({
                        'address_id':
                            int(address_id[1][0]),
                        'email':
                            str(user_form.email.data).strip(),
                        'first':
                            str(user_form.first_name.data).strip(),
                        'last':
                            str(user_form.last_name.data).strip(),
                        'photo':
                            pic_location,
                        'pass':
                            user_form.password.data,
                        'bio':
                            user_form.bio.data
                    })
                else:
                    flash('Invalid address fields.')

                if rowcount == 1:
                    user = db.get_one_login(user_form.email.data)
                    session['email'] = request.form['email']
                    session['user_id'] = user['user_id']
                    flash('Your new account was created.')
                    return redirect(url_for('index'))
                else:
                    flash('New user not created.')

    return render_template(
        'account-create.html', form=user_form, mode='create')


if __name__ == '__main__':
    app.run(host='localhost', port=5000, debug=True)
