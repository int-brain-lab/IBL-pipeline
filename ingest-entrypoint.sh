#! /bin/sh

# ingest entrypoint script
# ======================== 

# globals
# -------

dbdump="/tmp/dump.sql.gz"
dbcreated="/src/alyx/alyx/db_created"
dbloaded="/src/alyx/alyx/db_loaded"
sucreated="/src/alyx/alyx/superuser_created"

err_exit() { echo "error: $*"; exit 1; }

# checks
# ------

[ -z "$PGUSER" ] && err_exit "PGUSER unset";
[ -z "$PGHOST" ] && err_exit "PGPASSWORD unset";
[ -z "$PGPASSWORD" ] && err_exit "PGPASSWORD unset";

# fetchdump
# ---------

fetchdump() {
	echo "=> fetching dbdump for ${ALYX_DL_DATE}";

	mv -f ${dbdump} ${dbdump}.prev >/dev/null 2>&1;

	wget -q -O ${dbdump} \
		--user "$ALYX_DL_USER" \
		--password "$ALYX_DL_PASSWORD" \
	http://ibl.flatironinstitute.org/json/${ALYX_DL_DATE}_alyxfull.sql.gz
}

# mkdb
# ----

mkdb() {
	if [ -f "${dbcreated}" ]; then
		echo '# => using existing database';
	else
		echo '# ==> creating database';

		[ ! -f "${dbdump}" ] \
			&& err_exit ".. no database dump in $dbdump";

		createdb alyx_old;
		createdb alyx;

		touch ${dbcreated};
	fi
}

# loaddb
# ------

loaddb() {
	if [ -f "${dbloaded}" ]; then
		echo '# => database loaded - skipping load.';
	else
		echo "# => loading database ${dbdump}"
		gzip -dc ${dbdump} |psql -d alyx;
		touch ${dbloaded};
	fi
}

# configure alyx/django
# ---------------------

alyxcfg() {
	echo '# => configuring alyx'

	if [ ! -f "$sucreated" ]; then
	
		echo '# ==> configuring settings_secret.py'

		# custom settings_secret for multiple DBs
		# see also :alyx/alyx/alyx/settings_secret_template.py

		cnf="/src/alyx/alyx/alyx/settings_secret.py";
		sed \
			-e "s/%SECRET_KEY%/0xdeadbeef/" \
			-e "s/%DBNAME%/alyx/" \
			-e "s/%DBUSER%/$PGUSER/" \
			-e "s/%DBPASSWORD%/$PGPASSWORD/" \
			-e "s/127.0.0.1/$PGHOST/" \
			>  $cnf <<-EOF

		SECRET_KEY  = '%SECRET_KEY%'

		DATABASES  = {
		    'default': {
		        'ENGINE': 'django.db.backends.postgresql_psycopg2',
		        'NAME': '%DBNAME%',
		        'USER': '%DBUSER%',
		        'PASSWORD': '%DBPASSWORD%',
		        'HOST': '127.0.0.1',
		        'PORT': '5432',
		    },
		    'old': {
		        'ENGINE': 'django.db.backends.postgresql_psycopg2',
		        'NAME': '%DBNAME%_old',
		        'USER': '%DBUSER%',
		        'PASSWORD': '%DBPASSWORD%',
		        'HOST': '127.0.0.1',
		        'PORT': '5432',
		    }
		}
		
		EMAIL_HOST = 'mail.superserver.net'
		EMAIL_HOST_USER = 'alyx@awesomedomain.org'
		EMAIL_HOST_PASSWORD = 'UnbreakablePassword'
		EMAIL_PORT = 587
		EMAIL_USE_TLS = True
		
EOF
	
		echo '# ==> creating alyx superuser'
	
		/src/alyx/alyx/manage.py createsuperuser \
			--no-input \
			--username admin \
			--email admin@localhost
	
		echo '# ==> setting alyx superuser password'
	
		# note on superuser create: 
		#
		# - no-input 'createsuperuser' creates without password
		# - cant set password from cli here or in setpassword command
		# - so script reset via manage.py shell
		# - see also: 
		#   https://stackoverflow.com/questions/6358030/\
		#     how-to-reset-django-admin-password
	
		/src/alyx/alyx/manage.py shell <<-EOF
	
		from django.contrib.auth import get_user_model
		User = get_user_model()
		admin = User.objects.get(username='admin')
		admin.set_password('$PGPASSWORD')
		admin.save()
		exit()
EOF

		touch ${sucreated};
	fi

}

# alyxprep
# --------

alyxprep() {
	echo "# => alyxprep"
	/src/alyx/alyx/manage.py makemigrations;
	/src/alyx/alyx/manage.py migrate;
}

# alyxstart
# ---------

alyxstart() {
	echo '# => starting alyx'
	/src/alyx/alyx/manage.py runserver --insecure 0.0.0.0:8888;
}

# renamedb
# --------

renamedb() {
	echo "# => renaming databases:";

	echo "# ==> ... dropping alyx_old"; 
	dropdb alyx_old || err_exit "couldn't drop alyx_old";

	echo "# ==> ... renaming alyx to alyx_old"; 
	psql -c 'alter database alyx rename to alyx_old;' \
			> /dev/null \
		|| err_exit "couldn't rename alyx to alyx_old";

	echo "# ==> ... creating new alyx"; 
	createdb alyx || err_exit "couldn't rename alyx to alyx_old";

	rm -f ${dbloaded};
	rm -f ${sucreated};

	echo "# => ok.";
}


# init
# ----
# perform all initialization steps

init() {
	fetchdump;
	mkdb;
	loaddb;
	alyxcfg;
	alyxprep;
}


# www 
# ---
# initialize environment and run alyx web 

www() {
	init;
	alyxstart;
}

# dev
# ---
# initialize environment and wait indefinitely

dev() {
	init;
	exec tail -f /dev/null;
} 

# _start:

case "$1" in
	"fetchdump") fetchdump;;
	"mkdb") mkdb;;
	"loaddb") loaddb;;
	"alyxcfg") alyxcfg;;
	"alyxprep") alyxprep;;
	"alyxstart") alyxstart;;
	"renamedb") renamedb;;
	"www") www;;
	"dev") dev;;
	"sh") exec /bin/sh -c "$*";;
	"help") \
		echo "usage: `basename $0` [fetchdump|mkdb|loaddb|alyxcfg|alyxprep|alyxstart|renamedb|www|dev|sh]";;
	*) ;; # ... sourceable
esac

