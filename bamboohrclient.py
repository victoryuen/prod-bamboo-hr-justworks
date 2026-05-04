"""
bambooHrclient.py

interacting with the BambooHR API.

basic api class for clietn and get/post requests

Authentication:
    Uses HTTP Basic Auth with an API key as the username and a dummy
    password ('x'), as required by BambooHR.

Example:
    client = bambooHRClient(subdomain="mycompany", api_key="API_KEY")
    employees = client.get("employees/directory")

Notes:
    - API permissions are determined by the user tied to the API key
    - Some endpoints may return XML instead of JSON
    - For bulk data, consider using the BambooHR Reports API
"""

import requests
from requests.auth import HTTPBasicAuth
import json


class BambooHRClient:
    """
    Client for accessing the BambooHR API.

    Provides helper methods for making authenticated GET and POST
    requests to BambooHR endpoints.
    """

    def __init__(self, subdomain: str, api_key: str):
        """
        Initialize the BambooHR client.

        Args:
            subdomain (str): Your BambooHR company subdomain (e.g., 'mycompany')
            api_key (str): BambooHR API key
        """
        self.base_url = f"https://{subdomain}.bamboohr.com/api/v1"
        self.auth = HTTPBasicAuth(api_key, "x")
        self.headers = {
        "Accept": "application/json"
        }

    def get(self, endpoint: str, params: dict = None):
        """
        Send a GET request to a BambooHR API endpoint.

        Args:
            endpoint (str): API endpoint (e.g., 'employees/directory')
            params (dict, optional): Query parameters

        Returns:
            dict: Parsed JSON response

        Raises:
            Exception: If the request fails
        """
        url = f"{self.base_url}/{endpoint}"
        response = requests.get(url, auth=self.auth, params=params,headers=self.headers)
      
        if response.status_code != 200:
            raise Exception(f"GET {endpoint} failed: {response.status_code} - {response.text}")

        return response.json()

    def post(self, endpoint: str, data: dict = None):
        """
        Send a POST request to a BambooHR API endpoint.

        Args:
            endpoint (str): API endpoint
            data (dict, optional): JSON payload

        Returns:
            dict: Parsed JSON response (if any)

        Raises:
            Exception: If the request fails
        """
        url = f"{self.base_url}/{endpoint}"
        response = requests.post(url, auth=self.auth, json=data)

        if response.status_code not in [200, 201]:
            raise Exception(f"POST {endpoint} failed: {response.status_code} - {response.text}")

        return response.json() if response.text else {}
    
def get_timesheets(client : BambooHRClient, employee_id : int,start_date: str, end_date:str):

    time_sheet_info =  client.get("time_tracking/timesheet_entries",
               params={
                "start": start_date,
                "end" : end_date,
                "employeeIds": employee_id,
            }) 
    return time_sheet_info
    
    