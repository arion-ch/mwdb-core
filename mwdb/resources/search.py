from flask import g, request
from flask_restful import Resource
from luqum.parser import ParseError
from werkzeug.exceptions import BadRequest

from mwdb.core.deprecated import DeprecatedFeature, deprecated_endpoint
from mwdb.core.rate_limit import rate_limited_resource
from mwdb.core.search import SQLQueryBuilder, SQLQueryBuilderBaseException
from mwdb.model import Object
from mwdb.schema.object import ObjectListItemResponseSchema
from mwdb.schema.search import SearchRequestSchema

from . import loads_schema, requires_authorization


@rate_limited_resource
class SearchResource(Resource):
    @deprecated_endpoint(DeprecatedFeature.legacy_search)
    @requires_authorization
    def post(self):
        """
        ---
        summary: Search for objects (deprecated)
        description: |
            Returns objects found by Lucene query.

            Hard-limited to 10000 records.
            Use `query` argument in object get methods instead.

            Deprecated: use /object?query= instead
        deprecated: true
        security:
            - bearerAuth: []
        tags:
            - object
        requestBody:
            description: Search query
            content:
              application/json:
                schema: SearchRequestSchema
        responses:
            200:
                description: Resulting objects
                content:
                  application/json:
                    schema:
                      type: array
                      items:
                        $ref: '#/components/schemas/ObjectListItemResponse'
            400:
                description: When request body or query syntax is invalid
            503:
                description: |
                    Request canceled due to database statement timeout.
        """
        schema = SearchRequestSchema()
        obj = loads_schema(request.get_data(as_text=True), schema)

        query = obj["query"]
        try:
            result = (
                SQLQueryBuilder()
                .build_query(query)
                .filter(g.auth_user.has_access_to_object(Object.id))
                .order_by(Object.id.desc())
                .limit(10000)
            ).all()
        except SQLQueryBuilderBaseException as e:
            raise BadRequest(str(e))
        except ParseError as e:
            raise BadRequest(str(e))

        schema = ObjectListItemResponseSchema(many=True)
        return schema.dump(result)
