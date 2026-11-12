"""
GraphQL Schema for FleetFlow.

Integrates Query, Mutation, and Subscription types.
"""

import strawberry
from strawberry.fastapi import GraphQLRouter

from src.graphql.resolvers import Mutation, Query
from src.graphql.subscriptions import Subscription

# Create the schema
schema = strawberry.Schema(
    query=Query,
    mutation=Mutation,
    subscription=Subscription,
)

# Create the GraphQL router for FastAPI
graphql_router = GraphQLRouter(
    schema,
    path="/graphql",
    graphql_ide="graphiql",  # Supported Strawberry GraphQL IDE option
)
