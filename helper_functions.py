import sys
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

	listing_detail   = re.compile(r'/listing/\d*$').findall(path)
	listing_purchase = re.compile(r'/listing/buy/\d*$').findall(path)
	user_profile     = re.compile(r'/user/\d*$').findall(path)
	user_refer       = re.compile(r'/user/\d*$').findall(referrer)
	search           = re.findall(r'/search', referrer)
	index            = re.compile(r'\/[0-9]+').findall(path)

	if user_refer and listing_detail:
		return referrer
	elif listing_detail and not search:
		return '/'
	elif listing_purchase:
		return '/listing'+index[0]
	elif user_profile:
		return referrer
	elif search:
		return referrer
	elif index:
		return '/'


def address_string(user_id):
	address = db.get_user_address(user_id)
	location_address = '{} {}, {} {}'.format(
			address['street'], 
			address['city'], 
			address['name'],
			address['zipcode'])
	for_gapi = '{}+{}%2C+{}+{}'.format(
			'+'.join(address['street'].split(' ')), 
			address['city'], 
			address['name'],
			address['zipcode'])
	return (location_address, for_gapi)


def address_url(address):
	map_url = 'https://www.google.com/maps/search/?api=1&query={}'.format(address)
	return map_url
