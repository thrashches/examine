from math import ceil


def paginate(rows, paginate_by=10, page=1):
    if len(rows) <= paginate_by:
        return {
            'page_obj': rows,
            'has_next': False,
            'has_prev': False,
            'page_count': 1
        }
    else:
        has_prev = False
        has_next = True
        if page > 1:
            has_prev = True

        page_count = ceil(len(rows)/paginate_by)
        if page == page_count:
            has_next = False
        if page > page_count:
            page = 1
            has_prev = False
        first_slice = (page - 1) * paginate_by
        page_obj = rows[first_slice:first_slice + paginate_by]
        paginator = {
            'page_obj': page_obj,
            'has_next': has_next,
            'has_prev': has_prev,
            'page_count': page_count
        }
        return paginator
