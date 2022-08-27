import db


def search(results, q):
    listings = db.title_like_listings(q)
    categories = db.search_like_category(q)
    users = db.search_like_users(q)
    found_results = (len(listings), len(categories), len(users))

    if found_results[0] > 0:
        results['listings'] = listings
    if found_results[1] > 0:
        results['categories'] = categories
    if found_results[2] > 0:
        results['users'] = users
    return results


def filter_by(results, filter_id, q):
    results['listings'] = []
    results['categories'] = []
    results['users'] = []
    c_flag = False

    if filter_id == 1:
        results['listings'] = db.title_like_listings(q)
    elif filter_id == 2:
        results['categories'] = db.search_like_category(q)
        c_flag = True
    elif filter_id == 3:
        results['users'] = db.search_like_users(q)
    return results, c_flag
