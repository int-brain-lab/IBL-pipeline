#! /bin/sh

# ingest entrypoint script
# ======================== 

# globals
# -------

dbdump="/dump.sql.gz"
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

	wget -O ${dbdump} \
		--user "$ALYX_DL_USER" \
		--password "$ALYX_DL_PASSWORD" \
	http://ibl.flatironinstitute.org/json/$${ALYX_DL_DATE}_alyxfull.sql.gz
}

# createdb
# --------

createdb() {
	if [ -f "${dbloaded}" ]; then
		echo '# => using existing database';
	else
		echo '#==> creating database';

		[ ! -f "${dbdump}" ] \
			&& err_exit ".. no database dump in $dbdump";

		createdb -U $PGUSER alyx;
	fi
}

# loaddb
# ------

loaddb() {
	echo "# => loading database ${dbdump}"
	gzip -dc ${dbdump} |psql -U postgres -d alyx;
	touch ${dbloaded};
}

# rotatedb
# --------

rotatedb() {
	echo "# => rotating databases";
	echo "# ==> NOT IMPLEMENTED"; 
}


# configure alyx/django
# ---------------------

alyxcfg() {
	echo '# => configuring alyx'

	if [ ! -f "$sucreated" ]; then
	
		echo '# ==> configuring settings_secret.py'
	
		sed \
			-e "s/%SECRET_KEY%/0xdeadbeef/" \
			-e "s/%DBNAME%/alyx/" \
			-e "s/%DBUSER%/$PGUSER/" \
			-e "s/%DBPASSWORD%/$PGPASSWORD/" \
			-e "s/127.0.0.1/$PGHOST/" \
			< /src/alyx/alyx/alyx/settings_secret_template.py \
			> /src/alyx/alyx/alyx/settings_secret.py
	
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
	/src/alyx/alyx/manage.py runserver --insecure 0.0.0.0:8000;
}

# run 
# ---
# create/load/etc full-command

run() {
	fetchdump;
	createdb;
	loaddb;
	alyxcfg;
	alyxprep;
	alyxstart;
}


# _start:

case "$1" in
	"fetchdump") fetchdump;;
	"createdb") createdb;;
	"loaddb") loaddb;;
	"alyxstart") alyxstart;;
	"sh") exec /bin/sh -c "$*";;
	*) run;;
esac

