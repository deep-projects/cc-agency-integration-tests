import json
import os
from statistics import mean

import requests
from multiprocessing import Lock
from multiprocessing.pool import ThreadPool

from experiment_check import get_batches, get_state_dict, get_username_pw, get_arguments


BAR_WIDTH = 70


def main():
    args = get_arguments('Shows the result of all batches.')

    username, pw = get_username_pw()

    detailed_result = get_detailed_result(args.agency, args.experiment, username, pw)
    print('state dict: {}'.format(detailed_result['states']))
    print('total time: {}'.format(detailed_result['totalTime']))

    mean_scheduled_duration = mean(get_state_durations(detailed_result['batchHistories'], 'scheduled'))
    mean_processing_duration = mean(get_state_durations(detailed_result['batchHistories'], 'processing'))
    print('mean scheduled duration: {}'.format(mean_scheduled_duration))
    print('mean processing duration: {}'.format(mean_processing_duration))


def get_total_time(batch_list):
    start_time = batch_list[0]['history'][0]['time']
    end_time = start_time
    for history in batch_list:
        history_start_time = min(history['history'], key=lambda he: he['time'])['time']
        if history_start_time < start_time:
            start_time = history_start_time

        history_end_time = max(history['history'], key=lambda he: he['time'])['time']
        if history_end_time > end_time:
            end_time = history_end_time

    return end_time - start_time


def get_state_durations(batch_list, state):
    return list(map(lambda batch: get_state_duration(batch['history'], state), batch_list))


def get_state_duration(history, state):
    begin_time = None
    for history_entry in history:
        if state == history_entry['state']:
            begin_time = history_entry['time']

    if begin_time is None:
        raise ValueError('Could not find time of state "{}"'.format(state))

    next_time = min(filter(lambda he: he['time'] > begin_time, history), key=lambda he: he['time'])['time']
    return next_time - begin_time


def get_detailed_result(agency, experiment_id, username, pw):
    batches = get_batches(agency, username, pw, experiment_id)

    state_dict = get_state_dict(batches)

    cache_filename = 'cache/{}.json'.format(experiment_id)
    if os.path.isfile(cache_filename):
        # read cache
        print('reading {} from cache'.format(experiment_id), flush=True)
        with open(cache_filename, 'r') as cache_file:
            batch_list = json.load(cache_file)
    else:
        batch_list = fetch_batches(batches, agency, username, pw)

        # create cache
        if not os.path.isdir('cache'):
            os.mkdir('cache')

        with open(cache_filename, 'w') as cache_file:
            json.dump(batch_list, cache_file)

    batch_histories = []
    mount = False
    for batch in batch_list:
        if 'mount' in batch:
            mount = batch['mount']

        if batch['history']:
            batch_history = []
            for history_entry in batch['history']:
                batch_history.append({'state': history_entry['state'], 'time': history_entry['time']})
            batch_histories.append({'history': batch_history, 'node': batch['node']})

    return {
        'experimentId': experiment_id,
        'states': state_dict,
        'batchHistories': batch_histories,
        'totalTime': get_total_time(batch_list),
        'mount': mount
    }


class BatchFetcher:
    def __init__(self, agency, username, password, num_batches):
        self.agency = agency
        self.username = username
        self.password = password
        self.num_batches = num_batches
        self.lock = Lock()
        self.counter = 0

    def __call__(self, batch):
        result = requests.get(
            os.path.join(self.agency, 'batches', batch['_id']),
            auth=(self.username, self.password)
        ).json()
        with self.lock:
            self.counter += 1

        percentage = self.counter / self.num_batches

        format_string = 'fetching batches: [{{:<{}}}/{{:<{}}}][{{:-<{}}}]'.format(
            len(str(self.num_batches)),
            len(str(self.num_batches)),
            BAR_WIDTH
        )

        print(
            format_string.format(self.counter, self.num_batches, '#' * int(percentage * BAR_WIDTH)),
            end='\n' if self.counter == self.num_batches else '\r',
            flush=True
        )
        return result


def fetch_batches(batches, agency, username, pw):
    with ThreadPool(5) as p:
        batch_list = list(p.map(BatchFetcher(agency, username, pw, len(batches)), batches))

    return batch_list


if __name__ == '__main__':
    main()
