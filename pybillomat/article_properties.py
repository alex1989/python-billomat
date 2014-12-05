#!/usr/bin/env python
# coding: utf-8
"""
Article-Properties

- English API-Description: http://www.billomat.com/en/api/articles/properties
- Deutsche API-Beschreibung: http://www.billomat.com/de/api/artikel/attribute
"""

import urllib3
import xml.etree.ElementTree as ET
import errors
from bunch import Bunch
from http import Url


class ArticleProperty(Bunch):

    def __init__(self, conn, id = None, property_etree = None):
        """
        ArticleProperty

        :param conn: Connection-Object
        """

        Bunch.__init__(self)

        self.conn = conn

        self.id = id  # Integer
        self.article_id = None  # Integer
        self.article_property_id = None  # Integer
        self.type = None  # TEXTFIELD, CHECKBOX, TEXTAREA, ...
        self.name = None
        self.value = None

        if property_etree is not None:
            self.load_from_etree(property_etree)


    def load_from_etree(self, etree_element):
        """
        Loads data from Element-Tree
        """

        for item in etree_element:

            # Get data
            isinstance(item, ET.Element)
            tag = item.tag
            tag_type = item.attrib.get("type")
            text = item.text

            if text is not None:
                if tag_type == "integer":
                    setattr(self, tag, int(text))
                else:
                    if isinstance(text, str):
                        text = text.decode("utf-8")
                    setattr(self, tag, text)


    def load_from_xml(self, xml_string):
        """
        Loads data from XML-String
        """

        # Parse XML
        root = ET.fromstring(xml_string)

        # Load
        self.load_from_etree(root)


    def load(self, id = None):
        """
        Loads the property-data from server
        """

        # Parameters
        if id:
            self.id = id
        if not self.id:
            raise errors.NoIdError()

        # Path
        path = "/api/article-property-values/{id}".format(id = self.id)

        # Fetch data
        response = self.conn.get(path = path)
        if response.status != 200:
            raise errors.BillomatError(unicode(response.data, encoding = "utf-8"))

        # Fill in data from XML
        self.load_from_xml(response.data)


    @classmethod
    def create(
        cls,
        conn,
        article_id,
        article_property_id,
        value
    ):
        """
        Creates one Property

        :param conn: Connection-Object
        :param article_id: ID of the article
        :param article_property_id: ID of the property
        :param value: Property value
        """

        # XML
        property_tag = ET.Element("article-property-value")

        article_id_tag = ET.Element("article_id")
        article_id_tag.text = unicode(int(article_id))
        property_tag.append(article_id_tag)

        article_property_id_tag = ET.Element("article_property_id")
        article_property_id_tag.text = unicode(int(article_property_id))
        property_tag.append(article_property_id_tag)

        value_tag = ET.Element("value")
        value_tag.text = unicode(value)
        property_tag.append(value_tag)

        xml = ET.tostring(property_tag)

        # Path
        path = "/api/article-property-values"

        # Send POST-request
        response = conn.post(path = path, body = xml)
        if response.status != 201:  # Created
            raise errors.BillomatError(unicode(response.data, encoding = "utf-8"))

        # Create Property-Object
        property = cls(conn = conn)
        property.load_from_xml(response.data)

        # Finished
        return property


class ArticleProperties(list):

    def __init__(self, conn):
        """
        ArticleProperty-List

        :param conn: Connection-Object
        """

        list.__init__(self)

        self.conn = conn
        self.per_page = None
        self.total = None
        self.page = None
        self.pages = None


    def search(
        self,
        # Search parameters
        article_id = None,
        article_property_id = None,
        order_by = None,

        fetch_all = False,
        allow_empty_filter = False,
        keep_old_items = False,
        page = 1,
        per_page = None
    ):
        """
        Fills the (internal) list with ArticleProperty-objects

        If no search criteria given --> all properties will returned (REALLY ALL!).

        :param article_id: Article ID
        :param article_property_id: Article-Property-ID
        :param order_by: Sortings consist of the name of the field and
            sort order: ASC for ascending resp. DESC for descending order.
            If no order is specified, ascending order (ASC) is used.
            Nested sort orders are possible. Please separate the sort orders by
            comma.

        :param allow_empty_filter: If `True`, every filter-parameter may be empty.
            All article-properties will returned. !!! EVERY !!!
        """

        # Check empty filter
        if not allow_empty_filter:
            if not any([
                article_id,
                article_property_id,
            ]):
                raise errors.EmptyFilterError()

        # Empty the list
        if not keep_old_items:
            while True:
                try:
                    self.pop()
                except IndexError:
                    break

        # Url and system-parameters
        url = Url(path = "/api/article-property-values")
        url.query["page"] = page
        if per_page:
            url.query["per_page"] = per_page
        if order_by:
            url.query["order_by"] = order_by

        # Search parameters
        if article_id:
            url.query["article_id"] = article_id
        if article_property_id:
            url.query["article_property_id"] = article_property_id

        # Fetch data
        response = self.conn.get(path = str(url))
        if response.status != 200:
            # Check if "Unothorized" --> raise NotFoundError
            errors_etree = ET.fromstring(response.data)
            for error_etree in errors_etree:
                text = error_etree.text
                if text.lower() == "unauthorized":
                    raise errors.NotFoundError(
                        u"article_id: {article_id}".format(article_id = article_id)
                    )
            # Other Error
            raise errors.BillomatError(response.data)

        # No response (workaround for inconsistent gziped answer; DecodeError)
        try:
            if len(response.data) == 0:
                return
        except urllib3.exceptions.DecodeError:
            if response.headers.get("content-type", "").lower() != "application/xml":
                return
            else:
                raise

        # Parse XML
        properties_etree = ET.fromstring(response.data)

        self.per_page = int(properties_etree.attrib.get("per_page", "0"))
        self.total = int(properties_etree.attrib.get("total", "0"))
        self.page = int(properties_etree.attrib.get("page", "1"))
        self.pages = (self.total // self.per_page) + int(bool(self.total % self.per_page))

        # Iterate over all article-properties
        for property_etree in properties_etree:
            self.append(
                ArticleProperty(conn = self.conn, property_etree = property_etree)
            )

        # Fetch all
        if fetch_all and self.total > (self.page * self.per_page):
            self.search(
                # Search parameters
                article_id = article_id,
                article_property_id = article_property_id,

                fetch_all = fetch_all,
                allow_empty_filter = allow_empty_filter,
                keep_old_items = True,
                page = page + 1,
                per_page = per_page
            )


class ArticlePropertiesIterator(object):
    """
    Iterates over all found properties
    """

    def __init__(self, conn, per_page = 100):
        """
        ArticlePropertiesIterator
        """

        self.conn = conn
        self.article_properties = ArticleProperties(self.conn)
        self.per_page = per_page
        self.search_params = Bunch(
            article_id = None,
            article_property_id = None,
            order_by = None,
        )


    def search(
        self,
        article_id = None,
        article_property_id = None,
        order_by = None
    ):
        """
        Search
        """

        # Params
        self.search_params.article_id = article_id
        self.search_params.article_property_id = article_property_id
        self.search_params.order_by = order_by

        # Search and prepare first page as result
        self.load_page(1)


    def load_page(self, page):

        self.article_properties.search(
            article_id = self.search_params.article_id,
            article_property_id = self.search_params.article_property_id,
            order_by = self.search_params.order_by,

            fetch_all = False,
            allow_empty_filter = True,
            keep_old_items = False,
            page = page,
            per_page = self.per_page
        )


    def __len__(self):
        """
        Returns the count of found properties
        """

        return self.article_properties.total or 0


    def __iter__(self):
        """
        Iterate over all found items
        """

        if not self.article_properties.pages:
            return

        for page in range(1, self.article_properties.pages + 1):
            if not self.article_properties.page == page:
                self.load_page(page = page)
            for article in self.article_properties:
                yield article


    def __getitem__(self, key):
        """
        Returns the requested property from the pool of found properties
        """

        # List-Ids
        all_list_ids = range(len(self))
        requested_list_ids = all_list_ids[key]
        is_list = isinstance(requested_list_ids, list)
        if not is_list:
            requested_list_ids = [requested_list_ids]
        assert isinstance(requested_list_ids, list)

        result = []

        for list_id in requested_list_ids:

            # In welcher Seite befindet sich die gewünschte ID?
            for page_nr in range(1, self.article_properties.pages + 1):
                max_list_id = (page_nr * self.article_properties.per_page) - 1
                if list_id <= max_list_id:
                    page = page_nr
                    break
            else:
                raise AssertionError()

            # Load page if neccessary
            if not self.article_properties.page == page:
                self.load_page(page = page)

            # Add equested article-property to result
            list_id_in_page = list_id - ((page - 1) * self.article_properties.per_page)
            result.append(self.article_properties[list_id_in_page])

        if is_list:
            return result
        else:
            return result[0]



