"""
Container health check for the Lanvex Core image, for whichever role the container runs:

  core     the web application answers on port 8080
  worker   a background worker of this container is registered in Redis. RQ keeps that registration
           alive with heartbeats and drops it when the worker stops, so a hung or dead worker fails.
  manage   (one-off commands) always healthy

The role is read from the container's main process, so the check works with or without Compose.
"healthcheck.py core|worker" checks one role explicitly.
"""
import socket
import sys
import urllib.request

WEB_URL = 'http://127.0.0.1:8080/core/login/'


def running_role(cmdline='/proc/1/cmdline'):
    try:
        with open(cmdline, 'rb') as f:
            args = [a for a in f.read().split(b'\0') if a]
    except OSError:
        return 'other'
    if any(a.endswith(b'gunicorn') for a in args):
        return 'core'
    if b'rqworker' in args:
        return 'worker'
    return 'other'


def web_answers():
    with urllib.request.urlopen(WEB_URL, timeout=4) as response:
        return response.status == 200


def worker_registered():
    import redis

    sys.path.insert(0, '/opt/lanvex-core/netbox')
    from lanvex_configuration import REDIS  # reads the same environment as Lanvex Core itself

    tasks = REDIS['tasks']
    connection = redis.Redis(
        host=tasks['HOST'], port=tasks['PORT'], password=tasks['PASSWORD'] or None, db=tasks['DATABASE'],
        socket_timeout=4, socket_connect_timeout=4,
    )
    me = socket.gethostname().encode()
    # hget returns None for registrations whose key has already expired.
    return any(connection.hget(key, 'hostname') == me for key in connection.smembers('rq:workers'))


def main():
    role = sys.argv[1] if len(sys.argv) > 1 else running_role()
    try:
        healthy = {'core': web_answers, 'worker': worker_registered}.get(role, lambda: True)()
    except Exception as e:
        print(f'{role}: {e}')
        return 1
    print(f'{role}: {"healthy" if healthy else "not healthy"}')
    return 0 if healthy else 1


if __name__ == '__main__':
    sys.exit(main())
