# Anubis
An online judge platform.

## Prerequisites

* [Python 3.5+](https://www.python.org/downloads/)
* [MongoDB 3.0+](https://docs.mongodb.org/manual/installation/)
* [Node.js 6.0+](https://nodejs.org/en/download/package-manager/)
* [RabbitMQ](http://www.rabbitmq.com/)
* [Redis](https://redis.io/download)

## Install requirements

In the root of the repository, where `Pipfile` and `package.json` locates:

```bash
pipenv install  # You may have to install pipenv
npm install   # cnpm install
```

You don't need root privilege to run `npm install`. It installs stuffs in the project directory.

You may want to use [cnpm](https://npm.taobao.org/) and [tuna](https://pypi.tuna.tsinghua.edu.cn/)
if you are in China. Make sure to use `cnpm` by adding `alias` to `npm` instead of installing cnpm cli-tool.

Some requirements may need `Python.h`. In Ubuntu/Debian simply use

```bash
apt install python3-dev
```

to solve the problem.

### IP Geo-Location

To enable IP geo-location translation, you need to obtain a [MaxMind GeoLite City DB](http://dev.maxmind.com/geoip/geoip2/geolite2/) and put it in the project root directory:

```bash
curl "http://geolite.maxmind.com/download/geoip/database/GeoLite2-City.mmdb.gz" | gunzip -c > GeoLite2-City.mmdb
```

You may also want to install [libmaxminddb](https://github.com/maxmind/libmaxminddb/blob/master/README.md) for higher performance.

## Development

In the root of the repository:

```bash
npm run build   # or: npm run build:watch
python3 -m anubis.server --debug
```

> Set `--listen` (default: http://127.0.0.1:8888) to listen on a different address.

As an intuitive example, you may want to add a super administator and a problem to start:

```bash
alias pm="python3 -m"
pm anubis.model.user add 1 admin 12345 acm@sut.edu.cn
pm anubis.model.user set_superadmin 1
pm anubis.model.adaptor.problem add system "Dummy Problem" "# It *works*" -1 1000   # you can also use web UI
```
### Watch and Restart

Frontend source codes can be recompiled automatically by running:

```bash
npm run build:watch
```

However you need to manually restart the server for server-side code to take effect.

## Production

```bash
npm run build:production
python3 -m anubis.server --listen=unix:/var/run/anubis.sock
```

* Set `--listen` (default: http://127.0.0.1:8888) to listen on a different address.
* Set `--prefork` (default: 1) to specify the number of worker processes.
* Set `--ip-header` (default: '') to use IP address in request headers.
* Set `--url-prefix` (default: http://acm.sut.edu.cn) to set URL prefix.
* Set `--cdn-prefix` (default: /) to set CDN prefix.
* Set `--smtp-host`, `--smtp-user` and `--smtp-password` to specify a SMTP server.
* Set `--db-host` (default: localhost) and/or `--db-name` (default: test) to use a different
  database.

Better to use a reverse proxy like Nginx or h2o.

## Judging

To enable Anubis to judge, at least one judge user and one judge daemon instance are needed.

* Use following commands to create a judge user:

```bash
alias pm="python3 -m"
pm anubis.model.user add 2 judge 123456 judge@example.org
pm anubis.model.user set_judge 2
```

* See [YamaJudge](https://github.com/KawashiroNitori/YamaJudge) for more details about the judge daemon.
