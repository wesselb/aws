import argparse
import time

import numpy as np
import wbml.out as out

import aws
import aws.experiment as experiment

parser = argparse.ArgumentParser()
parser.add_argument('--spawn', type=int)
parser.add_argument('--kill', action='store_true')
parser.add_argument('--start', action='store_true')
args = parser.parse_args()

experiment.config['ssh_user'] = 'ubuntu'
experiment.config['ssh_pem'] = '~/.ssh/ConvNP.pem'
experiment.config['ssh_setup_commands'] = [
    ['cd', '/home/ubuntu/.julia/dev/ConvCNPs'],
    ['export', 'JULIA=~/julia-1.3.1/bin/julia']
]

with out.Section('Starting all stopped instances'):
    aws.start_stopped()

if args.spawn:
    with out.Section('Spawning instances'):
        experiment.spawn(image_id='ami-0d9c1e5ad46520d40',
                         total_count=args.spawn,
                         instance_type='p3.2xlarge',
                         key_name='ConvNP',
                         security_group='launch-wizard-1')

while not aws.check_all_running():
    out.out('Waiting for all instances to be running...')
    time.sleep(5)

out.out('Waiting a minute for all instances to have booted...')
time.sleep(60)

if args.kill:
    with out.Section('Killing all experiments'):
        experiment.kill_all()

if args.start:
    configs = []
    for model, datas, losses in [
        ('convcnp',
         ('eq', 'matern52', 'noisy-mixture', 'weakly-periodic', 'sawtooth'),
         ('loglik',)),
        ('convnp',
         ('eq', 'matern52', 'noisy-mixture', 'weakly-periodic', 'sawtooth'),
         ('loglik', 'loglik-iw', 'elbo')),
        ('anp',
         ('eq', 'matern52', 'noisy-mixture', 'weakly-periodic', 'sawtooth'),
         ('loglik', 'loglik-iw', 'elbo')),
        ('np',
         ('eq', 'matern52', 'noisy-mixture', 'weakly-periodic', 'sawtooth'),
         ('loglik', 'loglik-iw', 'elbo'))
    ]:
        for data in datas:
            for loss in losses:
                configs.append({'model': model, 'data': data, 'loss': loss})
    num_instances = len(aws.get_running_ips())
    pieces = np.array_split(configs, num_instances)

    with out.Section('Starting experiments'):
        out.kv('Number of configs', len(configs))
        out.kv('Number of instances', num_instances)
        out.kv('Runs per instance', max([len(piece) for piece in pieces]))
        experiment.ssh_map(*[
            [
                ['git', 'pull'],
                ['rm', '-rf', 'log', 'models', 'output'],
                ['mkdir', 'models', 'output'],
                *[[
                    './train.sh',
                    '--model', config['model'],
                    '--data', config['data'],
                    '--loss', config['loss'],
                    '2>&1', '|', 'tee', '-a', 'log',
                ] for config in configs],
                ['logout']
            ]
            for configs in pieces
        ], in_tmux=True, start_tmux=True)

while True:
    out.kv('Instances still running', len(aws.get_running_ips()))
    experiment.print_logs(path='log')
    experiment.sync(sources=['/home/ubuntu/.julia/dev/ConvCNPs/models',
                             '/home/ubuntu/.julia/dev/ConvCNPs/output'],
                    target='scripts/convnp_bake-off')
    experiment.shutdown_finished()
    out.out('Sleeping for two minutes...')
    time.sleep(2 * 60)
