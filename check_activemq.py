#!/usr/bin/env python
# -*- coding: utf-8 *-*

import urllib
import json
import argparse
#import logging
import fnmatch
import nagiosplugin as np

"""Check the size of a given ActiveMQ Queue."""

#_log = logging.getLogger('nagiosplugin')

def make_url(args, dest):
	return 'http://'+args.user+':'+args.pwd+'@'+args.host+':'+str(args.port)+'/api/jolokia/read/'+dest

def query_url(args):
	return make_url(args, 'org.apache.activemq:type=Broker,brokerName=localhost')

def queue_url(args, queue):
	return make_url(args, 'org.apache.activemq:type=Broker,brokerName=localhost,destinationType=Queue,destinationName='+queue)

def topic_url(args, topic):
	return make_url(args, 'org.apache.activemq:type=Broker,brokerName=localhost,destinationType=Topic,destinationName='+topic)


def queuesize(args):

	class ActiveMqScalarContext(np.ScalarContext):
		def evaluate(self, metric, resource):
			if metric.value < 0:
				return self.result_cls(np.Critical, "FAIL", metric)
			if not self.critical.match(metric.value):
				return self.result_cls(np.Critical, self.critical.violation, metric)
			elif not self.warning.match(metric.value):
				return self.result_cls(np.Warn, self.warning.violation, metric)
			else:
				return self.result_cls(np.Ok, None, metric)

	class ActiveMqQueueSize(np.Resource): # Check ALL queues of the server
		def __init__(self, pattern=None):
			self.pattern = pattern
		def probe(self):
			try:
				jsn = urllib.urlopen(query_url(args))
				resp = json.loads(jsn.read())
				for queue in resp['value']['Queues']:
						jsn = urllib.urlopen(make_url(args, queue['objectName']))
						qJ = json.loads(jsn.read())['value']
						if qJ['Name'].startswith('ActiveMQ'):
							continue # skip internal ActiveMQ queues
						if self.pattern and fnmatch.fnmatch(qJ['Name'], self.pattern) or not self.pattern:
							yield np.Metric('Queue Size of %s' % qJ['Name'],
														qJ['QueueSize'], min=0,
														context='size')
			except IOError as e:
				#_log.error('Network fetching FAILED. ' + str(e))
				yield np.Metric('Network fetching FAILED.', -1, context='size')
			except ValueError as e:
				#_log.error('Decoding Json FAILED. ' + str(e))
				yield np.Metric('Decoding Json FAILED.', -1, context='size')
			except KeyError as e:
				#_log.error('Loading Queue(s) FAILED. ' + str(e))
				yield np.Metric('Loading Queue(s) FAILED.', -1, context='size')

	if args.queue:
		check = np.Check(
				ActiveMqQueueSize(args.queue), ## check ONE queue
				ActiveMqScalarContext('size', args.warn, args.crit)
			)
		check.main()
	else:
		check = np.Check(
				ActiveMqQueueSize(), # check ALL queues
				ActiveMqScalarContext('size', args.warn, args.crit)
			)
		check.main()

def health(args):
	#global username, password, host, port
	pass

def subscriber(args):
	#global username, password, host, port
	pass




@np.guarded
def main():

	# Top-level Argument Parser & Subparsers Initialization
	parser = argparse.ArgumentParser(description = __doc__)
	connection = parser.add_argument_group('Connection')
	connection.add_argument('--host', default='localhost',
			help='ActiveMQ Server Hostname (default: %(default)s)')
	connection.add_argument('--port', type=int, default=8161,
			help='ActiveMQ Server Port (default: %(default)s)')
	credentials = parser.add_argument_group('Credentials')
	credentials.add_argument('-u', '--user', default='admin',
			help='Username for ActiveMQ admin account. (default: %(default)s)')
	credentials.add_argument('-p', '--pwd', default='admin',
			help='Password for ActiveMQ admin account. (default: %(default)s)')
	subparsers = parser.add_subparsers()

	# Sub-Parser for queuesize
	parser_queuesize = subparsers.add_parser('queuesize', help='Check QueueSize')
	parser_queuesize.add_argument('-w', '--warn', metavar='WARN', type=int, default=10,
			help='Warning if Queue Size is greater. (default: %(default)s)')
	parser_queuesize.add_argument('-c', '--crit', metavar='CRIT', type=int, default=100,
			help='Critical if Queue Size is greater. (default: %(default)s)')
	parser_queuesize.add_argument('queue', nargs='?',
			help='''Name of the Queue that will be checked.
			        If left empty, all Queues will be checked.
			        This also can be a Unix shell-style Wildcard
			        (much less powerful than a RegEx)
			        where * and ? can be used.''')
	parser_queuesize.set_defaults(func=queuesize)

	# Sub-Parser for health
	parser_health = subparsers.add_parser('health', help='Check Health')
	# no additional arguments necessary
	parser_health.set_defaults(func=health)

	# Sub-Parser for subscriber
	parser_subscriber = subparsers.add_parser('subscriber', help='Check Subscriber')
	parser_subscriber.add_argument('--clientId', required=True)
	parser_subscriber.add_argument('--topic', required=True)
	parser_subscriber.set_defaults(func=subscriber)

	# Evaluate Arguments
	args = parser.parse_args()
	# call the determined function with the parsed arguments
	args.func(args)

if __name__ == '__main__':
	main()

