from sqlalchemy_filters import apply_filters


def add_filter(filtered_query, query, filter_spec):
    if filtered_query is None:
        filtered_query = apply_filters(query, filter_spec)
    else:
        filtered_query = apply_filters(filtered_query, filter_spec)

    return filtered_query
