QRY_USER_EXISTS = 'SELECT EXISTS (SELECT from pg_catalog.pg_roles WHERE rolname = $1)'
QRY_USER_CREATE = 'CREATE ROLE "{user}"'
QUERY_USER_ALTER = '''ALTER ROLE "{user}" WITH LOGIN PASSWORD '{password}' NOSUPERUSER NOCREATEDB NOCREATEROLE'''
QRY_TEMPLATE_EXISTS = 'SELECT EXISTS (SELECT FROM pg_database WHERE datname = $1 AND datistemplate = true)'
QRY_TEMPLATE_CREATE = 'CREATE DATABASE "{template_name}" OWNER "{user}"'
QRY_TEMPLATE_FINALIZE = 'UPDATE pg_database SET datistemplate = true WHERE datname=$1'
QRY_DB_CLONE = 'CREATE DATABASE "{db_name}" WITH TEMPLATE "{template_name}" OWNER "{user}"'
QRY_DB_DROP = 'DROP DATABASE IF EXISTS "{db_name}"'

# Hash migrations
# Do only once per hash

# lock = threading.Lock()
# lock.acquire(blocking=True, timeout=3)
# or with lock: ...
# from psycopg_pool import ConnectionPool
# ConnPostgres = psycopg.Connection[tuple[Any, ...]]
# _pool: ConnectionPool | None = None
# @contextmanager
# def connection(db_url: str) -> Iterator[generic.ConnPostgres]:
#     global _pool
#     if _pool is None:
#         _pool = ConnectionPool(db_url)
#     with _pool.connection() as conn:
#         yield conn
# SEARCH_PATHS = (['/usr/local/pgsql', '/usr/local'] +
#                 glob('/usr/pgsql-*') +  # for CentOS/RHEL
#                 glob('/usr/lib/postgresql/*') +  # for Debian/Ubuntu
#                 glob('/opt/local/lib/postgresql*'))  # for MacPorts
# class Postgresql(Database):
#     DEFAULT_SETTINGS = dict(auto_start=2,
#                             base_dir=None,
#                             initdb=None,
#                             initdb_args='-U postgres -A trust',
#                             postgres=None,
#                             postgres_args='-h 127.0.0.1 -F -c logging_collector=off',
#                             pid=None,
#                             port=None,
#                             copy_data_from=None)
#     subdirectories = ['data', 'tmp']
#     def initialize(self):
#         self.initdb = self.settings.pop('initdb')
#         if self.initdb is None:
#             self.initdb = find_program('initdb', ['bin'])
#         self.postgres = self.settings.pop('postgres')
#         if self.postgres is None:
#             self.postgres = find_program('postgres', ['bin'])
#     def dsn(self, **kwargs):
#         # "database=test host=localhost user=postgres"
#         params = dict(kwargs)
#         params.setdefault('port', self.settings['port'])
#         params.setdefault('host', '127.0.0.1')
#         params.setdefault('user', 'postgres')
#         params.setdefault('database', 'test')
#         return params
#     def url(self, **kwargs):
#         params = self.dsn(**kwargs)
#         url = ('postgresql://%s@%s:%d/%s' %
#                (params['user'], params['host'], params['port'], params['database']))
#         return url
#     def get_data_directory(self):
#         return os.path.join(self.base_dir, 'data')
#     def initialize_database(self):
#         if not os.path.exists(os.path.join(self.base_dir, 'data', 'PG_VERSION')):
#             args = ([self.initdb, '-D', os.path.join(self.base_dir, 'data'), '--lc-messages=C'] +
#                     self.settings['initdb_args'].split())
#             try:
#                 p = subprocess.Popen(args, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
#                 output, err = p.communicate()
#                 if p.returncode != 0:
#                     raise RuntimeError("initdb failed: %r" % err)
#             except OSError as exc:
#                 raise RuntimeError("failed to spawn initdb: %s" % exc)
#     def get_server_commandline(self):
#         return ([self.postgres,
#                  '-p', str(self.settings['port']),
#                  '-D', os.path.join(self.base_dir, 'data'),
#                  '-k', os.path.join(self.base_dir, 'tmp')] +
#                 self.settings['postgres_args'].split())
#     def poststart(self):
#         with closing(pg8000.connect(**self.dsn(database='postgres'))) as conn:
#             conn.autocommit = True
#             with closing(conn.cursor()) as cursor:
#                 cursor.execute("SELECT COUNT(*) FROM pg_database WHERE datname='test'")
#                 if cursor.fetchone()[0] <= 0:
#                     cursor.execute('CREATE DATABASE test')
#     def is_server_available(self):
#         try:
#             with closing(pg8000.connect(**self.dsn(database='template1'))):
#                 pass
#         except pg8000.Error:
#             return False
#         else:
#             return True
#     def terminate(self, *args):
#         # send SIGINT instead of SIGTERM
#         super(Postgresql, self).terminate(signal.SIGINT if os.name != 'nt' else None)
