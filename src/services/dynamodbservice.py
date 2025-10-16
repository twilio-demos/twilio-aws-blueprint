import json
from abc import ABC

import boto3
from botocore.exceptions import ClientError, TokenRetrievalError

from src.utils.logger import get_logger
from src.utils.env import AWS_REGION

logger = get_logger(__name__)


class DynamoDBService(ABC):
    """Base class for interacting with DynamoDB tables"""

    def __init__(self, name):
        self.table_name = name
        self.table = None
        try:
            self.dyn_resource = boto3.resource("dynamodb", region_name=AWS_REGION)
        except Exception as e:
            logger.error(
                "Unable to connect to DynamoDB",
                {"table_name": self.table_name, "error": e},
            )
            self.exists = False
        else:
            self.exists = self.load()

    def load(self):
        """
        Determines whether a table exists. As a side effect, stores the table in
        a member variable.

        :return: True when the table exists; otherwise, False.
        """
        try:
            table = self.dyn_resource.Table(self.table_name)
            table.load()
            exists = True
        except ClientError as err:
            if err.response["Error"]["Code"] == "ResourceNotFoundException":
                logger.error(
                    "Table does not exist in DynamoDB",
                    {
                        "table_name": self.table_name,
                    },
                )
                exists = False
            else:
                logger.error(
                    "Unable to load table from DynamoDB",
                    {
                        "table_name": self.table_name,
                        "error_code": err.response["Error"]["Code"],
                        "error_msg": err.response["Error"]["Message"],
                    },
                )
                exists = False
        except TokenRetrievalError as err:
            logger.error(
                "Token error trying to load table from DynamoDB",
                {
                    "table_name": self.table_name,
                    "error": err,
                },
            )
            exists = False
        else:
            self.table = table
        return exists

    def _add_item(self, data):
        """
        Adds an item to the table.
        """
        try:
            if not self.exists:
                logger.error(
                    "Table does not exist!",
                    {
                        "table_name": self.table_name,
                    },
                )
                return
            self.table.put_item(Item=self.object_to_dict(data))
        except ClientError as err:
            logger.error(
                "Unable to add item to table",
                {
                    "table_name": self.table_name,
                    "data": data,
                    "error_code": err.response["Error"]["Code"],
                    "error_msg": err.response["Error"]["Message"],
                },
            )

    def _get_item(self, key):
        """
        Gets an item from the table by key.
        """
        try:
            if not self.exists:
                logger.error(
                    "Table does not exist!",
                    {
                        "table_name": self.table_name,
                    },
                )
                return None
            response = self.table.get_item(Key=key)
        except ClientError as err:
            logger.error(
                "Unable to get item from table",
                {
                    "table_name": self.table_name,
                    "key": key,
                    "error_code": err.response["Error"]["Code"],
                    "error_msg": err.response["Error"]["Message"],
                },
            )
        else:
            return response["Item"]

    def _update_item(self, key, expression: str, expression_values):
        """
        Updates data in the table by key.
        """
        try:
            if not self.exists:
                logger.error(
                    "Table does not exist!",
                    {
                        "table_name": self.table_name,
                    },
                )
                return None
            self.table.update_item(
                Key=key,
                UpdateExpression=expression,
                ExpressionAttributeValues=expression_values,
            )
        except ClientError as err:
            logger.error(
                "Unable to update item in table",
                {
                    "table_name": self.table_name,
                    "key": key,
                    "expression": expression,
                    "expression_values": expression_values,
                    "error_code": err.response["Error"]["Code"],
                    "error_msg": err.response["Error"]["Message"],
                },
            )

    def _query(self, condition):
        """
        Queries for items based on the provided condition.
        """
        try:
            if not self.exists:
                logger.error(
                    "Table does not exist!",
                    {
                        "table_name": self.table_name,
                    },
                )
                return
            response = self.table.query(KeyConditionExpression=condition)
        except ClientError as err:
            logger.error(
                "Unable to query for items in the table",
                {
                    "table_name": self.table_name,
                    "condition": condition,
                    "error_code": err.response["Error"]["Code"],
                    "error_msg": err.response["Error"]["Message"],
                },
            )
        else:
            return response["Items"]

    def _delete_item(self, key):
        """
        Deletes an item from the table by key.
        """
        try:
            if not self.exists:
                logger.error(
                    "Table does not exist!",
                    {
                        "table_name": self.table_name,
                    },
                )
                return
            self.table.delete_item(Key=key)
        except ClientError as err:
            logger.error(
                "Unable to delete item from table",
                {
                    "table_name": self.table_name,
                    "key": key,
                    "error_code": err.response["Error"]["Code"],
                    "error_msg": err.response["Error"]["Message"],
                },
            )

    def object_to_dict(self, python_obj) -> dict:
        return json.loads(json.dumps(python_obj, default=lambda o: o.__dict__))
