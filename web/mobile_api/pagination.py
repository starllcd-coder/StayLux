from rest_framework.pagination import PageNumberPagination


class MobilePageNumberPagination(PageNumberPagination):
    page_size = 10
    page_size_query_param = "page_size"
    max_page_size = 50
    page_query_param = "page"

    def get_paginated_response(self, data):
        response = super().get_paginated_response(data)
        response.data["meta"] = {
            "page": self.page.number,
            "page_size": self.get_page_size(self.request),
            "total_pages": self.page.paginator.num_pages,
            "total_items": self.page.paginator.count,
        }
        return response