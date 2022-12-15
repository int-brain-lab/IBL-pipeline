#!/bin/bash --login

# IBL Ingestion Entrypoint Script
# ===============================
set -e
script_cmd="${BASH_SOURCE[0]}"
script_file=$(basename "${script_cmd}")
SHOW_HELP=false
OPS_SEQ=()
POPULATE_TASK=ingest
POPULATE_ARGS=()

[[ -z "$CONDA_ENV_USER" ]] && CONDA_ENV_USER=base
[[ -z "${IBL_PATH_ROOT}" ]] && IBL_PATH_ROOT=/int-brain-lab

show_help() {
	echo "usage: $script_file FUNC/ROUTINE [OPTION]... [-- EXEC_CMD]

Entrypoint for ingestion routines or dev mode

Functions:

configure ........ Set configuration files for Alyx, ONE, and DataJoint. Use one of the
                   following options after:
                     --all, -a
                     --django, --alyx
                     --one
                     --datajoint
populate ......... Run the python script '/usr/local/bin/populate'.
                   Can pass args to script if args are specified after 'populate'.
                   See examples section below.
terminate ........ Terminate all running database connection jobs.
dev .............. Wait indefinitely.

Environment Variables:

  IBL_PATH_ROOT=${IBL_PATH_ROOT}
  ALYX_SRC_PATH=${ALYX_SRC_PATH}

Examples:

 Start a dev container
   > $script_file dev

 Initialize configuration for Django, ONE and DataJoint
   > $script_file configure

 Run a populate task
   > $script_file populate behavior -b 5 --duration=0.5
"
	exit 0
}

raise_except() {
	set -e
	local exit_code=$1
	shift
	if [[ $exit_code ]]; then
		if ((exit_code > 0)); then
			printf '\n%s exited with error code %s: %s\n' "$script_file" "$exit_code" "$@" >&2
			exit "$exit_code"
		elif ((exit_code == -1)); then
			printf '\nSTATUS: %s\n\n' "$@" >&2
		elif ((exit_code == -2)); then
			printf '\nWARNING: %s\n\n' "$@" >&2
		elif ((exit_code < -2)); then
			printf '\n%s\n\n' "$@" >&2
		fi
	fi
}

run_function_seq() {
	local fn
	if [[ $# -gt 0 ]]; then
		echo "# > operation sequence: $*"
		for fn in "$@"; do
			echo "# >> ${fn}()"
			$fn
		done
	fi
}

while [[ $# -gt 0 ]]; do
	case "$1" in
	"help" | "--help" | "-h")
		SHOW_HELP=true
		break
		;;
	"dev")
		OPS_SEQ+=("run_dev")
		shift
		;;
	"configure")
		shift
		for _arg in "$@"; do
			case "$1" in
			--all | -a)
				OPS_SEQ+=("config_django" "config_one_params" "config_datajoint")
				shift
				break
				;;
			--django | --alyx)
				OPS_SEQ+=("config_django")
				shift
				;;
			--one)
				OPS_SEQ+=("config_one_params")
				shift
				;;
			--datajoint)
				OPS_SEQ+=("config_datajoint")
				shift
				;;
			esac
		done
		;;
	"populate")
		OPS_SEQ+=("run_populate")
		shift
		for _arg in "$@"; do
			case "$1" in
			ingest | behavior | wheel | ephys)
				POPULATE_TASK="$1"
				shift
				;;
			--duration=* | --backtrack=* | --sleep=* | --xtable=* | --xplots)
				echo "populate.py arg: '$1'"
				POPULATE_ARGS+=("$1")
				shift
				;;
			-d)
				echo "populate.py arg: '-d $2'"
				POPULATE_ARGS+=("--duration=$2")
				shift
				shift
				;;
			-b)
				echo "populate.py arg: '-b $2'"
				POPULATE_ARGS+=("--backtrack=$2")
				shift
				shift
				;;
			-s)
				echo "populate.py arg: '-s $2'"
				POPULATE_ARGS+=("--sleep=$2")
				shift
				shift
				;;
			-x)
				echo "populate.py arg: '-x $2'"
				POPULATE_ARGS+=("--xtable=$2")
				shift
				shift
				;;
			esac
		done
		;;
	"terminate")
		OPS_SEQ+=("terminate_jobs")
		shift
		;;
	"--")
		shift
		echo "Other command: $*"
		break
		;;
	*)
		raise_except -2 "Unknown option: $1"
		shift
		;;
	esac
done

# show help if asked
# ------------------

[[ ${SHOW_HELP} = true ]] && show_help

run_dev() {
	echo "=============================================================================="
	echo "# => Starting development environment..."
	while :; do
		sleep 10
	done
}

config_django() {
	echo "=============================================================================="
	echo "# => Configuring Alyx/Django settings.py"
	[[ -n "${PGPASSWORD}" ]] ||
		raise_except $? "database password environment variable PGPASSWORD is not set"

	[[ -n "${ALYX_SRC_PATH}" ]] ||
		raise_except $? "alyx source code path location ALYX_SRC_PATH must exist"

	tmplcfg -vv \
		--env-file="${IBL_PATH_ROOT}/ibldatajoint.env" \
		--chmod=660 \
		-s "${ALYX_SRC_PATH}/alyx/alyx/settings_template.py"
}

config_one_params() {
	echo "=============================================================================="
	echo "# => Configuring ONE-api .one_params.json"
	LOGLEVEL=DEBUG ONE-connect --env-file="${IBL_PATH_ROOT}/ibldatajoint.env"
}

config_datajoint() {
	echo "=============================================================================="
	echo "# => Configuring DataJoint .datajoint_config.json"
	tmplcfg -vv \
		--env-file="${IBL_PATH_ROOT}/ibldatajoint.env" \
		--chmod=660 --allow-empty \
		-s "${IBL_PATH_ROOT}/.datajoint_config_template.json" \
		-t ~/.datajoint_config.json
}

run_populate() {
	echo "=============================================================================="
	echo "# => > populate.py $POPULATE_TASK ${POPULATE_ARGS[*]}"
	populate "${POPULATE_TASK}" "${POPULATE_ARGS[@]}"
}

terminate_jobs() {
	echo "=============================================================================="
	echo "# => Sending job termination request"
	populate terminate
}

# Start operations ---------------------------------------------------------------------

# switch to appropriate python environment
micromamba activate $CONDA_ENV_USER || true

# run sequence of operations specified by user
run_function_seq "${OPS_SEQ[@]}"

# run rest of command
exec "$@"
