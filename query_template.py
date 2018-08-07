# -*- coding: utf-8 -*-
import sys
import json
import logging
import datetime
import configparser
import requests


start = datetime.datetime.now()
logger = logging.getLogger(__name__)
session = requests.Session()


def end():
    """ Calclate and log the elapsed run time """
    end_time = datetime.datetime.now()
    logger.info('Ended at: %s', end_time)
    logger.info('Elapsed time: %s', end_time-start)


def get(url, **kwargs):
    """Get the URL log exceptions"""
    built_request = requests.Request('get', url, params=kwargs)
    prepped_request = session.prepare_request(built_request)
    try:
        return session.send(prepped_request)
    except requests.exceptions.RequestException as requests_error:
        logger.error('%s: %s', requests_error.__class__.__name__, requests_error)
        return prepped_request


def decode_json(response):
    """Decode JSON log exceptions"""
    try:
        return response.json()
    except json.decoder.JSONDecodeError:
        logger.error('Failed to decode JSON for: %s', response.url)
        return False


def status_ok(response):
    """Check returned status code"""
    if response.status_code == 401:
        message_401 = 'The server returned 401 unauthorized. Check your API key.'
        logger.error(message_401)
        if response.text:
            logger.debug('Server response: %s', response.text)
        end()
        sys.exit(message_401)
    if response.status_code // 100 != 2:
        logger.error('Recieved status code %s for: %s', response.status_code, response.url)
        if response.text:
            logger.debug('Server response: %s', response.text)
        return False
    return True


def retry(response, url, attempt_count=3, **kwargs):
    """Retry the query if anything goes wrong"""
    retry_attempts = 0
    while ((not isinstance(response, requests.models.Response)
            or status_ok(response) is False
            or decode_json(response) is False)
           and retry_attempts < attempt_count):
        logger.info('Retry attemt %s of %s for: %s', retry_attempts+1, attempt_count, response.url)
        response = get(url, **kwargs)
        retry_attempts += 1

    # Return False for failed queries
    if retry_attempts == attempt_count:
        logger.error('Failed %s times to successfully query: %s', attempt_count, response.url)
        return False

    # If the query was retried log the number of attempts
    if retry_attempts != 0:
        logger.info('Recovered after %s attempts for: %s', retry_attempts, response.url)

    logger.debug('Successfully queried: %s', response.url)
    return decode_json(response)


def query_api(url, **kwargs):
    """Query the API"""
    response = retry(get(url, **kwargs), url, **kwargs)
    return response


def main():
    """The main script logic"""

    # Setup logging
    log_format = '%(asctime)s: %(levelname)s: %(name)s: %(message)s'
    datefmt = '%Y-%m-%d %H:%M:%S'
    logging.basicConfig(filename='logs.txt', level=logging.INFO, format=log_format, datefmt=datefmt)

    logger.info('Started querying at: %s', start)

    # Specify the config file to read from
    config_file = 'api.cfg'
    config = configparser.RawConfigParser()
    config.read_file(open(config_file))
    api_key = config.get('Main', 'api_key')
    api_key = str.strip(api_key)
    hostname = config.get('Main', 'hostname')
    hostname = str.strip(hostname)

    # Setup session object
    auth_param = {'api_key': api_key}
    session.params.update(auth_param)

    # Base URL to query
    base_url = 'https://{}/api/v2/search/submissions'.format(hostname)

    query = '1.2.3.4'
    offset = 0
    while True:
        response = query_api(base_url, q=query, offset=offset, limit=10)
        items_per_page = response['data']['items_per_page']
        current_item_count = response['data']['current_item_count']
        offset += items_per_page

        # PROCESS RESULTS

        items = response['data']['items']
        for item in items:
            item = item['item']
            print(item['sample'])

        # Stop pagination
        if current_item_count != items_per_page:
            break
    end()


if __name__ == "__main__":
    main()
