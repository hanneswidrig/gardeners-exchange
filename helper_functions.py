import re
import db


def relative_link(request_path, request_referrer):
    path = request_path
    referrer = request_referrer
    # print('Path: '+path+'\n'+'Referrer: '+referrer)

    if path is None:
        return '/'

    if referrer is None:
        referrer = ''

    listing_detail = re.compile(r'/listing/\d*$').findall(path)
    listing_purchase = re.compile(r'/listing/buy/\d*$').findall(path)
    user_profile = re.compile(r'/user/\d*$').findall(path)
    user_refer = re.compile(r'/user/\d*$').findall(referrer)
    search = re.findall(r'/search', referrer)
    account = re.findall(r'/account', referrer)
    index = re.compile(r'\/[0-9]+').findall(path)

    if listing_detail and user_refer:
        return referrer
    elif listing_detail and not search and not account:
        return '/'
    elif listing_detail and not search and account:
        return referrer
    elif listing_purchase:
        return '/listing' + index[0]
    elif user_profile:
        return referrer
    elif search:
        return referrer
    elif index:
        return '/'


def address_string(user_id):
    address = db.get_user_address(user_id)
    location_address = '{}, {}'.format(address['city'], address['abbrev'])
    for_gapi = '{}+{}%2C+{}+{}'.format(
        '+'.join(address['street'].split(' ')), '+'.join(
            address['city'].split(' ')), '+'.join(address['name'].split(' ')),
        address['zipcode'])
    return location_address, for_gapi


def address_url(address):
    map_url = 'https://www.google.com/maps/search/?api=1&query={}'.format(
        address)
    return map_url


def get_usa_states():
    states = db.get_all_states()
    states_list = []
    for state in states:
        states_list.append((state[0], state[1]))
    return states_list
